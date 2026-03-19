import os
os.environ["HF_HUB_OFFLINE"] = "1"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
import torch

# =========================
# PATHS
# =========================

BASE = Path(__file__).parent.parent
OUT = BASE / "generated_images"
OUT.mkdir(exist_ok=True)

MODEL_PATHS = {
    "dreamshaper": BASE / "models/dreamshaper/dreamshaperXL_lightningDPMSDE.safetensors",
    "juggernaut": BASE / "models/juggernaut/JuggernautXL_v9.safetensors",
    "realvis": BASE / "models/realvis/RealVisXL_V5.safetensors"
}

pipe_txt2img = None
pipe_img2img = None
current_model = None

progress_state = {
    "current": 0,
    "total": 1,
    "running": False
}

# =========================
# REQUEST MODEL
# =========================

class Req(BaseModel):
    prompt: str
    model: str = "juggernaut"
    steps: int = 30
    guidance_scale: float = 6.5
    width: int = 1024
    height: int = 1024

# =========================
# APP INIT
# =========================

app = FastAPI()
app.mount("/images", StaticFiles(directory=str(OUT)), name="images")

# =========================
# LOAD MODEL
# =========================

def load_model(name):
    global pipe_txt2img, pipe_img2img, current_model

    if current_model == name:
        return

    path = MODEL_PATHS.get(name)

    if not path or not path.exists():
        raise RuntimeError(f"Model not found: {name}")

    print(f"🔄 Loading model: {name}")

    pipe_txt2img = StableDiffusionXLPipeline.from_single_file(
        str(path),
        torch_dtype=torch.float32
    ).to("cpu")

    pipe_img2img = StableDiffusionXLImg2ImgPipeline.from_single_file(
        str(path),
        torch_dtype=torch.float32
    ).to("cpu")

    current_model = name

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
# GENERATION
# =========================

@app.post("/generate")
def generate(r: Req):
    global progress_state

    try:
        load_model(r.model)

        NEG = "blurry, bad anatomy, low quality, distorted, watermark, artifacts"

        # SAFE SIZE (CPU optimized)
        width = min(r.width, 1024)
        height = min(r.height, 1024)

        progress_state.update({
            "current": 0,
            "total": r.steps,
            "running": True
        })

        def cb(pipe, step, timestep, kwargs):
            progress_state["current"] = step
            return kwargs if kwargs else {}

        # =========================
        # STAGE 1 (BASE GENERATION)
        # =========================
        res = pipe_txt2img(
            prompt=r.prompt,
            negative_prompt=NEG,
            width=width,
            height=height,
            num_inference_steps=r.steps,
            guidance_scale=r.guidance_scale,
            callback_on_step_end=cb
        )

        img = res.images[0]

        # =========================
        # STAGE 2 (REFINE)
        # =========================
        res2 = pipe_img2img(
            prompt=r.prompt,
            negative_prompt=NEG,
            image=img,
            strength=0.3,
            num_inference_steps=20,
            guidance_scale=r.guidance_scale
        )

        img = res2.images[0]

        # =========================
        # SAVE
        # =========================
        p = OUT / f"img_{len(list(OUT.glob('*')))}.png"
        img.save(p)

        progress_state["running"] = False

        return {
            "image_urls": [f"http://127.0.0.1:8502/images/{p.name}"]
        }

    except Exception as e:
        progress_state["running"] = False
        return {"error": str(e)}