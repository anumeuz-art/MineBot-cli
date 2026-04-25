import sqlite3
import time
import os
from datetime import datetime

# Путь к файлу базы данных SQLite. 
# Используется папка 'data/', которая обычно мапится на Railway Volume для сохранения данных при перезагрузках.
DB_PATH = 'data/bot_data.db'

def init_db():
    """Инициализация структуры базы данных при запуске приложения."""
    if not os.path.exists('data'):
        os.makedirs('data')
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблица очереди постов: хранит медиа, текст, статус и время публикации
    c.execute('''CREATE TABLE IF NOT EXISTS queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  photo_id TEXT,
                  text TEXT,
                  document_id TEXT,
                  status TEXT DEFAULT 'pending')''')
    
    # Динамическое добавление колонок (для миграции старых БД без удаления данных)
    try: c.execute("ALTER TABLE queue ADD COLUMN channel_id TEXT")
    except: pass
    try: c.execute("ALTER TABLE queue ADD COLUMN scheduled_time INTEGER")
    except: pass
        
    # Таблица индивидуальных настроек пользователей (язык, активный канал)
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                 (user_id INTEGER, key TEXT, value TEXT, PRIMARY KEY (user_id, key))''')

    # Таблица комментариев пользователей (для анализа через Groq)
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, text TEXT, timestamp INTEGER)''')

    # Таблица списка каналов, которыми управляет бот
    c.execute('''CREATE TABLE IF NOT EXISTS managed_channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)''')

    # Статистика подписчиков (срез по дням)
    c.execute('''CREATE TABLE IF NOT EXISTS stats_subscribers
                 (channel_id TEXT, count INTEGER, date TEXT, PRIMARY KEY (channel_id, date))''')

    # Статистика просмотров постов
    c.execute('''CREATE TABLE IF NOT EXISTS stats_posts
                 (post_id INTEGER PRIMARY KEY, views INTEGER, date TEXT)''')

    # Глобальные настройки (рекламный текст и прочее)
    c.execute('''CREATE TABLE IF NOT EXISTS global_settings
                 (key TEXT PRIMARY KEY, value TEXT)''')

    conn.commit()
    conn.close()

# --- Глобальные настройки ---
def set_global_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_global_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM global_settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

# --- Управление каналами ---
def add_channel(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO managed_channels (username) VALUES (?)", (username,))
        conn.commit()
    finally: conn.close()

def remove_channel(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM managed_channels WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_all_managed_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM managed_channels")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# --- Статистика ---
def save_sub_count(channel_id, count):
    date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO stats_subscribers (channel_id, count, date) VALUES (?, ?, ?)", (channel_id, count, date))
    conn.commit()
    conn.close()

def get_sub_history(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT date, count FROM stats_subscribers WHERE channel_id = ? ORDER BY date ASC LIMIT 30", (channel_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def save_post_views(post_id, views):
    date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO stats_posts (post_id, views, date) VALUES (?, ?, ?)", (post_id, views, date))
    conn.commit()
    conn.close()

# --- Настройки пользователя ---
def update_user_setting(user_id, key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, str(value)))
    conn.commit()
    conn.close()

def get_user_setting(user_id, key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE user_id = ? AND key = ?", (user_id, key))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

# --- Очередь ---
def add_to_queue(photo_id, text, document_id=None, channel_id=None, scheduled_time=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time) VALUES (?, ?, ?, ?, ?)", 
              (photo_id, text, document_id, channel_id, scheduled_time))
    conn.commit()
    conn.close()

def get_ready_posts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_time = int(time.time())
    c.execute('''SELECT id, photo_id, text, document_id, channel_id FROM queue 
                 WHERE status='pending' AND (scheduled_time IS NULL OR scheduled_time <= ?) 
                 ORDER BY scheduled_time ASC''', (current_time,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_as_posted(post_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE queue SET status='posted' WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def get_stats():
    import pytz
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM queue")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM queue WHERE status='posted'")
    published = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM queue WHERE status='pending'")
    queue_count = c.fetchone()[0]
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    today_start = int(datetime.now(tashkent_tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    c.execute("SELECT COUNT(*) FROM queue WHERE scheduled_time >= ?", (today_start,))
    today = c.fetchone()[0]
    conn.close()
    return {'total': total, 'published': published, 'queue': queue_count, 'today': today}

def get_all_pending():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, photo_id, text, document_id, channel_id, scheduled_time FROM queue WHERE status='pending' ORDER BY scheduled_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_posts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM queue")
    rows = c.fetchall()
    conn.close()
    return rows

def get_post_by_id(post_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, photo_id, text, document_id, channel_id, scheduled_time, status FROM queue WHERE id = ?", (post_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_post_content(post_id, text, scheduled_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE queue SET text = ?, scheduled_time = ? WHERE id = ?", (text, scheduled_time, post_id))
    conn.commit()
    conn.close()

def delete_from_queue(post_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM queue WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def get_last_scheduled_time():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT scheduled_time FROM queue WHERE status='pending' AND scheduled_time IS NOT NULL ORDER BY scheduled_time DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def record_published_post(photo_id, text, document_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_time = int(time.time())
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time, status) VALUES (?, ?, ?, ?, ?, 'posted')", 
              (photo_id, text, document_id, channel_id, current_time))
    conn.commit()
    conn.close()

def save_comment(user_name, text, timestamp):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO comments (user_name, text, timestamp) VALUES (?, ?, ?)", (user_name, text, timestamp))
    conn.commit()
    conn.close()

def get_all_comments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_name, text FROM comments ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def clear_comments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM comments")
    conn.commit()
    conn.close()

init_db()
