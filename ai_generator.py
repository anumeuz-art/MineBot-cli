import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

# не трогать промпт, он уже оптимизирован для генерации постов по Minecraft модам 
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
        
        # Реклама добавляется автоматически из БД, если она есть
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text and ad_text not in gen:
            gen += f"\n\n{ad_text}"
            
        return gen
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    try:
        prompt = f"Перепиши этот пост про Minecraft мод, сделай его {style}. Сохрани структуру и эмодзи. Вот текст:\n\n{text}"
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=MODEL_ID
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error rewriting: {e}"
