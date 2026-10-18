"""TEZEROK — finish the AI-generated starter rock (FLUX.1-schnell image -> Hunyuan3D-2 shape).

Decimates, colours it with stone noise + cavity darkening, scales it to fist size and exports
assets/models/game/rock_ai.glb plus the inventory icon assets/icons/rock.png.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

SRC = os.path.join(tz.ROOT, "tools", "ai_pipeline", "work", "rock_hunyuan_raw.glb")
tz.reset_scene()
bpy.ops.import_scene.gltf(filepath=SRC)
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
for o in list(bpy.context.scene.objects):
    if o != obj:
        bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
dec = obj.modifiers.new("Decimate", "DECIMATE")
dec.ratio = min(1.0, 12000 / max(len(obj.data.polygons), 1))
bpy.ops.object.modifier_apply(modifier=dec.name)
me = obj.data
co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
lo, hi = co.min(0), co.max(0)
s = 0.15 / float((hi - lo).max())
co = (co - (lo + hi) / 2) * s
me.vertices.foreach_set("co", co.ravel())
me.update()
cols = []
for v in me.vertices:
    p = v.co * 40.0
    n = noise.noise(p, noise_basis="PERLIN_ORIGINAL") * 0.5 + 0.5
    f = noise.noise(p * 4.0, noise_basis="PERLIN_ORIGINAL") * 0.5 + 0.5
    speck = noise.noise(p * 9.0, noise_basis="PERLIN_ORIGINAL")
    k = 0.15 + 0.07 * n + 0.03 * f
    k = 0.05 if speck > 0.25 else (0.42 if speck < -0.35 else k)  # granite speckles
    k *= 0.7 + 0.3 * max(0.0, v.normal.z)
    cols += [k * 1.02, k, k * 0.96, 1.0]
attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", cols)
tz.activate_colors(me)
mat = tz.material("RockAI", "#ffffff", 0.85)
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
vc = nt.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
me.materials.clear()
me.materials.append(mat)
me.shade_smooth()
obj.name = me.name = "RockAI"
tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "rock_ai.glb"), [obj])
print(f"ROCK_AI faces={len(me.polygons)}")

scene = bpy.context.scene
tz.setup_cycles(scene, samples=24, res=(128, 128))
scene.render.film_transparent = True
scene.view_settings.view_transform = "Standard"
tz.world_color(scene, (0.5, 0.5, 0.55, 1), 0.8)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.17
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = Vector((1.0, -1.4, 0.9)).normalized() * 0.6
tz.look_at(cam, (0, 0, 0))
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (math.radians(50), 0, math.radians(-40))
scene.collection.objects.link(sun)
scene.render.filepath = os.path.join(tz.ROOT, "assets", "icons", "rock.png")
bpy.ops.render.render(write_still=True)
scene.render.resolution_x = scene.render.resolution_y = 400
scene.render.film_transparent = False
scene.render.filepath = "/tmp/verify/rock_ai.png"
bpy.ops.render.render(write_still=True)
