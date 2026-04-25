import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

# Инициализация клиента Groq
client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

# ГЛОБАЛЬНЫЙ ШАБЛОН ОФОРМЛЕНИЯ (Неизменяемая часть)
# Это гарантирует, что ИИ всегда будет использовать HTML и правильную структуру.
BASE_FORMATTING = """
STRICT FORMATTING RULES:
1. Use HTML tags: <b>name</b>, <i>text</i>.
2. Use <blockquote expandable> for description.
3. Use <blockquote> for engaging questions/polls.
4. Keep it concise but exciting.
5. Add relevant emojis.
6. Include 3-5 relevant hashtags at the end, but no more.
7. Do NOT include any hashtags that are not related to the topic.
Quyidagi ma'lumotlar asosida post yoz. Bu xeshteglarni faqat minecraft modlari uchun ishlat:
'#Mods', '#Maps', '#Textures', '#Shaders', '#Addons', '#Mobs', '#Biomes', '#Structures', '#Survival', '#Magic', '#Armor', '#Tools', '#Furniture', '#Redstone', '#Utility', '#Building', '#Horror', '#Adventure', '#FPS', '#UI', '#Guns', '#Vehicles', 
'#Multiplayer', '#Singleplayer', '#Custom', '#Vanilla', '#Fun', '#Realistic', '#Fantasy', '#SciFi', '#Historical', '#Nature', '#City', '#Space', '#Underwater', '#Animals', '#Tech', '#Combat', '#Farming', '#Roleplay', '#MiniGames',
Shu xeshteglarni postga mos ravishda qo'sh. Post qisqa, lekin ma'lumotga boy bo'lsin.

Example structure:
📦 <b>[Post Title]</b>

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
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:3000]
    except: return ""

def limit_hashtags(text, limit=5):
    hashtag_pattern = re.compile(r'#\w+')
    all_tags = hashtag_pattern.findall(text)
    unique_tags = []
    for t in all_tags:
        if t not in unique_tags: unique_tags.append(t)
    
    clean_body = re.sub(r'(#\w+\s*)+$', '', text).strip()
    return clean_body + "\n\n" + " ".join(unique_tags[:limit])

def improve_prompt(short_desc):
    try:
        instruction = f"Role: Expert Prompt Engineer. Task: Convert this idea into a detailed System Prompt for a Telegram AI Editor. Description: {short_desc}"
        res = client.chat.completions.create(messages=[{"role": "user", "content": instruction}], model=MODEL_ID)
        return res.choices[0].message.content.strip()
    except Exception as e: return f"Error: {e}"

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_content = fetch_page_content(url) if url else ""
    
    lang_map = {'uz': "O'zbek tilida", 'ru': "на русском языке", 'en': "in English"}
    target_lang = lang_map.get(persona, "O'zbek tilida")

    # Получаем активный промпт (Тему) из БД
    active_prompt_id = database.get_user_setting(config.ADMIN_IDS[0], 'active_prompt_id', '1')
    active_topic = database.get_prompt_by_id(active_prompt_id) or "You are a Minecraft Editor."

    # СОЕДИНЯЕМ ТЕМУ И ШАБЛОН
    full_system_prompt = f"""
    PERSONALITY & TOPIC:
    {active_topic}

    {BASE_FORMATTING}

    TASK: Write a post strictly {target_lang}.
    """

    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": full_system_prompt},
                      {"role": "user", "content": f"Input: {user_input}\nContext: {site_content}"}],
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        gen = limit_hashtags(gen)
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text and ad_text not in gen: gen += f"\n\n{ad_text}"
        return gen
    except Exception as e: return f"Error: {e}"

def translate_post(text, target_persona="uz"):
    try:
        lang_map = {'uz': "O'zbek tili", 'ru': "Русский язык", 'en': "English"}
        prompt = f"Translate this Telegram post strictly to {lang_map.get(target_persona)}. Keep all HTML tags like <b>, <blockquote>. Text:\n\n{text}"
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        return res.choices[0].message.content.strip()
    except Exception as e: return f"Error: {e}"

def generate_reply(comment_text, persona="uz"):
    try:
        personality = {
            'uz': "Siz @Lazikomods moderatormiz. Juda do'stona va qisqa javob bering.",
            'ru': "Ты модератор канала @Lazikomods. Отвечай кратко, используй сленг.",
            'en': "You are a moderator of @Lazikomods. Be brief and friendly."
        }
        prompt = f"{personality.get(persona)} User said: \"{comment_text}\". Reply briefly."
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        return res.choices[0].message.content.strip()
    except: return None
