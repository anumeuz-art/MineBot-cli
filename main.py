import os
import sys

# Ищем launcher.py, игнорируя системные папки
for root, dirs, files in os.walk("/app"):
    if "launcher.py" in files and "backup" not in root and "venv" not in root:
        os.chdir(root)
        os.execv(sys.executable, [sys.executable, "launcher.py"])
