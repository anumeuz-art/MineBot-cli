import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database
import json

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

PROMPT_TEMPLATE = """
Sen Minecraft modlari bo'yicha Telegram kanali muharririsan. Berilgan ma'lumotdan foydalanib, quyidagi qat'iy shablon bo'yicha post yoz.
Hech narsani o'zgartirma, faqat ma'lumotni to'ldir!

SHABLON:
📦 <b>[Mod Nomi]</b>

Bu nima?
[Mod haqida qisqacha va tushunarli ma'lumot]

Asosiy xususiyatlar:
• [Xususiyat 1]
• [Xususiyat 2]
• [Xususiyat 3]

🎮 Versiya: [Versiya]

💖 - juda zo'r
💔 - unchamas

#Minecraft #Mods

💎 Obuna bo'ling: @Lazikomods (https://t.me/Lazikomods)
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

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_content = fetch_page_content(url) if url else ""
    
    prompt = f"{PROMPT_TEMPLATE}\n\nMa'lumot:\n{user_input}\n{site_content}"
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # Авто-добавка рекламы из БД, если она не попала в шаблон
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text and ad_text not in gen:
            gen += f"\n\n{ad_text}"
            
        return gen
    except Exception as e:
        return f"Error: {e}"

def generate_map(posts_data):
    return "Weekly Map Report..."

def generate_report(posts_data):
    return "Weekly Top Report..."
