import sqlite3
import os

db_path = "work/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main/bot_data.db"
if not os.path.exists(db_path):
    print(f"File {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT * FROM user_settings WHERE lang = 'menu'")
rows = c.fetchall()
print(f"Found {len(rows)} users with lang='menu'")
for row in rows:
    print(row)

c.execute("SELECT DISTINCT lang FROM user_settings")
langs = c.fetchall()
print(f"Distinct languages: {langs}")

conn.close()
