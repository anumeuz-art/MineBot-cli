import sqlite3
import os

dbs = [
    'work/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main/bot_data.db',
    'mine_bot_tg-main_backup/bot_data.db'
]

for db in dbs:
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            # Проверяем наличие таблицы
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'")
            if c.fetchone():
                c.execute("UPDATE user_settings SET lang = 'uz' WHERE lang = 'menu'")
                print(f"Fixed {c.rowcount} rows in {db}")
                conn.commit()
            else:
                print(f"No user_settings table in {db}")
            conn.close()
        except Exception as e:
            print(f"Error in {db}: {e}")
    else:
        print(f"Database {db} not found.")
