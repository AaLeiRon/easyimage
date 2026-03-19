import streamlit as st
import requests
import json
import base64

IMAGE_SERVICE = "http://127.0.0.1:8502"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

st.set_page_config(layout="wide")
st.title("🧠 Local AI Workstation")

# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Settings")

mode = st.sidebar.radio(
    "Mode",
    ["Chat", "Text → Image", "Image → Image"]
)

llm_model = st.sidebar.selectbox(
    "🧠 Language Model",
    ["qwen3.5:9b", "qwen3-coder:30b", "deepseek-r1:32b"]
)

image_model = st.sidebar.selectbox(
    "🎨 Image Model",
    ["dreamshaper", "juggernaut", "realvis", "flux"]
)

steps = st.sidebar.slider("Steps", 1, 60, 25)
guidance = st.sidebar.slider("Guidance", 1.0, 15.0, 7.0)
width = st.sidebar.selectbox("Width", [512, 768, 1024], index=1)
height = st.sidebar.selectbox("Height", [512, 768, 1024], index=1)
count = st.sidebar.slider("Images", 1, 8, 1)
strength = st.sidebar.slider("Img2Img Strength", 0.1, 1.0, 0.6)

# =========================
# HEALTH
# =========================

def check_health():
    try:
        return requests.get(f"{IMAGE_SERVICE}/health").status_code == 200
    except:
        return False

if check_health():
    st.sidebar.success("🟢 Image Service Online")
else:
    st.sidebar.error("🔴 Image Service Offline")

# =========================
# STREAMING CHAT
# =========================

def chat_stream(prompt):
    with requests.post(
        OLLAMA_URL,
        json={"model": llm_model, "prompt": prompt, "stream": True},
        stream=True
    ) as response:
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode())
                yield data.get("response", "")

# =========================
# IMAGE CALLS
# =========================

def txt2img(prompt):
    return requests.post(
        f"{IMAGE_SERVICE}/generate",
        json={
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance,
            "count": count,
            "model": image_model
        }
    ).json()

def img2img(prompt, file):
    file.seek(0)
    encoded = base64.b64encode(file.read()).decode()

    return requests.post(
        f"{IMAGE_SERVICE}/img2img",
        json={
            "prompt": prompt,
            "image": encoded,
            "strength": strength,
            "steps": steps,
            "guidance_scale": guidance,
            "count": count,
            "model": image_model
        }
    ).json()

# =========================
# PROGRESS
# =========================

def get_progress():
    try:
        return requests.get(f"{IMAGE_SERVICE}/progress").json()
    except:
        return {"current": 0, "total": 1, "running": False}

# =========================
# IMAGE UPLOAD
# =========================

uploaded_file = None

if mode == "Image → Image":
    uploaded_file = st.file_uploader(
        "📤 Upload image",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)

# =========================
# MAIN INPUT
# =========================

prompt = st.chat_input("Type your prompt...")

if prompt:
    st.chat_message("user").write(prompt)

    if mode == "Chat":

        container = st.chat_message("assistant")
        placeholder = container.empty()

        full = ""
        for token in chat_stream(prompt):
            full += token
            placeholder.markdown(full)

    elif mode == "Text → Image":

        progress_bar = st.progress(0)
        progress_text = st.empty()

        result = txt2img(prompt)

        while True:
            prog = get_progress()

            if prog["running"]:
                pct = (prog["current"] + 1) / prog["total"]
                progress_bar.progress(min(pct, 1.0))
                progress_text.markdown(
                    f"**{int(pct*100)}%** ({prog['current']+1}/{prog['total']})"
                )
            else:
                break

        if result.get("error"):
            st.error(result["error"])
        else:
            for url in result["image_urls"]:
                st.image(url)

    elif mode == "Image → Image":

        if not uploaded_file:
            st.warning("Upload an image first")
        else:
            progress_bar = st.progress(0)
            progress_text = st.empty()

            result = img2img(prompt, uploaded_file)

            while True:
                prog = get_progress()

                if prog["running"]:
                    pct = (prog["current"] + 1) / prog["total"]
                    progress_bar.progress(min(pct, 1.0))
                    progress_text.markdown(
                        f"**{int(pct*100)}%** ({prog['current']+1}/{prog['total']})"
                    )
                else:
                    break

            if result.get("error"):
                st.error(result["error"])
            else:
                for url in result["image_urls"]:
                    st.image(url)