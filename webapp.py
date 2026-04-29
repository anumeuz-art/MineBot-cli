from flask import Flask, render_template, request, jsonify, redirect, send_file
import database
import config
import os
import time
from datetime import datetime, timedelta
import pytz
import telebot
import publisher
import comments_analyzer
from bot_instance import bot

app = Flask(__name__)

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

def get_channel_growth(channel_id):
    history = database.get_sub_history(channel_id)
    if not history or len(history) < 2:
        return {'24h': 0, '7d': 0, '30d': 0, 'current': 0}
    
    current = history[-1][1]
    
    def get_diff(days):
        target_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        prev = next((h[1] for h in reversed(history) if h[0] <= target_date), history[0][1])
        return current - prev

    return {
        '24h': get_diff(1),
        '7d': get_diff(7),
        '30d': get_diff(30),
        'current': current
    }

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
    
    managed_channels = database.get_all_managed_channels()
    channel_stats = []
    total_subs = 0
    for ch in managed_channels:
        growth = get_channel_growth(ch)
        total_subs += growth['current']
        channel_stats.append({
            'username': ch,
            'subs': growth['current'],
            'g24h': growth['24h'],
            'g7d': growth['7d'],
            'g30d': growth['30d']
        })

    current_lang = database.get_user_setting(config.ADMIN_IDS[0], 'persona', 'uz')
    ad_text = database.get_global_setting('ad_text', '')
    sq_interval = database.get_global_setting('smart_queue_interval', '6')
    sq_text = database.get_global_setting('smart_queue_text', '')
    
    watermarks = database.get_all_watermarks()
    active_prompt, active_prompt_id = database.get_active_prompt()
    
    published_raw = database.get_published_history(50)
    history = []
    for p in published_raw:
        history.append({
            'id': p[0],
            'photos': p[1].split(',') if p[1] else [],
            'text': p[2],
            'channel': p[3],
            'time_str': format_timestamp(p[4]),
            'message_id': p[5]
        })
    
    import json
    with open('translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
    
    return render_template('dashboard.html', stats=stats, queue=queue, 
                           history=history,
                           channels=channel_stats, total_subs=total_subs, 
                           current_lang=current_lang, ad_text=ad_text, 
                           sq_interval=sq_interval, sq_text=sq_text,
                           watermarks=watermarks, active_prompt=active_prompt,
                           active_prompt_id=active_prompt_id,
                           translations=translations,
                           config=config)

@app.route('/api/watermarks/upload', methods=['POST'])
def upload_watermark():
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No file'}), 400
    
    # Проверка размера (макс 2МБ)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024:
        return jsonify({'error': 'File too large (max 2MB)'}), 400
    
    filename = f"wm_{int(time.time())}.png"
    path = os.path.join('data', filename)
    file.save(path)
    
    if database.add_watermark_db(path, file.filename):
        return jsonify({'status': 'success'})
    else:
        os.remove(path)
        return jsonify({'error': 'Limit reached (max 5)'}), 400

@app.route('/api/watermarks/activate/<int:wm_id>', methods=['POST'])
def activate_watermark(wm_id):
    database.set_active_watermark(wm_id)
    return jsonify({'status': 'success'})

@app.route('/api/watermarks/delete/<int:wm_id>', methods=['POST'])
def delete_watermark(wm_id):
    database.delete_watermark(wm_id)
    return jsonify({'status': 'success'})

@app.route('/api/settings/sq', methods=['POST'])
def set_sq_settings():
    data = request.json
    database.set_global_setting('smart_queue_interval', data.get('interval', '6'))
    database.set_global_setting('smart_queue_text', data.get('text', ''))
    return jsonify({'status': 'success'})

@app.route('/api/prompts/activate/<int:prompt_id>', methods=['POST'])
def api_activate_prompt(prompt_id):
    database.activate_prompt(prompt_id)
    return jsonify({'status': 'success'})

@app.route('/api/prompts/update/<int:prompt_id>', methods=['POST'])
def api_update_prompt(prompt_id):
    data = request.json
    database.update_prompt(prompt_id, data.get('name'), data.get('prompt'))
    return jsonify({'status': 'success'})

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    return jsonify(database.get_all_prompts())

@app.route('/api/prompts/add', methods=['POST'])
def add_prompt():
    data = request.json
    database.add_prompt(data.get('name'), data.get('prompt'))
    return jsonify({'status': 'success'})

@app.route('/api/prompts/delete/<int:prompt_id>', methods=['POST'])
def delete_prompt(prompt_id):
    database.delete_prompt(prompt_id)
    return jsonify({'status': 'success'})

@app.route('/api/comments', methods=['GET'])
def get_comments():
    comments = database.get_all_comments()
    return jsonify([{'user': c[0], 'text': c[1]} for c in comments])

@app.route('/api/comments/analyze', methods=['POST'])
def analyze_comments_api():
    summary = comments_analyzer.analyze_comments()
    return jsonify({'summary': summary})

@app.route('/api/comments/clear', methods=['POST'])
def clear_comments_api():
    database.clear_comments()
    return jsonify({'status': 'success'})

@app.route('/api/settings/ad', methods=['POST'])
def set_ad():
    text = request.json.get('text', '')
    database.set_global_setting('ad_text', text)
    return jsonify({'status': 'success'})

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
    path = os.path.join('templates', 'logo.png')
    if os.path.exists(path): return send_file(path, mimetype='image/png')
    return "Not found", 404

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

@app.route('/file/<path:file_id>')
def serve_file(file_id):
    if not file_id.startswith('AgAC') and not file_id.startswith('file_') and ('.' in file_id or '/' in file_id or '\\' in file_id):
        for folder in ['data', 'templates']:
            path = os.path.join(folder, os.path.basename(file_id))
            if os.path.exists(path):
                return send_file(path)
    
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
    if not order: return jsonify({'status': 'error'})
    
    pending = database.get_all_pending()
    # Собираем все существующие временные метки или генерируем новые, если их нет
    existing_timestamps = sorted([p[5] for p in pending if p[5]])
    
    # Если меток меньше чем постов, генерируем недостающие
    interval = int(database.get_global_setting('smart_queue_interval', 6)) * 3600
    last_time = existing_timestamps[-1] if existing_timestamps else int(time.time())
    
    # Создаем полный список таймстампов для всех ID в новом порядке
    new_timestamps = []
    if existing_timestamps:
        # Если были старые времена, пытаемся их переиспользовать
        new_timestamps = existing_timestamps
        while len(new_timestamps) < len(order):
            last_time += interval
            new_timestamps.append(last_time)
    else:
        # Если все посты были "ASAP", создаем новую последовательность
        for i in range(len(order)):
            new_timestamps.append(last_time + (i * interval))

    # Обновляем каждый пост в базе
    for i, p_id in enumerate(order):
        post = database.get_post_by_id(int(p_id))
        if post:
            database.update_post_content(post[0], post[2], new_timestamps[i])
            
    return jsonify({'status': 'success'})

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
