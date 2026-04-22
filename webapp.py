from flask import Flask, render_template, request, jsonify, redirect, send_file
import database
import config
import os
import time
from datetime import datetime, timedelta
import pytz
import telebot
import publisher

app = Flask(__name__)
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

file_path_cache = {}

def get_telegram_file_url(file_id):
    if file_id in file_path_cache: return file_path_cache[file_id]
    try:
        file_info = bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{file_info.file_path}"
        file_path_cache[file_id] = url
        return url
    except: return None

def format_timestamp(ts):
    if not ts: return "⏰ ASAP"
    tz = pytz.timezone('Asia/Tashkent')
    return datetime.fromtimestamp(ts, tz).strftime('%d.%m %H:%M')

def collect_stats():
    channels = database.get_all_managed_channels()
    for ch in channels:
        try:
            count = bot.get_chat_member_count(ch)
            database.save_sub_count(ch, count)
        except: pass

@app.route('/')
def index():
    collect_stats()
    stats = database.get_stats()
    pending = database.get_all_pending()
    queue = []
    for p in pending:
        doc_ids = p[3].split(',') if p[3] else []
        queue.append({
            'id': p[0],
            'photos': p[1].split(',') if p[1] else [],
            'text': p[2],
            'channel': p[4] or config.DEFAULT_CHANNEL,
            'time_str': format_timestamp(p[5]),
            'timestamp': p[5],
            'iso_time': datetime.fromtimestamp(p[5]).strftime('%Y-%m-%dT%H:%M') if p[5] else "",
            'files_count': len(doc_ids)
        })
    
    all_posts = database.get_all_posts()
    history_raw = [p for p in all_posts if p[4] == 'posted']
    history_raw.sort(key=lambda x: x[6] if len(x) > 6 and x[6] else 0, reverse=True)
    history = []
    for p in history_raw[:15]:
        history.append({
            'id': p[0], 'photos': p[1].split(',') if p[1] else [],
            'text': p[2], 'channel': p[5] if len(p) > 5 else config.DEFAULT_CHANNEL,
            'time_str': format_timestamp(p[6] if len(p) > 6 else None)
        })

    managed_channels = database.get_all_managed_channels()
    
    # Расширенная статистика
    total_subs = 0
    growth_24h = 0
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    for ch in managed_channels:
        current_history = database.get_sub_history(ch)
        if current_history:
            current_count = current_history[-1][1]
            total_subs += current_count
            # Ищем вчерашнее значение
            prev_count = next((h[1] for h in current_history if h[0] == yesterday), current_count)
            growth_24h += (current_count - prev_count)

    # Текущие настройки (берем для первого админа в списке или дефолт)
    current_lang = database.get_user_setting(config.ADMIN_IDS[0], 'persona', 'uz')
    
    return render_template('dashboard.html', stats=stats, queue=queue, history=history, 
                           channels=managed_channels, total_subs=total_subs, 
                           growth_24h=growth_24h, current_lang=current_lang, config=config)

@app.route('/api/settings/language', methods=['POST'])
def set_language():
    lang = request.json.get('lang')
    if lang in ['uz', 'ru', 'en']:
        for admin_id in config.ADMIN_IDS:
            database.update_user_setting(admin_id, 'persona', lang)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/logo.png')
def get_logo():
    if os.path.exists('logo.png'): return send_file('logo.png', mimetype='image/png')
    return "Not found", 404

@app.route('/api/refresh')
def api_refresh():
    collect_stats()
    return jsonify({'status': 'ok'})

@app.route('/api/publish/<int:post_id>', methods=['POST'])
def api_publish_now(post_id):
    post = database.get_post_by_id(post_id)
    if post and publisher.publish_post_data(bot, post[0], post[1], post[2], post[3], post[4] or config.DEFAULT_CHANNEL):
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/stats')
def get_stats_data():
    channels = database.get_all_managed_channels()
    result = {}
    for ch in channels:
        history = database.get_sub_history(ch)
        result[ch] = {'labels': [h[0] for h in history], 'data': [h[1] for h in history]}
    return jsonify(result)

@app.route('/api/channels', methods=['POST'])
def api_add_channel():
    username = request.json.get('username')
    if username:
        if not username.startswith('@'): username = '@' + username
        database.add_channel(username)
    return jsonify({'status': 'success'})

@app.route('/api/channels/delete', methods=['POST'])
def api_remove_channel():
    username = request.json.get('username')
    database.remove_channel(username)
    return jsonify({'status': 'success'})

@app.route('/file/<file_id>')
def proxy_file(file_id):
    url = get_telegram_file_url(file_id)
    return redirect(url) if url else ("/static/no-image.png", 404)

@app.route('/api/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    database.delete_from_queue(post_id)
    return jsonify({'status': 'success'})

@app.route('/api/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    data = request.json
    text = data.get('text')
    iso_time = data.get('time')
    try:
        tz = pytz.timezone('Asia/Tashkent')
        dt = datetime.fromisoformat(iso_time)
        timestamp = int(tz.localize(dt).timestamp())
    except: timestamp = data.get('timestamp')
    database.update_post_content(post_id, text, timestamp)
    return jsonify({'status': 'success'})

@app.route('/api/reorder', methods=['POST'])
def reorder():
    order = request.json.get('order')
    interval = getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6) * 3600
    start = int(time.time()) + 300
    for i, p_id in enumerate(order):
        post = database.get_post_by_id(int(p_id))
        if post: database.update_post_content(post[0], post[2], start + (i * interval))
    return jsonify({'status': 'success'})

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
