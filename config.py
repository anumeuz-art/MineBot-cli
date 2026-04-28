import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_IDS = [5703605946] # Твой ID администратора
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CURSEFORGE_API_KEY = os.getenv("CURSEFORGE_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_TOKEN не установлен!")
if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY is not set. AI functions might fail.")
if not GEMINI_KEY:
    print("⚠️ WARNING: GEMINI_KEY is not set.")
if not CURSEFORGE_API_KEY:
    print("⚠️ WARNING: CURSEFORGE_API_KEY is not set. CurseForge integration will not work.")

CHANNELS_STR = os.getenv("CHANNELS", "@lazikomods")
AVAILABLE_CHANNELS = [ch.strip() for ch in CHANNELS_STR.split(',')]
DEFAULT_CHANNEL = AVAILABLE_CHANNELS[0] if AVAILABLE_CHANNELS else ""

WATERMARK_TEXT = "@lazikomods"

# 🧠 НОВАЯ НАСТРОЙКА: Интервал умной очереди (в часах)
SMART_QUEUE_INTERVAL_HOURS = 6