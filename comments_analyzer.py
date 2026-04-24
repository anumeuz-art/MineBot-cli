import config
import database
from groq import Groq

# Инициализация Groq
client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

def analyze_comments():
    """Собирает комментарии из БД и просит Groq сделать выжимку"""
    comments = database.get_all_comments()
    
    if not comments:
        return "📭 Пока нет новых комментариев от подписчиков."

    # Собираем все комментарии в один текст
    comments_text = "\n".join([f"- {c[0]}: {c[1]}" for c in comments])

    # Инструкция для ИИ
    prompt = f"""
    Ты — аналитик Telegram-канала о модах Minecraft.
    Ниже приведены сообщения из чата. 
    ВАЖНО: В списке могут быть как комментарии пользователей, так и описания модов от самого канала.
    Твоя задача: 
    1. ИГНОРИРУЙ любые описания модов (длинные тексты с пунктами, хештегами и т.д.).
    2. ФОКУСИРУЙСЯ только на реальных запросах пользователей (например: "нужен мод на машины", "сделайте карту города", "спасибо за мод").
    3. Сгруппируй пожелания и укажи количество просящих.

    Формат ответа (используй эмодзи):
    💡 Конкретные запросы (моды/карты/шейдеры):
    - [Суть запроса] (X человек)
    
    💬 Общая обратная связь и благодарности:
    - ...

    ⚠️ Жалобы (если есть):
    - ...

    Сообщения для анализа:
    {comments_text}
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=MODEL_ID,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка ИИ при анализе: {e}")
        return "❌ Произошла ошибка при анализе комментариев ИИ через Groq."
