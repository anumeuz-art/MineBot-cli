import telebot
from apscheduler.schedulers.background import BackgroundScheduler
import time
import config
import database
import publisher
import handlers

# Инициализация бота
database.init_db()
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

# Глобальные кеши
user_drafts = {}
album_cache = {}

# Регистрация всех обработчиков из модуля handlers
handlers.register_handlers(bot, user_drafts, album_cache)

# Настройка планировщика для очереди постов
scheduler = BackgroundScheduler()
scheduler.add_job(publisher.process_queue, 'interval', minutes=1, args=[bot])
scheduler.start()

if __name__ == "__main__":
    print("Бот Mine Bot запущен и готов к работе!")
    while True:
        try:
            bot.polling(none_stop=True, timeout=90)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)
