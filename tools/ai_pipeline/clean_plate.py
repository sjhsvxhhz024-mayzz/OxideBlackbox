"""Step 2: remove the player and the UI area from the concept with LaMa (Apache-2.0, ONNX, CPU),
then re-estimate depth on the clean plate so the hidden background gets proper depth too."""
import os

import cv2
import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "menu_plate")
WORK = os.path.join(ROOT, "tools", "ai_pipeline", "work")
PANEL_X = 466  # concept's UI panel ends here

image = np.asarray(Image.open(os.path.join(WORK, "reference.png")).convert("RGB"))
matte = np.asarray(Image.open(os.path.join(WORK, "player_matte_raw.png")))
H, W = matte.shape
session = ort.InferenceSession(hf_hub_download("Carve/LaMa-ONNX", "lama_fp32.onnx"), providers=["CPUExecutionProvider"])
names = [i.name for i in session.get_inputs()]


def lama(rgb, hole):
    img = cv2.resize(rgb, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    msk = (cv2.resize(hole.astype(np.uint8) * 255, (512, 512), interpolation=cv2.INTER_NEAREST) > 127).astype(np.float32)
    feeds = {names[0]: img.transpose(2, 0, 1)[None], names[1]: msk[None, None]}
    out = session.run(None, feeds)[0][0].transpose(1, 2, 0)
    if out.max() <= 1.5:
        out = out * 255.0
    return cv2.resize(np.clip(out, 0, 255).astype(np.uint8), (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC)


def composite(base, filled, hole, feather=6):
    alpha = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), feather)[..., None]
    alpha = np.clip(alpha * 1.6, 0, 1)
    return (base * (1 - alpha) + filled * alpha).astype(np.uint8)


plate = image.copy()
# player: dilate the matte so no outline survives, inpaint inside a square window around him
hole = cv2.dilate((matte > 40).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
ys, xs = np.nonzero(hole)
cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 60
x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
x1, y1 = min(W, x0 + side), min(H, y0 + side)
win = plate[y0:y1, x0:x1]
plate[y0:y1, x0:x1] = composite(win, lama(win, hole[y0:y1, x0:x1]), hole[y0:y1, x0:x1])
# UI panel of the concept: extend the landscape leftwards
panel = np.zeros((H, W), bool)
panel[:, :PANEL_X + 4] = True
win_w = 760
win = plate[:, :win_w]
filled = lama(win, panel[:, :win_w])
plate[:, :win_w] = composite(win, filled, panel[:, :win_w], feather=3)
os.makedirs(OUT, exist_ok=True)
Image.fromarray(plate).save(os.path.join(OUT, "plate.png"))
Image.fromarray(hole.astype(np.uint8) * 255).save(os.path.join(WORK, "player_hole.png"))
print("inputs", names, "window", (x0, y0, x1, y1))

from transformers import pipeline  # noqa: E402

depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device="cpu")
pred = depth(Image.fromarray(plate))["predicted_depth"].squeeze().numpy().astype(np.float32)
disp = cv2.resize(pred, (W, H), interpolation=cv2.INTER_CUBIC)
disp = (disp - disp.min()) / (disp.max() - disp.min())
np.save(os.path.join(WORK, "plate_disparity.npy"), disp)
Image.fromarray((disp * 255).astype(np.uint8)).save(os.path.join(WORK, "plate_disparity.png"))
print("plate depth ok")
