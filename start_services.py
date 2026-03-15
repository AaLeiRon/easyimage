import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable

# Image service (local only)
image_cmd = [
    PYTHON,
    "-m",
    "uvicorn",
    "image_service.app:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8502"
]

# Streamlit UI (LAN accessible)
ui_cmd = [
    PYTHON,
    "-m",
    "streamlit",
    "run",
    str(ROOT / "ai_workstation/app.py"),
    "--server.address",
    "0.0.0.0",
    "--server.port",
    "8501",
    "--server.enableCORS",
    "false"
]

print("Starting image service...")
p1 = subprocess.Popen(image_cmd, cwd=ROOT)

time.sleep(3)

print("Starting AI workstation...")
p2 = subprocess.Popen(ui_cmd, cwd=ROOT)

print("Running. Press CTRL+C to stop")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping services...")
    p1.terminate()
    p2.terminate()