import streamlit as st
import requests
import time
from PIL import Image

IMAGE_SERVICE = "http://127.0.0.1:8502"

st.set_page_config(layout="wide", page_title="AI Workstation")

# =========================
# STATE
# =========================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================
# HELPERS
# =========================

def is_image_request(text):
    t = text.lower()
    triggers = ["image", "draw", "generate", "picture", "render", "photo"]
    return any(x in t for x in triggers)

def health():
    try:
        return requests.get(f"{IMAGE_SERVICE}/health").status_code == 200
    except:
        return False

def get_progress():
    try:
        return requests.get(f"{IMAGE_SERVICE}/progress").json()
    except:
        return {"current": 0, "total": 1, "running": False}

def generate_image(prompt, settings):
    payload = {
        "prompt": prompt,
        "model": settings["model"],
        "steps": settings["steps"],
        "guidance_scale": settings["guidance"],
        "width": settings["width"],
        "height": settings["height"]
    }
    return requests.post(f"{IMAGE_SERVICE}/generate", json=payload, timeout=3600).json()

# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Settings")

if health():
    st.sidebar.success("🟢 Image Service Online")
else:
    st.sidebar.error("🔴 Image Service Offline")

model = st.sidebar.selectbox("Model", ["juggernaut", "realvis", "dreamshaper"])

mode = st.sidebar.selectbox("Quality", ["Fast", "Balanced", "Ultra"])

if mode == "Fast":
    steps, guidance, size = 10, 5.0, 512
elif mode == "Balanced":
    steps, guidance, size = 25, 6.5, 768
else:
    steps, guidance, size = 40, 8.5, 1024

settings = {
    "model": model,
    "steps": steps,
    "guidance": guidance,
    "width": size,
    "height": size
}

# =========================
# MAIN CHAT UI
# =========================

st.title("💬 AI Workstation")

# Display chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            st.image(msg["content"])

# =========================
# INPUT
# =========================

uploaded = st.file_uploader("📎 Upload Image (optional)", type=["png", "jpg"], label_visibility="collapsed")

prompt = st.chat_input("Ask or generate something...")

if prompt:

    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        progress_bar = st.progress(0)
        status = st.empty()

        # =========================
        # IMAGE REQUEST
        # =========================
        if is_image_request(prompt):

            result = generate_image(prompt, settings)

            # progress tracking
            while True:
                p = get_progress()
                if p["running"]:
                    percent = int((p["current"] / max(p["total"], 1)) * 100)
                    progress_bar.progress(percent)
                    status.text(f"Generating image... {percent}%")
                    time.sleep(0.3)
                else:
                    break

            if result.get("error"):
                st.error(result["error"])
            else:
                for url in result["image_urls"]:
                    st.image(url)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "image",
                        "content": url
                    })

        # =========================
        # TEXT RESPONSE (LLM placeholder)
        # =========================
        else:
            response = f"🧠 You said:\n\n{prompt}\n\n(LLM integration next step)"

            st.markdown(response)

            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": response
            })

# =========================
# FOOTER GALLERY
# =========================

st.divider()
st.subheader("🖼️ Recent Images")

from pathlib import Path

IMG_DIR = Path("generated_images")

if IMG_DIR.exists():
    imgs = list(IMG_DIR.glob("*.png"))[-8:]

    cols = st.columns(4)

    for i, img in enumerate(imgs):
        with cols[i % 4]:
            st.image(str(img))