"""TEZEROK — first-person viewmodel: both hands cupping the starter rock from below.

Camera space: camera at the origin looking along +Y, up +Z, right +X. Each hand is modelled flat
(palm up, fingers along +Y) and then wrapped onto the rock sphere so palm and fingers conform to it,
the way the fingers curl over the front of the rock in the reference screenshot.
Rig: root (rock) -> arm.L/R -> hand -> fingers; actions Idle, Draw, Swing (hit at frame 9 / 30 fps).

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

ROCK_C = V((0.02, 0.29, -0.105))
ROCK_R = 0.12
GAP = 0.004  # skin sits this far above the rock surface
SKIN = tz.rgb("#c9967b")
SKIN_PALM = tz.rgb("#d8aa92")
SLEEVE = tz.rgb("#2f3236")


# ----------------------------------------------------------------------------- flat hand (local frame)
# origin at the wrist, fingers +Y, palm surface z=0 facing the rock (+Z into the rock), thumb on side*X
def hand_chains(side):
    chains, radii = {}, {}
    chains["arm"] = [V((0, -0.34, -0.03)), V((0, -0.18, -0.025)), V((0, -0.0, -0.018))]
    radii["arm"] = [(0.046, 0.04), (0.04, 0.035), (0.034, 0.024)]
    chains["palm"] = [V((0, 0.0, -0.016)), V((0, 0.05, -0.015)), V((0, 0.092, -0.014))]
    radii["palm"] = [(0.032, 0.017), (0.043, 0.017), (0.044, 0.014)]
    for name, x, k in (("index", 0.031, 1.0), ("middle", 0.0105, 1.1), ("ring", -0.0105, 1.02), ("pinky", -0.031, 0.8)):
        p = V((x * side, 0.085, -0.008))
        pts = [p.copy()]
        for seg in (0.042 * k, 0.027 * k, 0.023 * k):
            p = p + V((0, seg, 0))
            pts.append(p.copy())
        chains[name] = pts
        r = 0.0095 * (0.9 if name == "pinky" else 1.0)
        radii[name] = [(r, r), (r * 0.95, r * 0.9), (r * 0.88, r * 0.82), (r * 0.8, r * 0.72)]
    tp = [V((0.03 * side, 0.015, -0.014))]
    for d, seg in ((V((0.75 * side, 0.65, 0.0)), 0.04), (V((0.4 * side, 0.92, 0.0)), 0.032), (V((0.15 * side, 1.0, 0.0)), 0.026)):
        tp.append(tp[-1] + d.normalized() * seg)
    chains["thumb"] = tp
    radii["thumb"] = [(0.016, 0.013), (0.0125, 0.011), (0.011, 0.0105), (0.0095, 0.009)]
    return chains, radii


class Wrap:
    """Maps flat-hand local coordinates onto the rock sphere (exponential map around a contact point)."""

    def __init__(self, contact_dir, finger_dir, side):
        self.o = V(contact_dir).normalized()                   # outward normal at the contact point
        f = V(finger_dir)
        self.f = (f - self.o * f.dot(self.o)).normalized()     # tangent: finger direction
        self.x = self.o.cross(self.f).normalized() * side      # tangent: thumb side (right-hand rule)
        self.wrist_dir = (-self.f * 0.8 + self.o * 0.6).normalized()
        self.R = ROCK_R + GAP

    def __call__(self, p):
        p = V(p)
        y = max(p.y, 0.0)
        theta = V((p.x, y)).length / self.R
        if theta < 1e-6:
            d = self.o
        else:
            t = (self.x * p.x + self.f * y) / (theta * self.R)
            d = self.o * math.cos(theta) + t * math.sin(theta)
        # radius follows the real rock surface so palm and fingers sit on it instead of inside it
        r_surface = rock_radius(d) + GAP
        world = ROCK_C + d * (r_surface - p.z)
        if p.y < 0:
            world += self.wrist_dir * (-p.y)
        return world


def build_hand(side, wrap):
    chains, radii = hand_chains(side)
    parts = []
    for name, pts in chains.items():
        nodes = [(p, r) for p, r in zip(pts, radii[name])]
        me = tz.skin_mesh(f"hand{side}_{name}", nodes, [(i, i + 1) for i in range(len(pts) - 1)], root=0, subsurf=2)
        bm = tz.bm_from_mesh(me)
        col = tz.color_layer(bm)
        for v in bm.verts:
            c = SKIN
            if name == "arm" and v.co.y < -0.1:
                c = SLEEVE
            elif name == "palm" and v.co.z > -0.012:
                c = SKIN_PALM
            elif name not in ("arm", "palm") and (v.co - pts[-1]).length < 0.011:
                c = tz.rgb("#d49a7e")
            v[col] = c
            v.co = wrap(v.co)
        parts.append(tz.mesh_object(f"part{side}_{name}", bm, [tz.material("ViewSkin", "#ffffff", 0.6)],
                                    smooth=True, sharp_angle=None))
    obj = tz.join_objects(parts, "ViewHand" + ("R" if side > 0 else "L"))
    bones = []
    tag = ".R" if side > 0 else ".L"
    bones.append((f"arm{tag}", wrap(chains["arm"][0]), wrap(chains["arm"][2]), "root"))
    bones.append((f"hand{tag}", wrap(chains["palm"][0]), wrap(chains["palm"][2]), f"arm{tag}"))
    for name in ("thumb", "index", "middle", "ring", "pinky"):
        pts = chains[name]
        for j in range(3):
            bones.append((f"{name}{j + 1}{tag}", wrap(pts[j]), wrap(pts[j + 1]), f"hand{tag}" if j == 0 else f"{name}{j}{tag}"))
    return obj, bones


# the actual AI rock surface (not a sphere): hands are pushed outside it after wrapping
bpy.ops.import_scene.gltf(filepath=os.path.join(tz.MODELS_DIR, "game", "rock_ai.glb"))
rock = next(o for o in bpy.context.selected_objects if o.type == "MESH")
rock.name = "ViewRock"
rock.scale = rock.scale * (ROCK_R * 2.05 / max(rock.dimensions))
rock.location = ROCK_C
rock.rotation_euler = (0.5, 0.3, 1.2)
bpy.context.view_layer.update()
from mathutils.bvhtree import BVHTree  # noqa: E402
rock_bvh = BVHTree.FromPolygons([rock.matrix_world @ v.co for v in rock.data.vertices],
                                [tuple(p.vertices) for p in rock.data.polygons])


def rock_radius(direction):
    """Distance from the rock centre to its surface along `direction` (world space)."""
    hit = rock_bvh.ray_cast(ROCK_C + direction * 0.6, -direction, 0.6)
    if hit[0] is None:
        raise RuntimeError("rock raycast missed")
    return (hit[0] - ROCK_C).length


# right hand grips the lower-right-front of the rock, left hand the lower-left-front; fingers curl up the front face
wrap_r = Wrap(V((0.6, -0.3, -0.75)), V((0.0, -1.0, 0.8)), +1)
wrap_l = Wrap(V((-0.6, -0.3, -0.75)), V((0.0, -1.0, 0.8)), -1)
hand_r, bones_r = build_hand(+1, wrap_r)
hand_l, bones_l = build_hand(-1, wrap_l)
hands = tz.join_objects([hand_r, hand_l], "ViewHands")

# ----------------------------------------------------------------------------- armature
BONES = [("root", ROCK_C, ROCK_C + V((0, 0, 0.1)), None)] + bones_r + bones_l
arm_data = bpy.data.armatures.new("ViewRig")
rig = bpy.data.objects.new("ViewRig", arm_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, h, t, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = V(h), V(t)
    if parent:
        eb.parent = arm_data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


segs = [(n, V(h), V(t)) for n, h, t, _ in BONES if n != "root"]
groups = {n: hands.vertex_groups.new(name=n) for n, _, _, _ in BONES}
for v in hands.data.vertices:
    side_tag = ".R" if v.co.x > 0 else ".L"
    ds = sorted((seg_dist(v.co, a, b), n) for n, a, b in segs if n.endswith(side_tag))[:2]
    w = [(n, 1.0 / max(d, 1e-4) ** 6) for d, n in ds]
    tot = sum(x for _, x in w)
    for n, x in w:
        groups[n].add([v.index], x / tot, "REPLACE")
hands.parent = rig
hands.modifiers.new("Armature", "ARMATURE").object = rig

mw = rock.matrix_world.copy()
rock.parent = rig
rock.parent_type = "BONE"
rock.parent_bone = "root"
bpy.context.view_layer.update()
rock.matrix_world = mw

# ----------------------------------------------------------------------------- actions
rig.animation_data_create()
X3, Y3, Z3 = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def key(frame, bone, rot=(), loc=None):
    pb = rig.pose.bones[bone]
    m = arm_data.bones[bone].matrix_local.to_3x3().inverted()
    q = Quaternion()
    for axis, deg in rot:
        q = Quaternion((m @ axis).normalized(), math.radians(deg)) @ q
    pb.rotation_quaternion = q
    pb.location = m @ V(loc) if loc is not None else V()
    pb.keyframe_insert("rotation_quaternion", frame=frame, group=bone)
    pb.keyframe_insert("location", frame=frame, group=bone)


def new_action(name):
    for pb in rig.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = V()
    action = bpy.data.actions.new(name)
    rig.animation_data.action = action
    return action


actions = []
actions.append(new_action("Idle"))  # 2 s breathing: rock and hands bob and roll slightly
for f in range(0, 91, 3):
    a = 2 * math.pi * f / 90
    key(f, "root", [(X3, 2.2 * math.sin(a)), (Y3, 2.0 * math.sin(a * 2 + 1.0)), (Z3, 1.2 * math.sin(a + 2.0))],
        (0.006 * math.sin(a * 2 + 0.7), 0.004 * math.sin(a), 0.012 * math.sin(a)))
    for tag, ph in ((".R", 0.0), (".L", 1.1)):
        key(f, f"arm{tag}", [(X3, 1.0 * math.sin(a + ph))])
        for i, name in enumerate(("index", "middle", "ring", "pinky")):
            key(f, f"{name}1{tag}", [(X3, -2.0 * max(0.0, math.sin(a * 2 + ph + i * 0.5)))])
actions.append(new_action("Draw"))  # rises from below the screen
for f, rx, loc in ((0, -30, (0.0, -0.08, -0.3)), (6, -10, (0.0, -0.03, -0.09)), (11, 2, (0, 0, 0.006)), (15, 0, (0, 0, 0))):
    key(f, "root", [(X3, rx)], loc)
actions.append(new_action("Swing"))  # both arms lift the rock up, smash forward-down, recover; contact frame 9
for f, rx, rz, loc in ((0, 0, 0, (0, 0, 0)), (5, 32, -6, (0.02, -0.07, 0.09)), (9, -34, 5, (-0.01, 0.13, -0.05)),
                       (11, -38, 6, (-0.015, 0.14, -0.065)), (16, -16, 2, (0, 0.06, -0.03)), (22, 0, 0, (0, 0, 0))):
    key(f, "root", [(X3, rx), (Z3, rz)], loc)
for act in actions:
    track = rig.animation_data.nla_tracks.new()
    track.name = act.name
    track.strips.new(act.name, int(act.frame_range[0]), act)
    act.use_fake_user = True
rig.animation_data.action = None

tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "viewmodel_rock.glb"), [rig, hands, rock], animations=True,
              export_animation_mode="NLA_TRACKS")
print(f"VIEWMODEL verts={len(hands.data.vertices)} bones={len(BONES)} actions={[a.name for a in actions]}")

# ----------------------------------------------------------------------------- preview (game camera, 80 deg vertical FOV)
c = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
c.data.sensor_fit = "VERTICAL"
c.data.angle_y = math.radians(80)
c.data.clip_start = 0.01
c.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(c)
scene.camera = c
for o in (hands, rock):
    for m in o.data.materials:
        nt = m.node_tree
        b = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
        if not b.inputs["Base Color"].is_linked:
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
    rig.animation_data.action = actions[2]
    for f in (5, 9, 16):
        scene.frame_set(f)
        scene.render.filepath = f"/tmp/verify/vm_swing{f}.png"
        bpy.ops.render.render(write_still=True)
    rig.animation_data.action = actions[0]
    scene.frame_set(0)
    c.data.angle_y = math.radians(35)
    for i, d in enumerate((V((0.3, -1, 0.2)), V((1, -0.3, -0.6)), V((0, -0.5, -1)))):
        c.location = ROCK_C + d.normalized() * 0.8
        tz.look_at(c, ROCK_C)
        scene.render.filepath = f"/tmp/verify/vmdbg{i}.png"
        bpy.ops.render.render(write_still=True)
