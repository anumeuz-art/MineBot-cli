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

user_current_draft_id = {}

def register_handlers(bot, user_drafts, album_cache):

    @bot.message_handler(commands=['map'])
    def send_map(message):
        posts = database.get_recent_posts(7)
        if not posts: return bot.reply_to(message, "Нет данных за неделю.")
        map_text = ai_generator.generate_map(str(posts))
        bot.send_message(message.chat.id, map_text, parse_mode="HTML")

    @bot.message_handler(commands=['report'])
    def send_report(message):
        top_ids = database.get_top_posts(5)
        all_posts = database.get_all_posts()
        top_data = [p for p in all_posts if p[0] in top_ids]
        report_text = ai_generator.generate_report(str(top_data))
        bot.send_message(message.chat.id, report_text, parse_mode="HTML")

    @bot.message_handler(content_types=['text', 'photo'])
    def handle_text_photo(message):
        if message.text and message.text.startswith('/'): return
        if message.text == "📝 Создать пост":
            bot.send_message(message.chat.id, "Отправь фото, текст или ссылку:", reply_markup=keyboards.get_cancel_markup())
            return
        if message.text == "❌ Отмена":
            bot.send_message(message.chat.id, "❌ Действие отменено.", reply_markup=keyboards.get_main_menu())
            return

        if message.media_group_id:
            if message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
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
            if not user_input: return
            
            persona = database.get_user_setting(message.from_user.id, 'persona', 'uz')
            generated_text = ai_generator.generate_post(user_input, persona)
            
            photo_id = None
            if message.photo:
                bot.send_message(message.chat.id, "🎨 Обрабатываю фото...")
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                with open(temp_in, 'wb') as f: f.write(downloaded_file)
                watermarker.add_watermark(temp_in, temp_out)
                with open(temp_out, 'rb') as f:
                    sent = bot.send_photo(message.chat.id, f)
                    photo_id = sent.photo[-1].file_id
                    bot.delete_message(message.chat.id, sent.message_id) 
            
            active_ch = database.get_user_setting(message.from_user.id, 'active_channel', config.DEFAULT_CHANNEL)
            draft = {'photo': photo_id, 'text': generated_text, 'document': None, 'channel': active_ch}
            send_draft_preview(message.chat.id, message.from_user.id, draft)
        except Exception as e: bot.send_message(message.chat.id, f"Ошибка: {e}")
        finally:
            if os.path.exists(temp_in): os.remove(temp_in)
            if os.path.exists(temp_out): os.remove(temp_out)

    def send_draft_preview(chat_id, user_id, draft):
        text = draft['text']
        photo_id = draft['photo']
        if photo_id:
            sent = bot.send_photo(chat_id, photo_id, caption=text, parse_mode='HTML')
        else:
            sent = bot.send_message(chat_id, text, parse_mode='HTML')
        
        user_drafts[sent.message_id] = draft
        user_current_draft_id[user_id] = sent.message_id
        bot.edit_message_reply_markup(chat_id, sent.message_id, reply_markup=keyboards.get_draft_markup(sent.message_id))

    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        user_id = message.from_user.id
        target_id = user_current_draft_id.get(user_id)
        if target_id and target_id in user_drafts:
            current = user_drafts[target_id].get('document', '')
            user_drafts[target_id]['document'] = f"{current},{message.document.file_id}" if current else message.document.file_id
            bot.reply_to(message, "✅ Файл прикреплен!")
        else: bot.reply_to(message, "❌ Нет активного черновика.")

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        chat_id = call.message.chat.id
        target_id = call.message.message_id
        
        if call.data == "cancel_action":
            bot.delete_message(chat_id, target_id)
            if target_id in user_drafts: del user_drafts[target_id]
            bot.answer_callback_query(call.id, "🗑 Удалено")
            return
        
        draft = user_drafts.get(target_id)
        if not draft and not call.data.startswith("sched_"): return

        if call.data == "pub_queue_menu":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("2ч", callback_data=f"sched_interval_2_{target_id}"), InlineKeyboardButton("6ч", callback_data=f"sched_interval_6_{target_id}"))
            markup.add(InlineKeyboardButton("📅 Точная дата", callback_data=f"sched_exact_{target_id}"), InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=markup)
            return

        if call.data == "back_to_draft":
            bot.edit_message_reply_markup(chat_id, target_id, reply_markup=keyboards.get_draft_markup(target_id))
            return
            
        # Остальная логика ... (аналогично была)
