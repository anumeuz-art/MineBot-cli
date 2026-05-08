import database

def reorder_post(target_post_id, new_index):
    """
    Перемещает пост в очереди и обновляет время публикации.
    new_index: 0-based индекс в списке pending posts.
    """
    posts = database.get_pending_posts()
    if not posts:
        return

    # Находим целевой пост и удаляем его из списка
    target_post = None
    for i, post in enumerate(posts):
        if post[0] == target_post_id:
            target_post = posts.pop(i)
            break
    
    if not target_post:
        return
    
    # Вставляем на новую позицию
    posts.insert(new_index, target_post)
    
    # 1. Получаем список всех scheduled_time в порядке возрастания.
    # 2. Присваиваем их новому списку постов по индексу.
    times = sorted([p[1] for p in posts])
    
    updates = {}
    for i, post in enumerate(posts):
        updates[post[0]] = times[i]
        
    database.update_post_times(updates)
