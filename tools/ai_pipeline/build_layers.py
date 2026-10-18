"""Step 3: metric depth for the plate and the player relief, animation masks and the player texture.

Depth Anything gives relative disparity; it is mapped to metres with hand-calibrated control points
(ground under the player ~4.3 m, factory ~600 m, sky ~9 km)."""
import json
import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "menu_plate")
WORK = os.path.join(ROOT, "tools", "ai_pipeline", "work")
D_PTS = [0.0, 0.012, 0.02, 0.03, 0.06, 0.08, 0.15, 0.3, 0.55, 0.72, 0.76, 0.84, 1.0]
Z_PTS = [9000, 5000, 2000, 1400, 760, 600, 160, 30, 8.5, 4.6, 4.3, 2.6, 1.6]
PLAYER_CROP = (850, 66, 1172, 740)  # x0, y0, x1, y1 in concept pixels
PLAYER_Z = 4.33

plate = np.asarray(Image.open(os.path.join(OUT, "plate.png")).convert("RGB"))
ref = np.asarray(Image.open(os.path.join(WORK, "reference.png")).convert("RGB"))
H, W = plate.shape[:2]
disp = cv2.GaussianBlur(np.load(os.path.join(WORK, "plate_disparity.npy")), (0, 0), 1.5)
z_plate = np.exp(np.interp(disp, D_PTS, np.log(Z_PTS))).astype(np.float32)
np.save(os.path.join(WORK, "plate_depth_m.npy"), z_plate)

# player relief: flattened disparity around the median so the body stays ~0.4 m deep
matte = np.asarray(Image.open(os.path.join(WORK, "player_matte_raw.png"))).astype(np.float32) / 255.0
d0 = np.load(os.path.join(WORK, "disparity.npy"))
inside = matte > 0.5
med = float(np.median(d0[inside]))
rel = np.where(inside, d0 - med, 0.0).astype(np.float32)
weight = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 2.5)
rel = cv2.GaussianBlur(rel, (0, 0), 2.5) / np.maximum(weight, 1e-3)
z_player = np.clip(PLAYER_Z - 1.5 * rel, PLAYER_Z - 0.28, PLAYER_Z + 0.25).astype(np.float32)
x0, y0, x1, y1 = PLAYER_CROP
np.save(os.path.join(WORK, "player_depth_m.npy"), z_player[y0:y1, x0:x1])
rgba = np.dstack([ref[y0:y1, x0:x1], (matte[y0:y1, x0:x1] * 255).astype(np.uint8)])
Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, "player_photo.png"))

# animation masks: R sky, G vegetation sway, B water, A cloud-shadow land
hsv = cv2.cvtColor(plate, cv2.COLOR_RGB2HSV).astype(np.float32)
hue, sat, val = hsv[..., 0] * 2.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
yy, xx = np.mgrid[0:H, 0:W]
horizon = np.where(xx < 770, 343, int(0.62 * H))
sky = ((disp < 0.0135) & (yy < horizon)).astype(np.uint8)
sky = cv2.GaussianBlur(cv2.erode(sky, np.ones((7, 7), np.uint8)).astype(np.float32), (0, 0), 3.0)
veg = (hue > 25) & (hue < 175) & (sat > 0.16) & (disp > 0.1) & (yy > 0.42 * H)
veg = veg.astype(np.float32) * np.clip((disp - 0.1) / 0.6, 0.25, 1.0)
veg = cv2.GaussianBlur(veg, (0, 0), 1.5)
water_poly = np.array([[0, 350], [760, 344], [762, 372], [690, 396], [640, 412], [560, 438], [380, 440], [280, 428], [0, 428]], np.int32)
water = np.zeros((H, W), np.uint8)
cv2.fillPoly(water, [water_poly], 1)
water = cv2.GaussianBlur((water * (sat < 0.3)).astype(np.float32), (0, 0), 2.0)
land = 1.0 - sky
masks = np.dstack([sky, veg, water, land])
Image.fromarray((np.clip(masks, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "plate_masks.png"))

anchors = {
    "smoke": [[513, 349], [567, 324]],
    "beacon": [[830, 263]],
    "factory_lights": [[476, 455], [530, 468], [582, 492], [620, 505], [700, 470], [742, 486], [790, 455], [512, 520]],
    "player_crop": list(PLAYER_CROP),
    "player_depth": PLAYER_Z,
    "joints": {  # concept pixels, picked from the reference
        "feet": [1000, 705], "pelvis": [1002, 410], "waist": [998, 352], "chest": [1002, 260], "neck": [1007, 172],
        "chin": [1006, 150], "head_top": [1005, 70],
        "clav_R": [995, 185], "shoulder_R": [947, 192], "elbow_R": [907, 300], "wrist_R": [897, 385], "hand_R": [898, 425],
        "clav_L": [1015, 185], "shoulder_L": [1085, 190], "elbow_L": [1145, 310], "wrist_L": [1095, 330], "hand_L": [1068, 322],
        "hip_R": [962, 420], "knee_R": [950, 530], "ankle_R": [947, 642], "toe_R": [915, 692],
        "hip_L": [1040, 420], "knee_L": [1055, 522], "ankle_L": [1077, 645], "toe_L": [1082, 710],
    },
    "rigid": {"hand.R": [[895, 448, 48]], "forearm.L": [[1090, 288, 52]], "hips": [[1068, 380, 34]]},
    "depth_points": {"d": D_PTS, "z": Z_PTS},
}
with open(os.path.join(OUT, "anchors.json"), "w") as f:
    json.dump(anchors, f, indent=1)
print("player median disparity", med, "plate z range", float(z_plate.min()), float(z_plate.max()))
print("smoke depth", [float(z_plate[y, x]) for x, y in anchors["smoke"]], "beacon", float(z_plate[263, 830]))
