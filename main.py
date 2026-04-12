import os
import sys
import subprocess

def find_launcher():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"🔍 Root: {base_dir}")
    
    # Прямой поиск
    for root, dirs, files in os.walk(base_dir):
        if "launcher.py" in files:
            # Игнорируем бэкапы
            if "backup" in root: continue
            return os.path.join(root, "launcher.py")
    return None

if __name__ == "__main__":
    launcher_path = find_launcher()
    
    if not launcher_path:
        print("💀 CRITICAL: launcher.py not found!")
        # Выведем структуру для отладки
        subprocess.run(["find", ".", "-maxdepth", "4", "-not", "-path", "*/.*"])
        sys.exit(1)
        
    work_dir = os.path.dirname(launcher_path)
    print(f"🚀 Found launcher at {launcher_path}. WorkDir: {work_dir}")
    
    try:
        # Используем абсолютный путь к python из текущего окружения
        python_exe = sys.executable
        os.chdir(work_dir)
        # Запускаем через execv, чтобы этот процесс полностью заменился ботом
        os.execv(python_exe, [python_exe, "launcher.py"])
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        sys.exit(1)
