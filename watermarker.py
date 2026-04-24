from PIL import Image, ImageDraw, ImageFont
import os
import database

def add_watermark(input_image_path, output_image_path, watermark_image_path='templates/logo.png'):
    """
    Накладывает водяной знак. 
    Приоритет: Текстовый водяной знак из БД -> Логотип (logo.png).
    """
    try:
        base_image = Image.open(input_image_path).convert("RGBA")
        width, height = base_image.size
        
        # Создаем слой для водяного знака
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Получаем текст водяного знака из базы
        wm_text = database.get_global_setting('watermark_custom_text', '')
        
        if wm_text:
            # ТЕКСТОВЫЙ ВАТЕРМАРК
            # Подбираем размер шрифта (примерно 5% от высоты изображения)
            font_size = int(height * 0.05)
            try:
                # Пытаемся загрузить стандартный шрифт, если есть
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
                
            # Позиция: правый нижний угол
            text_width = draw.textlength(wm_text, font=font)
            position = (width - text_width - 20, height - font_size - 20)
            
            # Рисуем текст с небольшой тенью для читаемости
            draw.text((position[0]+2, position[1]+2), wm_text, font=font, fill=(0, 0, 0, 128))
            draw.text(position, wm_text, font=font, fill=(255, 255, 255, 180))
        else:
            # ГРАФИЧЕСКИЙ ВАТЕРМАРК (LOGO.PNG)
            if os.path.exists(watermark_image_path):
                watermark = Image.open(watermark_image_path).convert("RGBA")
                wm_width = int(width * 0.20)
                w_percent = (wm_width / float(watermark.size[0]))
                h_size = int((float(watermark.size[1]) * float(w_percent)))
                watermark = watermark.resize((wm_width, h_size), Image.Resampling.LANCZOS)
                
                offset_x = int(width * 0.03)
                offset_y = int(height * 0.03)
                position = (width - watermark.size[0] - offset_x, height - watermark.size[1] - offset_y)
                overlay.paste(watermark, position, mask=watermark)
        
        # Совмещаем слои
        finished = Image.alpha_composite(base_image, overlay)
        finished.convert("RGB").save(output_image_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False
