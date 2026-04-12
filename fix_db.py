import sqlite3
import os

db_path = 'work/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main/bot_data.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE user_settings SET lang = 'uz' WHERE lang = 'menu'")
    print(f"Fixed {c.rowcount} rows in database.")
    conn.commit()
    conn.close()
else:
    print("Database not found.")
