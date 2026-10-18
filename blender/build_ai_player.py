"""TEZEROK — finish the AI-generated player (Hunyuan3D-2 shape from the concept art).

Projects the concept colours onto the untextured mesh from the front (vertex colours, darker on the back),
decimates it for the game and exports assets/models/game/player_ai.glb.
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

SRC = os.path.join(tz.ROOT, "tools", "ai_pipeline", "work", "player_hunyuan_raw.glb")
PHOTO = os.path.join(tz.ROOT, "assets", "menu_plate", "player_photo.png")
TARGET_FACES = 40000

tz.reset_scene()
bpy.ops.import_scene.gltf(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o != obj:
        bpy.data.objects.remove(o)
dec = obj.modifiers.new("Decimate", "DECIMATE")
dec.ratio = min(1.0, TARGET_FACES / max(len(obj.data.polygons), 1))
bpy.ops.object.modifier_apply(modifier=dec.name)
me = obj.data

img = bpy.data.images.load(PHOTO)
w, h = img.size
px = np.asarray(img.pixels[:], dtype=np.float32).reshape(h, w, 4)  # rows bottom-up
alpha = px[..., 3] > 0.5
rows, cols = np.nonzero(alpha)
r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
lo, hi = co.min(0), co.max(0)
u = (co[:, 0] - lo[0]) / (hi[0] - lo[0])
v = (co[:, 2] - lo[2]) / (hi[2] - lo[2])
cx = np.clip((c0 + u * (c1 - c0)).astype(int), 0, w - 1)
cy = np.clip((r0 + v * (r1 - r0)).astype(int), 0, h - 1)
# nearest opaque pixel for points that project outside the matte
from collections import deque  # noqa: E402
filled = px[..., :3].copy()
known = alpha.copy()
queue = deque(zip(*np.nonzero(known)))
while queue:
    y, x = queue.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and not known[ny, nx]:
            known[ny, nx] = True
            filled[ny, nx] = filled[y, x]
            queue.append((ny, nx))
col = filled[cy, cx]
me.calc_normals_split() if hasattr(me, "calc_normals_split") else None
normals = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.vertices.foreach_get("normal", normals)
facing = -normals.reshape(-1, 3)[:, 1]  # front looks towards -Y
shade = np.clip(0.55 + 0.45 * (facing * 0.5 + 0.5), 0.55, 1.0)
col = col * shade[:, None] * np.where(facing < -0.2, 0.75, 1.0)[:, None]
attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", np.hstack([col, np.ones((len(col), 1), np.float32)]).ravel())
tz.activate_colors(me)
mat = tz.material("PlayerAI", "#ffffff", 0.8)
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
vc = nt.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
me.materials.clear()
me.materials.append(mat)
# stand on the origin, 1.8 m tall, facing -Y (Godot +Z after export is the back; we rotate in Godot)
height = hi[2] - lo[2]
s = 1.8 / height
obj.scale = (s, s, s)
obj.location = Vector((-(lo[0] + hi[0]) / 2 * s, -(lo[1] + hi[1]) / 2 * s, -lo[2] * s))
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me.shade_smooth()
obj.name = me.name = "PlayerAI"
tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "player_ai.glb"), [obj])
print(f"PLAYER_AI faces={len(me.polygons)} verts={len(me.vertices)}")

scene = bpy.context.scene
tz.setup_cycles(scene, samples=24, res=(500, 700))
tz.world_color(scene, (0.6, 0.6, 0.65, 1), 1.0)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
scene.collection.objects.link(cam)
scene.camera = cam
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (0.9, 0, -0.5)
scene.collection.objects.link(sun)
for name, loc in (("front", (0.9, -3.6, 1.2)), ("back", (-0.9, 3.6, 1.2))):
    cam.location = loc
    tz.look_at(cam, (0, 0, 0.9))
    scene.render.filepath = f"/tmp/verify/player_ai_{name}.png"
    bpy.ops.render.render(write_still=True)
