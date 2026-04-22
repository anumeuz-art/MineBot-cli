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
    Ниже приведены комментарии пользователей из чата канала.
    Твоя задача — проанализировать их и составить краткую и понятную выжимку.
    
    Сгруппируй одинаковые запросы. Укажи количество людей, просящих одно и то же.
    Игнорируй спам, бессмысленные сообщения и обычное общение (типа "привет", "как дела", "круто").

    Формат ответа (используй эмодзи):
    💡 Запросы на моды/карты/шейдеры:
    - [Название или суть] (просили X человек)
    
    ⚠️ Проблемы и жалобы (если есть):
    - ...
    
    💬 Интересные идеи:
    - ...

    Комментарии для анализа:
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
