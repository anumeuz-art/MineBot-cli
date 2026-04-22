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

def get_translations():
    with open('translations.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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
    trans = get_translations().get(persona, get_translations()['uz'])
    url = extract_url(user_input)
    site_content = f"\n\nSITE CONTENT:\n{fetch_page_content(url)}" if url else ""
    
    system_prompt = f"""You are a Minecraft content generator.
    Language: {persona}.
    Follow this structure strictly:
    📦 <b>[Name]</b>
    <blockquote expandable><b>{trans['title']}</b>
    [Description]
    
    <b>{trans['features']}</b>
    • [F1]
    • [F2]
    • [F3]
    
    🎮 {trans['version']}: [Version]
    </blockquote>
    <blockquote>{trans['rating']}</blockquote>
    
    {trans['instructions']}
    """
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Info: {user_input} {site_content}"}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # Очистка и вставка тегов
        gen = re.sub(r'#\w+', '', gen)
        gen += "\n\n#Minecraft #Mods"
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: gen += f"\n\n{ad_text}"
        
        return gen
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    return text
