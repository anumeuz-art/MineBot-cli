from flask import Flask, render_template, request, jsonify, redirect, send_file, Response
import database
import config
import os
import time
from datetime import datetime, timedelta
import pytz
import telebot
import publisher
import comments_analyzer
import ai_generator
from bot_instance import bot
from functools import wraps

app = Flask(__name__)

# --- АВТОРИЗАЦИЯ ---
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Авторизация отключена по просьбе пользователя
        return f(*args, **kwargs)
    return decorated

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

@app.route('/')
@requires_auth
def index():
    user_id = request.args.get('user_id')
    if user_id: user_id = int(user_id)
    
    stats = database.get_stats()
    pending = database.get_all_pending(user_id)
    
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
    admin_id = config.ADMIN_IDS[0]
    
    return render_template('dashboard.html', stats=stats, queue=queue, 
                           channels=managed_channels, all_channels=managed_channels,
                           current_lang=database.get_user_setting(user_id or admin_id, 'persona', 'uz'),
                           ad_text=database.get_global_setting('ad_text', ''),
                           system_prompt=ai_generator.get_system_prompt(), 
                           smart_interval=database.get_global_setting('smart_queue_interval', '6'),
                           watermark_text=database.get_global_setting('watermark_custom_text', ''),
                           prompts=database.get_prompts(),
                           selected_prompt_id=database.get_user_setting(user_id or admin_id, 'active_prompt_id', '1'),
                           user_id=user_id, config=config)

@app.route('/api/settings/prompt/select', methods=['POST'])
@requires_auth
def select_prompt():
    prompt_id = request.json.get('id')
    user_id = request.args.get('user_id')
    uid = int(user_id) if user_id else config.ADMIN_IDS[0]
    database.update_user_setting(uid, 'active_prompt_id', prompt_id)
    return jsonify({'status': 'success'})

@app.route('/api/upload/logo', methods=['POST'])
@requires_auth
def upload_logo():
    file = request.files.get('file')
    if file:
        file.save(os.path.join('templates', 'logo.png'))
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/settings/prompt', methods=['POST'])
@requires_auth
def set_prompt():
    text = request.json.get('prompt', '')
    if text:
        database.set_global_setting('system_prompt', text)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/settings/interval', methods=['POST'])
@requires_auth
def set_interval():
    interval = request.json.get('interval', '6')
    database.set_global_setting('smart_queue_interval', interval)
    return jsonify({'status': 'success'})

@app.route('/api/comments', methods=['GET'])
@requires_auth
def get_comments():
    comments = database.get_all_comments()
    return jsonify([{'user': c[0], 'text': c[1]} for c in comments])

@app.route('/api/comments/analyze', methods=['POST'])
@requires_auth
def analyze_comments_api():
    summary = comments_analyzer.analyze_comments()
    return jsonify({'summary': summary})

@app.route('/api/comments/clear', methods=['POST'])
@requires_auth
def clear_comments_api():
    database.clear_comments()
    return jsonify({'status': 'success'})

@app.route('/api/settings/ad', methods=['POST'])
@requires_auth
def set_ad():
    text = request.json.get('text', '')
    database.set_global_setting('ad_text', text)
    return jsonify({'status': 'success'})

@app.route('/api/settings/language', methods=['POST'])
@requires_auth
def set_language():
    lang = request.json.get('lang')
    user_id = request.args.get('user_id')
    if lang in ['uz', 'ru', 'en']:
        database.update_user_setting(int(user_id or config.ADMIN_IDS[0]), 'persona', lang)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/logo.png')
def get_logo():
    path = os.path.join('templates', 'logo.png')
    if os.path.exists(path): return send_file(path, mimetype='image/png')
    return "Not found", 404

@app.route('/api/publish/<int:post_id>', methods=['POST'])
@requires_auth
def api_publish_now(post_id):
    post = database.get_post_by_id(post_id)
    if post and publisher.publish_post_data(bot, post[0], post[1], post[2], post[3], post[4]):
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/stats')
@requires_auth
def get_stats_data():
    channels = database.get_all_managed_channels()
    result = {}
    for ch in channels:
        history = database.get_sub_history(ch)
        result[ch] = {'labels': [h[0] for h in history], 'data': [h[1] for h in history]}
    return jsonify(result)

@app.route('/api/channels', methods=['POST'])
@requires_auth
def api_add_channel():
    username = request.json.get('username')
    if username:
        if not username.startswith('@'): username = '@' + username
        database.add_channel(username)
    return jsonify({'status': 'success'})

@app.route('/api/channels/delete', methods=['POST'])
@requires_auth
def api_remove_channel():
    username = request.json.get('username')
    database.remove_channel(username)
    return jsonify({'status': 'success'})

@app.route('/file/<file_id>')
@requires_auth
def proxy_file(file_id):
    url = get_telegram_file_url(file_id)
    return redirect(url) if url else ("/static/no-image.png", 404)

@app.route('/api/delete/<int:post_id>', methods=['POST'])
@requires_auth
def delete_post(post_id):
    database.delete_from_queue(post_id)
    return jsonify({'status': 'success'})

@app.route('/api/edit/<int:post_id>', methods=['POST'])
@requires_auth
def edit_post(post_id):
    data = request.json
    text = data.get('text')
    channels = data.get('channels', [])
    iso_time = data.get('time')
    try:
        tz = pytz.timezone('Asia/Tashkent')
        dt = datetime.fromisoformat(iso_time)
        timestamp = int(tz.localize(dt).timestamp())
    except: timestamp = data.get('timestamp')
    database.update_post_content(post_id, text, timestamp, ",".join(channels))
    return jsonify({'status': 'success'})

@app.route('/api/reorder', methods=['POST'])
@requires_auth
def reorder():
    order = request.json.get('order')
    if not order: return jsonify({'status': 'error'})
    pending = database.get_all_pending(request.args.get('user_id'))
    existing_timestamps = sorted([p[5] for p in pending if p[5]])
    if len(existing_timestamps) < len(order):
        last_time = existing_timestamps[-1] if existing_timestamps else int(time.time())
        interval = int(database.get_global_setting('smart_queue_interval', '6')) * 3600
        while len(existing_timestamps) < len(order):
            last_time += interval
            existing_timestamps.append(last_time)
    for i, p_id in enumerate(order):
        post = database.get_post_by_id(int(p_id))
        if post: database.update_post_content(post[0], post[2], existing_timestamps[i])
    return jsonify({'status': 'success'})

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
