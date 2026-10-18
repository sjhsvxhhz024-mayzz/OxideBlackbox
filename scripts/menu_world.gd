extends Node3D
## Photo-real living backdrop of the main menu.
## The background and the player are built from the AI-processed concept art (tools/ai_pipeline,
## blender/build_menu_scene.py); this script layers the motion on top: the idle loop, chimney smoke,
## drifting valley haze, birds, the tower beacon, flickering factory lights and floating dust.

const PLATE_SHADER := preload("res://shaders/photo_plate.gdshader")
const PLAYER_SHADER := preload("res://shaders/photo_player.gdshader")
const GLOW_SHADER := preload("res://shaders/glow_sprite.gdshader")
const BIRD_SHADER := preload("res://shaders/bird.gdshader")
const PLATE_TEXTURE := preload("res://assets/menu_plate/plate.png")
const PLATE_MASKS := preload("res://assets/menu_plate/plate_masks.png")
const PLAYER_TEXTURE := preload("res://assets/menu_plate/player_photo.png")
const BIRD_SCENE := preload("res://assets/models/bird.glb")
const PUFF_TEXTURE := preload("res://assets/textures/smoke_puff.png")

@export var bird_count := 6

var _beacon: MeshInstance3D
var _factory_lights: Array[MeshInstance3D] = []
var _birds: Array[Dictionary] = []
var _time := 0.0

@onready var _background: Node3D = $Background
@onready var _player: Node3D = $Player


func _ready() -> void:
	var plate := ShaderMaterial.new()
	plate.shader = PLATE_SHADER
	plate.set_shader_parameter("plate", PLATE_TEXTURE)
	plate.set_shader_parameter("masks", PLATE_MASKS)
	_override_material(_background, plate)
	var player := ShaderMaterial.new()
	player.shader = PLAYER_SHADER
	player.set_shader_parameter("photo", PLAYER_TEXTURE)
	_override_material(_player, player)
	_play_idle()
	_setup_smoke()
	_setup_haze()
	_setup_lights()
	_setup_birds()
	_setup_dust()


func _process(delta: float) -> void:
	_time += delta
	var blink := clampf(sin(_time * PI) * 3.0, 0.0, 1.0)
	_beacon.set_instance_shader_parameter("level", lerpf(0.08, 1.0, blink))
	for i in _factory_lights.size():
		var flicker := 0.8 + 0.2 * sin(_time * (2.0 + i * 0.7) + i) * sin(_time * (5.3 + i) + i * 2.0)
		var on := 1.0 if fmod(_time * 0.05 + i * 0.37, 1.0) > 0.12 else 0.15
		_factory_lights[i].set_instance_shader_parameter("level", flicker * on)
	_update_birds(delta)


func _override_material(root: Node, material: Material) -> void:
	for node in root.find_children("*", "MeshInstance3D", true, false):
		(node as MeshInstance3D).material_override = material


func _marker(marker_name: String) -> Node3D:
	return _background.find_child(marker_name, true, false) as Node3D


func _play_idle() -> void:
	var animation_player := _player.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if animation_player and animation_player.has_animation("Idle"):
		animation_player.get_animation("Idle").loop_mode = Animation.LOOP_LINEAR
		animation_player.play("Idle")


func _billboard_material(color: Color, alpha_curve: PackedColorArray, offsets: PackedFloat32Array) -> Array:
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	# Godot 4.7 drops the per-particle scale on billboards unless this is set.
	material.billboard_keep_scale = true
	material.vertex_color_use_as_albedo = true
	material.albedo_texture = PUFF_TEXTURE
	material.albedo_color = color
	var quad := QuadMesh.new()
	quad.material = material
	var ramp := Gradient.new()
	ramp.offsets = offsets
	ramp.colors = alpha_curve
	var ramp_texture := GradientTexture1D.new()
	ramp_texture.gradient = ramp
	return [quad, ramp_texture]


func _setup_smoke() -> void:
	var parts := _billboard_material(Color.WHITE,
			PackedColorArray([Color(0.16, 0.16, 0.17, 0.0), Color(0.14, 0.14, 0.15, 0.85),
				Color(0.22, 0.22, 0.24, 0.5), Color(0.3, 0.3, 0.33, 0.0)]),
			PackedFloat32Array([0.0, 0.07, 0.5, 1.0]))
	var growth := Curve.new()
	growth.max_value = 5.0
	growth.add_point(Vector2(0.0, 0.8))
	growth.add_point(Vector2(1.0, 4.0))
	var growth_texture := CurveTexture.new()
	growth_texture.curve = growth
	for i in range(1, 3):
		var marker := _marker("Smoke%d" % i)
		if marker == null:
			continue
		var process := ParticleProcessMaterial.new()
		process.direction = Vector3(0.45, 1.0, 0.0)
		process.spread = 6.0
		process.initial_velocity_min = 4.0
		process.initial_velocity_max = 5.5
		process.gravity = Vector3(0.6, 0.0, 0.0)
		process.damping_min = 0.1
		process.damping_max = 0.15
		process.scale_min = 10.0
		process.scale_max = 15.0
		process.scale_curve = growth_texture
		process.angle_min = -180.0
		process.angle_max = 180.0
		process.angular_velocity_min = -5.0
		process.angular_velocity_max = 5.0
		process.color_ramp = parts[1]
		var particles := GPUParticles3D.new()
		particles.amount = 40
		particles.lifetime = 24.0
		particles.preprocess = 24.0
		particles.process_material = process
		particles.draw_pass_1 = parts[0]
		particles.visibility_aabb = AABB(Vector3(-80.0, -20.0, -80.0), Vector3(320.0, 200.0, 160.0))
		marker.add_child(particles)


