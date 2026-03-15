
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from diffusers import StableDiffusionXLPipeline
import torch

BASE = Path(__file__).parent.parent

MODELS = {
    "dreamshaper": BASE / "models/dreamshaper/dreamshaperXL_lightningDPMSDE.safetensors",
    "flux": BASE / "models/flux/flux1-dev.safetensors"
}

OUT = BASE / "generated_images"
OUT.mkdir(exist_ok=True)

pipe_cache = {}

progress_state = {
    "current": 0,
    "total": 1,
    "running": False
}

class Req(BaseModel):
    model: str = "dreamshaper"
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512
    steps: int = 8
    guidance_scale: float = 5
    count: int = 1
    seed: int = -1

app = FastAPI()
app.mount("/images", StaticFiles(directory=str(OUT)), name="images")


def diffusion_callback(pipe, step, timestep, callback_kwargs):
    global progress_state
    progress_state["current"] = step + 1
    return callback_kwargs


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/progress")
def progress():
    return progress_state


@app.post("/generate")
def gen(r: Req):

    global progress_state

    progress_state["running"] = True
    progress_state["current"] = 0
    progress_state["total"] = r.steps

    model_name = r.model

    if model_name not in pipe_cache:

        model_path = MODELS.get(model_name)

        if model_path is None or not model_path.exists():
            raise ValueError(f"Model not found: {model_name}")

        pipe = StableDiffusionXLPipeline.from_single_file(
            str(model_path),
            torch_dtype=torch.float32
        )

        pipe.to("cpu")

        pipe_cache[model_name] = pipe

    pipe = pipe_cache[model_name]

    res = pipe(
        prompt=r.prompt,
        negative_prompt=r.negative_prompt,
        width=r.width,
        height=r.height,
        num_inference_steps=r.steps,
        guidance_scale=r.guidance_scale,
        num_images_per_prompt=r.count,
        callback_on_step_end=diffusion_callback
    )

    progress_state["running"] = False

    paths = []

    for img in res.images:
        p = OUT / f"img_{len(list(OUT.glob('*')))}.png"
        img.save(p)
        paths.append(p)

    urls = [f"http://127.0.0.1:8502/images/{p.name}" for p in paths]

    return {"image_urls": urls}
