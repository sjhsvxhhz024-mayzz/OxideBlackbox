extends Node3D
## Living backdrop of the main menu: applies materials to the Blender models, loops the player's
## idle animation and animates chimney smoke, birds, the radio-tower beacon and the device glow.

const MenuMaterials := preload("res://scripts/menu_materials.gd")
const BIRD_SCENE := preload("res://assets/models/bird.glb")
const BIRD_SHADER := preload("res://shaders/bird.gdshader")
const SMOKE_TEXTURE := preload("res://assets/textures/smoke_puff.png")
## Visual layer that only the character key light affects.
const PLAYER_LAYER := 2

@export var player_yaw_degrees := -20.0
@export var sun_pitch_degrees := -5.0
@export var sun_yaw_degrees := 177.0
@export var bird_count := 7

var _materials := MenuMaterials.new()
var _beacon_lights: Array[OmniLight3D] = []
var _birds: Array[Dictionary] = []
var _time := 0.0

@onready var _environment: Node3D = $Environment
@onready var _player: Node3D = $Player
@onready var _sun: DirectionalLight3D = $Sun
@onready var _key_light: DirectionalLight3D = $KeyLight
@onready var _cloud_dome: MeshInstance3D = $CloudDome


func _ready() -> void:
	_apply_materials(_environment, _materials.for_environment())
	_apply_materials(_player, _materials.for_player())
	_setup_player()
	_setup_lights()
	_setup_smoke()
	_setup_beacons()
	_setup_birds()
	_setup_dust()


func _process(delta: float) -> void:
	_time += delta
	var blink := clampf(sin(_time * PI) * 3.0, 0.0, 1.0)
	_materials.beacon.emission_energy_multiplier = lerpf(0.3, 16.0, blink)
	for light in _beacon_lights:
		light.light_energy = blink * 8.0
	_materials.glow.emission_energy_multiplier = 3.6 + sin(_time * 1.8) * 1.1
	_update_birds(delta)


func _apply_materials(root: Node, by_name: Dictionary) -> void:
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		for i in mesh_instance.mesh.get_surface_count():
			var source := mesh_instance.mesh.surface_get_material(i)
			if source and by_name.has(source.resource_name):
				mesh_instance.set_surface_override_material(i, by_name[source.resource_name])


func _setup_player() -> void:
	var spot := _environment.find_child("PlayerSpot", true, false) as Node3D
	if spot:
		_player.global_position = spot.global_position
	_player.rotation_degrees.y = player_yaw_degrees
	for node in _player.find_children("*", "MeshInstance3D", true, false):
		(node as MeshInstance3D).layers = 1 | PLAYER_LAYER
	var animation_player := _player.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if animation_player and animation_player.has_animation("Idle"):
		animation_player.get_animation("Idle").loop_mode = Animation.LOOP_LINEAR
		animation_player.play("Idle")


func _setup_lights() -> void:
	_sun.rotation_degrees = Vector3(sun_pitch_degrees, sun_yaw_degrees, 0.0)
	var clouds := _cloud_dome.get_surface_override_material(0) as ShaderMaterial
	clouds.set_shader_parameter("sun_direction", _sun.global_transform.basis.z)
	var target := _player.global_position + Vector3(0.0, 1.2, 0.0)
	_key_light.look_at_from_position(target + Vector3(-4.0, 3.5, 5.0), target)


func _setup_smoke() -> void:
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	material.vertex_color_use_as_albedo = true
	material.albedo_texture = SMOKE_TEXTURE
	var quad := QuadMesh.new()
	quad.material = material
	var ramp := Gradient.new()
	ramp.offsets = PackedFloat32Array([0.0, 0.08, 0.55, 1.0])
	ramp.colors = PackedColorArray([Color(0.2, 0.19, 0.18, 0.0), Color(0.19, 0.18, 0.18, 0.9),
			Color(0.27, 0.27, 0.28, 0.45), Color(0.33, 0.33, 0.35, 0.0)])
	var ramp_texture := GradientTexture1D.new()
	ramp_texture.gradient = ramp
	var growth := Curve.new()
	growth.max_value = 5.0
	growth.add_point(Vector2(0.0, 0.8))
	growth.add_point(Vector2(1.0, 4.5))
	var growth_texture := CurveTexture.new()
	growth_texture.curve = growth
	for i in range(1, 4):
		var marker := _environment.find_child("Smoke%d" % i, true, false) as Node3D
		if marker == null:
			continue
		var big := i < 3
		var process := ParticleProcessMaterial.new()
		process.direction = Vector3(0.35, 1.0, -0.1)
		process.spread = 7.0
		process.initial_velocity_min = 3.0
		process.initial_velocity_max = 4.2
		process.gravity = Vector3(0.28, 0.0, -0.05)
		process.damping_min = 0.08
		process.damping_max = 0.12
		process.scale_min = 6.0 if big else 3.0
		process.scale_max = 9.0 if big else 4.5
		process.scale_curve = growth_texture
		process.angle_min = -180.0
		process.angle_max = 180.0
		process.angular_velocity_min = -6.0
		process.angular_velocity_max = 6.0
		process.color_ramp = ramp_texture
		var particles := GPUParticles3D.new()
		particles.amount = 44 if big else 22
		particles.lifetime = 22.0
		particles.preprocess = 22.0
		particles.process_material = process
		particles.draw_pass_1 = quad
		particles.visibility_aabb = AABB(Vector3(-60.0, -20.0, -60.0), Vector3(260.0, 160.0, 120.0))
		particles.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		marker.add_child(particles)