func _setup_haze() -> void:
	var parts := _billboard_material(Color.WHITE,
			PackedColorArray([Color(0.62, 0.66, 0.72, 0.0), Color(0.62, 0.66, 0.72, 0.09),
				Color(0.62, 0.66, 0.72, 0.09), Color(0.62, 0.66, 0.72, 0.0)]),
			PackedFloat32Array([0.0, 0.3, 0.7, 1.0]))
	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(260.0, 18.0, 180.0)
	process.direction = Vector3(1.0, 0.0, 0.0)
	process.spread = 10.0
	process.initial_velocity_min = 1.5
	process.initial_velocity_max = 3.0
	process.gravity = Vector3.ZERO
	process.scale_min = 70.0
	process.scale_max = 150.0
	process.angle_min = -180.0
	process.angle_max = 180.0
	process.color_ramp = parts[1]
	var haze := GPUParticles3D.new()
	haze.amount = 22
	haze.lifetime = 45.0
	haze.preprocess = 45.0
	haze.process_material = process
	haze.draw_pass_1 = parts[0]
	haze.visibility_aabb = AABB(Vector3(-500.0, -100.0, -400.0), Vector3(1000.0, 200.0, 800.0))
	add_child(haze)
	haze.position = Vector3(20.0, -45.0, -430.0)


func _glow(at: Vector3, size: float, color: Color, intensity: float) -> MeshInstance3D:
	var material := ShaderMaterial.new()
	material.shader = GLOW_SHADER
	material.set_shader_parameter("color", color)
	material.set_shader_parameter("intensity", intensity)
	var sprite := MeshInstance3D.new()
	sprite.mesh = QuadMesh.new()
	sprite.material_override = material
	sprite.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sprite)
	sprite.global_position = at
	sprite.scale = Vector3.ONE * size
	return sprite


func _setup_lights() -> void:
	var beacon_marker := _marker("BeaconTop")
	_beacon = _glow(beacon_marker.global_position, 22.0, Color(1.0, 0.18, 0.1), 6.0)
	var i := 1
	while _marker("FactoryLight%d" % i):
		_factory_lights.append(_glow(_marker("FactoryLight%d" % i).global_position, 5.0, Color(1.0, 0.68, 0.36), 2.2))
		i += 1


func _setup_birds() -> void:
	var material := ShaderMaterial.new()
	material.shader = BIRD_SHADER
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for n in bird_count:
		var bird := BIRD_SCENE.instantiate() as Node3D
		add_child(bird)
		for node in bird.find_children("*", "MeshInstance3D", true, false):
			var mesh_instance := node as MeshInstance3D
			mesh_instance.material_override = material
			mesh_instance.set_instance_shader_parameter("phase", rng.randf() * TAU)
		bird.scale = Vector3.ONE * rng.randf_range(2.0, 2.6)
		_birds.append({
			"node": bird,
			"center": Vector3(rng.randf_range(-40.0, 150.0), rng.randf_range(32.0, 70.0), rng.randf_range(-520.0, -330.0)),
			"radius": rng.randf_range(30.0, 60.0),
			"speed": rng.randf_range(0.06, 0.1) * (1.0 if rng.randf() > 0.3 else -1.0),
			"angle": rng.randf() * TAU,
		})
	_update_birds(0.0)


func _update_birds(delta: float) -> void:
	for bird in _birds:
		bird.angle += bird.speed * delta
		var here := _bird_position(bird, bird.angle)
		var ahead := _bird_position(bird, bird.angle + 0.05 * signf(bird.speed))
		(bird.node as Node3D).look_at_from_position(here, ahead)


func _bird_position(bird: Dictionary, angle: float) -> Vector3:
	var radius: float = bird.radius
	return bird.center + Vector3(cos(angle) * radius, sin(angle * 2.0) * 3.0, sin(angle) * radius * 0.5)


func _setup_dust() -> void:
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	material.vertex_color_use_as_albedo = true
	material.albedo_texture = PUFF_TEXTURE
	var quad := QuadMesh.new()
	quad.size = Vector2(0.014, 0.014)
	quad.material = material
	var fade := Gradient.new()
	fade.offsets = PackedFloat32Array([0.0, 0.3, 0.7, 1.0])
	fade.colors = PackedColorArray([Color(1.0, 0.86, 0.66, 0.0), Color(1.0, 0.86, 0.66, 0.22),
			Color(1.0, 0.86, 0.66, 0.22), Color(1.0, 0.86, 0.66, 0.0)])
	var fade_texture := GradientTexture1D.new()
	fade_texture.gradient = fade
	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(3.0, 0.7, 2.0)
	process.direction = Vector3(1.0, 0.2, 0.0)
	process.spread = 180.0
	process.initial_velocity_min = 0.04
	process.initial_velocity_max = 0.18
	process.gravity = Vector3(0.05, 0.01, 0.0)
	process.color_ramp = fade_texture
	var dust := GPUParticles3D.new()
	dust.amount = 40
	dust.lifetime = 9.0
	dust.preprocess = 9.0
	dust.process_material = process
	dust.draw_pass_1 = quad
	add_child(dust)
	dust.position = Vector3(0.9, -0.4, -3.9)
