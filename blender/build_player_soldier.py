"""TEZEROK — game player: Mixamo "Vanguard" soldier (tools/third_party/Soldier.glb, 49-bone Mixamo rig,
mocap Idle / Walk / Run) plus a hand-keyed two-handed rock Swing. Exports assets/models/game/player_soldier.glb.

Run:    blender -b --factory-startup --python blender/build_player_soldier.py
"""
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tz_common as tz  # noqa: E402

V = Vector
scene = tz.reset_scene()
bpy.ops.import_scene.gltf(filepath=os.path.join(tz.ROOT, "tools", "third_party", "Soldier.glb"))
for o in list(bpy.context.scene.objects):
    if o.name == "Icosphere":
        bpy.data.objects.remove(o)
rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.data.actions["TPose"].use_fake_user = False
bpy.data.actions.remove(bpy.data.actions["TPose"])
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
B = "mixamorig:"


def rot(bone, rots):
    """Quaternion for world-axis rotations applied to a bone (bone rest frame -> world via armature matrix)."""
    m = (rig.matrix_world.to_3x3() @ rig.data.bones[bone].matrix_local.to_3x3()).inverted()
    out = Quaternion()
    for axis, deg in rots:
        out = Quaternion((m @ axis).normalized(), math.radians(deg)) @ out
    return out


def key(frame, bone, rots):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = rot(bone, rots)
    pb.keyframe_insert("rotation_quaternion", frame=frame, group=bone)


# Swing: both arms lift the rock over the head, smash forward-down, recover. Contact at frame 9 (30 fps).
act = bpy.data.actions.new("Swing")
rig.animation_data.action = act
idle = bpy.data.actions["Idle"]
KEYS = [(0, 0.0, 0.0), (5, 1.0, 0.0), (9, 0.0, 1.0), (11, 0.0, 1.0), (16, 0.0, 0.45), (22, 0.0, 0.0)]
for f, up, down in KEYS:
    for side, sgn in (("Right", -1), ("Left", 1)):
        # arms forward and up (about world X), slightly inward; elbows bend on the wind-up
        key(f, B + side + "Arm", [(X, -120 * up - 55 * down), (Z, sgn * (-15 * up - 25 * down))])
        key(f, B + side + "ForeArm", [(X, -60 * up - 20 * down)])
        key(f, B + side + "Hand", [(X, -20 * up + 25 * down)])
    key(f, B + "Spine", [(X, 10 * up - 22 * down)])
    key(f, B + "Spine1", [(X, 8 * up - 14 * down)])
    key(f, B + "Head", [(X, -12 * up + 10 * down)])
    key(f, B + "RightUpLeg", [(X, -8 * down)])
    key(f, B + "LeftUpLeg", [(X, 8 * down)])
for action in bpy.data.actions:
    track = rig.animation_data.nla_tracks.new()
    track.name = action.name
    track.strips.new(action.name, int(action.frame_range[0]), action)
    action.use_fake_user = True
rig.animation_data.action = None
tz.export_glb(os.path.join(tz.MODELS_DIR, "game", "player_soldier.glb"), [rig] + meshes, animations=True,
              export_animation_mode="NLA_TRACKS", export_image_format="AUTO")
print("PLAYER_SOLDIER actions=", [a.name for a in bpy.data.actions])

if os.environ.get("RIG_DEBUG"):
    tz.setup_cycles(scene, samples=8, res=(360, 480))
    tz.world_color(scene, (0.6, 0.6, 0.65, 1), 1.0)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (2.6, -3.0, 1.3)
    tz.look_at(cam, (0, 0, 0.9))
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (0.9, 0, -0.5)
    scene.collection.objects.link(sun)
    rig.animation_data.action = act
    for f in (0, 5, 9, 16):
        scene.frame_set(f)
        scene.render.filepath = f"/tmp/verify/sw_{f:02d}.png"
        bpy.ops.render.render(write_still=True)
