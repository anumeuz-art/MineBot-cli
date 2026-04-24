import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

# Инициализация клиента Groq для работы с ИИ
client = Groq(api_key=config.GROQ_API_KEY)
# Используемая модель ИИ
MODEL_ID = "llama-3.3-70b-versatile"

# Промпт-инструкция для ИИ. Определяет роль, стиль и структуру поста.
# Содержит список разрешенных хэштегов и пример разметки HTML для Telegram.
PROMPT_TEMPLATE = """
Sen Minecraft modlari bo'yicha Telegram kanali muharririsan. Quyidagi ma'lumotlar asosida post yoz.
'#Mods', '#Maps', '#Textures', '#Shaders', '#Addons', '#Mobs', '#Biomes', '#Structures', '#Survival', '#Magic', '#Armor', '#Tools', '#Furniture', '#Redstone', '#Utility', '#Building', '#Horror', '#Adventure', '#FPS', '#UI', '#Guns', '#Vehicles', 
'#Multiplayer', '#Singleplayer', '#Custom', '#Vanilla', '#Fun', '#Realistic', '#Fantasy', '#SciFi', '#Historical', '#Nature', '#City', '#Space', '#Underwater', '#Animals', '#Tech', '#Combat', '#Farming', '#Roleplay', '#MiniGames',
Shu xeshteglarni postga mos ravishda qo'sh. Post qisqa, lekin ma'lumotga boy bo'lsin.
Format va uslubni quyidagidek saqla:

Struktura:
📦 <b>[Mod/Karta nomi]</b>

<blockquote expandable><b>Nima bu? ✨</b>
[Hayajonli va emojilarga boy tavsif]

<b>Asosiy imkoniyatlar: 🛠</b>
• [Fakt 1 🔥]
• [Fact 2 💎]
• [Fact 3 🚀]</blockquote>

<blockquote>Sizga yoqdimi? 😎
🔥 — Albatta! / 🌚 — Shunchaki...</blockquote>

#Minecraft #[Xeshteg1] #[Xeshteg2] #[Xeshteg3] #[Xeshteg4]

💎 Obuna bo'ling: @Lazikomods
"""

def extract_url(text):
    """Извлекает первую найденную URL-ссылку из текста."""
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    """Загружает содержимое страницы по ссылке и очищает его от скриптов/стилей для передачи в ИИ."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Удаляем лишние теги, которые не несут смысловой нагрузки для описания мода
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:3000]
    except: return ""

def limit_hashtags(text, limit=5):
    """
    Очищает текст от избыточного количества хэштегов.
    Оставляет максимум 5 уникальных тегов, где #Minecraft всегда первый.
    """
    lines = text.strip().split('\n')
    main_body = []
    hashtags = []
    
    hashtag_pattern = re.compile(r'#\w+')
    
    for line in lines:
        found_in_line = hashtag_pattern.findall(line)
        # Если строка состоит только из хэштегов, собираем их в список
        if found_in_line and len(line.strip().replace(' ', '')) == sum(len(h) for h in found_in_line):
            for h in found_in_line:
                if h not in hashtags:
                    hashtags.append(h)
        else:
            main_body.append(line)

    # Если хэштеги были вплетены в текст, а не в конце, извлекаем их
    if not hashtags:
        all_tags = hashtag_pattern.findall(text)
        for h in all_tags:
            if h not in hashtags:
                hashtags.append(h)

    # Формируем финальный список: #Minecraft + остальные до лимита
    final_tags = []
    if '#Minecraft' in hashtags:
        final_tags.append('#Minecraft')
        hashtags.remove('#Minecraft')
    
    final_tags.extend(hashtags[:limit - len(final_tags)])
    
    # Очищаем основной текст от хэштегов в самом конце
    clean_body = "\n".join(main_body).strip()
    clean_body = re.sub(r'(#\w+\s*)+$', '', clean_body).strip()
    
    return clean_body + "\n\n" + " ".join(final_tags)

def generate_post(user_input, persona="uz"):
    """Основная функция генерации поста через Groq API."""
    url = extract_url(user_input)
    site_content = fetch_page_content(url) if url else ""
    
    # Формируем полный промпт, объединяя шаблон и входные данные
    prompt = f"{PROMPT_TEMPLATE}\n\nMa'lumot:\n{user_input}\n{site_content}"
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # Пост-обработка для контроля количества хэштегов
        gen = limit_hashtags(gen)
        
        # Добавляем рекламную подпись, если она настроена в БД
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text and ad_text not in gen:
            gen += f"\n\n{ad_text}"
            
        return gen
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    """Переписывает уже готовый текст в заданном стиле (коротко/подробно)."""
    try:
        prompt = f"Перепиши этот пост про Minecraft мод, сделай его {style}. Сохрани структуру и эмодзи. Вот текст:\n\n{text}"
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error rewriting: {e}"
