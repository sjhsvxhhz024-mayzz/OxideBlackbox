"""TEZEROK — full humanoid skeleton and animations for the AI-generated player.

Fits a 22-bone humanoid armature to assets/models/game/player_ai.glb (Hunyuan3D-2 mesh, 1.8 m, faces -Y),
skins it with smooth distance weights and bakes the actions Idle, Walk, Run, Swing.

Run:    blender -b --factory-startup --python blender/build_player_rig.py
Writes: assets/models/game/player_rigged.glb
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

V = Vector
scene = tz.reset_scene()
bpy.ops.import_scene.gltf(filepath=os.path.join(tz.MODELS_DIR, "game", "player_ai.glb"))
body = next(o for o in bpy.context.scene.objects if o.type == "MESH")
body.name = "PlayerBody"

# x > 0 is the character's left. Positions measured from the mesh cross-sections.
BONES = [
    ("hips", (0, 0, 0.94), (0, 0, 1.06), None),
    ("spine", (0, 0, 1.06), (0, 0, 1.22), "hips"),
    ("chest", (0, 0, 1.22), (0, 0, 1.44), "spine"),
    ("neck", (0, 0, 1.44), (0, -0.01, 1.56), "chest"),
    ("head", (0, -0.01, 1.56), (0, -0.01, 1.8), "neck"),
    ("shoulder.R", (-0.05, 0, 1.42), (-0.19, 0, 1.42), "chest"),
    ("upper_arm.R", (-0.19, 0, 1.42), (-0.3, 0, 1.13), "shoulder.R"),
    ("forearm.R", (-0.3, 0, 1.13), (-0.37, -0.01, 0.86), "upper_arm.R"),
    ("hand.R", (-0.37, -0.01, 0.86), (-0.4, -0.02, 0.7), "forearm.R"),
    ("shoulder.L", (0.05, 0, 1.42), (0.19, 0, 1.42), "chest"),
    ("upper_arm.L", (0.19, 0, 1.42), (0.33, 0.03, 1.15), "shoulder.L"),
    ("forearm.L", (0.33, 0.03, 1.15), (0.38, -0.08, 1.23), "upper_arm.L"),
    ("hand.L", (0.38, -0.08, 1.23), (0.42, -0.11, 1.27), "forearm.L"),
]
for side, x in (("R", -0.11), ("L", 0.11)):
    BONES += [
        (f"thigh.{side}", (x, 0, 0.94), (x * 1.08, 0, 0.5), "hips"),
        (f"shin.{side}", (x * 1.08, 0, 0.5), (x * 1.15, 0.02, 0.1), f"thigh.{side}"),
        (f"foot.{side}", (x * 1.15, 0.02, 0.1), (x * 1.15, -0.12, 0.03), f"shin.{side}"),
    ]

arm_data = bpy.data.armatures.new("PlayerRig")
rig = bpy.data.objects.new("PlayerRig", arm_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, h, t, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = V(h), V(t)
    eb.roll = 0.0
    if parent:
        eb.parent = arm_data.edit_bones[parent]
        eb.use_connect = (V(h) - arm_data.edit_bones[parent].tail).length < 1e-4
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- skin weights (distance to bone segments)
co = np.array([v.co[:] for v in body.data.vertices])
heads = np.array([b[1] for b in BONES], float)
tails = np.array([b[2] for b in BONES], float)
ab = tails - heads
t = np.clip(((co[:, None, :] - heads[None]) * ab[None]).sum(-1) / (ab * ab).sum(-1)[None], 0, 1)
closest = heads[None] + t[..., None] * ab[None]
dist = np.linalg.norm(co[:, None, :] - closest, axis=-1)
# keep legs and arms from grabbing the wrong side / the torso from grabbing limbs
names = [b[0] for b in BONES]
for i, n in enumerate(names):
    if n.endswith(".L"):
        dist[co[:, 0] < -0.02, i] += 1.0
    if n.endswith(".R"):
        dist[co[:, 0] > 0.02, i] += 1.0
    if n.startswith(("thigh", "shin", "foot")):
        dist[co[:, 2] > 1.0, i] += 1.0
# the carried helmets move rigidly with their hands
for hand, mask in (("hand.R", (co[:, 0] < -0.235) & (co[:, 2] < 0.95) & (co[:, 2] > 0.55)),
                   ("hand.L", (co[:, 0] > 0.3) & (co[:, 2] > 1.02) & (co[:, 2] < 1.4) & (co[:, 1] < 0.0))):
    dist[mask] += 1.0
    dist[mask, names.index(hand)] = 0.0
order = np.argsort(dist, axis=1)[:, :3]
groups = [body.vertex_groups.new(name=n) for n in names]
for vi in range(len(co)):
    d = dist[vi, order[vi]]
    w = 1.0 / np.maximum(d, 0.004) ** 8
    w /= w.sum()
    for bi, wi in zip(order[vi], w):
        if wi > 0.01:
            groups[bi].add([vi], float(wi), "REPLACE")
body.parent = rig
body.modifiers.new("Armature", "ARMATURE").object = rig

# ---------------------------------------------------------------- animation helpers (world-axis rotations)
rig.animation_data_create()
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def q(bone, rots):
    m = arm_data.bones[bone].matrix_local.to_3x3().inverted()
    out = Quaternion()
    for axis, deg in rots:
        out = Quaternion((m @ axis).normalized(), math.radians(deg)) @ out
    return out


def pose(frame, spec):
    for pb in rig.pose.bones:
        rots, loc = spec.get(pb.name, ([], None))
        pb.rotation_quaternion = q(pb.name, rots)
        pb.location = arm_data.bones[pb.name].matrix_local.to_3x3().inverted() @ V(loc) if loc else V()
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        pb.keyframe_insert("location", frame=frame, group=pb.name)


def action(name, length, fn, step=2):
    act = bpy.data.actions.new(name)
    rig.animation_data.action = act
    for f in range(0, length + 1, step):
        pose(f, fn(f / length))
    track = rig.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, 0, act)
    act.use_fake_user = True
    return act


TAU = math.tau


def idle(p):
    a = TAU * p
    b = math.sin(a)
    return {
        "spine": ([(X, 1.0 * b)], None), "chest": ([(X, 1.2 * b)], None), "head": ([(Z, 2.0 * math.sin(a * 0.5 * 2))], None),
        "upper_arm.R": ([(Y, -2 * b)], None), "upper_arm.L": ([(Y, 1.5 * b)], None),
        "hips": ([], (0, 0, 0.004 * b)),
    }


def gait(p, stride, bounce, lean, arm):
    a = TAU * p
    s, c = math.sin(a), math.cos(a)
    lift_r = max(0.0, -math.sin(a + 0.6))
    lift_l = max(0.0, math.sin(a + 0.6))
    return {
        "hips": ([(Z, 4 * s)], (0, 0, -bounce + bounce * abs(c))),
        "spine": ([(X, -lean), (Z, -5 * s)], None),
        "chest": ([(Z, -4 * s)], None),
        "head": ([(Z, 5 * s)], None),
        "thigh.R": ([(X, -stride * s)], None), "thigh.L": ([(X, stride * s)], None),
        "shin.R": ([(X, 1.6 * stride * lift_r)], None), "shin.L": ([(X, 1.6 * stride * lift_l)], None),
        "foot.R": ([(X, -0.4 * stride * s)], None), "foot.L": ([(X, 0.4 * stride * s)], None),
        "upper_arm.R": ([(X, arm * s)], None), "upper_arm.L": ([(X, -arm * 0.4 * s)], None),
        "forearm.R": ([(X, -abs(arm) * 0.5 - arm * 0.3 * s)], None),
    }


def swing(p):
    # rest -> wind up over the shoulder -> strike forward-down (contact ~0.5) -> recover
    keys = [(0.0, 0, 0, 0), (0.35, -55, -50, 14), (0.5, -28, -8, -16), (0.62, -25, -10, -18), (1.0, 0, 0, 0)]
    for k0, k1 in zip(keys, keys[1:]):
        if p <= k1[0]:
            u = (p - k0[0]) / (k1[0] - k0[0])
            u = u * u * (3 - 2 * u)
            arm, fore, twist = (a + (b - a) * u for a, b in zip(k0[1:], k1[1:]))
            break
    return {
        "upper_arm.R": ([(X, arm), (Y, -0.15 * arm)], None),
        "forearm.R": ([(X, fore)], None),
        "chest": ([(Z, twist)], None),
        "spine": ([(Z, 0.4 * twist)], None),
    }


acts = [action("Idle", 90, idle, 3), action("Walk", 30, lambda p: gait(p, 28, 0.02, 3, 22)),
        action("Run", 20, lambda p: gait(p, 42, 0.045, 10, 38)), action("Swing", 20, swing, 1)]
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = V()

tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "player_rigged.glb"), [rig, body], animations=True,
              export_animation_mode="NLA_TRACKS")
print(f"PLAYER_RIG bones={len(BONES)} actions={[a.name for a in acts]}")

if os.environ.get("RIG_DEBUG"):
    mat = body.data.materials[0]
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    if not bsdf.inputs["Base Color"].is_linked:
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    tz.setup_cycles(scene, samples=8, res=(360, 480))
    tz.world_color(scene, (0.6, 0.6, 0.65, 1), 1.0)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (2.6, -3.4, 1.3)
    tz.look_at(cam, (0, 0, 0.9))
    for act, frames in ((acts[1], (0, 8, 15, 23)), (acts[3], (0, 7, 10, 16))):
        rig.animation_data.action = act
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = f"/tmp/verify/rig_{act.name}_{f:02d}.png"
            bpy.ops.render.render(write_still=True)
