import os
import sys

# Определяем путь к папке с кодом
base_dir = os.path.dirname(os.path.abspath(__file__))
nested_path = os.path.join(base_dir, "work", "mine_bot_tg-main", "mine_bot_tg-main", "mine_bot_tg-main")

# Добавляем путь в sys.path для корректного импорта модулей
sys.path.append(nested_path)

# Переходим в рабочую директорию бота
os.chdir(nested_path)

# Импортируем и запускаем launcher (или основной процесс)
if __name__ == "__main__":
    print(f"🚀 Root redirector: Starting bot from {nested_path}...")
    import launcher
