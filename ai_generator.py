import config
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
import database

client = Groq(api_key=config.GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile"

def generate_post(user_input, persona="uz"):
    # Промпт теперь максимально строгий, без лишних "творческих" вводных
    system_prompt = f"""You are a Minecraft content bot. 
    1. Write in {persona}.
    2. Follow this structure strictly:
    📦 <b>[Name]</b>
    <blockquote expandable>
    <b>Description:</b>
    [Text]
    
    <b>Features:</b>
    • [F1]
    • [F2]
    • [F3]
    
    🎮 Version: [Version]
    </blockquote>
    <blockquote>💖 - Awesome\n💔 - Not great</blockquote>
    
    3. NO hashtags in the output.
    4. Provide details.
    """
    
    try:
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}], 
            model=MODEL_ID
        )
        gen = res.choices[0].message.content.strip()
        
        # 1. Принудительное удаление хэштегов из ответа ИИ
        gen = re.sub(r'#\w+', '', gen)
        
        # 2. Добавление хэштегов по правилам
        gen += "\n\n#Minecraft #Mods"
        
        # 3. Добавление рекламы
        ad_text = database.get_global_setting('ad_text', '')
        if ad_text: gen += f"\n\n{ad_text}"
        
        return gen
    except Exception as e:
        return f"Error: {e}"

def rewrite_post(text, style="short"):
    return text
