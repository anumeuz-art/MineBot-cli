import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time
import pytz
import html
from datetime import datetime, timedelta

import config
import database
import ai_generator
import watermarker
import comments_analyzer
import utils
import keyboards
import publisher

# Глобальный словарь для отслеживания последнего активного черновика каждого админа
user_current_draft_id = {}

def register_handlers(bot, user_drafts, album_cache):

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        greeting = utils.get_time_greeting()
        bot.send_message(message.chat.id, f"{greeting}! Бот готов к работе. Все настройки теперь в Панели Управления.", reply_markup=keyboards.get_main_menu())

    @bot.message_handler(content_types=['text', 'photo'])
    def handle_text_photo(message):
        if message.content_type == 'text':
            if message.text == "📝 Создать пост":
                bot.send_message(message.chat.id, "Отправь мне фото, текст или ссылку с описанием мода! 🚀", parse_mode="HTML")
                return

        if message.media_group_id:
            if message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
                bot.send_message(message.chat.id, "📸 Загружаю альбом...")
                threading.Timer(2.0, process_album, args=[message.media_group_id, message.chat.id, message.from_user.id]).start()
            album_cache[message.media_group_id].append(message)
            return

        process_single_message(message)

    def process_single_message(message):
        temp_in = f"in_{message.message_id}.jpg"
        temp_out = f"out_{message.message_id}.jpg"
        try:
            bot.send_chat_action(message.chat.id, 'upload_photo')
            user_input = message.caption if message.photo else message.text
            if not user_input and message.photo: user_input = "Опиши этот мод."
            elif not user_input: return
            
            # Берем язык из БД (теперь настраивается в Web App)
            persona = database.get_user_setting(message.from_user.id, 'persona', 'uz')
            generated_text = ai_generator.generate_post(user_input, persona)
            
            # Приклеиваем рекламу вручную здесь
            ad_text = database.get_global_setting('ad_text', '')
            if ad_text:
                generated_text += f"\n\n{ad_text}"
            
            photo_id = None
            
            if message.photo:
                bot.send_message(message.chat.id, "🎨 Обрабатываю фото...")
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                target_image = temp_out if os.path.exists(temp_out) else temp_in
                with open(target_image, 'rb') as f:
                    sent_msg = bot.send_photo(message.chat.id, f)
                    photo_id = sent_msg.photo[-1].file_id
                    bot.delete_message(message.chat.id, sent_msg.message_id) 
            else:
                bot.send_message(message.chat.id, "⏳ Генерирую пост...")

            # Берем активный канал из БД
            active_ch = database.get_user_setting(message.from_user.id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': photo_id, 'text': generated_text, 'document': None, 'ad_added': False, 'channel': active_ch}
            send_draft_preview(message.chat.id, message.from_user.id, draft)

        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка: {e}")
        finally:
            if os.path.exists(temp_in): os.remove(temp_in)
            if os.path.exists(temp_out): os.remove(temp_out)

    def process_album(media_group_id, chat_id, user_id):
        messages = album_cache.pop(media_group_id, None)
        if not messages: return
        messages.sort(key=lambda x: x.message_id)
        caption = next((m.caption for m in messages if m.caption), None)
        bot.send_message(chat_id, "🎨 Обрабатываю альбом...")
        
        persona = database.get_user_setting(user_id, 'persona', 'uz')
        generated_text = ai_generator.generate_post(caption or "Опиши мод", persona)
        
        temp_files = []
        opened_files = [] 
        try:
            for i, m in enumerate(messages):
                file_info = bot.get_file(m.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                tin, tout = f"in_{media_group_id}_{i}.jpg", f"out_{media_group_id}_{i}.jpg"
                with open(tin, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(tin, tout)
                target_img = tout if os.path.exists(tout) else tin
                temp_files.append((tin, target_img))
            
            media = []
            for tin, target_img in temp_files:
                f = open(target_img, 'rb')
                opened_files.append(f) 
                media.append(telebot.types.InputMediaPhoto(f))
            
            sent_msgs = bot.send_media_group(chat_id, media)
            photo_ids = [m.photo[-1].file_id for m in sent_msgs]
            photo_id_str = ",".join(photo_ids)
            for m in sent_msgs:
                try: bot.delete_message(chat_id, m.message_id)
                except: pass
            
            active_ch = database.get_user_setting(user_id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': photo_id_str, 'text': generated_text, 'document': None, 'ad_added': False, 'channel': active_ch}
            send_draft_preview(chat_id, user_id, draft)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Ошибка альбома: {e}")
        finally:
            for f in opened_files:
                try: f.close()
                except: pass
            for tin, tout in temp_files:
                if os.path.exists(tin): os.remove(tin)
                if os.path.exists(tout) and tout != tin: os.remove(tout)

    def send_draft_preview(chat_id, user_id, draft):
        text = draft['text']
        photo_id = draft['photo']
        if photo_id:
            if ',' in photo_id:
                ids = photo_id.split(',')
                media = [telebot.types.InputMediaPhoto(media=pid) for pid in ids]
                bot.send_media_group(chat_id, media)
                sent = bot.send_message(chat_id, text, parse_mode='HTML')
                target_id = sent.message_id
            else:
                if len(text) <= 1024:
                    sent = bot.send_photo(chat_id, photo_id, caption=text, parse_mode='HTML')
                    target_id = sent.message_id
                else:
                    bot.send_photo(chat_id, photo_id)
                    sent = bot.send_message(chat_id, text, parse_mode='HTML')
                    target_id = sent.message_id
        else:
            sent = bot.send_message(chat_id, text, parse_mode='HTML')
            target_id = sent.message_id
            
        user_drafts[target_id] = draft
        user_current_draft_id[user_id] = target_id
        bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id))

    def save_edited_text(message, target_id, chat_id):
        if message.text and message.text.lower() in ['отмена', '❌ отмена']:
            bot.send_message(chat_id, "❌ Отменено.", reply_markup=keyboards.get_main_menu())
            return
        draft = user_drafts.pop(target_id, None)
        if not draft: return
        draft['text'] = message.text
        try: bot.delete_message(chat_id, target_id)
        except: pass
        try: bot.delete_message(chat_id, message.message_id)
        except: pass
        bot.send_message(chat_id, "✅ Текст обновлен!", reply_markup=keyboards.get_main_menu())
        send_draft_preview(chat_id, message.from_user.id, draft)

    def process_exact_time(message, draft_id, chat_id):
        if message.text and message.text.lower() in ['отмена', '❌ отмена']:
            bot.send_message(chat_id, "❌ Отменено.", reply_markup=keyboards.get_main_menu())
            return
        try:
            dt_naive = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
            tashkent_tz = pytz.timezone('Asia/Tashkent')
            dt_aware = tashkent_tz.localize(dt_naive)
            timestamp = int(dt_aware.timestamp())
            if timestamp < time.time():
                msg = bot.send_message(chat_id, "⚠️ Время прошло! Введи дату заново:", reply_markup=keyboards.get_cancel_markup())
                bot.register_next_step_handler(msg, process_exact_time, draft_id, chat_id)
                return
            draft = user_drafts.get(draft_id)
            if draft:
                database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], timestamp)
                bot.edit_message_reply_markup(chat_id, draft_id, reply_markup=None)
                bot.send_message(chat_id, f"🕒 Запланировано на {dt_naive.strftime('%d.%m.%Y %H:%M')} ({draft['channel']})", reply_markup=keyboards.get_main_menu())
                del user_drafts[draft_id]
                if user_current_draft_id.get(message.from_user.id) == draft_id:
                    del user_current_draft_id[message.from_user.id]
        except ValueError:
            msg = bot.send_message(chat_id, "❌ Формат: ДД.ММ.ГГГГ ЧЧ:ММ", reply_markup=keyboards.get_cancel_markup())
            bot.register_next_step_handler(msg, process_exact_time, draft_id, chat_id)

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        chat_id = call.message.chat.id
        target_id = call.message.message_id
        
        if call.data == "cancel_action":
            try: bot.delete_message(chat_id, target_id)
            except: pass
            if target_id in user_drafts: del user_drafts[target_id]
            if user_current_draft_id.get(call.from_user.id) == target_id:
                del user_current_draft_id[call.from_user.id]
            bot.answer_callback_query(call.id, "🗑 Черновик удален")
            return

        draft = user_drafts.get(target_id)
        if not draft and not call.data.startswith("sched_"):
            return bot.answer_callback_query(call.id, "Черновик устарел.", show_alert=True)

        if call.data == "rewrite_menu":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("🤏 Короче", callback_data="rw_short"), InlineKeyboardButton("🤪 Веселее", callback_data="rw_fun"))
            markup.add(InlineKeyboardButton("👔 Серьезнее", callback_data="rw_pro"), InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=markup)
            return

        if call.data.startswith("rw_"):
            style = call.data.split("_")[1]
            bot.answer_callback_query(call.id, "⏳ ИИ переписывает текст...")
            new_text = ai_generator.rewrite_post(draft['text'], style)
            draft['text'] = new_text
            update_draft_inline(chat_id, target_id, draft)
            return

        if call.data == "add_to_smart_q":
            last_time = database.get_last_scheduled_time()
            tashkent_tz = pytz.timezone('Asia/Tashkent')
            current_time = int(datetime.now(tashkent_tz).timestamp())
            interval_seconds = getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600
            if last_time and last_time > current_time: new_time = last_time + interval_seconds
            else: new_time = current_time + interval_seconds
            database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], new_time)
            dt_str = datetime.fromtimestamp(new_time, tashkent_tz).strftime('%d.%m.%Y %H:%M')
            bot.answer_callback_query(call.id, "✅ Добавлено!")
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=None)
            bot.send_message(chat_id, f"🧠 Пост запланирован на {dt_str} для {draft['channel']}", parse_mode="HTML")
            del user_drafts[target_id]
            if user_current_draft_id.get(call.from_user.id) == target_id:
                del user_current_draft_id[call.from_user.id]
            return

        if call.data == "edit_text":
            raw_text = html.escape(draft['text'])
            msg = bot.send_message(chat_id, f"✏️ <b>Скопируй код ниже:</b>\n\n<code>{raw_text}</code>", parse_mode="HTML", reply_markup=keyboards.get_cancel_markup())
            bot.register_next_step_handler(msg, save_edited_text, target_id, chat_id)
            return

        if call.data == "pub_now":
            if publisher.publish_post_data(bot, -1, draft['photo'], draft['text'], draft['document'], draft['channel']):
                database.record_published_post(draft['photo'], draft['text'], draft['document'], draft['channel'])
                bot.answer_callback_query(call.id, "Опубликовано!")
                bot.edit_message_reply_markup(chat_id, target_id, reply_markup=None)
                bot.send_message(chat_id, f"🚀 Отправлено в {draft['channel']}!")
                del user_drafts[target_id]
                if user_current_draft_id.get(call.from_user.id) == target_id:
                    del user_current_draft_id[call.from_user.id]
            return

        if call.data == "pub_queue_menu":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("2 часа", callback_data=f"sched_interval_2_{target_id}"), InlineKeyboardButton("4 часа", callback_data=f"sched_interval_4_{target_id}"))
            markup.add(InlineKeyboardButton("6 часов", callback_data=f"sched_interval_6_{target_id}"), InlineKeyboardButton("12 часов", callback_data=f"sched_interval_12_{target_id}"))
            markup.add(InlineKeyboardButton("📅 Точная дата", callback_data=f"sched_exact_{target_id}"), InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=markup)
            return

        if call.data == "back_to_draft":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id))
            return

        if call.data.startswith("sched_interval_"):
            parts = call.data.split('_')
            hours, dr_id = int(parts[2]), int(parts[3])
            t_draft = user_drafts.get(dr_id)
            if not t_draft: return bot.answer_callback_query(call.id, "Ошибка.")
            tashkent_tz = pytz.timezone('Asia/Tashkent')
            future = datetime.now(tashkent_tz) + timedelta(hours=hours)
            timestamp = int(future.timestamp())
            database.add_to_queue(t_draft['photo'], t_draft['text'], t_draft['document'], t_draft['channel'], timestamp)
            bot.edit_message_reply_markup(chat_id, dr_id, reply_markup=None)
            bot.send_message(chat_id, f"🕒 Запланировано (+{hours} ч.) для {t_draft['channel']}")
            del user_drafts[dr_id]
            if user_current_draft_id.get(call.from_user.id) == dr_id:
                del user_current_draft_id[call.from_user.id]
            return

        if call.data.startswith("sched_exact_"):
            dr_id = int(call.data.split('_')[2])
            msg = bot.send_message(chat_id, "📅 Формат `ДД.ММ.ГГГГ ЧЧ:ММ`:", parse_mode="Markdown", reply_markup=keyboards.get_cancel_markup())
            bot.register_next_step_handler(msg, process_exact_time, dr_id, chat_id)
            return

    def update_draft_inline(chat_id, target_id, draft):
        markup = keyboards.get_draft_markup(target_id)
        try: bot.edit_message_text(text=draft['text'], chat_id=chat_id, message_id=target_id, parse_mode='HTML', reply_markup=markup)
        except:
            try: bot.edit_message_caption(caption=draft['text'], chat_id=chat_id, message_id=target_id, parse_mode='HTML', reply_markup=markup)
            except: pass

    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        user_id = message.from_user.id
        target_id = message.reply_to_message.message_id if message.reply_to_message else user_current_draft_id.get(user_id)
        if target_id and target_id in user_drafts:
            current = user_drafts[target_id].get('document', '')
            user_drafts[target_id]['document'] = f"{current},{message.document.file_id}" if current else message.document.file_id
            bot.reply_to(message, f"✅ Файл прикреплен! (Всего: {len(user_drafts[target_id]['document'].split(','))})")
            return
        bot.reply_to(message, "❌ Нет активного черновика.")

    @bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text'])
    def catch_group_comments(message):
        if not message.text.startswith('/'):
            database.save_comment(message.from_user.first_name, message.text, int(time.time()))
