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
import utils
import keyboards
import publisher

# Глобальные словари для хранения текущего состояния пользователей
user_current_draft_id = {} # ID сообщения-черновика для каждого пользователя
user_states = {} # Состояние редактирования (например, "EDITING" при вводе текста)

def register_handlers(bot, user_drafts, album_cache):
    """Регистрация всех обработчиков команд и сообщений бота."""

    @bot.message_handler(content_types=['text', 'photo'])
    def handle_text_photo(message):
        """Обработка входящих текстовых сообщений и одиночных фото."""
        user_id = message.from_user.id
        
        # Если пользователь находится в режиме редактирования текста черновика
        if user_states.get(user_id) == "EDITING":
            target_id = user_current_draft_id.get(user_id)
            if target_id and target_id in user_drafts:
                user_drafts[target_id]['text'] = message.text
                user_states[user_id] = None
                bot.send_message(message.chat.id, "✅ Текст обновлен!", reply_markup=keyboards.get_main_menu())
                send_draft_preview(message.chat.id, user_id, user_drafts[target_id])
            return

        # Игнорируем команды
        if message.text and message.text.startswith('/'): return
        
        # Главное меню: Создать пост
        if message.text == "📝 Создать пост":
            bot.send_message(message.chat.id, "Отправь фото, текст или ссылку:", reply_markup=keyboards.get_cancel_markup())
            return
        
        # Кнопка отмены
        if message.text == "❌ Отмена":
            user_states[user_id] = None
            bot.send_message(message.chat.id, "❌ Действие отменено.", reply_markup=keyboards.get_main_menu())
            return

        # Если пришел альбом (Media Group)
        if message.media_group_id:
            if message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
                bot.send_message(message.chat.id, "📸 Загружаю альбом...")
                # Ждем 2 секунды, пока все фото из альбома дойдут до бота
                threading.Timer(2.0, process_album, args=[message.media_group_id, message.chat.id, message.from_user.id]).start()
            album_cache[message.media_group_id].append(message)
            return
        
        # Обработка одиночного сообщения (текст или фото)
        process_single_message(message)

    def process_single_message(message):
        """Логика обработки одиночного фото или ссылки: генерация текста и наложение водяного знака."""
        temp_in = f"in_{message.message_id}.jpg"
        temp_out = f"out_{message.message_id}.jpg"
        status_msg = bot.send_message(message.chat.id, "⏳ Генерирую пост...")
        try:
            bot.send_chat_action(message.chat.id, 'upload_photo')
            user_input = message.caption if message.photo else message.text
            if not user_input: return
            
            # Получаем предпочтения пользователя (язык/стиль)
            persona = database.get_user_setting(message.from_user.id, 'persona', 'uz')
            # Генерация текста через ИИ
            generated_text = ai_generator.generate_post(user_input, persona)
            
            photo_id = None
            if message.photo:
                # Работа с фото: скачивание и водяной знак
                bot.edit_message_text("🎨 Обрабатываю фото...", message.chat.id, status_msg.message_id)
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                with open(temp_out, 'rb') as f:
                    sent = bot.send_photo(message.chat.id, f)
                    photo_id = sent.photo[-1].file_id
                    bot.delete_message(message.chat.id, sent.message_id) 
            
            bot.delete_message(message.chat.id, status_msg.message_id)
            active_ch = database.get_user_setting(message.from_user.id, 'active_channel', config.DEFAULT_CHANNEL)
            
            # Создаем объект черновика
            draft = {'photo': photo_id, 'text': generated_text, 'document': None, 'channel': active_ch}
            send_draft_preview(message.chat.id, message.from_user.id, draft)
        except Exception as e: bot.edit_message_text(f"❌ Ошибка: {e}", message.chat.id, status_msg.message_id)
        finally:
            # Очистка временных файлов
            if os.path.exists(temp_in): os.remove(temp_in)
            if os.path.exists(temp_out): os.remove(temp_out)

    def send_draft_preview(chat_id, user_id, draft):
        """Отправляет пользователю превью созданного поста с кнопками управления."""
        text = draft['text']
        photo_id = draft['photo']
        if photo_id:
            if ',' in photo_id: # Если это альбом
                ids = photo_id.split(',')
                media = [telebot.types.InputMediaPhoto(media=pid) for pid in ids]
                bot.send_media_group(chat_id, media)
                sent = bot.send_message(chat_id, text, parse_mode='HTML')
            else: # Если одиночное фото
                sent = bot.send_photo(chat_id, photo_id, caption=text, parse_mode='HTML')
        else: # Только текст
            sent = bot.send_message(chat_id, text, parse_mode='HTML')
        
        target_id = sent.message_id
        user_drafts[target_id] = draft
        user_current_draft_id[user_id] = target_id
        # Добавляем Inline-кнопки к сообщению-превью
        bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id))

    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        """Прикрепление документов к текущему активному черновику."""
        user_id = message.from_user.id
        target_id = user_current_draft_id.get(user_id)
        if target_id and target_id in user_drafts:
            current = user_drafts[target_id].get('document', '')
            user_drafts[target_id]['document'] = f"{current},{message.document.file_id}" if current else message.document.file_id
            count = len(user_drafts[target_id]['document'].split(','))
            bot.reply_to(message, f"✅ Файл прикреплен! (Всего: <b>{count}</b>)", parse_mode="HTML")
        else: bot.reply_to(message, "❌ Нет активного черновика.")

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        """Обработка всех нажатий на Inline-кнопки."""
        chat_id = call.message.chat.id
        target_id = call.message.message_id
        
        # Удаление черновика
        if call.data == "cancel_action":
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.answer_callback_query(call.id, "🗑 Удалено")
            return
        
        draft = user_drafts.get(target_id)
        if not draft and not call.data.startswith("sched_"): return

        # Мгновенная публикация
        if call.data == "pub_now":
            publisher.publish_post_data(bot, -1, draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL))
            bot.answer_callback_query(call.id, "🚀 Пост опубликован!")
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, "✅ Пост опубликован!", reply_markup=keyboards.get_main_menu())
            return

        # Добавление в умную очередь (автоматическое распределение времени)
        if call.data == "add_to_smart_q":
            scheduled_time = int(time.time()) + (getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600)
            database.add_to_queue(draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL), scheduled_time)
            bot.answer_callback_query(call.id, "🧠 Добавлено в умную очередь")
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, "🧠 Пост добавлен в умную очередь!", reply_markup=keyboards.get_main_menu())
            return

        # Планирование на конкретный интервал (2ч, 6ч)
        if call.data.startswith("sched_interval_"):
            parts = call.data.split('_')
            hours = int(parts[2])
            sched_time = int(time.time()) + (hours * 3600)
            database.add_to_queue(draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL), sched_time)
            bot.answer_callback_query(call.id, f"📅 Запланировано на через {hours}ч")
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, f"📅 Пост запланирован (через {hours}ч)!", reply_markup=keyboards.get_main_menu())
            return

        # Переход в меню выбора времени
        if call.data == "pub_queue_menu":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("2ч", callback_data=f"sched_interval_2_{target_id}"), InlineKeyboardButton("6ч", callback_data=f"sched_interval_6_{target_id}"))
            markup.add(InlineKeyboardButton("📅 Точная дата", callback_data=f"sched_exact_{target_id}"), InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=markup)
            return

        # Возврат к основным кнопкам черновика
        if call.data == "back_to_draft":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id))
            return
            
        # Режим ручного редактирования текста
        if call.data == "edit_text":
            user_states[call.from_user.id] = "EDITING"
            bot.send_message(chat_id, "✍️ Отправь новый текст для поста:")
            bot.answer_callback_query(call.id)
            return

        # Меню переписывания текста ИИ (коротко/подробно)
        if call.data == "rewrite_menu":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("Коротко", callback_data=f"rewrite_short_{target_id}"), InlineKeyboardButton("Подробно", callback_data=f"rewrite_long_{target_id}"))
            markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=markup)
            return

        # Запрос к ИИ на переписывание
        if call.data.startswith("rewrite_"):
            style = "short" if "short" in call.data else "long"
            bot.answer_callback_query(call.id, "⏳ Переписываю...")
            new_text = ai_generator.rewrite_post(draft['text'], style)
            draft['text'] = new_text
            send_draft_preview(chat_id, call.from_user.id, draft)
            bot.delete_message(chat_id, target_id)
            return

    def process_album(media_group_id, chat_id, user_id):
        """Сборка и обработка альбома из нескольких фотографий."""
        messages = album_cache.get(media_group_id)
        if not messages: return
        
        status_msg = bot.send_message(chat_id, "⏳ Обрабатываю альбом...")
        try:
            # Берем описание из того сообщения в альбоме, где оно есть
            user_input = next((m.caption for m in messages if m.caption), None)
            if not user_input: user_input = "Альбом без описания"
            
            persona = database.get_user_setting(user_id, 'persona', 'uz')
            generated_text = ai_generator.generate_post(user_input, persona)
            
            photo_ids = []
            for i, msg in enumerate(messages):
                bot.edit_message_text(f"🎨 Обработка фото {i+1}/{len(messages)}...", chat_id, status_msg.message_id)
                temp_in = f"in_alb_{msg.message_id}.jpg"
                temp_out = f"out_alb_{msg.message_id}.jpg"
                
                file_info = bot.get_file(msg.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                
                with open(temp_out, 'rb') as f:
                    # Отправляем во временное место, чтобы получить file_id обработанного фото
                    sent = bot.send_photo(config.LOG_CHANNEL if hasattr(config, 'LOG_CHANNEL') else chat_id, f)
                    photo_ids.append(sent.photo[-1].file_id)
                    if not hasattr(config, 'LOG_CHANNEL'): bot.delete_message(chat_id, sent.message_id)
                
                if os.path.exists(temp_in): os.remove(temp_in)
                if os.path.exists(temp_out): os.remove(temp_out)
            
            bot.delete_message(chat_id, status_msg.message_id)
            active_ch = database.get_user_setting(user_id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': ",".join(photo_ids), 'text': generated_text, 'document': None, 'channel': active_ch}
            send_draft_preview(chat_id, user_id, draft)
            
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка альбома: {e}", chat_id, status_msg.message_id)
        finally:
            if media_group_id in album_cache: del album_cache[media_group_id]
