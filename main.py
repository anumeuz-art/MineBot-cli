import os
import subprocess

print("--- 🔍 DEBUG: FILE SYSTEM STRUCTURE ---")
# Используем команду find для вывода всей структуры
try:
    result = subprocess.run(["find", ".", "-maxdepth", "5"], capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"DEBUG ERROR: {e}")

# Ищем launcher.py
found = None
for root, dirs, files in os.walk("."):
    if "launcher.py" in files and "backup" not in root and "venv" not in root:
        found = os.path.join(root, "launcher.py")
        break

if found:
    print(f"--- ✅ FOUND: {found} ---")
    os.environ["PYTHONPATH"] = os.path.dirname(found)
    subprocess.run(["python", found], cwd=os.path.dirname(found))
else:
    print("--- 💀 FATAL: launcher.py NOT FOUND IN STRUCTURE ---")
