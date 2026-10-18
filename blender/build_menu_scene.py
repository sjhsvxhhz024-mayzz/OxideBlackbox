"""TEZEROK — realistic menu scene built from the AI-processed concept art.

Inputs come from tools/ai_pipeline (Depth Anything V2 depth, IS-Net player matte, LaMa clean plate).
Builds, for the menu camera at the origin looking along +Y with a 32 degree vertical FOV:
  * MenuBackground — the clean photo plate displaced by metric depth (2.5D background model),
  * PlayerPhoto    — the player as a depth relief, rigged with 20 bones and a seamless 8 s idle loop,
  * empties for chimney smoke, the tower beacon and factory lights.

Run:    blender -b --factory-startup --python blender/build_menu_scene.py
Writes: assets/models/menu_background.glb, assets/models/player_photo.glb, blender/menu_scene.blend
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

PLATE_DIR = os.path.join(tz.ROOT, "assets", "menu_plate")
WORK_DIR = os.path.join(tz.ROOT, "tools", "ai_pipeline", "work")
W, H = 1376, 768
TAN_V = math.tan(math.radians(16.0))
TAN_H = TAN_V * W / H
BEACON_DEPTH = 1900.0  # the thin mast reads as sky in the depth map; use the hill behind it

scene = tz.reset_scene()
anchors = json.load(open(os.path.join(PLATE_DIR, "anchors.json")))


def rays(px, py):
    """Camera-space ray directions (Blender axes, +Y forward) for concept pixel coordinates."""
    return np.stack([(2.0 * px / W - 1.0) * TAN_H, np.ones_like(px), (1.0 - 2.0 * py / H) * TAN_V], axis=-1)


def point(px, py, depth):
    return Vector(rays(np.array(float(px)), np.array(float(py))) * depth)


def bilinear(img, px, py):
    x = np.clip(px, 0, img.shape[1] - 1.001)
    y = np.clip(py, 0, img.shape[0] - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def grid_mesh(name, px, py, depth, uv, keep=None):
    rows, cols = px.shape
    verts = (rays(px, py) * depth[..., None]).reshape(-1, 3)
    idx = np.arange(rows * cols).reshape(rows, cols)
    quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], axis=-1).reshape(-1, 4)
    if keep is not None:
        k = keep.reshape(-1)
        quads = quads[k[quads].any(axis=1)]
    used = np.unique(quads)
    remap = -np.ones(rows * cols, dtype=np.int64)
    remap[used] = np.arange(len(used))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts[used].tolist(), [], remap[quads].tolist())
    uv_layer = me.uv_layers.new(name="UVMap")
    loop_vert = np.zeros(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", loop_vert)
    uv_used = uv.reshape(-1, 2)[used]
    uv_layer.data.foreach_set("uv", uv_used[loop_vert].astype(np.float32).ravel())
    me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    return obj, uv_used, used


def photo_material(name, image_path):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path)
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


# ----------------------------------------------------------------------------- background model
z_plate = np.load(os.path.join(WORK_DIR, "plate_depth_m.npy"))
STEP, MX, MY = 4, 168, 48
gx, gy = np.meshgrid(np.arange(-MX, W + MX + 1, STEP, dtype=np.float64), np.arange(-MY, H + MY + 1, STEP, dtype=np.float64))
depth = bilinear(z_plate, gx, gy)
uv = np.stack([np.clip(gx / W, 0, 1), 1.0 - np.clip(gy / H, 0, 1)], axis=-1)
background, _, _ = grid_mesh("MenuBackground", gx, gy, depth, uv)
background.data.materials.append(photo_material("PhotoPlate", os.path.join(PLATE_DIR, "plate.png")))

# ----------------------------------------------------------------------------- player relief
x0, y0, x1, y1 = anchors["player_crop"]
z_player = np.load(os.path.join(WORK_DIR, "player_depth_m.npy"))
alpha = np.asarray(bpy.data.images.load(os.path.join(PLATE_DIR, "player_photo.png")).pixels[:], dtype=np.float32)
alpha = alpha.reshape(y1 - y0, x1 - x0, 4)[::-1, :, 3]  # Blender stores rows bottom-up
PSTEP = 2
lx, ly = np.meshgrid(np.arange(0, x1 - x0 + 1, PSTEP, dtype=np.float64), np.arange(0, y1 - y0 + 1, PSTEP, dtype=np.float64))
keep = bilinear(alpha, lx, ly) > 0.02
pdepth = bilinear(z_player, lx, ly)
puv = np.stack([lx / (x1 - x0), 1.0 - ly / (y1 - y0)], axis=-1)
player, _, used = grid_mesh("PlayerPhoto", lx + x0, ly + y0, pdepth, puv, keep=keep)
player.data.materials.append(photo_material("PlayerPhoto", os.path.join(PLATE_DIR, "player_photo.png")))
pix = np.stack([(lx + x0).reshape(-1)[used], (ly + y0).reshape(-1)[used]], axis=-1)

J = {k: np.array(v, dtype=np.float64) for k, v in anchors["joints"].items()}
PZ = anchors["player_depth"]
BONES = [
    ("root", "feet", None, None), ("hips", "pelvis", "waist", "root"), ("spine", "waist", "chest", "hips"),
    ("chest", "chest", "neck", "spine"), ("neck", "neck", "chin", "chest"), ("head", "chin", "head_top", "neck"),
]
for k in ("L", "R"):
    BONES += [
        (f"shoulder.{k}", f"clav_{k}", f"shoulder_{k}", "chest"), (f"upper_arm.{k}", f"shoulder_{k}", f"elbow_{k}", f"shoulder.{k}"),
        (f"forearm.{k}", f"elbow_{k}", f"wrist_{k}", f"upper_arm.{k}"), (f"hand.{k}", f"wrist_{k}", f"hand_{k}", f"forearm.{k}"),
        (f"thigh.{k}", f"hip_{k}", f"knee_{k}", "hips"), (f"shin.{k}", f"knee_{k}", f"ankle_{k}", f"thigh.{k}"),
        (f"foot.{k}", f"ankle_{k}", f"toe_{k}", f"shin.{k}"),
    ]

# skin weights from 2D distance to the bone segments in concept pixels
seg_names = [b[0] for b in BONES if b[2] is not None]
seg_a = np.array([J[b[1]] for b in BONES if b[2] is not None])
seg_b = np.array([J[b[2]] for b in BONES if b[2] is not None])
ab = seg_b - seg_a
t = np.clip(((pix[:, None, :] - seg_a[None]) * ab[None]).sum(-1) / (ab ** 2).sum(-1)[None], 0, 1)
dist = np.linalg.norm(seg_a[None] + ab[None] * t[..., None] - pix[:, None, :], axis=-1)
order = np.argsort(dist, axis=1)[:, :3]
near = np.take_along_axis(dist, order, axis=1)
w = 1.0 / np.maximum(near, 2.0) ** 4
w /= w.sum(axis=1, keepdims=True)
groups = {name: player.vertex_groups.new(name=name) for name in seg_names}
rigid = np.full(len(pix), -1)
for bone, circles in anchors["rigid"].items():
    for cx, cy, r in circles:
        rigid[np.hypot(pix[:, 0] - cx, pix[:, 1] - cy) < r] = seg_names.index(bone)
for i in range(len(pix)):
    if rigid[i] >= 0:
        groups[seg_names[rigid[i]]].add([i], 1.0, "REPLACE")
        continue
    for j in range(3):
        if w[i, j] > 0.01:
            groups[seg_names[order[i, j]]].add([i], float(w[i, j]), "REPLACE")

arm = bpy.data.armatures.new("PlayerRig")
rig = bpy.data.objects.new("PlayerRig", arm)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent in BONES:
    eb = arm.edit_bones.new(name)
    eb.head = point(*J[head], PZ)
    eb.tail = point(*J[tail], PZ) if tail else eb.head + Vector((0.0, 0.0, 0.15))
    if parent:
        eb.parent = arm.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
player.parent = rig
player.modifiers.new("Armature", "ARMATURE").object = rig

# idle loop: in-plane sway around the feet, breathing, small head motion, swinging helmet
FPS, LOOP = 30, 240
scene.frame_start, scene.frame_end = 0, LOOP
rig.animation_data_create()
X3, Y3, Z3 = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
rad = math.radians


def qworld(bone, axis, ang):
    m = arm.bones[bone].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ axis).normalized(), ang)


for f in range(LOOP + 1):
    a = 2.0 * math.pi * f / FPS / 8.0
    breath = math.sin(2.0 * a)
    roll = rad(0.45) * math.sin(a)
    poses = {
        "root": [(Y3, roll), (X3, rad(0.2) * math.sin(2.0 * a + 0.7))],
        "hips": [(Y3, -0.4 * roll)],
        "spine": [(Y3, -0.3 * roll)],
        "chest": [(Y3, rad(0.35) * math.sin(a + 0.6)), (X3, rad(-0.5) * breath)],
        "neck": [(X3, rad(0.3) * breath)],
        "head": [(Z3, rad(1.3) * math.sin(a + 1.1) + rad(0.4) * math.sin(3.0 * a)), (Y3, rad(-0.8) * math.sin(a + 0.3)),
                 (X3, rad(0.6) * math.sin(2.0 * a + 2.0))],
        "shoulder.L": [(Y3, rad(0.6) * breath)],
        "shoulder.R": [(Y3, rad(-0.6) * breath)],
        "upper_arm.R": [(Y3, rad(0.9) * math.sin(a + 0.9))],
        "forearm.R": [(Y3, rad(0.7) * math.sin(a + 1.5))],
        "hand.R": [(Y3, rad(1.6) * math.sin(a + 2.1))],
        "upper_arm.L": [(Y3, rad(0.35) * math.sin(a + 0.6))],
    }
    for name, rots in poses.items():
        q = Quaternion()
        for axis, ang in rots:
            q = qworld(name, axis, ang) @ q
        pb = rig.pose.bones[name]
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=f, group=name)
    chest = rig.pose.bones["chest"]
    chest.scale = (1.0 + 0.004 * breath, 1.0 + 0.006 * breath, 1.0 + 0.004 * breath)
    chest.keyframe_insert("scale", frame=f, group="chest")
    counter = (Quaternion(Y3, roll) @ Quaternion(Y3, -0.4 * roll)).inverted()
    for k in ("L", "R"):
        axis, ang = counter.to_axis_angle()
        m = arm.bones[f"foot.{k}"].matrix_local.to_3x3()
        pb = rig.pose.bones[f"foot.{k}"]
        pb.rotation_quaternion = Quaternion((m.inverted() @ axis).normalized(), ang)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=f"foot.{k}")
rig.animation_data.action.name = "Idle"
scene.frame_set(0)


# ----------------------------------------------------------------------------- anchors for effects
def marker(name, px, py, depth):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.5
    e.location = point(px, py, depth)
    scene.collection.objects.link(e)
    return e


markers = []
for i, (px, py) in enumerate(anchors["smoke"]):
    markers.append(marker(f"Smoke{i + 1}", px, py, float(bilinear(z_plate, np.array(px + 0.0), np.array(py + 2.0)))))
markers.append(marker("BeaconTop", *anchors["beacon"][0], BEACON_DEPTH))
for i, (px, py) in enumerate(anchors["factory_lights"]):
    markers.append(marker(f"FactoryLight{i + 1}", px, py, float(bilinear(z_plate, np.array(px + 0.0), np.array(py + 0.0)))))

tz.export_glb(os.path.join(tz.MODELS_DIR, "menu_background.glb"), [background] + markers, export_image_format="NONE")
tz.export_glb(os.path.join(tz.MODELS_DIR, "player_photo.glb"), [rig, player], animations=True, export_image_format="NONE")
print(f"MENU_SCENE background_verts={len(background.data.vertices)} player_verts={len(player.data.vertices)}")

cam = bpy.data.objects.new("MenuCamera", bpy.data.cameras.new("MenuCamera"))
cam.data.sensor_fit = "VERTICAL"
cam.data.angle_y = math.radians(32.0)
cam.data.clip_end = 12000.0
cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = W, H
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tz.BLEND_DIR, "menu_scene.blend"), compress=True)
