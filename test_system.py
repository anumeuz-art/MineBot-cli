import os
import sys
import sqlite3
import requests
import config

def test_paths():
    print("--- 📂 PATH CHECK ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Base Directory: {base_dir}")
    for root, dirs, files in os.walk(base_dir):
        if "launcher.py" in files:
            print(f"✅ FOUND launcher.py at: {root}")
    print("----------------------\n")

def test_db():
    print("--- 💾 DATABASE CHECK ---")
    try:
        import database
        database.init_db()
        conn = database.get_db_connection()
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print(f"✅ DB Connected. Tables: {[r['name'] for r in res]}")
    except Exception as e:
        print(f"❌ DB Error: {e}")
    print("--------------------------\n")

def test_ai():
    print("--- 🤖 AI API CHECK ---")
    if not config.TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN is missing!")
    else:
        print("✅ TELEGRAM_TOKEN found.")
    
    if not config.GEMINI_KEY:
        print("⚠️ GEMINI_KEY is missing (Check your environment variables)")
    else:
        print("✅ GEMINI_KEY found.")
    print("------------------------\n")

if __name__ == "__main__":
    test_paths()
    test_db()
    test_ai()
