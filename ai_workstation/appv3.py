import streamlit as st
import requests
from pathlib import Path
import threading
import time

IMAGE_SERVICE = "http://127.0.0.1:8502"

st.set_page_config(layout="wide")
st.title("Local AI Workstation")

chat_tab, gallery_tab = st.tabs(["Chat", "Gallery"])

# ==================================
# PRESETS
# ==================================

PRESETS = {
    "Fast": {
        "steps": 6,
        "guidance": 4.5,
        "width": 512,
        "height": 512,
        "count": 1
    },
    "Balanced": {
        "steps": 10,
        "guidance": 5.5,
        "width": 512,
        "height": 512,
        "count": 1
    },
    "Quality": {
        "steps": 20,
        "guidance": 7.0,
        "width": 768,
        "height": 768,
        "count": 1
    }
}

# ==================================
# SIDEBAR
# ==================================

mode = st.sidebar.radio(
    "Mode",
    ["Image Generator", "Chat"]
)

model = st.sidebar.selectbox(
    "Image Model",
    ["dreamshaper"]
)

preset = st.sidebar.selectbox(
    "Preset",
    list(PRESETS.keys())
)

preset_values = PRESETS[preset]

st.sidebar.divider()

steps = st.sidebar.slider(
    "Steps",
    1,
    40,
    preset_values["steps"]
)

guidance = st.sidebar.slider(
    "Guidance Scale (CFG)",
    1.0,
    15.0,
    preset_values["guidance"]
)

width = st.sidebar.selectbox(
    "Width",
    [512, 768, 1024],
    index=[512, 768, 1024].index(preset_values["width"])
)

height = st.sidebar.selectbox(
    "Height",
    [512, 768, 1024],
    index=[512, 768, 1024].index(preset_values["height"])
)

count = st.sidebar.slider(
    "Images per prompt",
    1,
    4,
    preset_values["count"]
)

seed = st.sidebar.number_input(
    "Seed (-1 random)",
    value=-1
)

# ==================================
# SERVICE HEALTH
# ==================================

try:

    r = requests.get(f"{IMAGE_SERVICE}/health", timeout=2)

    if r.status_code == 200:
        st.sidebar.success("Image Service (8502) Online")
    else:
        st.sidebar.warning("Image Service unhealthy")

except:
    st.sidebar.error("Image Service Offline")

# ==================================
# FUNCTIONS
# ==================================

def generate(prompt):

    payload = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance,
        "count": count,
        "seed": seed
    }

    r = requests.post(
        f"{IMAGE_SERVICE}/generate",
        json=payload,
        timeout=3600
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()

# ==================================
# CHAT HISTORY
# ==================================

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:

    with st.chat_message(m["role"]):

        if m.get("images"):

            for img in m["images"]:
                st.image(img)

        else:
            st.write(m["content"])

# ==================================
# INPUT
# ==================================

prompt = st.chat_input("Enter prompt")

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.write(prompt)

    if mode == "Image Generator":

        with st.chat_message("assistant"):

            progress_bar = st.progress(0)
            status = st.empty()

            result_holder = {
                "result": None,
                "error": None
            }

            def run_generation():

                try:
                    result_holder["result"] = generate(prompt)
                except Exception as e:
                    result_holder["error"] = str(e)

            thread = threading.Thread(target=run_generation)
            thread.start()

            while thread.is_alive():

                try:

                    r = requests.get(
                        f"{IMAGE_SERVICE}/progress",
                        timeout=1
                    )

                    data = r.json()

                    if data["running"]:

                        percent = data["current"] / data["total"]

                        progress_bar.progress(percent)

                        status.write(
                            f"Generating image {data['current']} / {data['total']}"
                        )

                except:
                    pass

                time.sleep(0.2)

            thread.join()

            progress_bar.progress(1.0)

            if result_holder["error"]:

                st.error(result_holder["error"])
                status.write("Generation failed")

            else:

                result = result_holder["result"]

                if not result:

                    st.error("Image service returned no result")

                else:

                    urls = result.get("image_urls", [])

                    status.write("Image generation complete")

                    for u in urls:
                        st.image(u)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "images": urls
                    })

    else:

        with st.chat_message("assistant"):
            st.write("LLM integration placeholder")

# ==================================
# GALLERY
# ==================================

with gallery_tab:

    st.header("Generated Images")

    ROOT = Path(__file__).resolve().parents[1]
    img_dir = ROOT / "generated_images"

    if img_dir.exists():

        imgs = sorted(
            img_dir.glob("*.png"),
            reverse=True
        )

        if imgs:

            cols = st.columns(3)

            for i, img in enumerate(imgs):

                with cols[i % 3]:
                    st.image(str(img))

        else:
            st.write("No images yet.")

    else:
        st.write("generated_images folder not found")