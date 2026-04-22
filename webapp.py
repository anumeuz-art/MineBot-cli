from flask import Flask, render_template, request, jsonify
import database
import config
import os
import time
from datetime import datetime
import pytz

app = Flask(__name__)

def format_timestamp(ts):
    if not ts: return "Не запланировано"
    tz = pytz.timezone('Asia/Tashkent')
    return datetime.fromtimestamp(ts, tz).strftime('%d.%m.%Y %H:%M')

@app.route('/')
def index():
    stats = database.get_stats()
    pending = database.get_all_pending()
    # Конвертируем кортежи в словари для удобства шаблона
    queue = []
    for p in pending:
        queue.append({
            'id': p[0],
            'photos': p[1].split(',') if p[1] else [],
            'text': p[2],
            'channel': p[4] or config.DEFAULT_CHANNEL,
            'time_str': format_timestamp(p[5]),
            'timestamp': p[5]
        })
    
    # Последние 10 опубликованных
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

    return render_template('dashboard.html', stats=stats, queue=queue, history=history)

@app.route('/api/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    database.delete_from_queue(post_id)
    return jsonify({'status': 'success'})

@app.route('/api/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    data = request.json
    text = data.get('text')
    timestamp = data.get('timestamp')
    database.update_post_content(post_id, text, timestamp)
    return jsonify({'status': 'success'})

@app.route('/api/reorder', methods=['POST'])
def reorder():
    data = request.json
    order = data.get('order') # Список ID в новом порядке
    if not order: return jsonify({'status': 'error'})
    
    pending = database.get_all_pending()
    if not pending: return jsonify({'status': 'success'})
    
    # Собираем все имеющиеся временные метки
    timestamps = sorted([p[5] for p in pending if p[5]])
    
    # Если меток меньше чем постов, создаем новые с интервалом
    if len(timestamps) < len(order):
        start_time = int(time.time()) + 3600
        interval = getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600
        timestamps = [start_time + i * interval for i in range(len(order))]
    
    # Обновляем время каждого поста согласно новому порядку
    for i, post_id in enumerate(order):
        post = database.get_post_by_id(int(post_id))
        if post:
            database.update_post_content(post[0], post[2], timestamps[i])
            
    return jsonify({'status': 'success'})

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
