import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

PROMPTS = {
    "uz": """Siz Minecraft modlari haqidagi Telegram kanalining muharririsiz.
FAQAT o'zbek tilida (lotin alifbosida) yozing. 800 belgidan oshmasin.
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

XESHTEGLAR QOIDASI (JUDA MUHIM):
1. Faqat bitta turkumni tanlang: #Mods, #Maps, #Textures yoki #Shaders.
2. Post oxirida FAQAT IKKITA xeshteg bo'lishi kerak: #Minecraft va tanlangan turkum.
3. Boshqa xeshteg qo'shmang! Mod nomini xeshteg qilmang!
""",

    "ru": """Ты — редактор канала о модах для Minecraft.
Пиши ТОЛЬКО на русском языке. Уложись в 800 символов.
Используй тег <blockquote expandable> для описания.

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

ПРАВИЛО ХЭШТЕГОВ (КРИТИЧНО):
1. Выбери только ОДНУ категорию: #Mods, #Maps, #Textures или #Shaders.
2. В конце должно быть ровно ДВА хэштега: #Minecraft и категория.
3. НИКАКИХ других хэштегов. Название мода хэштегом делать нельзя.
""",

    "en": """Minecraft mods channel editor. English only. Max 800 chars.
Use <blockquote expandable> tag for the main body.

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

HASHTAG RULE (VERY IMPORTANT):
1. Select exactly ONE: #Mods, #Maps, #Textures, or #Shaders.
2. End the post with ONLY TWO hashtags: #Minecraft and the category.
3. No other hashtags allowed. Do not use mod names as hashtags.
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
        
        # Автоматическая очистка лишних хэштегов (защита от "фантазии" ИИ)
        # Оставляем только разрешенные
        valid_cats = ['#Mods', '#Maps', '#Textures', '#Shaders', '#Minecraft']
        tags = re.findall(r'#\w+', generated)
        for t in tags:
            if t not in valid_cats:
                generated = generated.replace(t, "")
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: generated += f"\n\n{ad_text}"
        return generated
    except: return f"Error. Input: {user_input}"

def rewrite_post(text, style="short"):
    inst = {"short": "Make it shorter.", "fun": "Make it fun.", "pro": "Make it professional."}.get(style, "Improve it.")
    try:
        res = client.chat.completions.create(messages=[{"role": "system", "content": f"{inst} Keep HTML tags."}, {"role": "user", "content": text}], model=MODEL_ID)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
    except: return text
