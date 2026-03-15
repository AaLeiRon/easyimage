import streamlit as st
import requests
from pathlib import Path
import threading
import time

IMAGE_SERVICE = "http://127.0.0.1:8502"

st.set_page_config(layout="wide")
st.title("Local AI Workstation")

chat_tab, gallery_tab = st.tabs(["Chat", "Gallery"])


def is_image_request(t):
    t = t.lower()
    triggers = ["/image", "image", "draw", "picture", "render", "sketch", "paint"]
    return any(x in t for x in triggers)


def extract_prompt(t):
    if t.startswith("/image"):
        return t.replace("/image", "").strip()
    return t


def generate(prompt, preset, model):

    if preset == "Fast":
        steps = 6
        size = 512
    elif preset == "Balanced":
        steps = 10
        size = 512
    else:
        steps = 20
        size = 768

    payload = {
        "model": model,
        "prompt": prompt,
        "width": size,
        "height": size,
        "steps": steps,
        "guidance_scale": 5,
        "count": 1
    }

    r = requests.post(f"{IMAGE_SERVICE}/generate", json=payload, timeout=3600)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


with chat_tab:

    model = st.sidebar.selectbox(
        "Image Model",
        ["dreamshaper"]   #, "flux"]
    )

    preset = st.sidebar.selectbox(
        "Image Preset",
        ["Fast", "Balanced", "Quality"]
    )

    # Health indicator
    try:
        r = requests.get(f"{IMAGE_SERVICE}/health", timeout=2)
        if r.status_code == 200:
            st.sidebar.success("Image Service (8502) Online")
        else:
            st.sidebar.warning("Image Service unhealthy")
    except:
        st.sidebar.error("Image Service Offline")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:

        with st.chat_message(m["role"]):

            if m.get("images"):
                for img in m["images"]:
                    st.image(img)
            else:
                st.write(m["content"])

    prompt = st.chat_input("Message")

    if prompt:

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.write(prompt)

        if is_image_request(prompt):

            p = extract_prompt(prompt)

            with st.chat_message("assistant"):

                progress_bar = st.progress(0)
                status = st.empty()

                result_holder = {"result": None, "error": None}

                def run_generation():
                    try:
                        result_holder["result"] = generate(p, preset, model)
                    except Exception as e:
                        result_holder["error"] = str(e)

                thread = threading.Thread(target=run_generation)
                thread.start()

                while thread.is_alive():

                    try:
                        r = requests.get(f"{IMAGE_SERVICE}/progress", timeout=1)
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


with gallery_tab:

    st.header("Generated Images")

    ROOT = Path(__file__).resolve().parents[1]
    img_dir = ROOT / "generated_images"

    if img_dir.exists():

        imgs = sorted(img_dir.glob("*.png"), reverse=True)

        if imgs:

            cols = st.columns(3)

            for i, img in enumerate(imgs):
                with cols[i % 3]:
                    st.image(str(img))

        else:
            st.write("No images yet.")

    else:
        st.write("generated_images folder not found")