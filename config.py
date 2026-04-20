import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_IDS = [5703605946] # Твой ID администратора
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

if not TELEGRAM_TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN is not set in environment variables!")
if not GEMINI_KEY:
    print("❌ ERROR: GEMINI_KEY is not set in environment variables!")

CHANNELS_STR = os.getenv("CHANNELS", "@lazikomods")
AVAILABLE_CHANNELS = [ch.strip() for ch in CHANNELS_STR.split(',')]
DEFAULT_CHANNEL = AVAILABLE_CHANNELS[0] if AVAILABLE_CHANNELS else ""

WATERMARK_TEXT = "@lazikomods"

# 🧠 НОВАЯ НАСТРОЙКА: Интервал умной очереди (в часах)
SMART_QUEUE_INTERVAL_HOURS = 8