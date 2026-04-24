import telebot
import config
import database

def publish_post_data(bot, post_id, photo_id, text, document_id, channel_id, is_auto=False):
    """
    Основная функция публикации контента в Telegram канал.
    Поддерживает одиночные фото, альбомы, текстовые сообщения и документы.
    """
    try:
        # 1. Отправка фото или альбома
        if photo_id:
            if ',' in photo_id: # Если в строке несколько ID через запятую — это альбом
                ids = photo_id.split(',')
                # Формируем список MediaGroup. Текст (caption) прикрепляем к первому фото.
                media = [telebot.types.InputMediaPhoto(media=pid, caption=text if i==0 and len(text)<=1024 else None, parse_mode='HTML') for i, pid in enumerate(ids)]
                bot.send_media_group(channel_id, media)
                # Если текст слишком длинный для подписи к фото (>1024 симв), отправляем его отдельным сообщением
                if len(text) > 1024:
                    bot.send_message(channel_id, text, parse_mode='HTML')
            else: # Одиночное фото
                if len(text) <= 1024:
                    bot.send_photo(channel_id, photo_id, caption=text, parse_mode='HTML')
                else:
                    bot.send_photo(channel_id, photo_id)
                    bot.send_message(channel_id, text, parse_mode='HTML')
        else: # Только текст (без фото)
            bot.send_message(channel_id, text, parse_mode='HTML')
            
        # 2. Отправка документов (поддержка нескольких файлов через запятую)
        if document_id:
            doc_ids = document_id.split(',')
            for d_id in doc_ids:
                d_id = d_id.strip()
                if d_id:
                    try:
                        bot.send_document(channel_id, d_id)
                    except Exception as de:
                        print(f"⚠️ Ошибка отправки документа {d_id}: {de}")
        
        # Если это пост из очереди (post_id != -1), помечаем его как опубликованный в БД
        if post_id != -1: 
            database.mark_as_posted(post_id)
            # Уведомляем админа об автоматической публикации
            if is_auto:
                for admin in getattr(config, 'ADMIN_IDS', []):
                    try: bot.send_message(admin, f"✅ <b>Автопостинг:</b> Пост успешно опубликован в {channel_id}!", parse_mode='HTML')
                    except: pass
                    
        print(f"✅ Пост #{post_id} опубликован в {channel_id}!")
        return True
    except Exception as e:
        # В случае ошибки при автопостинге — уведомляем админа
        if post_id != -1 and is_auto:
            for admin in getattr(config, 'ADMIN_IDS', []):
                try: bot.send_message(admin, f"❌ <b>Ошибка автопостинга:</b> Канал {channel_id}. Ошибка: {e}", parse_mode='HTML')
                except: pass
        print(f"❌ Ошибка публикации в {channel_id}: {e}")
        return False

import ai_generator

def auto_ask_suggestions(bot):
    """Автоматически генерирует и публикует пост с запросом предложений."""
    try:
        # Берем язык по умолчанию (админа)
        admin_lang = database.get_user_setting(config.ADMIN_IDS[0], 'persona', 'uz')
        text = ai_generator.generate_suggestion_request(admin_lang)
        
        if text:
            bot.send_message(config.DEFAULT_CHANNEL, text, parse_mode='HTML')
            # Также записываем это событие в БД как опубликованный пост
            database.record_published_post(None, text, None, config.DEFAULT_CHANNEL)
            print("📢 Авто-опрос опубликован!")
    except Exception as e:
        print(f"❌ Ошибка авто-опроса: {e}")

def process_queue(bot):
    """Функция для планировщика (APScheduler). Проверяет очередь и публикует готовые посты."""
    posts = database.get_ready_posts()
    for post in posts:
        post_id, photo_id, text, document_id, channel_id = post
        target_channel = channel_id if channel_id else config.DEFAULT_CHANNEL
        publish_post_data(bot, post_id, photo_id, text, document_id, target_channel, is_auto=True)
