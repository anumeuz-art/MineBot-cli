from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config
import database
import utils

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📝 Создать пост"))
    markup.add(KeyboardButton("🌍 Выбор языка"), KeyboardButton("📢 Выбор канала"))
    markup.add(KeyboardButton("➕ Добавить канал"), KeyboardButton("📊 Статус очереди"))
    markup.add(KeyboardButton("💰 Реклама"))
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
        text = "📭 Очередь пуста."
        if message_id: bot.edit_message_text(text, chat_id, message_id)
        else: bot.send_message(chat_id, text)
        return

    if page >= len(posts): page = len(posts) - 1
    if page < 0: page = 0

    msg_text = f"🕒 <b>В очереди: {len(posts)} постов</b>\n\n"
    msg_text += utils.format_queue_post(posts[page], page + 1, len(posts))

    markup = InlineKeyboardMarkup(row_width=2)
    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️ Пред.", callback_data=f"q_page_{page-1}"))
    if page < len(posts) - 1: nav_row.append(InlineKeyboardButton("След. ➡️", callback_data=f"q_page_{page+1}"))
    if nav_row: markup.add(*nav_row)

    markup.add(
        InlineKeyboardButton("🚀 Выпустить сейчас", callback_data=f"q_pub_{posts[page][0]}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"q_del_{posts[page][0]}")
    )

    if message_id:
        try: bot.edit_message_text(msg_text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
        except Exception: pass
    else:
        bot.send_message(chat_id, msg_text, parse_mode='HTML', reply_markup=markup)
