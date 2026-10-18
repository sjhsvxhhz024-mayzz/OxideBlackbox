extends Node3D
## Offline server world: noise terrain with collision, sky, sun, grass and harvestable nodes.

const SIZE := 240
const TREE := preload("res://assets/models/game/tree.glb")
const STONE := preload("res://assets/models/game/stone_node.glb")
const SULFUR := preload("res://assets/models/game/sulfur_node.glb")
const METAL := preload("res://assets/models/game/metal_node.glb")
const GROUND_SHADER := preload("res://shaders/ground.gdshader")
const GRASS_SHADER := preload("res://shaders/grass.gdshader")
const GRASS_COUNT := [0, 12000, 30000, 55000]
const VIEW_DISTANCE := [120.0, 180.0, 260.0, 340.0]

@export var seed := 1337

var _noise := FastNoiseLite.new()
var _detail := FastNoiseLite.new()
var _env: Environment
var _sun: DirectionalLight3D
var _grass: MultiMeshInstance3D
var _vertex_material := StandardMaterial3D.new()


func _ready() -> void:
	_noise.seed = seed
	_noise.frequency = 0.008
	_noise.fractal_octaves = 4
	_detail.seed = seed + 1
	_detail.frequency = 0.05
	_vertex_material.vertex_color_use_as_albedo = true
	_vertex_material.roughness = 0.85
	_build_environment()
	_build_terrain()
	_spawn_nodes()
	_build_grass()
	Settings.changed.connect(_apply_quality)
	_apply_quality()


func height(x: float, z: float) -> float:
	var h := _noise.get_noise_2d(x, z) * 9.0 + _detail.get_noise_2d(x, z) * 0.6
	var edge := clampf((Vector2(x, z).length() - SIZE * 0.38) / (SIZE * 0.12), 0.0, 1.0)
	return h + edge * edge * 14.0


func spawn_point() -> Vector3:
	return Vector3(0.0, height(0.0, 0.0) + 1.0, 0.0)


func _build_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.25, 0.36, 0.52)
	sky_mat.sky_horizon_color = Color(0.72, 0.66, 0.6)
	sky_mat.ground_horizon_color = Color(0.5, 0.46, 0.42)
	sky_mat.ground_bottom_color = Color(0.12, 0.12, 0.11)
	sky_mat.sun_angle_max = 25.0
	var sky := Sky.new()
	sky.sky_material = sky_mat
	_env = Environment.new()
	_env.background_mode = Environment.BG_SKY
	_env.sky = sky
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	_env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	_env.fog_enabled = true
	_env.fog_light_color = Color(0.68, 0.66, 0.64)
	_env.fog_aerial_perspective = 0.5
	_env.glow_enabled = true
	_env.glow_intensity = 0.4
	_env.adjustment_enabled = true
	_env.adjustment_saturation = 0.95
	var world_env := WorldEnvironment.new()
	world_env.environment = _env
	add_child(world_env)
	_sun = DirectionalLight3D.new()
	_sun.light_color = Color(1.0, 0.9, 0.78)
	_sun.light_energy = 1.25
	_sun.shadow_enabled = true
	_sun.rotation_degrees = Vector3(-38.0, 150.0, 0.0)
	add_child(_sun)


func _build_terrain() -> void:
	var half := SIZE / 2
	var n := SIZE + 1
	var heights := PackedFloat32Array()
	heights.resize(n * n)
	for z in n:
		for x in n:
			heights[z * n + x] = height(x - half, z - half)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var grass := Color(0.27, 0.32, 0.16)
	var dry := Color(0.45, 0.41, 0.25)
	var dirt := Color(0.33, 0.27, 0.2)
	var rock := Color(0.42, 0.41, 0.39)
	for z in n:
		for x in n:
			var h := heights[z * n + x]
			var hx := heights[z * n + mini(x + 1, n - 1)] - heights[z * n + maxi(x - 1, 0)]
			var hz := heights[mini(z + 1, n - 1) * n + x] - heights[maxi(z - 1, 0) * n + x]
			var slope := Vector2(hx, hz).length() * 0.5
			var t := _detail.get_noise_2d((x - half) * 0.6, (z - half) * 0.6) * 0.5 + 0.5
			var c := grass.lerp(dry, smoothstep(0.45, 0.75, t))
			c = c.lerp(dirt, smoothstep(0.7, 0.9, _noise.get_noise_2d((x - half) * 4.0, (z - half) * 4.0) * 0.5 + 0.5) * 0.7)
			c = c.lerp(rock, smoothstep(0.45, 0.9, slope))
			st.set_color(c)
			st.set_uv(Vector2(x, z) / SIZE)
			st.add_vertex(Vector3(x - half, h, z - half))
	for z in SIZE:
		for x in SIZE:
			var i := z * n + x
			st.add_index(i)
			st.add_index(i + 1)
			st.add_index(i + n)
			st.add_index(i + 1)
			st.add_index(i + n + 1)
			st.add_index(i + n)
	st.generate_normals()
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.mesh = st.commit()
	var material := ShaderMaterial.new()
	material.shader = GROUND_SHADER
	mesh_instance.material_override = material
	add_child(mesh_instance)
	var body := StaticBody3D.new()
	var shape := HeightMapShape3D.new()
	shape.map_width = n
	shape.map_depth = n
	shape.map_data = heights
	var collision := CollisionShape3D.new()
	collision.shape = shape
	body.add_child(collision)
	add_child(body)


