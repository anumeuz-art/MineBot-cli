import sqlite3
import time

def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  photo_id TEXT,
                  text TEXT,
                  document_id TEXT,
                  status TEXT DEFAULT 'pending')''')
    
    # Безопасно добавляем новые колонки, если их нет
    try:
        c.execute("ALTER TABLE queue ADD COLUMN channel_id TEXT")
    except sqlite3.OperationalError:
        pass 
    
    try:
        c.execute("ALTER TABLE queue ADD COLUMN scheduled_time INTEGER")
    except sqlite3.OperationalError:
        pass 
        
    # Таблица для настроек пользователей (канал, язык и т.д.)
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                 (user_id INTEGER,
                  key TEXT,
                  value TEXT,
                  PRIMARY KEY (user_id, key))''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_name TEXT,
                  text TEXT,
                  timestamp INTEGER)''')

    conn.commit()
    conn.close()

def update_user_setting(user_id, key, value):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", 
              (user_id, key, str(value)))
    conn.commit()
    conn.close()

def get_user_setting(user_id, key, default=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE user_id = ? AND key = ?", (user_id, key))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

def add_to_queue(photo_id, text, document_id=None, channel_id=None, scheduled_time=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time) VALUES (?, ?, ?, ?, ?)", 
              (photo_id, text, document_id, channel_id, scheduled_time))
    conn.commit()
    conn.close()

def get_ready_posts():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current_time = int(time.time())
    c.execute('''SELECT id, photo_id, text, document_id, channel_id 
                 FROM queue 
                 WHERE status='pending' AND (scheduled_time IS NULL OR scheduled_time <= ?) 
                 ORDER BY scheduled_time ASC''', (current_time,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_as_posted(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE queue SET status='posted' WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def get_queue_count():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM queue WHERE status='pending'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_pending():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT id, photo_id, text, document_id, channel_id, scheduled_time FROM queue WHERE status='pending' ORDER BY scheduled_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_from_queue(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM queue WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def get_last_scheduled_time():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT scheduled_time FROM queue WHERE status='pending' AND scheduled_time IS NOT NULL ORDER BY scheduled_time DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_stats():
    import pytz
    from datetime import datetime
    conn = sqlite3.connect('bot_data.db')
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

def get_all_posts():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM queue")
    rows = c.fetchall()
    conn.close()
    return rows

def record_published_post(photo_id, text, document_id, channel_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current_time = int(time.time())
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time, status) VALUES (?, ?, ?, ?, ?, 'posted')", 
              (photo_id, text, document_id, channel_id, current_time))
    conn.commit()
    conn.close()

def save_comment(user_name, text, timestamp):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO comments (user_name, text, timestamp) VALUES (?, ?, ?)", 
              (user_name, text, timestamp))
    conn.commit()
    conn.close()

def get_all_comments():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_name, text FROM comments ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def clear_comments():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM comments")
    conn.commit()
    conn.close()

init_db()
