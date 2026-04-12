import os
import sys
import subprocess

# Определяем путь к папке с кодом
base_dir = os.path.dirname(os.path.abspath(__file__))
nested_path = os.path.join(base_dir, "work", "mine_bot_tg-main", "mine_bot_tg-main", "mine_bot_tg-main")

print(f"🔍 Debug: Checking path {nested_path}")

if not os.path.exists(nested_path):
    print(f"❌ Error: Path not found! Current dir contents: {os.listdir(base_dir)}")
    # Попробуем найти launcher.py рекурсивно, если путь не совпал
    found = False
    for root, dirs, files in os.walk(base_dir):
        if "launcher.py" in files:
            nested_path = root
            print(f"✅ Found launcher.py at: {nested_path}")
            found = True
            break
    if not found:
        print("💀 Critical: launcher.py not found anywhere!")
        sys.exit(1)

# Запускаем через subprocess, чтобы сохранить чистоту окружения
if __name__ == "__main__":
    print(f"🚀 Root redirector: Starting launcher.py in {nested_path}...")
    try:
        # Устанавливаем рабочую директорию и запускаем процесс
        subprocess.run([sys.executable, "launcher.py"], cwd=nested_path, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Process exited with error: {e}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
