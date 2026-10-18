"""Shared helpers for the TEZEROK Blender generators (Blender 5.2, background mode)."""
import math
import os

import bmesh
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT, "assets", "models")
TEXTURES_DIR = os.path.join(ROOT, "assets", "textures")
BLEND_DIR = os.path.join(ROOT, "blender")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    return scene


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hex_str, alpha=1.0):
    """Linear RGBA from an sRGB hex string."""
    h = hex_str.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (alpha,)


def material(name, color, roughness=0.8, metallic=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    col = rgb(color) if isinstance(color, str) else color
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = rgb(emission) if isinstance(emission, str) else emission
        bsdf.inputs["Emission Strength"].default_value = strength
    mat.diffuse_color = col
    return mat


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def gauss(x, s):
    return math.exp(-(x / s) ** 2)


def lerp(a, b, t):
    return a + (b - a) * t


def color_layer(bm, name="Col"):
    return bm.verts.layers.float_color.get(name) or bm.verts.layers.float_color.new(name)


def activate_colors(me, name="Col"):
    attrs = me.color_attributes
    if name not in attrs:
        return
    for prop in ("active_color_name", "default_color_name"):
        try:
            setattr(attrs, prop, name)
        except (AttributeError, TypeError):
            pass


def mesh_object(name, bm, mats, collection=None, smooth=True, sharp_angle=40.0):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if smooth:
        me.shade_smooth()
        if sharp_angle is not None:
            me.set_sharp_from_angle(angle=math.radians(sharp_angle))
    else:
        me.shade_flat()
    activate_colors(me)
    return obj


def skin_mesh(name, nodes, edges, root=0, subsurf=2, branch_smoothing=0.0):
    """Evaluate a skin-modifier skeleton. nodes: [(co, (rx, ry))]; returns a Mesh datablock."""
    me = bpy.data.meshes.new(name + "_src")
    me.from_pydata([tuple(n[0]) for n in nodes], edges, [])
    obj = bpy.data.objects.new(name + "_src", me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("Skin", "SKIN")
    mod.branch_smoothing = branch_smoothing
    mod.use_smooth_shade = True
    data = me.skin_vertices[0].data
    for i, (_, r) in enumerate(nodes):
        data[i].radius = r
        data[i].use_root = i == root
    if subsurf:
        sub = obj.modifiers.new("Subsurf", "SUBSURF")
        sub.levels = subsurf
        sub.render_levels = subsurf
    me.update()
    dg = bpy.context.evaluated_depsgraph_get()
    result = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(me)
    result.name = name
    return result


def bm_from_mesh(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    return bm


def faces_of(verts):
    return list({f for v in verts for f in v.link_faces})


def join_objects(objs, name):
    target = objs[0]
    with bpy.context.temp_override(active_object=target, object=target,
                                   selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    target.name = name
    target.data.name = name
    return target


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def export_glb(path, objects, animations=False, **extra):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    opts = dict(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_animations=animations,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_optimize_animation_size=False,
        export_skins=True,
        export_vertex_color="ACTIVE",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )
    opts.update(extra)
    bpy.ops.export_scene.gltf(**opts)


def setup_cycles(scene, samples=32, res=(800, 800)):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"


def world_color(scene, color, strength=1.0):
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    bg.inputs["Color"].default_value = color
    bg.inputs["Strength"].default_value = strength
