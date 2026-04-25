from PIL import Image
import os

def add_watermark(input_image_path, output_image_path, watermark_image_path='templates/logo.png'):
    """
    Накладывает водяной знак (логотип) на изображение.
    Логотип автоматически масштабируется под размер основного фото и размещается в углу.
    """
    try:
        # Открываем основное изображение и логотип
        base_image = Image.open(input_image_path).convert("RGBA")
        watermark = Image.open(watermark_image_path).convert("RGBA")
        
        width, height = base_image.size
        
        # Логотип будет занимать 20% от ширины основного фото
        wm_width = int(width * 0.20)
        # Сохраняем пропорции логотипа при изменении размера
        w_percent = (wm_width / float(watermark.size[0]))
        h_size = int((float(watermark.size[1]) * float(w_percent)))
        watermark = watermark.resize((wm_width, h_size), Image.Resampling.LANCZOS)
        
        wm_w, wm_h = watermark.size
        
        # Позиция: правый нижний угол с небольшим отступом (3% от края)
        offset_x = int(width * 0.03)
        offset_y = int(height * 0.03)
        position = (width - wm_w - offset_x, height - wm_h - offset_y)
        
        # Создаем прозрачный слой для наложения логотипа
        transparent = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        transparent.paste(base_image, (0, 0))
        # Накладываем водяной знак на прозрачный слой
        transparent.paste(watermark, position, mask=watermark)
        
        # Конвертируем обратно в RGB для сохранения в JPG
        finished_image = transparent.convert("RGB")
        finished_image.save(output_image_path, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        # В случае ошибки просто копируем оригинал
        try:
            base_image = Image.open(input_image_path).convert("RGB")
            base_image.save(output_image_path, "JPEG")
        except: pass
        return False
