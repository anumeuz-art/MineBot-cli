import sqlite3
import os

dbs = [
    "D:/mine_bot/mine_bot_tg-main_backup/bot_data.db",
    "D:/mine_bot/work/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main/bot_data.db",
    "D:/mine_bot/work/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main/mine_bot_tg-main_backup/bot_data.db"
]

for db in dbs:
    if not os.path.exists(db):
        print(f"File {db} not found")
        continue
    
    print(f"\n--- Checking {db} ---")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in c.fetchall()]
    print(f"Tables: {tables}")
    
    if 'user_settings' in tables:
        c.execute("SELECT DISTINCT lang FROM user_settings")
        langs = c.fetchall()
        print(f"Distinct languages: {langs}")
        
        c.execute("SELECT COUNT(*) FROM user_settings WHERE lang = 'menu'")
        count = c.fetchone()[0]
        if count > 0:
            print(f"⚠️ Found {count} users with lang='menu'!")
            c.execute("SELECT * FROM user_settings WHERE lang = 'menu'")
            for row in c.fetchall():
                print(row)
    
    conn.close()
