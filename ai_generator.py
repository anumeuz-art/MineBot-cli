import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database
import json

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

VALID_CATS = [
    '#Mods', '#Maps', '#Textures', '#Shaders', '#Furniture', '#Tools', '#Mobs', 
    '#Biomes', '#Redstone', '#Magic', '#Structures', '#Armor', '#FPS', '#UI', 
    '#Addons', '#Building', '#Survival', '#Horror', '#Adventure', '#Utility'
]

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
    
    system_prompt = f"""You are a Minecraft content editor. 
Respond ONLY in JSON format: {{"name": "...", "description": "...", "features": ["...", "..."], "version": "...", "category": "#Mods"}}
Categories available: {', '.join(VALID_CATS)}
Language must be: {persona} (uz, ru, en).
Keep it short and punchy."""

    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Info: {user_input} {site_content}"}],
            model=MODEL_ID, response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        
        # Шаблон
        feat = "\n• " + "\n• ".join(data.get('features', []))
        
        # Языковые шаблоны
        if persona == 'uz':
            post = f"📦 <b>{data['name']}</b>\n\n<blockquote expandable><b>Bu nima?</b>\n{data['description']}\n\n<b>Asosiy xususiyatlar:</b>{feat}\n\n🎮 Versiya: {data['version']}</blockquote>\n\n<blockquote>💖 - Zo'r\n💔 - Unchamas</blockquote>"
        elif persona == 'ru':
            post = f"📦 <b>{data['name']}</b>\n\n<blockquote expandable><b>Что это такое?</b>\n{data['description']}\n\n<b>Главные фишки:</b>{feat}\n\n🎮 Версия: {data['version']}</blockquote>\n\n<blockquote>💖 - Имба\n💔 - Не оч</blockquote>"
        else:
            post = f"📦 <b>{data['name']}</b>\n\n<blockquote expandable><b>What is it?</b>\n{data['description']}\n\n<b>Key Features:</b>{feat}\n\n🎮 Version: {data['version']}</blockquote>\n\n<blockquote>💖 - Awesome\n💔 - Not great</blockquote>"
            
        post += f"\n\n#Minecraft {data.get('category', '#Mods')}"
        
        ad = database.get_global_setting('ad_text', '')
        if ad: post += f"\n\n{ad}"
        
        return post
    except Exception as e:
        return f"Generation error: {e}"

def rewrite_post(text, style="short"):
    return text # Простая переписка через Groq если нужно
