import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database
import curseforge_api # Импорт нового модуля

# Инициализация клиента Groq для работы с ИИ
client = Groq(api_key=config.GROQ_API_KEY)
# Используемая модель ИИ
MODEL_ID = "llama-3.3-70b-versatile"

# ... (остальной код PROMPT_TEMPLATE и другие функции)

def generate_post(user_input, persona="uz"):
    """Основная функция генерации поста через Groq API с поддержкой CurseForge API."""
    url = extract_url(user_input)
    
    # ИНТЕГРАЦИЯ CURSEFORGE
    cf_data = ""
    if url and "curseforge.com" in url:
        # Пытаемся извлечь modId из ссылки (упрощенно)
        # Пример: .../mods/just-enough-items -> обычно ID не в ссылке, 
        # нам нужно найти мод по названию из ссылки или доработать извлечение
        mod_name = url.split('/')[-1].replace('-', ' ')
        mod = curseforge_api.search_mod(mod_name)
        if mod:
            cf_data = f"CURSEFORGE DATA: Name: {mod['name']}, Summary: {mod['summary']}, Features: {mod.get('description', '')[:500]}"

    site_content = fetch_page_content(url) if url and not cf_data else ""
    
    # Получаем промпт из БД
    db_prompt = database.get_active_prompt()
    effective_prompt_template = db_prompt if db_prompt else PROMPT_TEMPLATE

    # Определяем язык вывода
    lang_map = {
        'uz': "O'zbek tilida (Uzbek)",
        'ru': "на русском языке (Russian)",
        'en': "in English"
    }
    target_lang = lang_map.get(persona, "O'zbek tilida")

    # Формируем полный промпт
    prompt = f"TASK: Write a Minecraft mod post strictly {target_lang}.\n\n{effective_prompt_template}\n\nDATA TO PROCESS:\n{user_input}\n{cf_data}\n{site_content}\n\nREMINDER: The entire post must be {target_lang}."
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # Пост-обработка
        gen = limit_hashtags(gen)
        
        # Добавляем рекламную подпись
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text and ad_text not in gen:
            gen += f"\n\n{ad_text}"
            
        return gen
    except Exception as e:
        return f"Error: {e}"


def translate_post(text, target_persona="uz"):
    """Переводит готовый пост на другой язык, сохраняя всю HTML разметку и эмодзи."""
    try:
        lang_map = {
            'uz': "O'zbek tili (Uzbek)",
            'ru': "Русский язык (Russian)",
            'en': "English"
        }
        target_lang = lang_map.get(target_persona, "English")
        
        prompt = f"Translate this Telegram post strictly to {target_lang}. Keep all HTML tags like <b>, <blockquote>, <blockquote expandable> exactly as they are. Do not remove any emojis. Text to translate:\n\n{text}"
        
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Translation error: {e}"

def generate_reply(comment_text, persona="uz"):
    """Генерирует живой, человечный ответ на комментарий пользователя."""
    try:
        # Инструкции для разных языков, чтобы сохранить "вайб"
        personality = {
            'uz': "Siz Minecraft fanatisiz va @Lazikomods kanalida moderatormiz. Juda do'stona, samimiy va qisqa javob bering. 'Imba', 'Gap yo'q', 'Zo'r' kabi so'zlarni ishlating. Robotdek gapirmang.",
            'ru': "Ты — фанат Майнкрафта и модератор канала @Lazikomods. Отвечай как живой человек: используй сленг (имба, годно, топ, чекай), будь на позитиве. Никакого официоза и фраз типа 'чем я могу вам помочь'.",
            'en': "You are a Minecraft fan and moderator of @Lazikomods. Reply like a real human: use slang (cool, sick, OP, lit), be energetic and very brief. Don't sound like a robot or a support agent."
        }

        selected_personality = personality.get(persona, personality['uz'])
        lang_map = {'uz': "O'zbek tilida", 'ru': "на русском языке", 'en': "in English"}
        target_lang = lang_map.get(persona, "O'zbek tilida")

        prompt = f"""
        {selected_personality}
        Foydalanuvchi yozdi: "{comment_text}"

        Vazifa: Ushbu xabarga {target_lang} qisqa (1 ta gap) javob ber. 
        Agar rahmat aytsa — xursand bo'l. Agar savol so'rasa — do'stona javob ber.
        Faqat matn, xeshteglar kerak emas.
        """

        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        return res.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        return None

def generate_suggestion_request(persona="uz"):
    """Генерирует пост с запросом предложений от подписчиков."""
    try:
        lang_map = {'uz': "O'zbek tilida", 'ru': "на русском языке", 'en': "in English"}
        target_lang = lang_map.get(persona, "O'zbek tilida")

        prompt = f"""
        Minecraft kanali uchun qisqa va qiziqarli post yoz. 
        Maqsad: Obunachilardan qanday modlar, karta yoki teksturalar ko'rishni xohlashlarini so'rash.
        Stil: Do'stona, emojilarga boy.
        Til: {target_lang}.
        Post oxirida obunachilarni kommentariyada yozishga unda.
        HTML teglaridan foydalan (<b>, <i>).
        """

        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return None
