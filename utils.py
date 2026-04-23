import os
import csv
import re
import pytz
from datetime import datetime, timedelta
import config
import database
import strings

def get_msg(key, lang='uz', **kwargs):
    msg = strings.MESSAGES.get(lang, strings.MESSAGES['uz']).get(key, key)
    return msg.format(**kwargs)

def get_time_greeting():
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    hour = datetime.now(tashkent_tz).hour
    if hour < 6: return "🌙 Доброй ночи"
    elif hour < 12: return "🌅 Доброе утро"
    elif hour < 18: return "☀️ Добрый день"
    else: return "🌆 Добрый вечер"

def format_queue_post(post, index, total):
    post_id, photo_id, text, doc_id, channel, time_sched = post
    type_icon = "🖼️" if photo_id else "📝" if not doc_id else "📁"
    if photo_id and ',' in photo_id: type_icon = "📚"
    
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    if time_sched:
        dt = datetime.fromtimestamp(time_sched, tashkent_tz)
        now = datetime.now(tashkent_tz)
        if dt.date() == now.date(): time_str = f"Сегодня в {dt.strftime('%H:%M')}"
        elif dt.date() == (now + timedelta(days=1)).date(): time_str = f"Завтра в {dt.strftime('%H:%M')}"
        else: time_str = dt.strftime('%d.%m.%Y %H:%M')
    else:
        time_str = "⏰ Не запланировано"
        
    preview = re.sub(r'<[^>]+>', '', text)[:100]
    return f"""╔═══📋 ПОСТ {index}/{total} ═══╗
{type_icon} <b>Тип:</b> {'Альбом' if photo_id and ',' in photo_id else 'Фото' if photo_id else 'Текст'}
📢 <b>Канал:</b> {channel or config.DEFAULT_CHANNEL}
⏰ <b>Время:</b> {time_str}

📝 <b>Превью:</b>
<i>{preview}{'...' if len(text) > 100 else ''}</i>
╚════════════════════╝"""

def get_channels():
    channels = database.get_all_managed_channels()
    if not channels:
        # При первом запуске переносим каналы из конфига в БД
        for ch in config.AVAILABLE_CHANNELS:
            database.add_channel(ch)
        channels = config.AVAILABLE_CHANNELS
    return channels

def get_active_channel(user_id):
    ch = database.get_user_setting(user_id, 'active_channel')
    if ch: return ch
    channels = get_channels()
    return channels[0] if channels else config.DEFAULT_CHANNEL

def get_active_persona(user_id):
    return database.get_user_setting(user_id, 'persona', 'uz') 

def save_ad_text(text):
    with open("ad.txt", "w", encoding="utf-8") as f: f.write(text)

def get_ad_text():
    if os.path.exists("ad.txt"):
        with open("ad.txt", "r", encoding="utf-8") as f: return f.read()
    return ""

def export_to_csv(bot, chat_id):
    bot.send_message(chat_id, "⏳ Выгружаю данные в таблицу Excel...")
    posts = database.get_all_posts()
    
    if not posts:
        bot.send_message(chat_id, "📭 База данных пуста, выгружать нечего.")
        return
        
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    filename = f"posts_export_{datetime.now(tashkent_tz).strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';') 
            writer.writerow(['ID', 'Канал', 'Текст поста', 'Статус', 'Время публикации', 'Наличие фото/файла'])
            
            for p in posts:
                time_str = datetime.fromtimestamp(p[6], tashkent_tz).strftime('%d.%m.%Y %H:%M') if len(p) > 6 and p[6] else "Нет"
                has_media = "Да" if p[1] or p[3] else "Нет"
                clean_text = re.sub(r'<[^>]+>', '', p[2])
                writer.writerow([p[0], p[5] if len(p) > 5 else "Default", clean_text, p[4], time_str, has_media])
                
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, caption="📊 <b>Экспорт завершен!</b>\n\nЭтот файл можно открыть в Excel.", parse_mode="HTML")
            
        os.remove(filename)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при выгрузке: {e}")
