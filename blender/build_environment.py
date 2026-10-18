"""TEZEROK — main-menu environment generator.

Hilltop with grass and rocks, pine forests, a brick factory with smoking chimneys, a port
with cranes and ships, a radio tower on a coastal hill, the sea and distant mountains.
Coordinates match the menu camera: camera at (0, 0, 1) looking along +Y (Godot: -Z).

Run:    blender -b --factory-startup --python blender/build_environment.py
Writes: assets/models/environment.glb, assets/models/bird.glb,
        assets/textures/smoke_puff.png, blender/environment.blend
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
from tz_common import gauss, lerp, rgb, smoothstep  # noqa: E402

scene = tz.reset_scene()
rng = random.Random(5)
V = Vector
GROUND = -74.6      # valley floor
SEA_LEVEL = -76.5


def fbm(x, y, octaves=4, seed=0.0):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * noise.noise(V((x * freq + seed, y * freq - seed * 0.7, seed * 0.31)), noise_basis="PERLIN_ORIGINAL")
        norm += amp
        amp *= 0.5
        freq *= 2.03
    return total / norm


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def scale_col(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, 1.0)


def collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


C_TERRAIN, C_VEG, C_INDUSTRY, C_MARKERS = (collection(n) for n in ("Terrain", "Vegetation", "Industry", "Markers"))

MAT = {
    "Ground": tz.material("Ground", "#ffffff", 0.95),
    "Terrain": tz.material("Terrain", "#ffffff", 0.95),
    "Grass": tz.material("Grass", "#ffffff", 0.8),
    "Rock": tz.material("Rock", "#ffffff", 0.9),
    "PineNeedles": tz.material("PineNeedles", "#ffffff", 0.85),
    "Bark": tz.material("Bark", "#ffffff", 0.95),
    "Brick": tz.material("Brick", "#ffffff", 0.9),
    "Concrete": tz.material("Concrete", "#ffffff", 0.9),
    "Roof": tz.material("Roof", "#ffffff", 0.8),
    "SteelPaint": tz.material("SteelPaint", "#ffffff", 0.6, metallic=0.3),
    "Glass": tz.material("Glass", "#1a2026", 0.2),
    "WindowLit": tz.material("WindowLit", "#ffcf8a", 0.5, emission="#ffb766", strength=3.0),
    "Beacon": tz.material("Beacon", "#ff2a1a", 0.4, emission="#ff2a1a", strength=12.0),
    "Water": tz.material("Water", "#1f3440", 0.08),
    "Bird": tz.material("Bird", "#15161a", 0.8),
}


class Builder:
    """Accumulates primitives with per-vertex colours into one bmesh."""

    def __init__(self, mats):
        self.bm = bmesh.new()
        self.col = tz.color_layer(self.bm)
        self.mats = list(mats)

    def _finish(self, verts, mat, color):
        mi = self.mats.index(mat)
        for f in tz.faces_of(verts):
            f.material_index = mi
        for v in verts:
            v[self.col] = color
        return verts

    def box(self, center, size, mat, color, rot_z=0.0):
        m = Matrix.Translation(center) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        return self._finish(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat, color)

    def beam(self, a, b, thick, mat, color):
        a, b = V(a), V(b)
        d = b - a
        q = d.to_track_quat("Z", "Y")
        m = Matrix.Translation((a + b) * 0.5) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((thick, thick, d.length, 1.0))
        return self._finish(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat, color)

    def cyl(self, base, r1, r2, h, mat, color, segs=16, caps=True, axis_m=None):
        m = Matrix.Translation(base) @ (axis_m or Matrix.Identity(4)) @ Matrix.Translation((0, 0, h * 0.5))
        verts = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=segs,
                                      radius1=r1, radius2=r2, depth=h, matrix=m)["verts"]
        return self._finish(verts, mat, color)

    def dome(self, center, r, h, mat, color, segs=16):
        verts = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=8, radius=1.0)["verts"]
        low = [v for v in verts if v.co.z < -0.01]
        bmesh.ops.delete(self.bm, geom=low, context="VERTS")
        keep = [v for v in verts if v.is_valid]
        for v in keep:
            v.co = V((center[0] + v.co.x * r, center[1] + v.co.y * r, center[2] + v.co.z * h))
        return self._finish(keep, mat, color)

    def poly(self, pts, mat, color):
        verts = [self.bm.verts.new(p) for p in pts]
        self.bm.faces.new(verts)
        return self._finish(verts, mat, color)

    def prism(self, x0, x1, y0, y1, zb, zt, mat, color, along="x"):
        """Gable roof whose ridge runs along the given axis."""
        if along == "x":
            cy = (y0 + y1) * 0.5
            pts = [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb), (x0, cy, zt), (x1, cy, zt)]
            faces = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (3, 2, 1, 0)]
        else:
            cx = (x0 + x1) * 0.5
            pts = [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb), (cx, y0, zt), (cx, y1, zt)]
            faces = [(1, 2, 5, 4), (3, 0, 4, 5), (0, 1, 4), (2, 3, 5), (3, 2, 1, 0)]
        verts = [self.bm.verts.new(p) for p in pts]
        for f in faces:
            self.bm.faces.new([verts[i] for i in f])
        return self._finish(verts, mat, color)

    def build(self, name, coll, smooth=False, sharp=30.0, recalc=True):
        if recalc:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        return tz.mesh_object(name, self.bm, [MAT[m] for m in self.mats], collection=coll, smooth=smooth, sharp_angle=sharp)


# ============================================================================ terrain
def edge_r(th):
    return 6.3 + 9.0 * smoothstep(0.02, 0.5, th) + 0.8 * math.sin(th * 9.0 + 1.3)


def near_z(x, y):
    r = math.hypot(x, y)
    th = math.atan2(x, y)
    z = 0.10 * fbm(x * 0.35, y * 0.35, 3, 1.7) + 0.05 * fbm(x * 1.3, y * 1.3, 2, 4.1)
    z += 0.55 * smoothstep(0.15, 0.55, th) * smoothstep(4.0, 14.0, r)
    z -= 0.22 * (1.0 - smoothstep(0.5, 3.0, r))
    z += 0.08 * gauss(math.hypot(x - 1.0, y - 4.0), 1.2)
    depth = lerp(15.0, 5.0, smoothstep(0.12, 0.5, th))
    z -= depth * smoothstep(edge_r(th), edge_r(th) + 4.5, r) ** 1.3
    return z


def port_mask(x):
    return smoothstep(-560.0, -500.0, x) * (1.0 - smoothstep(-30.0, 30.0, x))


def coast_y(x):
    natural = 1000.0 + 90.0 * fbm(x * 0.004, 3.3, 3, 2.0) + 650.0 * smoothstep(-80.0, 520.0, x)
    return lerp(natural, 1000.0, port_mask(x))


FACTORY_RECT = (-440.0, 140.0, 330.0, 940.0)


def factory_mask(x, y):
    x0, x1, y0, y1 = FACTORY_RECT
    return (smoothstep(x0 - 50, x0, x) * (1 - smoothstep(x1, x1 + 50, x))
            * smoothstep(y0 - 50, y0, y) * (1 - smoothstep(y1, y1 + 30, y)))


def far_z(x, y):
    d = math.hypot(x, y)
    th = math.atan2(x, y)
    wr = smoothstep(0.12, 0.5, th)
    z = lerp(-12.0 - 62.5 * smoothstep(30.0, 380.0, d), -4.0 - 45.0 * smoothstep(40.0, 900.0, d), wr)
    z += (2.5 + 7.0 * wr) * fbm(x * 0.008, y * 0.008, 4, 7.0) * smoothstep(25.0, 80.0, d)
    sea = smoothstep(coast_y(x) - 25.0, coast_y(x) + 60.0, y) * (1.0 - 0.9 * wr)
    z = lerp(z, -92.0, sea)
    z += 96.0 * math.exp(-(((x - 160.0) / 150.0) ** 2 + ((y - 1150.0) / 165.0) ** 2))
    mtn = smoothstep(260.0, 1150.0, x) * smoothstep(1250.0, 2300.0, y)
    ridge = 1.0 - abs(fbm(x * 0.0016, y * 0.0016, 4, 11.0))
    z += mtn * (190.0 + 110.0 * fbm(x * 0.0011, y * 0.0011, 5, 3.0) + 70.0 * ridge)
    z += 70.0 * smoothstep(1700.0, 2700.0, y) * smoothstep(-300.0, 250.0, x) * (0.6 + 0.4 * fbm(x * 0.002, y * 0.002, 4, 9.0))
    z += 85.0 * math.exp(-(((x + 2100.0) / 950.0) ** 2 + ((y - 4300.0) / 620.0) ** 2))
    z += 55.0 * math.exp(-(((x + 900.0) / 700.0) ** 2 + ((y - 5600.0) / 500.0) ** 2))
    return lerp(z, GROUND, factory_mask(x, y))


def polar_grid(name, coll, radii, th0, th1, nth, zfn, colfn, mat):
    bm = bmesh.new()
    col = tz.color_layer(bm)
    rows = []
    for r in radii:
        row = []
        for j in range(nth + 1):
            th = lerp(th0, th1, j / nth)
            x, y = r * math.sin(th), r * math.cos(th)
            row.append(bm.verts.new((x, y, zfn(x, y))))
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(nth):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bm.normal_update()
    for v in bm.verts:
        v[col] = colfn(v.co.x, v.co.y, v.co.z, v.normal.z)
    return tz.mesh_object(name, bm, [MAT[mat]], collection=coll, smooth=True, sharp_angle=None)


DRY = rgb("#6b6440")
DRY2 = rgb("#5b5a36")
DIRT = rgb("#4c4030")
ROCKC = rgb("#6a6862")
FOREST = rgb("#1d2a1e")
FOREST2 = rgb("#2c3a27")
MEADOW = rgb("#55583a")
PLAIN = rgb("#4f4a3e")
ROAD = rgb("#3a3936")
SAND = rgb("#80786a")
SEABED = rgb("#283330")


def near_color(x, y, z, nz):
    n = fbm(x * 0.4, y * 0.4, 3, 2.2) * 0.5 + 0.5
    c = mix(DRY2, DRY, smoothstep(0.3, 0.75, n))
    c = mix(c, DIRT, smoothstep(0.62, 0.82, fbm(x * 0.9, y * 0.9, 2, 5.5) * 0.5 + 0.5) * 0.8)
    c = mix(c, ROCKC, smoothstep(0.85, 0.6, nz))
    return c


def far_color(x, y, z, nz):
    d = math.hypot(x, y)
    n = fbm(x * 0.006, y * 0.006, 4, 4.4) * 0.5 + 0.5
    c = mix(FOREST, FOREST2, smoothstep(0.35, 0.7, n))
    clearing = smoothstep(0.62, 0.78, fbm(x * 0.0035, y * 0.0035, 3, 8.1) * 0.5 + 0.5)
    c = mix(c, MEADOW, clearing * 0.85)
    c = mix(MEADOW, c, smoothstep(30.0, 90.0, d))
    plain = smoothstep(-66.0, -72.0, z) * (1.0 - smoothstep(0.2, 0.6, math.atan2(x, y)))
    pc = mix(PLAIN, MEADOW, smoothstep(0.45, 0.7, n) * 0.6)
    roads = max(gauss((x + 205.0) % 160.0 - 80.0, 3.5), gauss((y - 360.0) % 140.0 - 70.0, 3.5)) * factory_mask(x, y)
    pc = mix(pc, ROAD, roads)
    c = mix(c, pc, plain)
    c = mix(c, ROCKC, smoothstep(0.8, 0.55, nz) * 0.9)
    c = mix(c, scale_col(ROCKC, 1.15), smoothstep(150.0, 230.0, z) * smoothstep(0.4, 0.6, n))
    c = mix(c, SAND, gauss(z - SEA_LEVEL - 1.2, 1.6))
    c = mix(c, SEABED, smoothstep(SEA_LEVEL - 0.5, SEA_LEVEL - 4.0, z))
    return c


near_radii = [0.5 + 0.22 * i for i in range(46)] + [10.6 + 0.6 * i for i in range(25)] + [25.6 + 2.2 * i for i in range(10)]
terrain_near = polar_grid("HillTop", C_TERRAIN, near_radii, -1.05, 1.05, 180, near_z, near_color, "Ground")
far_radii = [14.0 * (7000.0 / 14.0) ** (i / 170.0) for i in range(171)]
terrain_far = polar_grid("Valley", C_TERRAIN, far_radii, -1.1, 1.1, 260, far_z, far_color, "Terrain")

sea_bm = bmesh.new()
sea_v = [sea_bm.verts.new((x, y, SEA_LEVEL)) for x, y in ((-9000, 600), (9000, 600), (9000, 14000), (-9000, 14000))]
sea_bm.faces.new(sea_v)
tz.color_layer(sea_bm)
sea = tz.mesh_object("Sea", sea_bm, [MAT["Water"]], collection=C_TERRAIN, smooth=False)


def ground_z(x, y):
    return near_z(x, y) if math.hypot(x, y) < 13.0 else far_z(x, y)


# ============================================================================ rocks
def make_rock(name, seed, size, coll, loc, rot_z=0.0, moss=0.6):
    b = Builder(["Rock"])
    verts = bmesh.ops.create_icosphere(b.bm, subdivisions=3, radius=1.0)["verts"]
    for v in verts:
        n = v.co.normalized()
        disp = 0.32 * fbm(n.x * 1.5 + seed, n.y * 1.5 - seed, 3, seed) + 0.1 * fbm(n.x * 4.5, n.y * 4.5 + n.z * 3.0, 2, seed + 3.0)
        p = n * (1.0 + disp)
        p.z = p.z if p.z > -0.25 else -0.25 + (p.z + 0.25) * 0.2
        v.co = V((p.x * size[0], p.y * size[1], p.z * size[2]))
    b.bm.normal_update()
    base = rgb("#8e8b84")
    for v in verts:
        n = fbm(v.co.x * 2.0 + seed, v.co.y * 2.0, 3, seed + 1.0) * 0.5 + 0.5
        c = scale_col(base, 0.75 + 0.45 * n)
        m = smoothstep(0.55, 0.9, v.normal.z) * smoothstep(0.35, 0.65, fbm(v.co.x * 1.4, v.co.y * 1.4, 2, seed + 7.0) * 0.5 + 0.5)
        c = mix(c, rgb("#5f6534"), m * moss)
        c = mix(c, scale_col(c, 0.7), smoothstep(-0.2, -0.7, v.normal.z))
        v[b.col] = c
    obj = b.build(name, coll, smooth=True, sharp=38.0)
    obj.location = loc
    obj.rotation_euler.z = rot_z
    return obj


ROCKS = [  # name, seed, size, (x, y), sink, rot
    ("RockBig", 1.3, (2.7, 1.9, 1.45), (4.7, 9.6), 0.35, 0.4),
    ("RockRight2", 2.1, (1.1, 0.9, 0.55), (3.3, 7.0), 0.15, 1.2),
    ("RockFeetA", 3.7, (0.45, 0.35, 0.16), (0.55, 4.45), 0.05, 0.3),
    ("RockFeetB", 4.2, (0.35, 0.3, 0.12), (1.75, 3.75), 0.04, 2.0),
    ("RockFrontL", 5.5, (0.95, 0.7, 0.42), (-0.62, 3.9), 0.12, 0.9),
    ("RockFrontL2", 6.1, (0.55, 0.45, 0.24), (-0.2, 3.1), 0.08, 2.4),
    ("RockFrontC", 7.4, (0.6, 0.45, 0.2), (0.6, 3.3), 0.08, 1.7),
    ("RockFrontR", 8.8, (0.7, 0.5, 0.3), (2.45, 4.6), 0.1, 0.2),
    ("RockMidL", 9.3, (1.3, 1.0, 0.6), (-1.6, 6.6), 0.2, 0.8),
    ("RockMidC", 10.2, (0.8, 0.6, 0.35), (0.4, 6.9), 0.15, 2.9),
    ("RockRight3", 11.6, (1.6, 1.2, 0.9), (6.9, 12.5), 0.3, 1.9),
    ("RockRight4", 12.4, (0.9, 0.7, 0.5), (5.6, 7.4), 0.15, 0.5),
    ("RockEdgeL", 13.1, (1.5, 1.1, 0.7), (-2.9, 7.6), 0.25, 2.2),
]
rock_spots = []
for name, seed, size, (x, y), sink, rot in ROCKS:
    make_rock(name, seed, size, C_TERRAIN, (x, y, near_z(x, y) + size[2] * 0.25 - sink), rot)
    rock_spots.append((x, y, max(size[0], size[1]) * 0.85))
for i in range(26):
    th, r = rng.uniform(-0.3, 0.7), rng.uniform(5.0, 13.0)
    x, y = r * math.sin(th), r * math.cos(th)
    if r > edge_r(th) + 1.5:
        continue
    s = rng.uniform(0.15, 0.45)
    make_rock(f"Pebble{i}", 20.0 + i, (s * 1.3, s, s * 0.55), C_TERRAIN, (x, y, near_z(x, y) - s * 0.1), rng.uniform(0, 6.28))
    rock_spots.append((x, y, s))

# ============================================================================ grass
GRASS_BASE = rgb("#2f321d")
GRASS_TIP = rgb("#b3a66a")
GRASS_GREEN = rgb("#7f8a46")


def build_grass():
    bm = bmesh.new()
    col = tz.color_layer(bm)
    uv = bm.loops.layers.uv.new("UVMap")
    blades = 0
    tufts = 0
    while tufts < 2600:
        th = rng.uniform(-0.42, 0.68)
        r = 1.2 + (edge_r(th) + 2.2 - 1.2) * rng.random() ** 0.85
        x, y = r * math.sin(th), r * math.cos(th)
        if any(math.hypot(x - rx, y - ry) < rr for rx, ry, rr in rock_spots):
            continue
        dens = (0.55 + 0.45 * smoothstep(-0.2, 0.4, fbm(x * 0.5, y * 0.5, 2, 9.9))) * lerp(0.45, 1.0, smoothstep(2.0, 3.5, r))
        if rng.random() > dens:
            continue
        tufts += 1
        tall = 0.55 + 0.45 * (fbm(x * 0.3, y * 0.3, 2, 3.3) * 0.5 + 0.5)
        green = smoothstep(0.1, 0.6, fbm(x * 0.25, y * 0.25, 2, 6.6)) * 0.6
        for _ in range(rng.randint(7, 15)):
            bx, by = x + rng.gauss(0, 0.09), y + rng.gauss(0, 0.09)
            bz = near_z(bx, by) - 0.03
            h = rng.uniform(0.12, 0.46) * tall
            h *= lerp(0.55, 1.0, smoothstep(2.0, 4.0, r)) * lerp(1.0, 0.6, smoothstep(edge_r(th) - 2.0, edge_r(th), r))
            w = rng.uniform(0.011, 0.02)
            a = rng.uniform(0, math.tau)
            lean = rng.uniform(0.05, 0.35) * h
            la = a + rng.uniform(-0.6, 0.6)
            side = V((math.cos(a), math.sin(a), 0.0)) * w
            bend = V((math.cos(la), math.sin(la), 0.0)) * lean
            base = V((bx, by, bz))
            mid = base + bend * 0.35 + V((0, 0, h * 0.55))
            tip = base + bend + V((0, 0, h))
            vs = [bm.verts.new(p) for p in (base - side, base + side, mid + side * 0.6, mid - side * 0.6, tip)]
            tint = mix(GRASS_TIP, GRASS_GREEN, green + rng.uniform(-0.1, 0.2))
            k = rng.uniform(0.75, 1.15)
            cols = [GRASS_BASE, GRASS_BASE, scale_col(mix(GRASS_BASE, tint, 0.6), k), scale_col(mix(GRASS_BASE, tint, 0.6), k), scale_col(tint, k)]
            hts = [0.0, 0.0, 0.55, 0.55, 1.0]
            for v, c in zip(vs, cols):
                v[col] = c
            f1 = bm.faces.new((vs[0], vs[1], vs[2], vs[3]))
            f2 = bm.faces.new((vs[3], vs[2], vs[4]))
            for f in (f1, f2):
                for loop in f.loops:
                    i = vs.index(loop.vert)
                    loop[uv].uv = (1.0 if i in (1, 2) else 0.5 if i == 4 else 0.0, 1.0 - hts[i])
            blades += 1
    obj = tz.mesh_object("Grass", bm, [MAT["Grass"]], collection=C_VEG, smooth=True, sharp_angle=None)
    print(f"GRASS blades={blades}")
    return obj


build_grass()


# ============================================================================ pines
def make_pine_mesh(name, height, tiers, tips, seed, slim=1.0):
    r = random.Random(seed)
    b = Builder(["PineNeedles", "Bark"])
    b.cyl((0, 0, -0.6), 0.03 * height * slim, 0.006 * height, height * 0.95, "Bark", rgb("#3a2b21"), segs=7, caps=False)
    dark, mid, tip = rgb("#1c2b20"), rgb("#2b3c2d"), rgb("#4a5a3d")
    for i in range(tiers):
        t = i / (tiers - 1)
        z_top = height * (0.22 + 0.78 * t)
        radius = 0.29 * height * slim * (1.0 - t) ** 0.92 + 0.3
        hs = height * (0.17 - 0.07 * t)
        k = r.uniform(0.85, 1.15)
        apex = b.bm.verts.new((r.uniform(-0.04, 0.04) * height * 0.05, 0.0, z_top))
        under = b.bm.verts.new((0.0, 0.0, z_top - hs * 0.5))
        apex[b.col] = scale_col(dark, k * 0.8)
        under[b.col] = scale_col(dark, 0.6)
        n = tips * 2
        phase = r.uniform(0.0, math.tau)
        rim = []
        for j in range(n):
            a = phase + math.tau * j / n
            if j % 2 == 0:
                rr, zz, c = radius * r.uniform(0.85, 1.12), z_top - hs * r.uniform(0.95, 1.2), tip
            else:
                rr, zz, c = radius * r.uniform(0.5, 0.68), z_top - hs * r.uniform(0.5, 0.72), mid
            v = b.bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz))
            v[b.col] = scale_col(c, k * r.uniform(0.9, 1.1))
            rim.append(v)
        mi = 0
        for j in range(n):
            a_, b_ = rim[j], rim[(j + 1) % n]
            b.bm.faces.new((apex, a_, b_)).material_index = mi
            b.bm.faces.new((under, b_, a_)).material_index = mi
    mesh_obj = b.build(name, C_VEG, smooth=True, sharp=None)
    me = mesh_obj.data
    bpy.data.objects.remove(mesh_obj)
    return me


PINES = [make_pine_mesh("PineA", 18.0, 10, 6, 1), make_pine_mesh("PineB", 21.0, 12, 5, 2, slim=0.8),
         make_pine_mesh("PineC", 12.0, 8, 6, 3, slim=1.15)]
tree_count = 0


def place_tree(x, y, scale, z=None):
    global tree_count
    me = PINES[rng.randrange(len(PINES))]
    obj = bpy.data.objects.new(f"Pine{tree_count:04d}", me)
    C_VEG.objects.link(obj)
    obj.location = (x, y, (ground_z(x, y) if z is None else z) - 0.3)
    obj.rotation_euler = (rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), rng.uniform(0, math.tau))
    obj.scale = (scale * rng.uniform(0.9, 1.1), scale * rng.uniform(0.9, 1.1), scale)
    tree_count += 1


def scatter(n, th_range, d_range, s_range, density=None, min_spacing=0.0):
    placed = []
    tries = 0
    while len(placed) < n and tries < n * 40:
        tries += 1
        th = rng.uniform(*th_range)
        d = math.sqrt(rng.uniform(d_range[0] ** 2, d_range[1] ** 2))
        x, y = d * math.sin(th), d * math.cos(th)
        z = ground_z(x, y)
        if z < SEA_LEVEL + 1.5 or factory_mask(x, y) > 0.05:
            continue
        if density and rng.random() > density(x, y):
            continue
        if min_spacing and any((x - px) ** 2 + (y - py) ** 2 < min_spacing ** 2 for px, py in placed):
            continue
        placed.append((x, y))
        place_tree(x, y, rng.uniform(*s_range), z)
    return placed


def forest_density(x, y):
    return smoothstep(-0.35, 0.25, fbm(x * 0.012, y * 0.012, 3, 2.7))


scatter(200, (-0.8, -0.22), (45.0, 430.0), (0.75, 1.3), forest_density, 5.0)       # mid-ground left (behind the panel)
scatter(70, (-0.22, 0.14), (250.0, 420.0), (0.7, 1.15), forest_density, 7.0)       # pines below the factory view
scatter(150, (0.2, 0.62), (19.0, 260.0), (0.7, 1.25), forest_density, 4.5)          # right slope
scatter(170, (-0.2, 0.62), (430.0, 1500.0), (0.9, 1.3), forest_density, 12.0)      # far hills
scatter(40, (-0.75, -0.25), (380.0, 520.0), (0.8, 1.2), None, 9.0)                   # valley edge
print(f"TREES {tree_count}")

# ============================================================================ factory & port
BRICK = rgb("#7b3d2b")
BRICK2 = rgb("#6a3324")
CONCRETE = rgb("#8f8b82")
ROOF = rgb("#3d3f41")
STEEL = rgb("#5d6266")
G = GROUND
ind = Builder(["Brick", "Concrete", "Roof", "SteelPaint", "Glass", "WindowLit"])


def windows(x0, x1, y_face, z0, z1, rows, spacing, normal_sign=-1, lit=0.07, w=2.4, h=3.2, along="x"):
    n = max(1, int((x1 - x0) / spacing))
    for row in range(rows):
        z = z0 + (row + 0.5) * (z1 - z0) / rows
        for i in range(n):
            c = x0 + (i + 0.5) * (x1 - x0) / n
            lit_now = rng.random() < lit
            mat = "WindowLit" if lit_now else "Glass"
            col = (1, 1, 1, 1) if lit_now else scale_col((1, 1, 1, 1), rng.uniform(0.7, 1.1))
            off = 0.12 * normal_sign
            if along == "x":
                pts = [(c - w / 2, y_face + off, z - h / 2), (c + w / 2, y_face + off, z - h / 2),
                       (c + w / 2, y_face + off, z + h / 2), (c - w / 2, y_face + off, z + h / 2)]
                if normal_sign > 0:
                    pts.reverse()
            else:
                pts = [(y_face + off, c + w / 2, z - h / 2), (y_face + off, c - w / 2, z - h / 2),
                       (y_face + off, c - w / 2, z + h / 2), (y_face + off, c + w / 2, z + h / 2)]
                if normal_sign > 0:
                    pts.reverse()
            ind.poly(pts, mat, col)


def hall(cx, cy, w, d, h, roof="flat", brick=True, lit=0.07):
    wall = "Brick" if brick else "Concrete"
    tint = scale_col(mix(BRICK, BRICK2, rng.random()) if brick else CONCRETE, rng.uniform(0.85, 1.1))
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    ind.box((cx, cy, G + h / 2), (w, d, h), wall, tint)
    ind.box((cx, cy, G + 0.6), (w + 0.8, d + 0.8, 1.2), "Concrete", scale_col(CONCRETE, 0.7))
    if roof == "flat":
        ind.box((cx, cy, G + h + 0.5), (w + 0.6, d + 0.6, 1.0), "Roof", ROOF)
    elif roof == "gable":
        ind.prism(x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, G + h, G + h + d * 0.28, "Roof", scale_col(ROOF, 1.1), along="x")
    elif roof == "saw":
        teeth = max(2, int(d / 9.0))
        step = d / teeth
        for i in range(teeth):
            ya, yb = y0 + i * step, y0 + (i + 1) * step
            pts = [(x0, ya, G + h), (x1, ya, G + h), (x1, ya, G + h + 5.0), (x0, ya, G + h + 5.0)]
            ind.poly(pts, "Glass", (0.8, 0.85, 0.9, 1))
            vs = [ind.bm.verts.new(p) for p in ((x0, ya, G + h + 5.0), (x1, ya, G + h + 5.0), (x1, yb, G + h), (x0, yb, G + h))]
            ind.bm.faces.new(vs)
            ind._finish(vs, "Roof", ROOF)
    rows = max(1, int((h - 4.0) / 5.5))
    windows(x0 + 2.0, x1 - 2.0, y0, G + 3.0, G + h - 2.0, rows, 6.5, -1, lit)
    windows(y0 + 2.0, y1 - 2.0, x0, G + 3.0, G + h - 2.0, rows, 7.0, -1, lit, along="y")
    windows(y0 + 2.0, y1 - 2.0, x1, G + 3.0, G + h - 2.0, rows, 7.0, 1, lit, along="y")


HALLS = [
    (-175, 490, 110, 42, 18, "saw", True), (-62, 505, 70, 36, 14, "gable", True),
    (-262, 590, 92, 46, 22, "flat", True), (-125, 425, 52, 18, 21, "flat", True),
    (-345, 485, 60, 40, 12, "gable", True), (-30, 650, 54, 34, 16, "saw", True),
    (-190, 710, 120, 32, 11, "gable", False), (-370, 800, 110, 30, 10, "flat", False),
    (-150, 840, 90, 28, 9, "gable", False), (60, 490, 44, 30, 12, "flat", True),
    (-98, 580, 34, 34, 26, "flat", True), (40, 760, 60, 26, 10, "gable", False),
    (-420, 650, 50, 40, 15, "saw", True), (85, 590, 30, 46, 13, "flat", True),
]
for cx, cy, w, d, h, roof, brick in HALLS:
    hall(cx, cy, w, d, h, roof, brick)

CHIMNEYS = [(-108.0, 594.0, 92.0, 4.6), (-79.0, 578.0, 80.0, 4.0), (118.0, 650.0, 44.0, 2.3)]
for i, (x, y, h, r) in enumerate(CHIMNEYS):
    ind.cyl((x, y, G), r, r * 0.62, h, "Brick", scale_col(BRICK, 0.95), segs=20)
    ind.cyl((x, y, G + h - 3.0), r * 0.68, r * 0.68, 3.0, "Concrete", scale_col(CONCRETE, 0.45), segs=20)
    for k in range(2):
        z = G + h * (0.55 + 0.2 * k)
        rr = lerp(r, r * 0.62, (z - G) / h) + 0.25
        ind.cyl((x, y, z), rr, rr, 1.2, "Concrete", scale_col(CONCRETE, 0.6), segs=20, caps=False)

for x, y, r, h in ((-14, 590, 6.5, 22), (2, 597, 6.5, 22), (16, 583, 5.0, 17), (-28, 545, 4.0, 14)):
    ind.cyl((x, y, G), r, r, h, "SteelPaint", scale_col(rgb("#a6a59d"), rng.uniform(0.85, 1.0)), segs=24)
    ind.dome((x, y, G + h), r, r * 0.35, "SteelPaint", rgb("#9a9991"), segs=24)
    for k in range(3):
        ind.cyl((x, y, G + 4 + k * 6), r + 0.15, r + 0.15, 0.5, "SteelPaint", scale_col(STEEL, 0.8), segs=24, caps=False)

pipe_y = (450, 540, 625)
for py in pipe_y:
    ind.beam((-300, py, G + 12), (70, py, G + 12), 1.2, "SteelPaint", scale_col(STEEL, 0.9))
    for x in range(-290, 70, 30):
        ind.beam((x, py, G), (x, py, G + 12), 0.8, "SteelPaint", scale_col(STEEL, 0.7))
ind.beam((-60, 580, G + 20), (-14, 590, G + 22), 2.5, "SteelPaint", scale_col(STEEL, 0.9))
ind.beam((-230, 540, G + 16), (-108, 590, G + 24), 3.0, "Concrete", scale_col(CONCRETE, 0.8))

# port: quay, piers, cranes, ships
QY = 1000.0
ind.box((-290, QY - 8, G - 0.5), (520, 30, 4.0), "Concrete", scale_col(CONCRETE, 0.85))
for px in (-430, -280, -130):
    ind.box((px, QY + 45, G - 0.8), (14, 90, 3.2), "Concrete", scale_col(CONCRETE, 0.8))


def crane(x, y, h, boom, rot=0.0):
    col = scale_col(rgb("#b9822f"), rng.uniform(0.85, 1.05))
    for dx in (-5, 5):
        for dy in (-4, 4):
            ind.beam((x + dx, y + dy, G), (x + dx * 0.6, y + dy * 0.6, G + h), 1.0, "SteelPaint", col)
    ind.box((x, y, G + h + 1.5), (12, 10, 4), "SteelPaint", col)
    ind.beam((x, y - 18, G + h + 3.5), (x, y + boom, G + h + 3.5), 2.0, "SteelPaint", col)
    ind.beam((x, y, G + h + 10), (x, y + boom * 0.8, G + h + 3.5), 0.5, "SteelPaint", col)
    ind.beam((x, y, G + h + 10), (x, y - 16, G + h + 3.5), 0.5, "SteelPaint", col)
    ind.beam((x, y, G + h + 3.5), (x, y, G + h + 11), 1.2, "SteelPaint", col)


for cx in (-470, -380, -300, -205, -110):
    crane(cx, QY + 2, 26 + rng.uniform(-3, 4), 42)


def ship(x, y, length, beam_w, rot, hull_col, deck_col, containers=False):
    m = Matrix.Translation((x, y, SEA_LEVEL)) @ Matrix.Rotation(rot, 4, "Z")
    hb = bmesh.new()
    pts = [(-length / 2, -beam_w / 2), (length * 0.35, -beam_w / 2), (length / 2, 0.0), (length * 0.35, beam_w / 2), (-length / 2, beam_w / 2)]
    bot = [hb.verts.new((px * 0.97, py * 0.85, -3.0)) for px, py in pts]
    top = [hb.verts.new((px, py, 6.0)) for px, py in pts]
    hb.faces.new(bot[::-1])
    hb.faces.new(top)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        hb.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.transform(hb, matrix=m, verts=hb.verts[:])
    tmp = bpy.data.meshes.new("ship_tmp")
    hb.to_mesh(tmp)
    hb.free()
    start = len(ind.bm.verts)
    ind.bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)
    ind.bm.verts.ensure_lookup_table()
    ind._finish(list(ind.bm.verts[start:]), "SteelPaint", hull_col)
    sup = Matrix.Translation((x, y, SEA_LEVEL)) @ Matrix.Rotation(rot, 4, "Z")
    ind.box(sup @ V((-length * 0.38, 0, 11.0)), (length * 0.12, beam_w * 0.8, 10.0), "SteelPaint", deck_col, rot)
    ind.box(sup @ V((-length * 0.38, 0, 17.5)), (length * 0.06, beam_w * 0.5, 3.0), "SteelPaint", deck_col, rot)
    if containers:
        palette = [rgb("#8c2f22"), rgb("#2c4f6b"), rgb("#9a7b2d"), rgb("#3f5f3a"), rgb("#6b6b6b")]
        for i in range(8):
            for j in range(3):
                for k in range(rng.randint(1, 3)):
                    ind.box(sup @ V((-length * 0.25 + i * length * 0.075, (j - 1) * beam_w * 0.28, 7.3 + k * 2.6)),
                            (length * 0.07, beam_w * 0.26, 2.5), "SteelPaint", scale_col(rng.choice(palette), rng.uniform(0.8, 1.1)), rot)


ship(-360, QY + 70, 120, 20, math.radians(90), rgb("#2c3036"), rgb("#c2c1bb"), containers=True)
ship(-205, QY + 80, 95, 16, math.radians(88), rgb("#3a2724"), rgb("#bdbcb6"))
ship(-760, 2300, 150, 24, math.radians(12), rgb("#2b2f36"), rgb("#c8c7c0"), containers=True)
ship(380, 2650, 80, 14, math.radians(-25), rgb("#3c3a34"), rgb("#b8b7b1"))
industry = ind.build("Factory", C_INDUSTRY, smooth=False, recalc=False)

# radio tower on the coastal hill
best = max(((x, y) for x in range(40, 200, 8) for y in range(1110, 1280, 8)), key=lambda p: far_z(*p))
tx, ty = best
tz0 = far_z(tx, ty) - 1.0
tw = Builder(["SteelPaint", "Beacon"])
H_T, B0, B1 = 64.0, 6.0, 0.9
TOWER = rgb("#4a3c38")
corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]


def tower_pt(cx, cy, z):
    s = lerp(B0, B1, (z - tz0) / H_T)
    return V((tx + cx * s, ty + cy * s, z))


for cx, cy in corners:
    tw.beam(tower_pt(cx, cy, tz0), tower_pt(cx, cy, tz0 + H_T), 0.55, "SteelPaint", TOWER)
levels = 11
for i in range(levels):
    za, zb = tz0 + H_T * i / levels, tz0 + H_T * (i + 1) / levels
    for k in range(4):
        (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
        tw.beam(tower_pt(ax, ay, za), tower_pt(bx, by, zb), 0.25, "SteelPaint", TOWER)
        tw.beam(tower_pt(bx, by, za), tower_pt(ax, ay, zb), 0.25, "SteelPaint", TOWER)
        tw.beam(tower_pt(ax, ay, zb), tower_pt(bx, by, zb), 0.3, "SteelPaint", TOWER)
tw.beam((tx, ty, tz0 + H_T), (tx, ty, tz0 + H_T + 10.0), 0.4, "SteelPaint", TOWER)
for z in (tz0 + H_T + 10.3, tz0 + H_T * 0.62):
    v = bmesh.ops.create_uvsphere(tw.bm, u_segments=10, v_segments=6, radius=0.9, matrix=Matrix.Translation((tx, ty, z)))["verts"]
    tw._finish(v, "Beacon", (1, 1, 1, 1))
tw.build("RadioTower", C_INDUSTRY, smooth=False, recalc=False)


# ============================================================================ markers for Godot
def marker(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 2.0
    e.location = loc
    C_MARKERS.objects.link(e)
    return e


for i, (x, y, h, r) in enumerate(CHIMNEYS):
    marker(f"Smoke{i + 1}", (x, y, G + h + 0.5))
marker("BeaconTop", (tx, ty, tz0 + H_T + 10.3))
marker("BeaconMid", (tx, ty, tz0 + H_T * 0.62))
marker("PlayerSpot", (1.0, 4.0, near_z(1.0, 4.0)))
marker("CameraSpot", (0.0, 0.0, 1.0))

env_objects = [o for c in (C_TERRAIN, C_VEG, C_INDUSTRY, C_MARKERS) for o in c.objects]
tz.export_glb(os.path.join(tz.MODELS_DIR, "environment.glb"), env_objects)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in env_objects if o.type == "MESH")
print(f"ENV objects={len(env_objects)} mesh_tris(instanced counted per object)={tris} tower=({tx},{ty},{tz0:.1f})")

# ============================================================================ bird
bb = Builder(["Bird"])
body = bmesh.ops.create_uvsphere(bb.bm, u_segments=8, v_segments=6, radius=1.0,
                                 matrix=Matrix.Diagonal((0.07, 0.22, 0.06, 1.0)))["verts"]
bb._finish(body, "Bird", (1, 1, 1, 1))
for s in (1.0, -1.0):
    bb.poly([(0.04 * s, 0.08, 0.0), (0.5 * s, -0.02, 0.03), (0.42 * s, -0.12, 0.02), (0.04 * s, -0.06, 0.0)][:: int(s)],
            "Bird", (1, 1, 1, 1))
bird = bb.build("Bird", scene.collection, smooth=False, recalc=False)
tz.export_glb(os.path.join(tz.MODELS_DIR, "bird.glb"), [bird])

# ============================================================================ smoke puff texture
os.makedirs(tz.TEXTURES_DIR, exist_ok=True)
SIZE = 256
img = bpy.data.images.new("smoke_puff", SIZE, SIZE, alpha=True)
px = [0.0] * (SIZE * SIZE * 4)
for j in range(SIZE):
    for i in range(SIZE):
        u, v = (i + 0.5) / SIZE * 2 - 1, (j + 0.5) / SIZE * 2 - 1
        r = math.sqrt(u * u + v * v)
        n = fbm(u * 2.3 + 4.0, v * 2.3 - 1.0, 5, 3.7) * 0.5 + 0.5
        a = max(0.0, 1.0 - r) ** 1.4 * smoothstep(0.22, 0.7, n + 0.3 * (1.0 - r))
        shade = 0.72 + 0.28 * n
        k = (j * SIZE + i) * 4
        px[k:k + 4] = (shade, shade, shade, min(1.0, a * 1.3))
img.pixels.foreach_set(px)
img.filepath_raw = os.path.join(tz.TEXTURES_DIR, "smoke_puff.png")
img.file_format = "PNG"
img.save()

# reference camera matching the Godot menu camera
cam = bpy.data.objects.new("MenuCamera", bpy.data.cameras.new("MenuCamera"))
cam.data.sensor_fit = "VERTICAL"
cam.data.angle_y = math.radians(32.0)
cam.data.clip_end = 15000.0
cam.location = (0.0, 0.0, 1.0)
cam.rotation_euler = (math.radians(88.7), 0.0, 0.0)
scene.collection.objects.link(cam)
scene.camera = cam
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tz.BLEND_DIR, "environment.blend"), compress=True)
