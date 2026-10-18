class_name ModelUtil
extends RefCounted
## glTF materials from our Blender exports ignore vertex colours in Godot; swap in ones that use them.


static func use_vertex_colors(root: Node, roughness := 0.85, metallic := 0.0) -> void:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = roughness
	material.metallic = metallic
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		for i in mesh_instance.mesh.get_surface_count():
			mesh_instance.set_surface_override_material(i, material)
