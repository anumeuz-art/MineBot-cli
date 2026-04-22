import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

VALID_CATS = [
    '#Mods', '#Maps', '#Textures', '#Shaders', '#Furniture', '#Tools', '#Mobs', 
    '#Biomes', '#Redstone', '#Magic', '#Structures', '#Armor', '#FPS', '#UI', 
    '#Addons', '#Building', '#Survival', '#Horror', '#Adventure', '#Utility'
]

CAT_LIST = ', '.join(VALID_CATS)

PROMPTS = {
    "uz": """Siz Minecraft muharririsiz. FAQAT o'zbek tilida yozing. 800 belgidan oshmasin.
Asosiy blok uchun <blockquote expandable> tegidan foydalaning.

Format:
📦 <b>[Nomi]</b>

<blockquote expandable><b>Bu nima?</b>
[Tavsif]

<b>Asosiy xususiyatlar:</b>
• [Xususiyat 1]
• [Xususiyat 2]

🎮 Versiya: [Versiya]</blockquote>

<blockquote>💖 - Zo'r
💔 - Unchamas</blockquote>

HECH QANDAY XESHTEG YOZING! (Men o'zim qo'shaman).
""",

    "ru": """Ты — редактор канала о Minecraft. Пиши на РУССКОМ. До 800 симв.
Используй <blockquote expandable> для описания.

Формат:
📦 <b>[Название]</b>

<blockquote expandable><b>Что это такое?</b>
[Описание]

<b>Главные фишки:</b>
• [Фишка 1]
• [Фишка 2]

🎮 Версия: [Версия]</blockquote>

<blockquote>💖 - Имба
💔 - Не оч</blockquote>

НЕ ПИШИ ХЭШТЕГИ! (Я добавлю их сам).
""",

    "en": """Minecraft editor. English only. Max 800 chars.
Use <blockquote expandable> for description.

Format:
📦 <b>[Mod Name]</b>

<blockquote expandable><b>What is it?</b>
[Description]

<b>Key Features:</b>
• [Feature 1]
• [Feature 2]

🎮 Version: [Version]</blockquote>

<blockquote>💖 - Awesome
💔 - Not great</blockquote>

DO NOT WRITE HASHTAGS! (I will add them myself).
"""
}

def extract_url(text):
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:5000]
    except: return ""

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_context = ""
    if url:
        text = fetch_page_content(url)
        if text: site_context = f"\n\nINFO FROM SITE:\n{text}"
    
    # Вставляем список категорий динамически через replace
    prompt = PROMPTS.get(persona, PROMPTS['uz']).replace("[Turkum]", CAT_LIST)
    prompt = f"{prompt}\n\nRaw info:\n{user_input}{site_context}"
    
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        gen = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
        
        # Строгая проверка хэштегов
        tags = re.findall(r'#\w+', gen)
        found_cat = None
        for t in tags:
            if t in VALID_CATS: found_cat = t
            elif t != '#Minecraft': gen = gen.replace(t, "")
        
        if '#Minecraft' not in gen: gen += "\n#Minecraft"
        if not found_cat: gen += " #Mods"
        else: gen += f" {found_cat}"
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: gen += f"\n\n{ad_text}"
        return gen.strip()
    except: return f"Error. Input: {user_input}"

def rewrite_post(text, style="short"):
    inst = {"short": "Shorter.", "fun": "Fun.", "pro": "Professional."}.get(style, "Improve.")
    try:
        res = client.chat.completions.create(messages=[{"role": "system", "content": f"{inst} Keep HTML tags."}, {"role": "user", "content": text}], model=MODEL_ID)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
    except: return text
