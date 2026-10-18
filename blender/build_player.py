"""TEZEROK — player character generator.

Builds the soldier from procedural parts (skin-modifier body, sculpted head, plate
carrier, two helmets, glowing hip device), rigs it and bakes a seamless 8 s idle loop.

Run:    blender -b --factory-startup --python blender/build_player.py [-- --preview DIR]
Writes: assets/models/player.glb, blender/player.blend
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402
from tz_common import gauss, lerp, smoothstep  # noqa: E402

random.seed(11)
scene = tz.reset_scene()
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW_DIR = ARGS[ARGS.index("--preview") + 1] if "--preview" in ARGS else None

# ----------------------------------------------------------------------------- skeleton
V = Vector
J = {
    "root": V((0.0, 0.0, 0.0)),
    "pelvis": V((0.0, 0.0, 0.975)),
    "waist": V((0.0, 0.006, 1.115)),
    "chest": V((0.0, 0.0, 1.29)),
    "upper_chest": V((0.0, 0.01, 1.415)),
    "neck_base": V((0.0, 0.016, 1.498)),
    "neck_top": V((0.0, 0.008, 1.60)),
    "head_top": V((0.0, 0.0, 1.81)),
    # right arm hangs and carries a helmet
    "shoulder_R": V((-0.2, 0.02, 1.43)),
    "elbow_R": V((-0.257, 0.05, 1.165)),
    "wrist_R": V((-0.285, -0.008, 0.925)),
    "hand_R": V((-0.29, -0.024, 0.80)),
    # left arm is bent and holds the respirator helmet against the body
    "shoulder_L": V((0.2, 0.02, 1.43)),
    "elbow_L": V((0.268, 0.07, 1.16)),
    "wrist_L": V((0.282, -0.15, 1.075)),
    "hand_L": V((0.272, -0.235, 1.098)),
}
for s, k in ((1.0, "L"), (-1.0, "R")):
    J[f"clav_{k}"] = V((0.035 * s, 0.014, 1.432))
    J[f"hip_{k}"] = V((0.095 * s, 0.0, 0.925))
    J[f"knee_{k}"] = V((0.112 * s, -0.022, 0.52))
    J[f"ankle_{k}"] = V((0.128 * s, 0.025, 0.105))
    J[f"toe_{k}"] = V((0.134 * s, -0.135, 0.03))

BONES = [  # name, head, tail, parent
    ("root", J["root"], V((0.0, 0.0, 0.15)), None),
    ("hips", J["pelvis"], J["waist"], "root"),
    ("spine", J["waist"], J["chest"], "hips"),
    ("chest", J["chest"], J["neck_base"], "spine"),
    ("neck", J["neck_base"], J["neck_top"], "chest"),
    ("head", J["neck_top"], J["head_top"], "neck"),
]
for k in ("L", "R"):
    BONES += [
        (f"shoulder.{k}", J[f"clav_{k}"], J[f"shoulder_{k}"], "chest"),
        (f"upper_arm.{k}", J[f"shoulder_{k}"], J[f"elbow_{k}"], f"shoulder.{k}"),
        (f"forearm.{k}", J[f"elbow_{k}"], J[f"wrist_{k}"], f"upper_arm.{k}"),
        (f"hand.{k}", J[f"wrist_{k}"], J[f"hand_{k}"], f"forearm.{k}"),
        (f"thigh.{k}", J[f"hip_{k}"], J[f"knee_{k}"], "hips"),
        (f"shin.{k}", J[f"knee_{k}"], J[f"ankle_{k}"], f"thigh.{k}"),
        (f"foot.{k}", J[f"ankle_{k}"], J[f"toe_{k}"], f"shin.{k}"),
    ]
SEG = {b[0]: (b[1], b[2]) for b in BONES}
BODY_BONES = ["hips", "spine", "chest", "neck", "thigh.L", "shin.L", "thigh.R", "shin.R",
              "shoulder.L", "upper_arm.L", "forearm.L", "shoulder.R", "upper_arm.R", "forearm.R"]

# ----------------------------------------------------------------------------- materials
M = {
    "Jacket": tz.material("Jacket", "#2c2e31", 0.9),
    "Pants": tz.material("Pants", "#303235", 0.92),
    "Vest": tz.material("Vest", "#1f2123", 0.85),
    "Plate": tz.material("Plate", "#383b3e", 0.6),
    "Webbing": tz.material("Webbing", "#27292b", 0.9),
    "Boots": tz.material("Boots", "#241f1b", 0.55),
    "Sole": tz.material("Sole", "#121212", 0.9),
    "Skin": tz.material("Skin", "#c4906f", 0.5),
    "Hair": tz.material("Hair", "#1d1813", 0.65),
    "EyeWhite": tz.material("EyeWhite", "#cfc8bd", 0.25),
    "Iris": tz.material("Iris", "#2b1d13", 0.2),
    "Helmet": tz.material("Helmet", "#4b4e40", 0.5),
    "Visor": tz.material("Visor", "#0d0f11", 0.12, metallic=0.4),
    "Metal": tz.material("Metal", "#6d7072", 0.4, metallic=0.85),
    "Glow": tz.material("Glow", "#38f2e2", 0.3, emission="#38f2e2", strength=8.0),
    "Patch": tz.material("Patch", "#8a7748", 0.85),
}

PARTS = []


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


def auto_weights(candidates, power=6.0, top=3):
    segs = [(n, SEG[n][0], SEG[n][1]) for n in candidates]

    def fn(co):
        ds = sorted((seg_dist(co, a, b), n) for n, a, b in segs)[:top]
        ws = [(n, 1.0 / max(d, 1e-4) ** power) for d, n in ds]
        total = sum(w for _, w in ws)
        return {n: w / total for n, w in ws}
    return fn


def rigid(bone):
    return lambda co: {bone: 1.0}


def blend_z(low, high, z0, z1):
    return lambda co: {high: smoothstep(z0, z1, co.z), low: 1.0 - smoothstep(z0, z1, co.z)}


def add_part(name, bm, mats, weights, keep_colors=False, smooth=True, sharp=40.0):
    layer = tz.color_layer(bm)
    if not keep_colors:
        for v in bm.verts:
            v[layer] = (1.0, 1.0, 1.0, 1.0)
    obj = tz.mesh_object(name, bm, [M[m] for m in mats], smooth=smooth, sharp_angle=sharp)
    groups = {}
    for v in obj.data.vertices:
        for bone, w in weights(v.co).items():
            if w > 1e-3:
                groups.setdefault(bone, []).append((v.index, w))
    for bone, items in groups.items():
        vg = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        for idx, w in items:
            vg.add([idx], w, "REPLACE")
    PARTS.append(obj)
    return obj


# ----------------------------------------------------------------------------- body
def body_graph(with_arms=True):
    nodes, edges = [], []

    def n(co, r):
        nodes.append((co, r))
        return len(nodes) - 1

    pelvis = n(J["pelvis"], (0.163, 0.11))
    waist = n(J["waist"], (0.153, 0.105))
    chest = n(J["chest"], (0.182, 0.122))
    upper = n(J["upper_chest"], (0.178, 0.113))
    neck0 = n(J["neck_base"] + V((0, 0, 0.006)), (0.069, 0.069))
    neck1 = n(J["neck_top"] + V((0, 0, 0.012)), (0.061, 0.063))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck0), (neck0, neck1)]
    for k in ("L", "R"):
        hip = n(J[f"hip_{k}"] + V((0, 0, -0.02)), (0.093, 0.099))
        thigh = n(J[f"hip_{k}"].lerp(J[f"knee_{k}"], 0.45), (0.084, 0.088))
        knee = n(J[f"knee_{k}"], (0.066, 0.07))
        calf = n(J[f"knee_{k}"].lerp(J[f"ankle_{k}"], 0.4), (0.064, 0.068))
        ankle = n(J[f"ankle_{k}"] + V((0, 0, 0.005)), (0.05, 0.053))
        edges += [(pelvis, hip), (hip, thigh), (thigh, knee), (knee, calf), (calf, ankle)]
        if with_arms:
            sh = n(J[f"shoulder_{k}"], (0.069, 0.069))
            ua = n(J[f"shoulder_{k}"].lerp(J[f"elbow_{k}"], 0.5), (0.063, 0.063))
            el = n(J[f"elbow_{k}"], (0.056, 0.056))
            fa = n(J[f"elbow_{k}"].lerp(J[f"wrist_{k}"], 0.5), (0.052, 0.052))
            wr = n(J[f"wrist_{k}"], (0.047, 0.047))
            edges += [(upper, sh), (sh, ua), (ua, el), (el, fa), (fa, wr)]
    return nodes, edges


nodes, edges = body_graph(True)
body_me = tz.skin_mesh("BodyFull", nodes, edges, root=0, subsurf=2)
nodes_t, edges_t = body_graph(False)
torso_me = tz.skin_mesh("TorsoOnly", nodes_t, edges_t, root=0, subsurf=2)

bm_torso = tz.bm_from_mesh(torso_me)
BVH_TORSO = BVHTree.FromBMesh(bm_torso)
bm_torso.free()
bm_full = tz.bm_from_mesh(body_me)
BVH_FULL = BVHTree.FromBMesh(bm_full)
bm_full.free()

body_w = auto_weights(BODY_BONES)
bm = tz.bm_from_mesh(body_me)
JACKET, PANTS, SKIN = 0, 1, 2
for f in bm.faces:
    c = f.calc_center_median()
    w = body_w(c)
    bone = max(w, key=w.get)
    if c.z > 1.508 and abs(c.x) < 0.09:
        f.material_index = SKIN
    elif bone.startswith(("thigh", "shin")) or (bone == "hips" and c.z < 0.995):
        f.material_index = PANTS
    else:
        f.material_index = JACKET
add_part("Body", bm, ["Jacket", "Pants", "Skin"], body_w)


# ----------------------------------------------------------------------------- clothing shells
def wrap_band(bvh, z0, z1, nz, na, off_in, off_out, flare=None, mat=0):
    bm = bmesh.new()
    outer, inner = {}, {}
    for iz in range(nz + 1):
        z = z0 + (z1 - z0) * iz / nz
        for ia in range(na):
            a = 2.0 * math.pi * ia / na
            d = V((math.cos(a), math.sin(a), 0.0))
            hit = bvh.ray_cast(V((0.0, 0.0, z)) + d * 0.6, -d, 1.0)[0]
            p = hit if hit is not None else V((0.0, 0.0, z)) + d * 0.1
            fo = flare(z) if flare else 0.0
            outer[iz, ia] = bm.verts.new(p + d * (off_out + fo))
            inner[iz, ia] = bm.verts.new(p + d * (off_in + fo))
    for iz in range(nz):
        for ia in range(na):
            ib = (ia + 1) % na
            bm.faces.new((outer[iz, ia], outer[iz, ib], outer[iz + 1, ib], outer[iz + 1, ia]))
            bm.faces.new((inner[iz, ib], inner[iz, ia], inner[iz + 1, ia], inner[iz + 1, ib]))
    for ia in range(na):
        ib = (ia + 1) % na
        bm.faces.new((inner[0, ia], inner[0, ib], outer[0, ib], outer[0, ia]))
        bm.faces.new((outer[nz, ia], outer[nz, ib], inner[nz, ib], inner[nz, ia]))
    for f in bm.faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def surface_patch(bvh, d, center, u_axis, v_axis, half_u, half_v, nu, nv, off_in, off_out, mat=0, bm=None):
    bm = bm or bmesh.new()
    d = V(d).normalized()
    outer, inner = {}, {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            p = V(center) + V(u_axis) * (-half_u + 2.0 * half_u * i / nu) + V(v_axis) * (-half_v + 2.0 * half_v * j / nv)
            hit = bvh.ray_cast(p - d * 0.6, d, 1.2)[0]
            base = hit if hit is not None else p
            outer[i, j] = bm.verts.new(base - d * off_out)
            inner[i, j] = bm.verts.new(base - d * off_in)
    faces = []
    for i in range(nu):
        for j in range(nv):
            faces.append(bm.faces.new((outer[i, j], outer[i + 1, j], outer[i + 1, j + 1], outer[i, j + 1])))
            faces.append(bm.faces.new((inner[i, j + 1], inner[i + 1, j + 1], inner[i + 1, j], inner[i, j])))
    ring = ([(i, 0) for i in range(nu)] + [(nu, j) for j in range(nv)]
            + [(i, nv) for i in range(nu, 0, -1)] + [(0, j) for j in range(nv, 0, -1)])
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        faces.append(bm.faces.new((outer[a], inner[a], inner[b], outer[b])))
    for f in faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return bm


def shoulder_strap(bvh, x, half_w, steps, off_in, off_out, cz=1.40, mat=0, bm=None):
    bm = bm or bmesh.new()
    rows = []
    for i in range(steps + 1):
        th = math.pi * i / steps
        d = V((0.0, math.cos(th), -math.sin(th)))
        row = []
        for sx in (-half_w, half_w):
            axis = V((x + sx, 0.0, cz))
            hit = bvh.ray_cast(axis - d * 0.6, d, 1.2)[0]
            base = hit if hit is not None else axis
            row.append((bm.verts.new(base - d * off_out), bm.verts.new(base - d * off_in)))
        rows.append(row)
    faces = []
    for i in range(steps):
        (o0, i0), (o1, i1) = rows[i]
        (o2, i2), (o3, i3) = rows[i + 1]
        faces += [bm.faces.new((o0, o1, o3, o2)), bm.faces.new((i2, i3, i1, i0)),
                  bm.faces.new((o0, o2, i2, i0)), bm.faces.new((o1, i1, i3, o3))]
    (o0, i0), (o1, i1) = rows[0]
    faces.append(bm.faces.new((o0, i0, i1, o1)))
    (o0, i0), (o1, i1) = rows[-1]
    faces.append(bm.faces.new((o1, i1, i0, o0)))
    for f in faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return bm


X3, Y3, Z3 = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
torso_w = blend_z("spine", "chest", 1.16, 1.30)

# plate carrier: vest body, plates, pouches, straps
add_part("Vest", wrap_band(BVH_TORSO, 1.0, 1.385, 10, 40, 0.004, 0.018), ["Vest"], torso_w, sharp=50)
bm = surface_patch(BVH_TORSO, Y3, (0, 0, 1.262), X3, Z3, 0.118, 0.128, 8, 8, 0.012, 0.036)
surface_patch(BVH_TORSO, -Y3, (0, 0, 1.25), X3, Z3, 0.122, 0.14, 8, 8, 0.012, 0.03, bm=bm)
surface_patch(BVH_TORSO, Y3, (0, 0, 1.371), X3, Z3, 0.07, 0.012, 4, 1, 0.035, 0.041, bm=bm)  # name tape
add_part("Plates", bm, ["Plate"], torso_w, sharp=35)
bm = bmesh.new()
for x in (-0.082, 0.0, 0.082):
    surface_patch(BVH_TORSO, Y3, (x, 0, 1.075), X3, Z3, 0.036, 0.05, 3, 4, 0.028, 0.07, bm=bm)
    surface_patch(BVH_TORSO, Y3, (x, 0, 1.118), X3, Z3, 0.039, 0.012, 3, 1, 0.066, 0.076, bm=bm)
surface_patch(BVH_TORSO, Y3, (0.075, 0, 1.31), X3, Z3, 0.028, 0.045, 2, 4, 0.034, 0.062, bm=bm)  # radio pouch
for x in (-0.106, 0.106):
    shoulder_strap(BVH_TORSO, x, 0.026, 14, 0.006, 0.02, bm=bm)
add_part("Webbing", bm, ["Webbing"], torso_w, sharp=40)

# belt + buckle
bm = wrap_band(BVH_TORSO, 0.962, 1.004, 2, 40, 0.003, 0.017)
add_part("Belt", bm, ["Webbing"], rigid("hips"), sharp=50)
bm = surface_patch(BVH_TORSO, Y3, (0, 0, 0.983), X3, Z3, 0.03, 0.017, 2, 1, 0.015, 0.026)
add_part("Buckle", bm, ["Metal"], rigid("hips"), sharp=30)

# jacket collar
bm = wrap_band(BVH_TORSO, 1.452, 1.552, 3, 32, 0.003, 0.016, flare=lambda z: (z - 1.452) * 0.3)
add_part("Collar", bm, ["Jacket"], lambda co: {"neck": 0.5, "chest": 0.5}, sharp=60)

# knee pads, cargo pockets, sleeve patch
for k, s in (("L", 1.0), ("R", -1.0)):
    knee = J[f"knee_{k}"]
    bm = surface_patch(BVH_TORSO, Y3, (knee.x, 0, 0.515), X3, Z3, 0.045, 0.06, 4, 5, 0.004, 0.022)
    add_part(f"KneePad.{k}", bm, ["Plate"], blend_z(f"shin.{k}", f"thigh.{k}", 0.48, 0.56), sharp=35)
    bm = surface_patch(BVH_TORSO, V((-s, 0, 0)), (0.3 * s, -0.004, 0.70), Y3, Z3, 0.048, 0.062, 4, 5, 0.002, 0.024)
    surface_patch(BVH_TORSO, V((-s, 0, 0)), (0.3 * s, -0.004, 0.765), Y3, Z3, 0.052, 0.012, 4, 1, 0.022, 0.03, bm=bm)
    add_part(f"Pocket.{k}", bm, ["Webbing"], rigid(f"thigh.{k}"), sharp=35)
bm = surface_patch(BVH_FULL, V((-1, 0, 0)), (0.5, 0.03, 1.345), Y3, Z3, 0.028, 0.026, 2, 2, 0.001, 0.005)
add_part("SleevePatch", bm, ["Patch"], rigid("upper_arm.L"), sharp=30)


# ----------------------------------------------------------------------------- hands & boots
def frame_matrix(origin, direction, palm_normal):
    ez = -V(direction).normalized()
    n = V(palm_normal)
    ex = (n - ez * n.dot(ez)).normalized()
    ey = ez.cross(ex)
    m = Matrix.Identity(4)
    for r in range(3):
        m[r][0], m[r][1], m[r][2] = ex[r], ey[r], ez[r]
    m.translation = V(origin)
    return m


def build_hand(k, palm_normal):
    nodes = [((0, 0, 0), (0.033, 0.04)), ((0, 0, -0.06), (0.026, 0.05)), ((0.004, 0, -0.105), (0.022, 0.047)),
             ((0.016, 0, -0.14), (0.018, 0.042)), ((0.032, 0, -0.162), (0.014, 0.036)),
             ((0.014, -0.034, -0.045), (0.016, 0.016)), ((0.036, -0.052, -0.092), (0.012, 0.012))]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (1, 5), (5, 6)]
    me = tz.skin_mesh(f"Hand.{k}", [(V(c), r) for c, r in nodes], edges, root=0, subsurf=2)
    bm = tz.bm_from_mesh(me)
    wrist, tip = J[f"wrist_{k}"], J[f"hand_{k}"]
    mtx = frame_matrix(wrist - (tip - wrist).normalized() * 0.03, tip - wrist, palm_normal)
    bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts[:])
    add_part(f"Hand.{k}", bm, ["Skin"], rigid(f"hand.{k}"))



def convex_hull_2d(points):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


build_hand("R", (1.0, 0.0, 0.0))
build_hand("L", (0.0, 0.5, 0.86))

for k, s in (("L", 1.0), ("R", -1.0)):
    nodes = [((0, 0.0, 0.12), (0.056, 0.06)), ((0, 0.005, 0.25), (0.063, 0.067)), ((0, 0.045, 0.055), (0.046, 0.05)),
             ((0, -0.085, 0.048), (0.053, 0.045)), ((0, -0.15, 0.045), (0.047, 0.036))]
    me = tz.skin_mesh(f"Boot.{k}", [(V(c), r) for c, r in nodes], [(1, 0), (0, 2), (0, 3), (3, 4)], root=0, subsurf=2)
    bm = tz.bm_from_mesh(me)
    for f in bm.faces:
        f.material_index = 0
    pts = sorted({(round(v.co.x, 4), round(v.co.y, 4)) for v in bm.verts if v.co.z < 0.03})
    hull = convex_hull_2d(pts)
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    ring = [bm.verts.new((cx + (x - cx) * 1.07, cy + (y - cy) * 1.035, 0.0)) for x, y in hull]
    base = bm.faces.new(ring[::-1])
    ext = bmesh.ops.extrude_face_region(bm, geom=[base])
    bmesh.ops.translate(bm, vec=(0, 0, 0.026), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    for f in tz.faces_of(ring) + [e for e in ext["geom"] if isinstance(e, bmesh.types.BMFace)]:
        f.material_index = 1
    ankle = J[f"ankle_{k}"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation((ankle.x, ankle.y - 0.01, 0.0)) @ Matrix.Rotation(math.radians(-6 * s), 4, "Z"), verts=bm.verts[:])
    add_part(f"Boot.{k}", bm, ["Boots", "Sole"], lambda co, k=k: {f"foot.{k}": 1.0 - smoothstep(0.14, 0.24, co.z),
                                                                  f"shin.{k}": smoothstep(0.14, 0.24, co.z)}, sharp=60)


# ----------------------------------------------------------------------------- head
def sphere_cap(bm, scale, keep, mat, segs=(32, 20)):
    res = bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    verts = res["verts"]
    kill = [v for v in verts if not keep(v.co)]
    survivors = [v for v in verts if keep(v.co)]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    for v in survivors:
        v.co = V((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    faces = tz.faces_of(survivors)
    for f in faces:
        f.material_index = mat
    return faces


HEAD_C = V((0.0, 0.004, 1.695))
HS = (0.077, 0.097, 0.116)


def head_point(u, features=True):
    x, y, z = u.x, u.y, u.z
    if z < 0.0:
        t = -z
        x *= 1.0 - 0.13 * t ** 1.6
        if y < 0.0:
            y *= 1.0 - 0.12 * t
    if y > 0.0 and z > -0.3:
        y *= 1.0 + 0.08 * (z + 0.3)
    if y < -0.55:
        y = -0.55 + (y + 0.55) * 0.8
    px, py, pz = x * HS[0], y * HS[1], z * HS[2]
    d = 0.0
    if features:
        front = smoothstep(0.3, 0.8, -u.y)
        ax = abs(px)
        if -0.047 < pz < 0.03:
            prof = 0.004 + 0.017 * (0.02 - pz) / 0.054 if pz >= -0.034 else 0.021 * (pz + 0.047) / 0.013
            width = 0.0085 + 0.0065 * smoothstep(0.0, -0.036, pz)
            d += prof * gauss(px, width) * smoothstep(0.03, 0.012, pz)
        d += 0.006 * gauss(pz - 0.027, 0.01) * smoothstep(0.066, 0.03, ax)
        d -= 0.0065 * gauss(pz - 0.004, 0.011) * gauss(ax - 0.031, 0.013)
        d += 0.004 * gauss(pz + 0.014, 0.016) * gauss(ax - 0.05, 0.014)
        d += 0.004 * gauss(pz + 0.056, 0.007) * gauss(px, 0.02)
        d += 0.0035 * gauss(pz + 0.071, 0.006) * gauss(px, 0.017)
        d -= 0.002 * gauss(pz + 0.0635, 0.003) * gauss(px, 0.02)
        d -= 0.002 * gauss(pz + 0.045, 0.005) * gauss(px, 0.012)
        d += 0.007 * gauss(pz + 0.097, 0.013) * gauss(px, 0.022)
        d *= front
    return HEAD_C + V((px, py - d, pz)), (px, pz)


def head_tint(px, pz, u):
    front = smoothstep(0.2, 0.7, -u.y)
    ax = abs(px)
    stubble = smoothstep(-0.04, -0.06, pz) * front + smoothstep(-0.02, -0.06, pz) * smoothstep(0.03, 0.06, ax)
    stubble += gauss(pz + 0.05, 0.006) * gauss(px, 0.018) * front
    stubble *= 1.0 - gauss(pz + 0.064, 0.01) * gauss(px, 0.022)
    stubble = min(1.0, stubble) * smoothstep(-0.12, -0.08, pz) + min(1.0, stubble) * (1 - smoothstep(-0.12, -0.08, pz)) * 0.7
    r, g, b = 1.0 - 0.30 * stubble, 1.0 - 0.32 * stubble, 1.0 - 0.28 * stubble
    lips = gauss(pz + 0.064, 0.009) * gauss(px, 0.02) * front
    r, g, b = r * (1 - 0.08 * lips), g * (1 - 0.25 * lips), b * (1 - 0.22 * lips)
    sock = gauss(pz - 0.004, 0.012) * gauss(ax - 0.031, 0.016) * front
    r, g, b = r * (1 - 0.2 * sock), g * (1 - 0.24 * sock), b * (1 - 0.22 * sock)
    cheek = gauss(pz + 0.02, 0.02) * gauss(ax - 0.045, 0.02) * front
    g, b = g * (1 - 0.06 * cheek), b * (1 - 0.06 * cheek)
    return (r, g, b, 1.0)


bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=64, radius=1.0)
layer = tz.color_layer(bm)
for v in bm.verts:
    u = v.co.normalized()
    p, (px, pz) = head_point(u)
    v[layer] = head_tint(px, pz, u)
    v.co = p
add_part("Head", bm, ["Skin"], rigid("head"), keep_colors=True, sharp=None)

bm_head = bmesh.new()
bm_head.from_mesh(PARTS[-1].data)
BVH_HEAD = BVHTree.FromBMesh(bm_head)
bm_head.free()


def hair_threshold(u, jitter):
    f = -u.y
    if f >= 0.0:
        t = lerp(0.22, 0.44, smoothstep(0.2, 0.7, f))
    else:
        t = lerp(0.22, -0.52, smoothstep(-0.1, -0.75, f))
    return t + jitter


bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=112, v_segments=80, radius=1.0)
for v in bm.verts:
    u = v.co.normalized()
    jitter = 0.025 * math.sin(u.x * 23.0 + u.y * 11.0) * math.cos(u.y * 19.0 - u.z * 7.0)
    thr = hair_threshold(u, jitter)
    grow = smoothstep(thr - 0.09, thr + 0.07, u.z)
    p, _ = head_point(u, features=False)
    out = p - HEAD_C
    volume = 0.06 * grow + 0.02 * grow * max(0.0, u.z) - 0.04 * (1.0 - grow)
    v.co = HEAD_C + out * (1.0 + volume) + out.normalized() * 0.0012 * grow * math.sin(u.x * 90 + u.z * 70)
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.006)
add_part("Hair", bm, ["Hair"], rigid("head"), sharp=None)

# eyes, brows, ears
bm = bmesh.new()
for s in (1.0, -1.0):
    hit = BVH_HEAD.ray_cast(V((0.031 * s, -0.5, HEAD_C.z + 0.004)), Y3, 1.0)[0]
    eye_c = hit + V((0.0, 0.0072, 0.0))
    res = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.0115, matrix=Matrix.Translation(eye_c))
    for f in tz.faces_of(res["verts"]):
        f.material_index = 0
    res = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.0058,
                                    matrix=Matrix.Translation(eye_c + V((0.0, -0.0098, 0.0))) @ Matrix.Diagonal((1.0, 0.45, 1.0, 1.0)))
    for f in tz.faces_of(res["verts"]):
        f.material_index = 1
add_part("Eyes", bm, ["EyeWhite", "Iris"], rigid("head"), sharp=None)

for s in (1.0, -1.0):
    hit = BVH_HEAD.ray_cast(V((0.031 * s, -0.5, HEAD_C.z + 0.004)), Y3, 1.0)[0]
    eye_c = hit + V((0.0, 0.0072, 0.0))
    for idx, (keep, tilt) in enumerate(((lambda c: c.z > 0.3, -14), (lambda c: c.z < -0.62, 6))):
        bm = bmesh.new()
        faces = sphere_cap(bm, (0.0127, 0.0127, 0.0127), keep, 0, segs=(20, 14))
        bmesh.ops.solidify(bm, geom=faces, thickness=0.0016)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(eye_c) @ Matrix.Rotation(math.radians(tilt), 4, "X")
                            @ Matrix.Rotation(math.radians(-8 * s), 4, "Y"), verts=bm.verts[:])
        layer = tz.color_layer(bm)
        for v in bm.verts:
            v[layer] = (0.92, 0.84, 0.82, 1.0)
        add_part(f"Eyelid{idx}.{'L' if s > 0 else 'R'}", bm, ["Skin"], rigid("head"), keep_colors=True, sharp=None)

bm = bmesh.new()
for s in (1.0, -1.0):
    hit = BVH_HEAD.ray_cast(V((0.03 * s, -0.5, HEAD_C.z + 0.025)), Y3, 1.0)[0]
    mtx = (Matrix.Translation(hit + V((0.0, 0.0005, 0.0))) @ Matrix.Rotation(math.radians(-9 * s), 4, "Y")
           @ Matrix.Rotation(math.radians(14 * s), 4, "Z") @ Matrix.Diagonal((0.036, 0.007, 0.0065, 1.0)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
add_part("Brows", bm, ["Hair"], rigid("head"), sharp=None)

bm = bmesh.new()
for s in (1.0, -1.0):
    mtx = (Matrix.Translation(HEAD_C + V((0.076 * s, 0.012, -0.004))) @ Matrix.Rotation(math.radians(16 * s), 4, "Z")
           @ Matrix.Diagonal((0.011, 0.022, 0.031, 1.0)))
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0, matrix=mtx)
layer = tz.color_layer(bm)
for v in bm.verts:
    v[layer] = (1.0, 0.9, 0.88, 1.0)
add_part("Ears", bm, ["Skin"], rigid("head"), keep_colors=True, sharp=None)


# ----------------------------------------------------------------------------- helmets & device
# combat helmet with visor, hanging from the right hand
bm = bmesh.new()
shell = sphere_cap(bm, (0.118, 0.132, 0.116), lambda c: c.z > -0.12 + 0.42 * max(0.0, -c.y - 0.2), 0)
bmesh.ops.solidify(bm, geom=shell, thickness=0.01)
visor = sphere_cap(bm, (0.124, 0.139, 0.122), lambda c: c.y < -0.42 and -0.5 < c.z < 0.28, 1)
bmesh.ops.solidify(bm, geom=visor, thickness=0.006)
for s in (1.0, -1.0):
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.117 * s, -0.01, 0.0)) @ Matrix.Diagonal((0.012, 0.09, 0.022, 1)))
    for f in tz.faces_of(res["verts"]):
        f.material_index = 2
mtx = (Matrix.Translation(J["hand_R"] + V((-0.016, 0.004, -0.088))) @ Matrix.Rotation(math.radians(10), 4, "Z")
       @ Matrix.Rotation(math.radians(-95), 4, "Y"))
bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts[:])
add_part("HelmetR", bm, ["Helmet", "Visor", "Metal"], rigid("hand.R"), sharp=40)

# respirator helmet carried under the left arm
bm = bmesh.new()
shell = sphere_cap(bm, (0.122, 0.13, 0.128), lambda c: True, 0, segs=(36, 24))
visor = sphere_cap(bm, (0.127, 0.136, 0.133), lambda c: c.y < -0.38 and -0.25 < c.z < 0.42, 1)
bmesh.ops.solidify(bm, geom=visor, thickness=0.006)
res = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.034, radius2=0.03, depth=0.035,
                            matrix=Matrix.Translation((0.0, -0.122, -0.07)) @ Matrix.Rotation(math.radians(90), 4, "X"))
for f in tz.faces_of(res["verts"]):
    f.material_index = 2
res = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.022, radius2=0.022, depth=0.012,
                            matrix=Matrix.Translation((0.0, -0.142, -0.07)) @ Matrix.Rotation(math.radians(90), 4, "X"))
for f in tz.faces_of(res["verts"]):
    f.material_index = 1
for s in (1.0, -1.0):
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.121 * s, 0.0, 0.01)) @ Matrix.Diagonal((0.01, 0.07, 0.03, 1)))
    for f in tz.faces_of(res["verts"]):
        f.material_index = 2
mtx = Matrix.Translation((0.3, -0.09, 1.19)) @ Matrix.Rotation(math.radians(34), 4, "Z") @ Matrix.Rotation(math.radians(-6), 4, "X")
bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts[:])
add_part("HelmetL", bm, ["Helmet", "Visor", "Metal"], rigid("forearm.L"), sharp=40)

# glowing hip device (hexagonal power cell)
hit = BVH_TORSO.ray_cast(V((0.15, -0.6, 0.875)), Y3, 1.0)[0]
dev_c = hit + V((0.0, -0.034, 0.0))
bm = bmesh.new()
res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.064, radius2=0.064, depth=0.05,
                            matrix=Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(30), 4, "Z"))
for f in tz.faces_of(res["verts"]):
    f.material_index = 0
ring_o, ring_i = [], []
for i in range(6):
    a = math.radians(60 * i + 30)
    ring_o.append(V((math.cos(a) * 0.05, -0.0262, math.sin(a) * 0.05)))
    ring_i.append(V((math.cos(a) * 0.043, -0.0262, math.sin(a) * 0.043)))
glow = bmesh.new()
for i in range(6):
    j = (i + 1) % 6
    if i == 4:
        continue  # broken outline reads as a stylised glyph
    quad = [glow.verts.new(p) for p in (ring_i[i], ring_i[j], ring_o[j], ring_o[i])]
    glow.faces.new(quad)
for a, b in ((V((0, -0.0262, 0.036)), V((0, -0.0262, -0.004))), (V((0, -0.0262, -0.004)), V((-0.026, -0.0262, -0.03))),
             (V((0, -0.0262, -0.004)), V((0.026, -0.0262, -0.03)))):
    side = (b - a).cross(Y3).normalized() * 0.0028
    glow.faces.new([glow.verts.new(p) for p in (a - side, b - side, b + side, a + side)])
ext = bmesh.ops.extrude_face_region(glow, geom=glow.faces[:])
bmesh.ops.translate(glow, vec=(0, -0.003, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
bmesh.ops.recalc_face_normals(glow, faces=glow.faces[:])
tmp = bpy.data.meshes.new("glow_tmp")
glow.to_mesh(tmp)
glow.free()
n_faces = len(bm.faces)
bm.from_mesh(tmp)
bpy.data.meshes.remove(tmp)
bm.faces.ensure_lookup_table()
for f in bm.faces[n_faces:]:
    f.material_index = 1
res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.0, 0.004, 0.075)) @ Matrix.Diagonal((0.03, 0.03, 0.06, 1)))
for f in tz.faces_of(res["verts"]):
    f.material_index = 2
mtx = Matrix.Translation(dev_c) @ Matrix.Rotation(math.radians(14), 4, "Z") @ Matrix.Diagonal((1.0, 1.0, 1.22, 1.0))
bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts[:])
add_part("Device", bm, ["Plate", "Glow", "Webbing"], rigid("hips"), sharp=30)

# ----------------------------------------------------------------------------- join, AO, rig
player = tz.join_objects(PARTS, "Player")


def bake_vertex_ao(obj, samples=14, dist=0.14, strength=0.72):
    me = obj.data
    bm = tz.bm_from_mesh(me)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    dirs = []
    for i in range(samples):
        zc = math.sqrt(1.0 - (i + 0.5) / samples)
        r = math.sqrt(max(0.0, 1.0 - zc * zc))
        phi = i * 2.399963
        dirs.append(V((r * math.cos(phi), r * math.sin(phi), zc)))
    attr = me.color_attributes["Col"]
    cols = [0.0] * (len(me.vertices) * 4)
    attr.data.foreach_get("color", cols)
    for v in me.vertices:
        n = v.normal
        q = Z3.rotation_difference(n)
        origin = v.co + n * 0.0025
        hits = sum(1 for dv in dirs if bvh.ray_cast(origin, q @ dv, dist)[0] is not None)
        ao = 1.0 - strength * hits / samples
        i = v.index * 4
        cols[i] *= ao
        cols[i + 1] *= ao
        cols[i + 2] *= ao
    attr.data.foreach_set("color", cols)


bake_vertex_ao(player)

arm_data = bpy.data.armatures.new("PlayerRig")
rig = bpy.data.objects.new("PlayerRig", arm_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail, eb.roll = head, tail, 0.0
    if parent:
        eb.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")

player.parent = rig
mod = player.modifiers.new("Armature", "ARMATURE")
mod.object = rig

# ----------------------------------------------------------------------------- idle loop (8 s @ 30 fps)
FPS, LOOP = 30, 240
scene.frame_start, scene.frame_end = 0, LOOP
rig.animation_data_create()
rad = math.radians


def qworld(bone, axis, ang):
    m = arm_data.bones[bone].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ V(axis)).normalized(), ang)


for f in range(LOOP + 1):
    t = f / FPS
    a = 2.0 * math.pi * t / 8.0
    b = 2.0 * math.pi * t / 4.0
    breath = math.sin(b)
    roll = rad(0.6) * math.sin(a)
    pitch = rad(0.35) * math.sin(2.0 * a + 0.7)
    poses = {
        "root": [(Y3, roll), (X3, pitch)],
        "hips": [(Y3, -0.35 * roll)],
        "spine": [(Y3, -0.25 * roll), (X3, rad(-0.4) * breath)],
        "chest": [(X3, rad(-0.9) * breath), (Z3, rad(0.6) * math.sin(a + 0.4))],
        "neck": [(X3, rad(0.5) * breath)],
        "head": [(Z3, rad(3.5) * math.sin(a + 1.1) + rad(1.0) * math.sin(3.0 * a + 0.3)),
                 (X3, rad(1.2) * math.sin(2.0 * a + 2.0)), (Y3, -0.6 * roll)],
        "shoulder.L": [(Y3, rad(-0.8) * breath)],
        "shoulder.R": [(Y3, rad(0.8) * breath)],
        "upper_arm.R": [(X3, rad(1.4) * math.sin(a + 0.9))],
        "forearm.R": [(X3, rad(1.0) * math.sin(a + 1.5))],
        "hand.R": [(X3, rad(2.0) * math.sin(a + 2.0))],
        "upper_arm.L": [(X3, rad(0.5) * math.sin(a + 0.6))],
        "forearm.L": [(Z3, rad(0.6) * math.sin(a + 1.2))],
    }
    world_feet = (Quaternion(Y3, roll) @ Quaternion(X3, pitch) @ Quaternion(Y3, -0.35 * roll)).inverted()
    for name, rots in poses.items():
        q = Quaternion()
        for axis, ang in rots:
            q = qworld(name, axis, ang) @ q
        pb = rig.pose.bones[name]
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=f, group=name)
    for k in ("L", "R"):
        m = arm_data.bones[f"foot.{k}"].matrix_local.to_3x3()
        axis, ang = world_feet.to_axis_angle()
        pb = rig.pose.bones[f"foot.{k}"]
        pb.rotation_quaternion = Quaternion((m.inverted() @ axis).normalized(), ang)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=f"foot.{k}")
rig.animation_data.action.name = "Idle"
scene.frame_set(0)

tz.export_glb(os.path.join(tz.MODELS_DIR, "player.glb"), [rig, player], animations=True)
print(f"PLAYER_STATS verts={len(player.data.vertices)} faces={len(player.data.polygons)} "
      f"materials={[m.name for m in player.data.materials]}")

# ----------------------------------------------------------------------------- preview stage (not exported)
cam = bpy.data.objects.new("PreviewCamera", bpy.data.cameras.new("PreviewCamera"))
scene.collection.objects.link(cam)
cam.data.lens = 50
cam.location = (1.15, -3.7, 1.2)
tz.look_at(cam, (0.0, 0.0, 0.93))
scene.camera = cam
key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "AREA"))
key.data.energy, key.data.size = 420.0, 2.0
key.location = (-1.8, -2.4, 2.6)
tz.look_at(key, (0, 0, 1.1))
rim = bpy.data.objects.new("Rim", bpy.data.lights.new("Rim", "AREA"))
rim.data.energy, rim.data.size, rim.data.color = 520.0, 1.5, (1.0, 0.72, 0.45)
rim.location = (2.0, 2.2, 2.2)
tz.look_at(rim, (0, 0, 1.2))
for o in (key, rim):
    scene.collection.objects.link(o)
ground = bpy.data.objects.new("Ground", bpy.data.meshes.new("Ground"))
gbm = bmesh.new()
bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=4.0)
gbm.to_mesh(ground.data)
gbm.free()
ground.data.materials.append(tz.material("PreviewGround", "#3a3a37", 0.95))
scene.collection.objects.link(ground)
tz.world_color(scene, tz.rgb("#40464f"), 0.6)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tz.BLEND_DIR, "player.blend"), compress=True)

if PREVIEW_DIR:
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    tz.setup_cycles(scene, samples=40, res=(640, 900))
    scene.render.filepath = os.path.join(PREVIEW_DIR, "player_full.png")
    bpy.ops.render.render(write_still=True)
    cam.data.lens = 120
    cam.location = (0.32, -1.25, 1.72)
    tz.look_at(cam, (0.0, 0.0, 1.69))
    scene.render.resolution_x = scene.render.resolution_y = 560
    scene.render.filepath = os.path.join(PREVIEW_DIR, "player_head.png")
    bpy.ops.render.render(write_still=True)
