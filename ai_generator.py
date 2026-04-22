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
    site_content = f"\n\nINFO FROM SITE:\n{fetch_page_content(url)}" if url else ""
    
    system_prompt = f"""You are a Minecraft content generator. 
    Language: {persona}.
    Format strictly as:
    📦 <b>[Name]</b>
    <blockquote expandable><b>Description:</b> [Text]
    <b>Features:</b>
    • [F1]
    • [F2]
    • [F3]
    🎮 Version: [Version]
    </blockquote>
    <blockquote>💖 - Awesome\n💔 - Not great</blockquote>
    """
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Info: {user_input} {site_content}"}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        gen = re.sub(r'#\w+', '', gen)
        gen += "\n\n#Minecraft #Mods"
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: gen += f"\n\n{ad_text}"
        return gen
    except Exception as e:
        return f"Error: {e}"

def generate_map(posts_data):
    prompt = f"Create a structured weekly digest of mods. Categorize them (e.g. 'Weapons', 'Food'). List them with links from text:\n{posts_data}"
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        return res.choices[0].message.content
    except: return "Error generating map."

def generate_report(posts_data):
    prompt = f"Create a 'Best of the Week' report based on these popular posts:\n{posts_data}"
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODEL_ID)
        return res.choices[0].message.content
    except: return "Error generating report."
