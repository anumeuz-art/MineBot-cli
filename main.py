import os
import sys
import subprocess

# Ищем launcher.py
found = None
for root, dirs, files in os.walk("/app"):
    if "launcher.py" in files and "backup" not in root and "venv" not in root:
        found = os.path.join(root, "launcher.py")
        break

if not found:
    print("CRITICAL: launcher.py not found in /app")
    sys.exit(1)

print(f"Starting: {sys.executable} {found}")
# Запускаем через subprocess, передавая все аргументы
os.environ["PYTHONPATH"] = os.path.dirname(found)
subprocess.run([sys.executable, found], cwd=os.path.dirname(found), check=True)
