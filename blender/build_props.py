"""TEZEROK — small props for the menu: a flapping bird mesh and the soft smoke-puff texture.

Run:    blender -b --factory-startup --python blender/build_props.py
Writes: assets/models/bird.glb, assets/textures/smoke_puff.png
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402
from tz_common import smoothstep  # noqa: E402

scene = tz.reset_scene()
V = Vector
MAT = {"Bird": tz.material("Bird", "#15161a", 0.8)}


def fbm(x, y, octaves=4, seed=0.0):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * noise.noise(V((x * freq + seed, y * freq - seed * 0.7, seed * 0.31)), noise_basis="PERLIN_ORIGINAL")
        norm += amp
        amp *= 0.5
        freq *= 2.03
    return total / norm



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

