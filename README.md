# 🤖 Local AI Workstation

A **local AI workstation** that combines:

🧠 Local LLM chat  
🎨 AI image generation  
📊 Real-time generation progress  
🖥 Streamlit web interface  

Everything runs **100% locally on your machine**.

---

# ✨ Features

✅ Local Chat Interface  
✅ Text → Image Generation  
✅ Image Generation Progress Bar  
✅ Image Gallery  
✅ Presets (Fast / Balanced / Quality)  
✅ Adjustable Generation Parameters  
✅ Multi-model support  
✅ LAN access (use from phone / tablet)

---

# 🖥 Architecture
Browser (Phone / Laptop)
│
▼
Streamlit UI (Port 8501)
│
▼
Image Service API (Port 8502)
│
▼
Stable Diffusion / DreamShaper
│
▼
Generated Images

👨‍💻 Author

Built for experimentation with local AI systems.

📜 License

MIT License



## How to start
git clone https://github.com/AaLeiRon/local-ai-workstation
cd local-ai-workstation

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt

Add your model into:
models/dreamshaper/

run
python start_services.py
