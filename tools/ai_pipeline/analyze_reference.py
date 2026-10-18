"""Step 1 of the realistic menu: AI depth + character matte for the concept image.

Runs locally on CPU (no accounts needed):
  * Depth Anything V2 Small (Apache-2.0) -> relative depth of the whole scene
  * rembg / IS-Net (Apache-2.0)          -> alpha matte of the player
Outputs go to tools/ai_pipeline/work/.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "menu_plate")
WORK = os.path.join(ROOT, "tools", "ai_pipeline", "work")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, ".tools", "ai_out", "reference.jpg")
PLAYER_BOX = (815, 45, 1215, 740)  # x0, y0, x1, y1 of the player in the 1376x768 concept

os.makedirs(WORK, exist_ok=True)
image = Image.open(SRC).convert("RGB")
image.save(os.path.join(WORK, "reference.png"))

from transformers import pipeline  # noqa: E402

depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device="cpu")
pred = depth(image)["predicted_depth"]
disp = pred.squeeze().numpy().astype(np.float32)
disp_img = Image.fromarray(disp).resize(image.size, Image.BICUBIC)
disp = np.asarray(disp_img, dtype=np.float32)
disp = (disp - disp.min()) / (disp.max() - disp.min())
np.save(os.path.join(WORK, "disparity.npy"), disp)
Image.fromarray((disp * 255).astype(np.uint8)).save(os.path.join(WORK, "disparity.png"))
print("depth", disp.shape, float(disp.min()), float(disp.max()))

from rembg import new_session, remove  # noqa: E402

x0, y0, x1, y1 = PLAYER_BOX
crop = image.crop(PLAYER_BOX)
big = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
cut = remove(big, session=new_session("isnet-general-use"), only_mask=True)
matte = np.zeros((image.height, image.width), dtype=np.uint8)
matte[y0:y1, x0:x1] = np.asarray(cut.resize(crop.size, Image.LANCZOS))
Image.fromarray(matte).save(os.path.join(WORK, "player_matte_raw.png"))
print("matte coverage", float((matte > 128).mean()))
