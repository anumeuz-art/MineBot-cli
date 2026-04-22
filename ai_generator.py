import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

# Теперь промпты нацелены на максимальную информативность
PROMPTS = {
    "uz": """Siz Minecraft modlari muharririsiz. 
Matn berilganda batafsil va qiziqarli post yozing. 
MUHIM: Iloji boricha ko'proq ma'lumot bering (xususiyatlar, o'zgarishlar, o'yin jarayoni). 
Faqat o'zbek tilida yozing. Asosiy blok uchun <blockquote> tegidan foydalaning.

Format:
📦 <b>[Nomi]</b>

<blockquote><b>Bu nima?</b>
[Batafsil tavsif, 4-5 qator]

<b>Asosiy xususiyatlar:</b>
• [Batafsil xususiyat 1]
• [Batafsil xususiyat 2]
• [Batafsil xususiyat 3]
• [Batafsil xususiyat 4]

🎮 Versiya: [Versiya]</blockquote>

<blockquote>💖 - Zo'r
💔 - Unchamas</blockquote>

#Minecraft #[Mod_nomi_yoki_kategoriyasi] #[Qo'shimcha_teg]
""",
    "ru": """Ты — редактор канала о модах для Minecraft. 
При создании поста пиши МАКСИМАЛЬНО подробно. Описывай не только суть, но и детали, атмосферу, влияние на геймплей.
Используй <blockquote> для описания.

Формат:
📦 <b>[Название]</b>

<blockquote><b>Что это такое?</b>
[Развернутое описание, 4-5 строк]

<b>Главные фишки:</b>
• [Детальная фишка 1]
• [Детальная фишка 2]
• [Детальная фишка 3]
• [Детальная фишка 4]

🎮 Версия: [Версия]</blockquote>

<blockquote>💖 - Имба
💔 - Не оч</blockquote>

#Minecraft #[Категория] #[Доп_тег]
""",
    "en": """You are a Minecraft mods channel editor. 
Write DETAILED and engaging posts. Provide as much info as possible (features, gameplay impact, atmosphere).
Use <blockquote> for description.

Format:
📦 <b>[Mod Name]</b>

<blockquote><b>What is it?</b>
[Detailed description, 4-5 lines]

<b>Key Features:</b>
• [Detailed feature 1]
• [Detailed feature 2]
• [Detailed feature 3]
• [Detailed feature 4]

🎮 Version: [Version]</blockquote>

<blockquote>💖 - Awesome
💔 - Not great</blockquote>

#Minecraft #[Category] #[Tag]
"""
}

def extract_url(text):
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:6000]
    except: return ""

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_context = f"\n\nSITE CONTENT:\n{fetch_page_content(url)}" if url else ""
    
    prompt = f"{PROMPTS.get(persona, PROMPTS['uz'])}\n\nUser input:\n{user_input}{site_context}"
    
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        generated = res.choices[0].message.content.strip()
        generated = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', generated)
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: generated += f"\n\n{ad_text}"
        return generated
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    return text
