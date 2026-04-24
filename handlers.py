import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time
import pytz
import html
import re
from datetime import datetime, timedelta

import config
import database
import ai_generator
import watermarker
import utils
import keyboards
import publisher
import strings
from bot_instance import bot

# Глобальные словари для хранения текущего состояния пользователей
user_current_draft_id = {} # ID сообщения-черновика для каждого пользователя
user_states = {} # Состояние редактирования (например, "EDITING" или "SETTING_TIME")

def get_user_lang(user_id):
    return database.get_user_setting(user_id, 'persona', 'uz')

def get_txt(user_id, key, **kwargs):
    lang = get_user_lang(user_id)
    text = strings.MESSAGES.get(lang, strings.MESSAGES['uz']).get(key, key)
    return text.format(**kwargs)

def register_handlers(bot_instance, user_drafts, album_cache):
    """Регистрация всех обработчиков команд и сообщений бота."""

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        """Обработка команды /start."""
        user_id = message.from_user.id
        if not database.get_user_setting(user_id, 'persona'):
            database.update_user_setting(user_id, 'persona', 'uz')
        
        lang = get_user_lang(user_id)
        bot.send_message(
            message.chat.id, 
            get_txt(user_id, 'welcome'),
            parse_mode='HTML', 
            reply_markup=keyboards.get_main_menu(lang)
        )

    @bot.message_handler(content_types=['text', 'photo'])
    def handle_text_photo(message):
        """Обработка входящих текстовых сообщений и одиночных фото."""
        user_id = message.from_user.id
        lang = get_user_lang(user_id)
        btns = strings.BUTTONS.get(lang, strings.BUTTONS['uz'])
        
        # СОСТОЯНИЕ: Редактирование текста черновика
        if user_states.get(user_id) == "EDITING":
            target_id = user_current_draft_id.get(user_id)
            if target_id and target_id in user_drafts:
                user_drafts[target_id]['text'] = message.text
                user_states[user_id] = None
                bot.send_message(message.chat.id, get_txt(user_id, 'text_updated'), reply_markup=keyboards.get_main_menu(lang))
                send_draft_preview(message.chat.id, user_id, user_drafts[target_id])
            else:
                user_states[user_id] = None
                bot.send_message(message.chat.id, get_txt(user_id, 'err_draft'), reply_markup=keyboards.get_main_menu(lang))
            return

        # СОСТОЯНИЕ: Ввод точного времени публикации
        if user_states.get(user_id) == "SETTING_TIME":
            target_id = user_current_draft_id.get(user_id)
            if target_id and target_id in user_drafts:
                try:
                    time_match = re.search(r'(\d{1,2})\.(\d{1,2})\s+(\d{1,2})[:\-\s](\d{1,2})', message.text)
                    if time_match:
                        day, month, hour, minute = map(int, time_match.groups())
                        year = datetime.now().year
                        tz = pytz.timezone('Asia/Tashkent')
                        try:
                            dt = tz.localize(datetime(year, month, day, hour, minute))
                        except ValueError:
                            bot.send_message(message.chat.id, get_txt(user_id, 'invalid_date'))
                            return
                        if dt.timestamp() < time.time():
                            if (time.time() - dt.timestamp()) > 86400:
                                dt = tz.localize(datetime(year + 1, month, day, hour, minute))
                        timestamp = int(dt.timestamp())
                        draft = user_drafts[target_id]
                        database.add_to_queue(draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL), timestamp)
                        user_states[user_id] = None
                        bot.delete_message(message.chat.id, target_id)
                        if target_id in user_drafts: del user_drafts[target_id]
                        bot.send_message(message.chat.id, get_txt(user_id, 'scheduled', time=dt.strftime('%d.%m %H:%M')), reply_markup=keyboards.get_main_menu(lang))
                    else:
                        bot.send_message(message.chat.id, get_txt(user_id, 'enter_time'), parse_mode='HTML')
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Error: {e}")
            else:
                user_states[user_id] = None
                bot.send_message(message.chat.id, get_txt(user_id, 'err_draft'), reply_markup=keyboards.get_main_menu(lang))
            return

        # Игнорируем команды
        if message.text and message.text.startswith('/'): return
        
        # Кнопки основного меню
        if message.text == btns['create']:
            bot.send_message(message.chat.id, get_txt(user_id, 'choose_action'), reply_markup=keyboards.get_cancel_markup(lang))
            return
        
        if message.text == btns['cancel']:
            user_states[user_id] = None
            bot.send_message(message.chat.id, get_txt(user_id, 'cancel_msg'), reply_markup=keyboards.get_main_menu(lang))
            return

        # Обработка альбомов
        if message.media_group_id:
            if message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
                bot.send_message(message.chat.id, get_txt(user_id, 'album_loading'))
                threading.Timer(2.0, process_album, args=[message.media_group_id, message.chat.id, message.from_user.id]).start()
            album_cache[message.media_group_id].append(message)
            return
        
        # Обработка одиночного сообщения
        process_single_message(message)

    def process_single_message(message):
        user_id = message.from_user.id
        lang = get_user_lang(user_id)
        temp_in = f"in_{message.message_id}.jpg"
        temp_out = f"out_{message.message_id}.jpg"
        status_msg = bot.send_message(message.chat.id, get_txt(user_id, 'generation_start'), parse_mode='HTML')
        try:
            bot.send_chat_action(message.chat.id, 'upload_photo')
            user_input = message.caption if message.photo else message.text
            if not user_input: return
            persona = database.get_user_setting(user_id, 'persona', 'uz')
            generated_text = ai_generator.generate_post(user_input, persona)
            photo_id = None
            if message.photo:
                bot.edit_message_text(get_txt(user_id, 'processing_photo'), message.chat.id, status_msg.message_id, parse_mode='HTML')
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                with open(temp_out, 'rb') as f:
                    sent = bot.send_photo(message.chat.id, f)
                    photo_id = sent.photo[-1].file_id
                    bot.delete_message(message.chat.id, sent.message_id) 
            bot.delete_message(message.chat.id, status_msg.message_id)
            active_ch = database.get_user_setting(user_id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': photo_id, 'text': generated_text, 'document': None, 'channel': active_ch}
            send_draft_preview(message.chat.id, user_id, draft)
        except Exception as e: bot.edit_message_text(f"❌ Error: {e}", message.chat.id, status_msg.message_id)
        finally:
            if os.path.exists(temp_in): os.remove(temp_in)
            if os.path.exists(temp_out): os.remove(temp_out)

    def send_draft_preview(chat_id, user_id, draft):
        lang = get_user_lang(user_id)
        text = draft['text']
        photo_id = draft['photo']
        if photo_id:
            if ',' in photo_id:
                ids = photo_id.split(',')
                media = [telebot.types.InputMediaPhoto(media=pid) for pid in ids]
                bot.send_media_group(chat_id, media)
                sent = bot.send_message(chat_id, text, parse_mode='HTML')
            else:
                sent = bot.send_photo(chat_id, photo_id, caption=text, parse_mode='HTML')
        else:
            sent = bot.send_message(chat_id, text, parse_mode='HTML')
        target_id = sent.message_id
        user_drafts[target_id] = draft
        user_current_draft_id[user_id] = target_id
        bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id, lang))

    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        user_id = message.from_user.id
        target_id = user_current_draft_id.get(user_id)
        if target_id and target_id in user_drafts:
            current = user_drafts[target_id].get('document', '')
            user_drafts[target_id]['document'] = f"{current},{message.document.file_id}" if current else message.document.file_id
            count = len(user_drafts[target_id]['document'].split(','))
            bot.reply_to(message, get_txt(user_id, 'file_attached', count=count), parse_mode="HTML")
        else: bot.reply_to(message, get_txt(user_id, 'no_draft'))

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        chat_id = call.message.chat.id
        target_id = call.message.message_id
        user_id = call.from_user.id
        lang = get_user_lang(user_id)
        
        if call.data == "cancel_action":
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.answer_callback_query(call.id)
            return
        
        draft = user_drafts.get(target_id)
        if not draft and not call.data.startswith("sched_"): 
            bot.answer_callback_query(call.id, get_txt(user_id, 'err_draft'), show_alert=True)
            return

        if call.data == "pub_now":
            publisher.publish_post_data(bot, -1, draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL))
            bot.answer_callback_query(call.id, get_txt(user_id, 'published'))
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, get_txt(user_id, 'published'), reply_markup=keyboards.get_main_menu(lang))
            return

        if call.data == "add_to_smart_q":
            scheduled_time = int(time.time()) + (getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600)
            database.add_to_queue(draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL), scheduled_time)
            bot.answer_callback_query(call.id)
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, get_txt(user_id, 'smart_queue_added'), reply_markup=keyboards.get_main_menu(lang))
            return

        if call.data.startswith("sched_interval_"):
            parts = call.data.split('_')
            hours = int(parts[2])
            sched_time = int(time.time()) + (hours * 3600)
            database.add_to_queue(draft.get('photo'), draft.get('text'), draft.get('document'), draft.get('channel', config.DEFAULT_CHANNEL), sched_time)
            bot.answer_callback_query(call.id)
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.send_message(chat_id, get_txt(user_id, 'scheduled', time=f"+{hours}h"), reply_markup=keyboards.get_main_menu(lang))
            return

        if call.data.startswith("sched_exact_"):
            user_states[user_id] = "SETTING_TIME"
            bot.send_message(chat_id, get_txt(user_id, 'enter_time'), parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return

        if call.data == "pub_queue_menu":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_queue_menu(target_id, lang))
            return

        if call.data == "back_to_draft":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id, lang))
            return
            
        if call.data == "edit_text":
            user_states[user_id] = "EDITING"
            bot.send_message(chat_id, get_txt(user_id, 'enter_text'))
            bot.answer_callback_query(call.id)
            return

        if call.data == "rewrite_menu":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_rewrite_menu(target_id, lang))
            return

        if call.data.startswith("rewrite_"):
            style = "short" if "short" in call.data else "long"
            bot.answer_callback_query(call.id, get_txt(user_id, 'rewriting'))
            new_text = ai_generator.rewrite_post(draft['text'], style)
            draft['text'] = new_text
            send_draft_preview(chat_id, user_id, draft)
            bot.delete_message(chat_id, target_id)
            return

    def process_album(media_group_id, chat_id, user_id):
        lang = get_user_lang(user_id)
        messages = album_cache.get(media_group_id)
        if not messages: return
        status_msg = bot.send_message(chat_id, get_txt(user_id, 'album_loading'))
        try:
            user_input = next((m.caption for m in messages if m.caption), None)
            if not user_input: user_input = "Album"
            persona = database.get_user_setting(user_id, 'persona', 'uz')
            generated_text = ai_generator.generate_post(user_input, persona)
            photo_ids = []
            for i, msg in enumerate(messages):
                bot.edit_message_text(get_txt(user_id, 'album_processing', i=i+1, total=len(messages)), chat_id, status_msg.message_id, parse_mode='HTML')
                temp_in = f"in_alb_{msg.message_id}.jpg"
                temp_out = f"out_alb_{msg.message_id}.jpg"
                file_info = bot.get_file(msg.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                with open(temp_out, 'rb') as f:
                    sent = bot.send_photo(config.LOG_CHANNEL if hasattr(config, 'LOG_CHANNEL') else chat_id, f)
                    photo_ids.append(sent.photo[-1].file_id)
                    if not hasattr(config, 'LOG_CHANNEL'): bot.delete_message(chat_id, sent.message_id)
                if os.path.exists(temp_in): os.remove(temp_in)
                if os.path.exists(temp_out): os.remove(temp_out)
            bot.delete_message(chat_id, status_msg.message_id)
            active_ch = database.get_user_setting(user_id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': ",".join(photo_ids), 'text': generated_text, 'document': None, 'channel': active_ch}
            send_draft_preview(chat_id, user_id, draft)
        except Exception as e: bot.edit_message_text(f"❌ Error: {e}", chat_id, status_msg.message_id)
        finally:
            if media_group_id in album_cache: del album_cache[media_group_id]
