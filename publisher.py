import telebot
import config
import database

def publish_post_data(bot, post_id, photo_id, text, document_id, channel_id, is_auto=False):
    try:
        if photo_id:
            if ',' in photo_id:
                ids = photo_id.split(',')
                media = [telebot.types.InputMediaPhoto(media=pid, caption=text if i==0 and len(text)<=1024 else None, parse_mode='HTML') for i, pid in enumerate(ids)]
                bot.send_media_group(channel_id, media)
                if len(text) > 1024:
                    bot.send_message(channel_id, text, parse_mode='HTML')
            else:
                if len(text) <= 1024:
                    bot.send_photo(channel_id, photo_id, caption=text, parse_mode='HTML')
                else:
                    bot.send_photo(channel_id, photo_id)
                    bot.send_message(channel_id, text, parse_mode='HTML')
        else:
            bot.send_message(channel_id, text, parse_mode='HTML')
            
        if document_id: bot.send_document(channel_id, document_id)
        
        if post_id != -1: 
            database.mark_as_posted(post_id)
            if is_auto:
                for admin in getattr(config, 'ADMIN_IDS', []):
                    try: bot.send_message(admin, f"✅ <b>Автопостинг:</b> Запланированный пост успешно опубликован в {channel_id}!", parse_mode='HTML')
                    except: pass
                    
        print(f"✅ Пост #{post_id} опубликован в {channel_id}!")
        return True
    except Exception as e:
        if post_id != -1 and is_auto:
            for admin in getattr(config, 'ADMIN_IDS', []):
                try: bot.send_message(admin, f"❌ <b>Ошибка автопостинга:</b> Пост не опубликован в {channel_id}. Причина: {e}", parse_mode='HTML')
                except: pass
        print(f"❌ Ошибка публикации в {channel_id}: {e}")
        return False

def process_queue(bot):
    posts = database.get_ready_posts()
    for post in posts:
        post_id, photo_id, text, document_id, channel_id = post
        target_channel = channel_id if channel_id else config.DEFAULT_CHANNEL
        publish_post_data(bot, post_id, photo_id, text, document_id, target_channel, is_auto=True)
