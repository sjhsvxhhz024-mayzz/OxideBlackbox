import shutil
from gradio_client import Client, handle_file
from PIL import Image
img = None
for space, args in (("black-forest-labs/FLUX.1-schnell", dict(prompt="a single fist-sized grey granite rock, rough natural stone, studio photo, centered, plain white background, full object visible", seed=3, randomize_seed=False, width=768, height=768, num_inference_steps=4, api_name="/infer")),):
    try:
        r = Client(space, verbose=False).predict(**args)
        p = r[0] if isinstance(r, (list, tuple)) else r
        p = p.get("path") if isinstance(p, dict) else p
        shutil.copy(p, "tools/ai_pipeline/work/rock_flux.webp"); img = "tools/ai_pipeline/work/rock_flux.png"
        Image.open("tools/ai_pipeline/work/rock_flux.webp").convert("RGB").save(img); print("FLUX ok", flush=True)
    except Exception as e:
        print("FLUX_FAIL", repr(e)[:200], flush=True)
if img:
    try:
        r = Client("tencent/Hunyuan3D-2", verbose=False).predict(None, handle_file(img), None, None, None, None, 30, 5.0, api_name="/shape_generation")
        for it in (r if isinstance(r, (list, tuple)) else [r]):
            p = it.get("value", it.get("path")) if isinstance(it, dict) else it
            if isinstance(p, dict): p = p.get("path")
            if isinstance(p, str) and p.endswith(".glb"):
                shutil.copy(p, "tools/ai_pipeline/work/rock2_ai.glb"); print("SAVED rock2", flush=True); break
    except Exception as e:
        print("HY_FAIL", repr(e)[:200], flush=True)
