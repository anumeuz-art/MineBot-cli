import telebot
import config

# Единый экземпляр бота для всего приложения
# Это решает проблему 409 Conflict, когда бот запускается в нескольких местах
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)