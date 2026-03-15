
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable

image_cmd=[PYTHON,"-m","uvicorn","image_service.app:app","--host","127.0.0.1","--port","8502"]
ui_cmd=[PYTHON,"-m","streamlit","run",str(ROOT/"ai_workstation/app.py"),"--server.port","8501"]

print("Starting image service...")
p1=subprocess.Popen(image_cmd,cwd=ROOT)

time.sleep(3)

print("Starting AI workstation...")
p2=subprocess.Popen(ui_cmd,cwd=ROOT)

print("Running. Press CTRL+C to stop")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    p1.terminate()
    p2.terminate()
