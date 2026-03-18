from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
import torch
from PIL import Image
import base64
from io import BytesIO
import threading
import time

BASE = Path(__file__).parent.parent

MODEL_PATHS = {
    "dreamshaper": BASE / "models/dreamshaper/dreamshaperXL_lightningDPMSDE.safetensors",
    "juggernaut": BASE / "models/juggernaut/JuggernautXL_v9.safetensors",
    "realvis": BASE / "models/realvis/realvisxlV.safetensors"
}

OUT = BASE / "generated_images"
OUT.mkdir(exist_ok=True)

pipe_txt2img = None
pipe_img2img = None
current_model_name = None

progress_state = {"current": 0, "total": 1, "running": False}

# =========================
# REQUEST MODELS
# =========================

class Txt2ImgReq(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512
    steps: int = 8
    guidance_scale: float = 5
    count: int = 1
    model: str = "dreamshaper"


class Img2ImgReq(BaseModel):
    prompt: str
    image: str
    strength: float = 0.6
    steps: int = 8
    guidance_scale: float = 5
    count: int = 1
    model: str = "dreamshaper"

# =========================
# APP INIT
# =========================

app = FastAPI()
app.mount("/images", StaticFiles(directory=str(OUT)), name="images")

@app.on_event("startup")
def start():
    print("Image service ready (lazy loading enabled)")

# =========================
# MODEL LOADING
# =========================

def load_model(model_name):
    global pipe_txt2img, pipe_img2img, current_model_name

    if current_model_name == model_name:
        return

    print(f"Loading model: {model_name}")

    model_path = MODEL_PATHS[model_name]

    pipe_txt2img = StableDiffusionXLPipeline.from_single_file(
        str(model_path), torch_dtype=torch.float32
    )
    pipe_txt2img.to("cpu")

    pipe_img2img = StableDiffusionXLImg2ImgPipeline.from_single_file(
        str(model_path), torch_dtype=torch.float32
    )
    pipe_img2img.to("cpu")

    current_model_name = model_name
    print(f"Model loaded: {model_name}")

# =========================
# HEALTH + PROGRESS
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/progress")
def progress():
    return progress_state

# =========================
# PROGRESS SIMULATION
# =========================

def simulate_progress(steps):
    global progress_state
    progress_state["current"] = 0
    progress_state["total"] = steps

    for i in range(steps):
        if not progress_state["running"]:
            break
        progress_state["current"] = i + 1
        time.sleep(0.3)

# =========================
# TEXT → IMAGE
# =========================

@app.post("/generate")
def generate(r: Txt2ImgReq):
    global progress_state

    try:
        load_model(r.model)

        progress_state["running"] = True
        threading.Thread(target=simulate_progress, args=(r.steps,), daemon=True).start()

        res = pipe_txt2img(
            prompt=r.prompt,
            width=r.width,
            height=r.height,
            num_inference_steps=r.steps,
            guidance_scale=r.guidance_scale,
            num_images_per_prompt=r.count,
        )

        paths = []
        for img in res.images:
            p = OUT / f"img_{len(list(OUT.glob('*')))}.png"
            img.save(p)
            paths.append(p)

        progress_state["running"] = False

        urls = [f"http://127.0.0.1:8502/images/{p.name}" for p in paths]
        return {"image_urls": urls}

    except Exception as e:
        progress_state["running"] = False
        return {"error": str(e)}

# =========================
# IMAGE → IMAGE
# =========================

@app.post("/img2img")
def img2img(r: Img2ImgReq):
    global progress_state

    try:
        load_model(r.model)

        progress_state["running"] = True
        threading.Thread(target=simulate_progress, args=(r.steps,), daemon=True).start()

        image_bytes = base64.b64decode(r.image)
        init_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        init_image = init_image.resize((512, 512))

        res = pipe_img2img(
            prompt=r.prompt,
            image=init_image,
            strength=r.strength,
            num_inference_steps=r.steps,
            guidance_scale=r.guidance_scale,
            num_images_per_prompt=r.count,
        )

        paths = []
        for img in res.images:
            p = OUT / f"img_{len(list(OUT.glob('*')))}.png"
            img.save(p)
            paths.append(p)

        progress_state["running"] = False

        urls = [f"http://127.0.0.1:8502/images/{p.name}" for p in paths]
        return {"image_urls": urls}

    except Exception as e:
        progress_state["running"] = False
        return {"error": str(e)}