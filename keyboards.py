from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import config
import database
import utils

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("📝 Создать пост"))
    # Кнопка открытия Web App (теперь единственная точка управления всеми настройками)
    markup.add(KeyboardButton("🌐 Открыть панель", web_app=WebAppInfo(url="https://hospitable-clarity-production-3350.up.railway.app")))
    return markup

def get_cancel_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("❌ Отмена"))
    return markup

def get_draft_markup(draft_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"🧠 Умная очередь (+{getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 6)} ч)", callback_data="add_to_smart_q")
    )
    markup.add(
        InlineKeyboardButton("🚀 Сейчас", callback_data="pub_now"),
        InlineKeyboardButton("📅 Позже", callback_data="pub_queue_menu")
    )
    markup.add(
        InlineKeyboardButton("✏️ Правка", callback_data="edit_text"),
        InlineKeyboardButton("✨ Переписать", callback_data="rewrite_menu")
    )
    markup.add(
        InlineKeyboardButton("❌ Удалить", callback_data="cancel_action")
    )
    return markup

def show_queue_page(bot, chat_id, page, message_id=None):
    posts = database.get_all_pending()
    if not posts:
        text = "📭 Очередь пуста. Управляйте постами в панели управления."
        if message_id: bot.edit_message_text(text, chat_id, message_id)
        else: bot.send_message(chat_id, text)
        return
    # Оставляем логику для совместимости, но кнопка в боте больше не ведет сюда
