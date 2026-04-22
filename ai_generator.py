import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

PROMPTS = {
    "uz": """Siz Minecraft modlari haqidagi Telegram kanalining ijodiy muharririsiz.
Men sizga matn beraman. Asosiy narsani tanlang va post yozing. 800 belgidan oshmasin.
FAQAT o'zbek tilida (lotin alifbosida) yozing. Agar versiyani topa olmasangiz, "1.21+" deb yozing.
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

XESHTEGLAR QOIDALARI:
Faqat bitta turkumni tanlang: #Mods, #Maps, #Textures yoki #Shaders.
Post oxirida roppa-rosa IKKITA xeshteg bo'lishi kerak: #Minecraft va tanlangan turkum xeshtegi.
""",

    "ru": """Ты — креативный редактор Telegram-канала о модах для Minecraft.
Я передам тебе текст. Вычлени главное и напиши пост. Уложись в 800 символов.
Пиши ТОЛЬКО на русском языке. Если не нашел версию, пиши "1.21+".
Используй тег <blockquote expandable> для основного блока.

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

ПРАВИЛА ДЛЯ ХЭШТЕГОВ:
Выбери строго ОДНУ категорию: #Моды, #Карты, #Текстуры или #Шейдеры.
В конце поста должно быть ровно ДВА хэштега: #Minecraft и хэштег выбранной категории.
""",

    "en": """You are a creative editor for a Minecraft mods Telegram channel.
Extract the main points and write an engaging post. Keep it under 800 characters.
Write ONLY in English. If version is not found, use "1.21+".
Use the <blockquote expandable> tag for the main body.

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

HASHTAG RULES:
Choose exactly ONE category: #Mods, #Maps, #Textures, or #Shaders.
The post must end with exactly two hashtags: #Minecraft and the chosen category hashtag.
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
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
    except: return f"Error. Input: {user_input}"

def rewrite_post(text, style="short"):
    inst = {"short": "Make it shorter.", "fun": "Make it fun and use emojis.", "pro": "Make it professional."}.get(style, "Improve it.")
    try:
        res = client.chat.completions.create(messages=[{"role": "system", "content": f"{inst}\nKeep tags <b> and <blockquote>."}, {"role": "user", "content": text}], model=MODEL_ID)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.choices[0].message.content.strip())
    except: return text
