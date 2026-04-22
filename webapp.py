from flask import Flask, render_template, request, jsonify, redirect
import database
import config
import os
import time
from datetime import datetime
import pytz
import telebot

app = Flask(__name__)
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

# Кеш для путей файлов, чтобы не дергать API Telegram постоянно
file_path_cache = {}

def get_telegram_file_url(file_id):
    if file_id in file_path_cache:
        return file_path_cache[file_id]
    
    try:
        file_info = bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{file_info.file_path}"
        file_path_cache[file_id] = url
        return url
    except Exception as e:
        print(f"Ошибка получения файла {file_id}: {e}")
        return None

def format_timestamp(ts):
    if not ts: return "Не запланировано"
    tz = pytz.timezone('Asia/Tashkent')
    return datetime.fromtimestamp(ts, tz).strftime('%d.%m.%Y %H:%M')

@app.route('/')
def index():
    stats = database.get_stats()
    pending = database.get_all_pending()
    queue = []
    for p in pending:
        queue.append({
            'id': p[0],
            'photos': p[1].split(',') if p[1] else [],
            'text': p[2],
            'channel': p[4] or config.DEFAULT_CHANNEL,
            'time_str': format_timestamp(p[5]),
            'timestamp': p[5],
            'iso_time': datetime.fromtimestamp(p[5]).isoformat() if p[5] else ""
        })
    
    all_posts = database.get_all_posts()
    history_raw = [p for p in all_posts if p[4] == 'posted']
    history_raw.sort(key=lambda x: x[6] if len(x) > 6 and x[6] else 0, reverse=True)
    
    history = []
    for p in history_raw[:10]:
        history.append({
            'id': p[0],
            'photos': p[1].split(',') if p[1] else [],
            'text': p[2],
            'channel': p[5] if len(p) > 5 else config.DEFAULT_CHANNEL,
            'time_str': format_timestamp(p[6] if len(p) > 6 else None)
        })

    return render_template('dashboard.html', stats=stats, queue=queue, history=history, config=config)

@app.route('/file/<file_id>')
def proxy_file(file_id):
    url = get_telegram_file_url(file_id)
    if url:
        return redirect(url)
    return "File not found", 404

@app.route('/api/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    database.delete_from_queue(post_id)
    return jsonify({'status': 'success'})

@app.route('/api/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    data = request.json
    text = data.get('text')
    iso_time = data.get('time') # Приходит в формате ГГГГ-ММ-ДДTЧЧ:ММ
    
    try:
        tz = pytz.timezone('Asia/Tashkent')
        dt = datetime.fromisoformat(iso_time)
        # Если время наивное, локализуем его
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        timestamp = int(dt.timestamp())
    except Exception as e:
        print(f"Ошибка парсинга времени: {e}")
        timestamp = data.get('timestamp') # fallback на старый метод

    database.update_post_content(post_id, text, timestamp)
    return jsonify({'status': 'success'})

@app.route('/api/reorder', methods=['POST'])
def reorder():
    data = request.json
    order = data.get('order')
    if not order: return jsonify({'status': 'error'})
    
    # Логика: берем время первого поста (или текущее) и расставляем остальные с шагом в 6 часов
    interval = getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600
    current_time = int(time.time()) + 300 # Начинаем через 5 минут от текущего
    
    for i, post_id in enumerate(order):
        new_time = current_time + (i * interval)
        post = database.get_post_by_id(int(post_id))
        if post:
            database.update_post_content(post[0], post[2], new_time)
            
    return jsonify({'status': 'success'})

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
