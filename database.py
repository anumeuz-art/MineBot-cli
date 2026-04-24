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

# --- Функции для работы с глобальными настройками ---
def set_global_setting(key, value):
    """Сохраняет глобальную настройку (например, текст рекламы)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO global_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_global_setting(key, default=""):
    """Получает значение глобальной настройки."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM global_settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

# --- Функции управления каналами ---
def add_channel(username):
    """Добавляет канал в список управляемых."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO managed_channels (username) VALUES (?)", (username,))
        conn.commit()
    finally: conn.close()

def remove_channel(username):
    """Удаляет канал из списка."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM managed_channels WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_all_managed_channels():
    """Возвращает список всех usernames каналов."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM managed_channels")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# --- Функции сбора статистики ---
def save_sub_count(channel_id, count):
    """Сохраняет количество подписчиков на текущую дату."""
    date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO stats_subscribers (channel_id, count, date) VALUES (?, ?, ?)", (channel_id, count, date))
    conn.commit()
    conn.close()

def save_post_views(post_id, views):
    """Сохраняет количество просмотров конкретного поста."""
    date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO stats_posts (post_id, views, date) VALUES (?, ?, ?)", (post_id, views, date))
    conn.commit()
    conn.close()

# --- Настройки пользователя (язык, персона ИИ и т.д.) ---
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

# --- Работа с очередью постов ---
def add_to_queue(photo_id, text, document_id=None, channel_id=None, scheduled_time=None):
    """Добавляет новый пост в очередь на публикацию."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time) VALUES (?, ?, ?, ?, ?)", 
              (photo_id, text, document_id, channel_id, scheduled_time))
    conn.commit()
    conn.close()

def get_ready_posts():
    """Выбирает все посты, время публикации которых наступило."""
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
    """Помечает пост как опубликованный."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE queue SET status='posted' WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def delete_from_queue(post_id):
    """Удаляет пост из очереди."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM queue WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

# Инициализируем БД при импорте модуля
init_db()