func _spawn_nodes() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var tree_shape := CylinderShape3D.new()
	tree_shape.radius = 0.4
	tree_shape.height = 9.0
	var specs := [
		["tree", TREE, 110, tree_shape, Vector3(0, 4.3, 0), Vector2(0.85, 1.25)],
		["stone", STONE, 34, null, Vector3(0, 0.35, 0), Vector2(0.8, 1.2)],
		["sulfur", SULFUR, 20, null, Vector3(0, 0.35, 0), Vector2(0.8, 1.1)],
		["metal", METAL, 20, null, Vector3(0, 0.35, 0), Vector2(0.8, 1.1)],
	]
	var taken: Array[Vector2] = [Vector2.ZERO]
	for spec in specs:
		var placed := 0
		var tries := 0
		while placed < spec[2] and tries < 4000:
			tries += 1
			var p := Vector2(rng.randf_range(-SIZE * 0.4, SIZE * 0.4), rng.randf_range(-SIZE * 0.4, SIZE * 0.4))
			var min_gap := 6.0 if spec[0] == "tree" else 9.0
			if p.length() < 7.0 or taken.any(func(o: Vector2) -> bool: return o.distance_to(p) < min_gap):
				continue
			taken.append(p)
			placed += 1
			var s := rng.randf_range(spec[5].x, spec[5].y)
			var shape: Shape3D = spec[3]
			if shape == null:
				var sphere := SphereShape3D.new()
				sphere.radius = 1.0 * s
				shape = sphere
			var node := ResourceNode.new()
			node.setup(spec[0], spec[1], shape, spec[4] * s if spec[0] != "tree" else spec[4], s)
			add_child(node)
			node.position = Vector3(p.x, height(p.x, p.y) - (0.25 if spec[0] == "tree" else 0.2 * s), p.y)
			node.rotation.y = rng.randf() * TAU
			_apply_vertex_material(node.model)
	# Close starter nodes so the first harvest is right next to the spawn point.
	_place_starter("tree", TREE, tree_shape, Vector3(0, 4.3, 0), Vector2(4.5, -5.0))
	_place_starter("stone", STONE, null, Vector3(0, 0.35, 0), Vector2(-4.0, -4.5))
	_place_starter("sulfur", SULFUR, null, Vector3(0, 0.35, 0), Vector2(-8.0, -9.0))
	_place_starter("metal", METAL, null, Vector3(0, 0.35, 0), Vector2(7.5, -10.0))


func _place_starter(kind: String, scene: PackedScene, shape: Shape3D, offset: Vector3, p: Vector2) -> void:
	if shape == null:
		var sphere := SphereShape3D.new()
		sphere.radius = 1.0
		shape = sphere
	var node := ResourceNode.new()
	node.setup(kind, scene, shape, offset, 1.0)
	add_child(node)
	node.position = Vector3(p.x, height(p.x, p.y) - 0.2, p.y)
	_apply_vertex_material(node.model)


func _apply_vertex_material(root: Node) -> void:
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := mi as MeshInstance3D
		for i in mesh_instance.mesh.get_surface_count():
			var source := mesh_instance.mesh.surface_get_material(i) as BaseMaterial3D
			var mat := _vertex_material.duplicate() as StandardMaterial3D
			if source:
				mat.roughness = source.roughness
				mat.metallic = source.metallic
			mesh_instance.set_surface_override_material(i, mat)


func _build_grass() -> void:
	var blade := ArrayMesh.new()
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3(-0.03, 0, 0), Vector3(0.03, 0, 0), Vector3(0.02, 0.25, 0.02),
			Vector3(-0.02, 0.25, 0.02), Vector3(0.0, 0.5, 0.06)])
	arrays[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 1), Vector2(1, 1), Vector2(1, 0.5), Vector2(0, 0.5), Vector2(0.5, 0)])
	arrays[Mesh.ARRAY_NORMAL] = PackedVector3Array([Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3, 3, 2, 4])
	blade.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var material := ShaderMaterial.new()
	material.shader = GRASS_SHADER
	blade.surface_set_material(0, material)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = blade
	mm.instance_count = GRASS_COUNT[3]
	var rng := RandomNumberGenerator.new()
	rng.seed = seed + 7
	for i in mm.instance_count:
		var r := sqrt(rng.randf()) * 70.0
		var a := rng.randf() * TAU
		var x := cos(a) * r
		var z := sin(a) * r
		var s := rng.randf_range(0.6, 1.4)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s * rng.randf_range(0.7, 1.3), s))
		mm.set_instance_transform(i, Transform3D(basis, Vector3(x, height(x, z) - 0.02, z)))
		var dry := rng.randf()
		mm.set_instance_color(i, Color(0.34, 0.42, 0.2).lerp(Color(0.62, 0.56, 0.33), dry * dry))
	_grass = MultiMeshInstance3D.new()
	_grass.multimesh = mm
	_grass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_grass)


func _apply_quality() -> void:
	var q := Settings.quality()
	_grass.multimesh.visible_instance_count = GRASS_COUNT[q]
	_sun.directional_shadow_max_distance = [40.0, 70.0, 110.0, 160.0][q]
	_sun.shadow_enabled = true
	_env.ssao_enabled = q >= 2
	_env.glow_enabled = q >= 1
	_env.fog_density = 2.6 / VIEW_DISTANCE[q] * 0.1
	var camera := get_viewport().get_camera_3d()
	if camera:
		camera.far = VIEW_DISTANCE[q] + 200.0