func _setup_beacons() -> void:
	for marker_name in ["BeaconTop", "BeaconMid"]:
		var marker := _environment.find_child(marker_name, true, false) as Node3D
		if marker == null:
			continue
		var light := OmniLight3D.new()
		light.light_color = Color(1.0, 0.18, 0.1)
		light.omni_range = 30.0
		light.light_energy = 0.0
		marker.add_child(light)
		_beacon_lights.append(light)


func _setup_birds() -> void:
	var material := ShaderMaterial.new()
	material.shader = BIRD_SHADER
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in bird_count:
		var bird := BIRD_SCENE.instantiate() as Node3D
		add_child(bird)
		for node in bird.find_children("*", "MeshInstance3D", true, false):
			var mesh_instance := node as MeshInstance3D
			mesh_instance.material_override = material
			mesh_instance.set_instance_shader_parameter("phase", rng.randf() * TAU)
			mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		bird.scale = Vector3.ONE * rng.randf_range(1.4, 1.9)
		_birds.append({
			"node": bird,
			"center": Vector3(rng.randf_range(-40.0, 60.0), rng.randf_range(26.0, 44.0), rng.randf_range(-260.0, -180.0)),
			"radius": rng.randf_range(25.0, 55.0),
			"speed": rng.randf_range(0.07, 0.12) * (1.0 if rng.randf() > 0.3 else -1.0),
			"angle": rng.randf() * TAU,
		})
	_update_birds(0.0)


func _update_birds(delta: float) -> void:
	for bird in _birds:
		bird.angle += bird.speed * delta
		var position := _bird_position(bird, bird.angle)
		var ahead := _bird_position(bird, bird.angle + 0.05 * signf(bird.speed))
		(bird.node as Node3D).look_at_from_position(position, ahead)


func _bird_position(bird: Dictionary, angle: float) -> Vector3:
	var radius: float = bird.radius
	return bird.center + Vector3(cos(angle) * radius, sin(angle * 2.0) * 2.5, sin(angle) * radius * 0.55)


func _setup_dust() -> void:
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	material.vertex_color_use_as_albedo = true
	material.albedo_texture = SMOKE_TEXTURE
	var quad := QuadMesh.new()
	quad.size = Vector2(0.035, 0.035)
	quad.material = material
	var fade := Gradient.new()
	fade.offsets = PackedFloat32Array([0.0, 0.3, 0.7, 1.0])
	fade.colors = PackedColorArray([Color(1.0, 0.85, 0.6, 0.0), Color(1.0, 0.85, 0.6, 0.55),
			Color(1.0, 0.85, 0.6, 0.55), Color(1.0, 0.85, 0.6, 0.0)])
	var fade_texture := GradientTexture1D.new()
	fade_texture.gradient = fade
	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(5.0, 1.4, 3.0)
	process.direction = Vector3(1.0, 0.2, 0.0)
	process.spread = 180.0
	process.initial_velocity_min = 0.05
	process.initial_velocity_max = 0.22
	process.gravity = Vector3(0.06, 0.012, 0.0)
	process.color_ramp = fade_texture
	var dust := GPUParticles3D.new()
	dust.amount = 70
	dust.lifetime = 9.0
	dust.preprocess = 9.0
	dust.process_material = process
	dust.draw_pass_1 = quad
	dust.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(dust)
	dust.global_position = _player.global_position + Vector3(-0.5, 1.2, 0.8)
