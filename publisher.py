import telebot
import config
import database

def publish_post_data(bot, post_id, photo_id, text, document_id, channels_str, is_auto=False):
    """
    Публикация контента в список Telegram каналов.
    channels_str: строка через запятую, например '@chan1,@chan2'
    """
    if not channels_str:
        return False
        
    channels = [c.strip() for c in channels_str.split(',')]
    success = True
    
    for channel_id in channels:
        try:
            if photo_id:
                if ',' in photo_id:
                    media = [telebot.types.InputMediaPhoto(media=pid) for pid in photo_id.split(',')]
                    bot.send_media_group(channel_id, media)
                    bot.send_message(channel_id, text, parse_mode='HTML')
                else:
                    bot.send_photo(channel_id, photo_id, caption=text, parse_mode='HTML')
            elif document_id:
                bot.send_document(channel_id, document_id, caption=text, parse_mode='HTML')
            else:
                bot.send_message(channel_id, text, parse_mode='HTML')
        except Exception as e:
            print(f"Ошибка публикации в {channel_id}: {e}")
            success = False
            
    if post_id != -1 and success:
        database.mark_as_posted(post_id)
    return success
