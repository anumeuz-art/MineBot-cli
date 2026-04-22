import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

def generate_post(user_input, persona="uz"):
    # Жесткий промпт, чтобы ИИ просто заполнил пропуски
    system_prompt = f"""You are a content generator for Minecraft. 
    Fill the following template strictly. Do not change structure. Language: {persona}.
    
    📦 <b>[NAME]</b>

    <blockquote expandable><b>Bu nima?</b> (Write description here)
    [DESCRIPTION]

    <b>Asosiy xususiyatlar:</b>
    • [Feature 1]
    • [Feature 2]
    • [Feature 3]
    • [Feature 4]

    🎮 Versiya: [VERSION]</blockquote>

    <blockquote>💖 - juda zo'r
    💔 - unchamas</blockquote>
    """
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # Очистка от лишних хэштегов и вставка нужных
        gen = re.sub(r'#\w+', '', gen)
        gen += "\n\n#Minecraft #Mods"
        
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: gen += f"\n\n{ad_text}"
        
        return gen
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    return text
