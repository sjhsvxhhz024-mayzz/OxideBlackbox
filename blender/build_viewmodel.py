"""TEZEROK — first-person viewmodel: bare right hand (from below, palm up) holding the AI rock.

Built in camera space (camera at the origin looking along +Y, up +Z), rigged with 18 bones
(arm, hand, 3-bone thumb and fingers) and three actions: Idle, Draw, Swing.

Run:    blender -b --factory-startup --python blender/build_viewmodel.py
Writes: assets/models/game/viewmodel_rock.glb
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

V = Vector
scene = tz.reset_scene()
FPS = 30

# ----------------------------------------------------------------------------- hand skeleton (local frame)
# local: wrist at origin, fingers +Y, palm normal +Z (palm up), thumb on +X
ROCK_C = V((-0.002, 0.07, 0.06))
ROCK_D = 0.15
chains = {}  # name -> list of joint points
radii = {}
chains["arm"] = [V((0.0, -0.30, -0.07)), V((0.0, -0.14, -0.03)), V((0.0, 0.018, 0.0))]
radii["arm"] = [(0.042, 0.038), (0.036, 0.032), (0.03, 0.022)]
chains["palm"] = [V((0.0, 0.0, 0.0)), V((0.0, 0.045, 0.002)), V((0.0, 0.082, 0.004))]
radii["palm"] = [(0.03, 0.02), (0.042, 0.018), (0.043, 0.015)]
FINGERS = [("index", 0.027, 1.1, (28, 42, 30)), ("middle", 0.009, 1.18, (30, 44, 30)),
           ("ring", -0.009, 1.1, (32, 44, 30)), ("pinky", -0.026, 0.9, (36, 44, 30))]
for name, x, k, curls in FINGERS:
    p = V((x, 0.078, 0.004))
    d = V((0.0, 1.0, 0.0))
    pts = [p.copy()]
    for seg, ang in zip((0.043 * k, 0.027 * k, 0.022 * k), curls):
        d = Matrix.Rotation(math.radians(ang), 3, "X") @ d
        p = p + d * seg
        pts.append(p.copy())
    chains[name] = pts
    r = 0.0098 * (0.9 if name == "pinky" else 1.0)
    radii[name] = [(r, r * 0.9), (r * 0.92, r * 0.85), (r * 0.85, r * 0.78), (r * 0.75, r * 0.7)]
tp = [V((0.026, 0.012, -0.004))]
for d, seg in ((V((0.65, 0.55, 0.45)), 0.042), (V((0.25, 0.55, 0.8)), 0.032), (V((-0.15, 0.45, 0.88)), 0.026)):
    tp.append(tp[-1] + d.normalized() * seg)
chains["thumb"] = tp
radii["thumb"] = [(0.017, 0.014), (0.0125, 0.0115), (0.011, 0.0105), (0.0095, 0.009)]

# local -> camera space: rock centre in the lower middle of the screen, fingers to the left
fy = V((-0.55, 0.3, 0.78)).normalized()
fz = V((0.15, -0.9, 0.4))
fz = (fz - fy * fz.dot(fy)).normalized()
fx = fy.cross(fz)
basis = Matrix((fx, fy, fz)).transposed()
ROCK_WORLD = V((0.015, 0.235, -0.088))
origin = ROCK_WORLD - basis @ ROCK_C
HAND_SCALE = 1.4
basis = basis * HAND_SCALE
origin = ROCK_WORLD - basis @ ROCK_C
LOCAL_TO_CAM = Matrix.Translation(origin) @ basis.to_4x4()


def cam(p):
    return LOCAL_TO_CAM @ V(p)


# ----------------------------------------------------------------------------- mesh
SKIN = tz.rgb("#c58c6a")
SLEEVE = tz.rgb("#2f3236")
parts = []
for name, pts in chains.items():
    nodes = [(p, r) for p, r in zip(pts, radii[name])]
    me = tz.skin_mesh("hand_" + name, nodes, [(i, i + 1) for i in range(len(pts) - 1)], root=0, subsurf=2)
    bm = tz.bm_from_mesh(me)
    col = tz.color_layer(bm)
    for v in bm.verts:
        c = SKIN
        if name == "arm" and v.co.y < -0.075:
            c = SLEEVE
        elif name not in ("arm", "palm"):
            tip = (v.co - pts[-1]).length < 0.012
            c = tz.rgb("#d29a7c") if tip else SKIN
        if name in ("palm",) and v.co.z < -0.005:
            c = tz.rgb("#d6a184")  # palm side is lighter
        v[col] = c
    bmesh.ops.transform(bm, matrix=LOCAL_TO_CAM, verts=bm.verts[:])
    obj = tz.mesh_object("part_" + name, bm, [tz.material("ViewSkin", "#ffffff", 0.6)], smooth=True, sharp_angle=None)
    parts.append(obj)
hand = tz.join_objects(parts, "ViewHand")

# ----------------------------------------------------------------------------- armature
BONES = [("arm", chains["arm"][0], chains["arm"][-1], None), ("hand", chains["palm"][0], chains["palm"][-1], "arm")]
for name in ("thumb", "index", "middle", "ring", "pinky"):
    pts = chains[name]
    for j in range(3):
        BONES.append((f"{name}{j + 1}", pts[j], pts[j + 1], "hand" if j == 0 else f"{name}{j}"))
arm_data = bpy.data.armatures.new("ViewRig")
rig = bpy.data.objects.new("ViewRig", arm_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, h, t, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = cam(h), cam(t)
    if parent:
        eb.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


segs = [(n, cam(h), cam(t)) for n, h, t, _ in BONES]
groups = {n: hand.vertex_groups.new(name=n) for n, _, _, _ in BONES}
for v in hand.data.vertices:
    ds = sorted((seg_dist(v.co, a, b), n) for n, a, b in segs)[:2]
    w = [(n, 1.0 / max(d, 1e-4) ** 6) for d, n in ds]
    tot = sum(x for _, x in w)
    for n, x in w:
        groups[n].add([v.index], x / tot, "REPLACE")
hand.parent = rig
hand.modifiers.new("Armature", "ARMATURE").object = rig

# rock from the AI model, parented to the hand bone
bpy.ops.import_scene.gltf(filepath=os.path.join(tz.MODELS_DIR, "game", "rock_ai.glb"))
rock = next(o for o in bpy.context.selected_objects if o.type == "MESH")
rock.name = "ViewRock"
dims = max(rock.dimensions)
rock.scale = rock.scale * (ROCK_D / dims)
rock.location = cam(ROCK_C)
rock.rotation_euler = (0.4, 0.2, 1.1)
bpy.context.view_layer.update()
mw = rock.matrix_world.copy()
rock.parent = rig
rock.parent_type = "BONE"
rock.parent_bone = "hand"
bpy.context.view_layer.update()
rock.matrix_world = mw

# ----------------------------------------------------------------------------- actions
rig.animation_data_create()
X3, Y3, Z3 = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def qworld(bone, axis, deg):
    m = arm_data.bones[bone].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))


def lworld(bone, vec):
    return arm_data.bones[bone].matrix_local.to_3x3().inverted() @ V(vec)


def key(frame, bone, rot=(), loc=None):
    pb = rig.pose.bones[bone]
    q = Quaternion()
    for axis, deg in rot:
        q = qworld(bone, axis, deg) @ q
    pb.rotation_quaternion = q
    pb.keyframe_insert("rotation_quaternion", frame=frame, group=bone)
    pb.location = lworld(bone, loc) if loc is not None else V()
    pb.keyframe_insert("location", frame=frame, group=bone)


def new_action(name):
    for pb in rig.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = V()
    action = bpy.data.actions.new(name)
    rig.animation_data.action = action
    return action


actions = []
# Idle: 2 s breathing bob, fingers re-grip slightly
actions.append(new_action("Idle"))
for f in range(0, 61, 5):
    a = 2 * math.pi * f / 60
    key(f, "arm", [(X3, 1.2 * math.sin(a)), (Y3, 0.8 * math.sin(a + 1.0))], (0.0, 0.0, 0.004 * math.sin(a)))
    for name in ("index", "middle", "ring", "pinky"):
        key(f, f"{name}1", [(fx, 2.5 * math.sin(a + 0.5))])
# Draw: rises from below the screen
actions.append(new_action("Draw"))
for f, rx, loc in ((0, -35, (0.04, -0.06, -0.24)), (6, -12, (0.01, -0.02, -0.07)), (11, 2, (0, 0, 0.006)), (15, 0, (0, 0, 0))):
    key(f, "arm", [(X3, rx)], loc)
# Swing: wind up over the right shoulder, smash forward-down-left, recover (hit at frame 9)
actions.append(new_action("Swing"))
SWING = ((0, 0, 0, 0, (0, 0, 0)), (5, 38, -14, -10, (0.05, -0.05, 0.07)), (9, -40, 12, 8, (-0.03, 0.12, -0.03)),
         (11, -44, 14, 9, (-0.035, 0.13, -0.045)), (16, -20, 6, 4, (-0.01, 0.06, -0.02)), (22, 0, 0, 0, (0, 0, 0)))
for f, rx, rz, ry, loc in SWING:
    key(f, "arm", [(X3, rx), (Z3, rz), (Y3, ry)], loc)
    key(f, "hand", [(fx, rx * 0.25)])
for act in actions:
    track = rig.animation_data.nla_tracks.new()
    track.name = act.name
    track.strips.new(act.name, int(act.frame_range[0]), act)
    act.use_fake_user = True
rig.animation_data.action = None

tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "viewmodel_rock.glb"), [rig, hand, rock], animations=True,
              export_animation_mode="NLA_TRACKS")
print(f"VIEWMODEL verts={len(hand.data.vertices)} bones={len(BONES)} actions={[a.name for a in actions]}")

# preview from the game camera (80 deg vertical FOV)
c = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
c.data.sensor_fit = "VERTICAL"
c.data.angle_y = math.radians(80)
c.data.clip_start = 0.01
c.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(c)
scene.camera = c
for o in (hand,):
    for m in o.data.materials:
        nt = m.node_tree
        b = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
tz.setup_cycles(scene, samples=8, res=(960, 540))
tz.world_color(scene, (0.55, 0.62, 0.72, 1), 1.0)
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (0.6, 0.3, 0.5)
scene.collection.objects.link(sun)
rig.animation_data.action = actions[0]
scene.frame_set(0)
scene.render.filepath = "/tmp/verify/viewmodel.png"
bpy.ops.render.render(write_still=True)

if os.environ.get("VM_DEBUG"):
    rock.hide_render = True
    c.data.angle_y = math.radians(30)
    for i, d in enumerate((V((0, -1, 0.4)), V((1, 0, 0.3)), V((0, 0, 1)), V((-1, 0.2, 0.2)))):
        tgt = cam(ROCK_C)
        c.location = tgt + d.normalized() * 0.7
        tz.look_at(c, tgt)
        scene.render.filepath = f"/tmp/verify/vmdbg{i}.png"
        bpy.ops.render.render(write_still=True)
