"""TEZEROK — gameplay assets: first-person hand with a rock, pine tree, stone / sulfur / metal ore nodes
and 128 px inventory icons.

Run:    blender -b --factory-startup --python blender/build_game_assets.py
Writes: assets/models/game/*.glb, assets/icons/*.png
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402
from tz_common import rgb, smoothstep  # noqa: E402

OUT = os.path.join(tz.MODELS_DIR, "game")
ICONS = os.path.join(tz.ROOT, "assets", "icons")
os.makedirs(OUT, exist_ok=True)
os.makedirs(ICONS, exist_ok=True)
V = Vector


def fbm(p, octaves=3, seed=0.0):
    total, amp, norm = 0.0, 1.0, 0.0
    q = V(p) + V((seed, -seed * 0.7, seed * 0.3))
    for _ in range(octaves):
        total += amp * noise.noise(q, noise_basis="PERLIN_ORIGINAL")
        norm += amp
        amp *= 0.5
        q = q * 2.03
    return total / norm


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def scale_col(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, 1.0)


def fresh():
    tz.reset_scene()


def rock_bm(size, seed, base, accents=None, flat=0.25):
    """Displaced icosphere with vertex colours; accents(v, n) may return (color, amount)."""
    bm = bmesh.new()
    col = tz.color_layer(bm)
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    for v in bm.verts:
        n = v.co.normalized()
        d = 0.3 * fbm(n * 1.4, 3, seed) + 0.09 * fbm(n * 4.5, 2, seed + 3.0)
        p = n * (1.0 + d)
        if p.z < -flat:
            p.z = -flat + (p.z + flat) * 0.25
        v.co = V((p.x * size[0], p.y * size[1], p.z * size[2]))
    bm.normal_update()
    for v in bm.verts:
        k = 0.78 + 0.4 * (fbm(v.co * 2.2, 3, seed + 1.0) * 0.5 + 0.5)
        c = scale_col(base, k)
        c = mix(c, scale_col(c, 0.6), smoothstep(-0.1, -0.7, v.normal.z))
        if accents:
            ac, amt = accents(v.co, v.normal)
            c = mix(c, ac, amt)
        v[col] = c
    return bm


def crystals(bm, count, size, color, seed, spread, z_min=0.0):
    rng = random.Random(seed)
    col = tz.color_layer(bm)
    verts = [v for v in bm.verts if v.co.z > z_min and v.normal.z > 0.15]
    for _ in range(count):
        v = rng.choice(verts)
        h = size * rng.uniform(0.6, 1.3)
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=h * 0.32, radius2=0.0, depth=h)
        tilt = v.normal.lerp(V((rng.uniform(-1, 1), rng.uniform(-1, 1), 1)).normalized(), spread)
        m = Matrix.Translation(v.co + v.normal * h * 0.3) @ tilt.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])
        for nv in res["verts"]:
            nv[col] = scale_col(color, rng.uniform(0.85, 1.15))


def use_vertex_colors(mat):
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    if not bsdf.inputs["Base Color"].is_linked:
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def build(name, bm, mat, smooth=True, sharp=40.0):
    obj = tz.mesh_object(name, bm, [use_vertex_colors(mat)], smooth=smooth, sharp_angle=sharp)
    return obj


ROCK_MAT = lambda: tz.material("RockMat", "#ffffff", 0.88)  # noqa: E731


def export(name, objs, animations=False):
    tz.export_glb(os.path.join(OUT, name + ".glb"), objs, animations=animations)


# ----------------------------------------------------------------------------- resource nodes
fresh()
build("StoneNode", rock_bm((1.15, 1.0, 0.85), 2.0, rgb("#8d8a84")), ROCK_MAT())
export("stone_node", list(bpy.data.objects))

fresh()
sulfur_base = rgb("#8a8270")
bm = rock_bm((1.1, 0.95, 0.8), 5.0, sulfur_base,
             lambda p, n: (rgb("#d8c23a"), smoothstep(0.55, 0.8, fbm(p * 2.6, 2, 9.0) * 0.5 + 0.5)))
crystals(bm, 16, 0.32, rgb("#e6d13a"), 3, 0.5)
build("SulfurNode", bm, tz.material("SulfurMat", "#ffffff", 0.6))
export("sulfur_node", list(bpy.data.objects))

fresh()
bm = rock_bm((1.15, 1.0, 0.85), 8.0, rgb("#6e6862"),
             lambda p, n: (rgb("#8a4a2a"), smoothstep(0.5, 0.75, fbm(p * 3.1, 2, 4.0) * 0.5 + 0.5)))
crystals(bm, 10, 0.22, rgb("#5f6266"), 6, 0.7)
build("MetalNode", bm, tz.material("MetalMat", "#ffffff", 0.5, metallic=0.4))
export("metal_node", list(bpy.data.objects))

# ----------------------------------------------------------------------------- tree
fresh()
rng = random.Random(4)
bm = bmesh.new()
col = tz.color_layer(bm)
H = 9.0
trunk = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.32, radius2=0.06, depth=H,
                              matrix=Matrix.Translation((0, 0, H / 2 - 0.2)))
for v in trunk["verts"]:
    v.co.x += 0.03 * math.sin(v.co.z * 2.1)
    v[col] = scale_col(rgb("#4a3626"), 0.8 + 0.3 * rng.random())
for f in tz.faces_of(trunk["verts"]):
    f.material_index = 1
tiers = 9
for i in range(tiers):
    t = i / (tiers - 1)
    z = H * (0.45 + 0.6 * t)
    r = 2.1 * (1.0 - t) ** 0.9 + 0.35
    hs = 1.2 - 0.5 * t
    apex = bm.verts.new((0, 0, z))
    apex[col] = rgb("#1b2a1d")
    n = 14
    ring = []
    for j in range(n):
        a = math.tau * j / n + rng.random() * 0.3
        rr = r * (rng.uniform(0.9, 1.1) if j % 2 == 0 else rng.uniform(0.55, 0.7))
        vv = bm.verts.new((rr * math.cos(a), rr * math.sin(a), z - hs * (1.0 if j % 2 == 0 else 0.6)))
        vv[col] = scale_col(rgb("#3d5134") if j % 2 == 0 else rgb("#2a3b2a"), rng.uniform(0.85, 1.15))
        ring.append(vv)
    under = bm.verts.new((0, 0, z - hs * 0.55))
    under[col] = rgb("#142016")
    for j in range(n):
        a_, b_ = ring[j], ring[(j + 1) % n]
        bm.faces.new((apex, a_, b_)).material_index = 0
        bm.faces.new((under, b_, a_)).material_index = 0
obj = tz.mesh_object("Tree", bm, [tz.material("Needles", "#ffffff", 0.85), tz.material("Bark", "#ffffff", 0.95)],
                     smooth=True, sharp_angle=None)
export("tree", [obj])

# ----------------------------------------------------------------------------- held rock + hand
fresh()
held = build("HeldRock", rock_bm((0.075, 0.065, 0.06), 11.0, rgb("#86837d"), flat=0.9), ROCK_MAT())
skin = tz.material("Skin", "#c08a68", 0.55)
sleeve = tz.material("Sleeve", "#33363a", 0.9)
bm = bmesh.new()
col = tz.color_layer(bm)


def part(builder, mat_index, color):
    res = builder()
    for v in res["verts"]:
        v[col] = color
    for f in tz.faces_of(res["verts"]):
        f.material_index = mat_index


# forearm along -Y (towards the camera), fist at the origin wrapping the rock
part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.05, radius2=0.042, depth=0.36,
                                   matrix=Matrix.Translation((0, 0.25, -0.02)) @ Matrix.Rotation(math.radians(90), 4, "X")),
     1, (1, 1, 1, 1))
part(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.062, radius2=0.06, depth=0.3,
                                   matrix=Matrix.Translation((0, 0.5, -0.03)) @ Matrix.Rotation(math.radians(90), 4, "X")),
     0, (1, 1, 1, 1))
part(lambda: bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0,
                                       matrix=Matrix.Translation((0, 0.07, -0.035)) @ Matrix.Diagonal((0.055, 0.06, 0.045, 1))),
     1, (1, 1, 1, 1))
for i in range(4):  # fingers curled over the rock
    x = -0.036 + i * 0.024
    part(lambda x=x: bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=1.0,
                                               matrix=Matrix.Translation((x, 0.0, -0.065)) @ Matrix.Diagonal((0.013, 0.03, 0.016, 1))),
         1, (0.95, 0.9, 0.88, 1))
part(lambda: bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=1.0,
                                       matrix=Matrix.Translation((0.062, 0.03, -0.02)) @ Matrix.Rotation(math.radians(30), 4, "Z")
                                       @ Matrix.Diagonal((0.015, 0.035, 0.015, 1))),
     1, (0.95, 0.9, 0.88, 1))
hand = tz.mesh_object("Hand", bm, [sleeve, skin], smooth=True, sharp_angle=None)
export("hand_rock", [hand, held])

# ----------------------------------------------------------------------------- icons


def icon_scene():
    scene = bpy.context.scene
    tz.setup_cycles(scene, samples=24, res=(128, 128))
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    tz.world_color(scene, (0.5, 0.5, 0.55, 1), 0.8)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.type = "ORTHO"
    scene.collection.objects.link(cam)
    scene.camera = cam
    key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "SUN"))
    key.data.energy = 4.0
    key.rotation_euler = (math.radians(50), 0, math.radians(-40))
    scene.collection.objects.link(key)
    return scene, cam


def render_icon(name, objs):
    scene, cam = icon_scene()
    pts = [o.matrix_world @ V(c) for o in objs for c in o.bound_box]
    lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, size = (lo + hi) / 2, max((hi - lo).length, 0.01)
    cam.data.ortho_scale = size * 0.95
    cam.location = center + V((1.0, -1.4, 0.9)).normalized() * size * 3
    tz.look_at(cam, center)
    scene.render.filepath = os.path.join(ICONS, name + ".png")
    bpy.ops.render.render(write_still=True)


def icon_from_bm(name, bm, mat_fn):
    fresh()
    obj = build(name, bm, mat_fn())
    render_icon(name, [obj])


icon_from_bm("rock", rock_bm((0.9, 0.8, 0.7), 11.0, rgb("#86837d"), flat=0.9), ROCK_MAT)
icon_from_bm("stone", rock_bm((1.0, 0.8, 0.5), 21.0, rgb("#9a978f")), ROCK_MAT)
fresh()
bm = rock_bm((0.9, 0.8, 0.6), 23.0, rgb("#a49548"),
             lambda p, n: (rgb("#e0cc3c"), smoothstep(0.4, 0.7, fbm(p * 3.0, 2, 1.0) * 0.5 + 0.5)))
crystals(bm, 8, 0.3, rgb("#efd93e"), 2, 0.4)
render_icon("sulfur_ore", [build("s", bm, tz.material("SulfurMat", "#ffffff", 0.6))])
fresh()
bm = rock_bm((0.9, 0.8, 0.6), 25.0, rgb("#6e6862"),
             lambda p, n: (rgb("#94512c"), smoothstep(0.45, 0.7, fbm(p * 3.0, 2, 2.0) * 0.5 + 0.5)))
crystals(bm, 6, 0.25, rgb("#6a6d72"), 4, 0.6)
render_icon("metal_ore", [build("m", bm, tz.material("MetalMat", "#ffffff", 0.5, metallic=0.4))])
fresh()
logs = []
for i, (x, z) in enumerate(((-0.25, 0.0), (0.25, 0.0), (0.0, 0.42))):
    b = bmesh.new()
    c = tz.color_layer(b)
    res = bmesh.ops.create_cone(b, cap_ends=True, segments=14, radius1=0.24, radius2=0.24, depth=1.6,
                                matrix=Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    for v in res["verts"]:
        end = abs(v.co.y) > 0.79 and V((v.co.x - x, v.co.z - z)).length < 0.2
        v[c] = rgb("#c49a63") if end else scale_col(rgb("#5a3f2a"), 0.9 + 0.2 * random.random())
    logs.append(tz.mesh_object(f"log{i}", b, [use_vertex_colors(tz.material("Bark", "#ffffff", 0.9))], smooth=True, sharp_angle=50))
render_icon("wood", logs)
print("GAME_ASSETS_DONE")
