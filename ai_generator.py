import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

VALID_TAGS = [
    '#Mods', '#Maps', '#Textures', '#Shaders', '#Furniture', '#Tools', '#Mobs', '#Guns', '#Vehicles', '#Food',
    '#Biomes', '#Redstone', '#Magic', '#Structures', '#Armor', '#FPS', '#UI', 
    '#Addons', '#Building', '#Survival', '#Horror', '#Adventure', '#Utility'
]

PROMPTS = {
    "uz": f"""Siz Minecraft muharririsiz. FAQAT o'zbek tilida yozing. 800 belgidan oshmasin.
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

#Minecraft #[Turkum]

XESHTEGLAR QOIDASI:
Ro'yxatdan faqat BITTA turkumni tanlang: {", ".join(VALID_TAGS[:-1])}.
Oxirida faqat IKKITA xeshteg bo'lsin: #Minecraft va tanlangan turkum.
""",

    "ru": f"""Ты — редактор канала о Minecraft. Пиши на РУССКОМ. До 800 симв.
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

#Minecraft #[Категория]

ПРАВИЛО ХЭШТЕГОВ:
Выбери только ОДНУ категорию из списка: {", ".join(VALID_TAGS[:-1])}.
В конце должно быть ровно ДВА хэштега: #Minecraft и категория.
""",

    "en": f"""Minecraft editor. English only. Max 800 chars.
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

#Minecraft #[Category]

HASHTAG RULE:
Select exactly ONE from: {", ".join(VALID_TAGS[:-1])}.
Only TWO hashtags at the end: #Minecraft and the category.
"""
}

def extract_url(text):
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
    
    prompt = f"{PROMPTS.get(persona, PROMPTS['uz'])}\n\nRaw info:\n{user_input}{site_context}"
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        generated = res.choices[0].message.content.strip()
        generated = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', generated)
        
        # Строгая очистка хэштегов
        all_tags = re.findall(r'#\w+', generated)
        for t in all_tags:
            if t not in VALID_TAGS:
                generated = generated.replace(t, "")
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: generated += f"\n\n{ad_text}"
        return generated
    except: return f"Error. Input: {user_input}"

def rewrite_post(text, style="short"):
    inst = {"short": "Shorter.", "fun": "Fun.", "pro": "Professional."}.get(style, "Improve.")
    try:
        res = client.chat.completions.create(messages=[{"role": "system", "content": f"{inst} Keep HTML tags."}, {"role": "user", "content": text}], model=MODEL_ID)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
    except: return text
