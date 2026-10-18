extends CharacterBody3D
## First-person survivor: movement, mouse look, survival stats and the rock in hand
## (idle hold sway, swing animation, gathering on hit).

signal stats_changed
signal gathered(items: Array)
signal target_changed(node: ResourceNode)
signal message(text: String)

const WALK := 4.5
const SPRINT := 7.2
const JUMP := 4.6
const REACH := 2.8
const SWING_TIME := 0.75
## Contact frame of the viewmodel "Swing" action (frame 9 at 30 fps).
const HIT_TIME := 0.3
const HUNGER_RATE := 100.0 / 1500.0
const THIRST_RATE := 100.0 / 1000.0

var inventory: Inventory
var selected := 0
var health := 100.0
var hunger := 100.0
var thirst := 100.0
var controls_enabled := true
var third_person := false

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _pitch := 0.0
var _swinging := false
var _bob := 0.0
var _sway := Vector2.ZERO
var _land := 0.0
var _fall_speed := 0.0
var _was_on_floor := true
var _hold_base: Transform3D
var _view_anim: AnimationPlayer
var _body_anim: AnimationPlayer
var _target: ResourceNode

@onready var _head: Node3D = $Head
@onready var _camera: Camera3D = $Head/Camera3D
@onready var _hold: Node3D = $Head/Camera3D/Hold
@onready var _swing_pivot: Node3D = $Head/Camera3D/Hold/Swing


func _ready() -> void:
	_hold_base = _hold.transform
	ModelUtil.use_vertex_colors($Head/Camera3D/Hold/Swing/Viewmodel, 0.75)
	for meshi in $Head/Camera3D/Hold.find_children("*", "MeshInstance3D", true, false):
		meshi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_view_anim = $Head/Camera3D/Hold/Swing/Viewmodel.find_child("AnimationPlayer", true, false)
	_body_anim = $Body.find_child("AnimationPlayer", true, false)
	for anim_player in [_view_anim, _body_anim]:
		for anim_name in ["Idle", "Walk", "Run"]:
			if anim_player.has_animation(anim_name):
				anim_player.get_animation(anim_name).loop_mode = Animation.LOOP_LINEAR
	_view_anim.animation_finished.connect(func(_n: StringName) -> void: _view_anim.play("Idle", 0.15))
	_view_anim.play("Idle")
	_body_anim.play("Idle")
	Settings.changed.connect(_apply_settings)
	_apply_settings()


func _apply_settings() -> void:
	_camera.fov = float(Settings.get_value("fov"))


func held_item() -> String:
	return inventory.slots[selected].get("id", "") if inventory else ""


func select_slot(index: int) -> void:
	selected = clampi(index, 0, Inventory.HOTBAR - 1)
	_update_held()


func set_third_person(on: bool) -> void:
	third_person = on
	$Body.visible = on
	_camera.position = Vector3(0.45, 0.25, 2.8) if on else Vector3.ZERO
	_update_held()


func _update_held() -> void:
	var holding := held_item() == "rock" and not third_person
	if holding and not _hold.visible:
		_hold.visible = true
		if _view_anim:
			_view_anim.play("Draw")
	elif not holding:
		_hold.visible = false


func _unhandled_input(event: InputEvent) -> void:
	if not controls_enabled:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var sens := float(Settings.get_value("mouse_sensitivity")) * 0.01
		var dy: float = event.relative.y * (-1.0 if Settings.get_value("invert_y") else 1.0)
		rotate_y(-event.relative.x * sens)
		_pitch = clampf(_pitch - dy * sens, deg_to_rad(-88.0), deg_to_rad(88.0))
		_head.rotation.x = _pitch
		_sway += Vector2(event.relative.x, event.relative.y) * 0.0011
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			select_slot((selected + 1) % Inventory.HOTBAR)
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			select_slot((selected + Inventory.HOTBAR - 1) % Inventory.HOTBAR)
	if event.is_action_pressed("toggle_view"):
		set_third_person(not third_person)
	for i in Inventory.HOTBAR:
		if event.is_action_pressed("slot_%d" % (i + 1)):
			select_slot(i)


func _physics_process(delta: float) -> void:
	var input := Vector2.ZERO
	if controls_enabled:
		input = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var sprinting := controls_enabled and Input.is_action_pressed("sprint") and input.y < 0.0
	var speed := SPRINT if sprinting else WALK
	var direction := (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var accel := 12.0 if is_on_floor() else 3.0
	velocity.x = move_toward(velocity.x, direction.x * speed, accel * speed * delta)
	velocity.z = move_toward(velocity.z, direction.z * speed, accel * speed * delta)
	if not is_on_floor():
		velocity.y -= _gravity * delta
	elif controls_enabled and Input.is_action_just_pressed("jump"):
		velocity.y = JUMP
	move_and_slide()
	if position.y < -50.0:
		position = Vector3(0, 30, 0)
		velocity = Vector3.ZERO
	_update_stats(delta, sprinting and input != Vector2.ZERO)
	if controls_enabled and Input.is_action_pressed("attack"):
		_try_swing()
	_update_target()
	_update_body_anim()


func _update_body_anim() -> void:
	if _body_anim == null or not $Body.visible:
		return
	if _body_anim.current_animation == "Swing" and _body_anim.is_playing():
		return
	var speed := Vector2(velocity.x, velocity.z).length()
	var want := "Idle" if speed < 0.5 else ("Run" if speed > WALK + 0.5 else "Walk")
	if _body_anim.current_animation != want:
		_body_anim.play(want, 0.2)
	_body_anim.speed_scale = 1.0 if want == "Idle" else speed / (WALK if want == "Walk" else SPRINT)


func _process(delta: float) -> void:
	var planar := Vector2(velocity.x, velocity.z)
	var moving := planar.length()
	var move_t := clampf(moving / WALK, 0.0, 1.6)
	_bob += delta * (2.0 + moving * 2.1)
	_sway = _sway.lerp(Vector2.ZERO, 1.0 - exp(-delta * 6.0))
	_land = lerpf(_land, 0.0, 1.0 - exp(-delta * 7.0))
	if is_on_floor() and not _was_on_floor:
		_land = clampf(-_fall_speed / 12.0, 0.0, 1.0)
	_fall_speed = velocity.y
	_was_on_floor = is_on_floor()
	if _hold.visible:
		# figure-8 walk bob, mouse-look lag, strafe/sprint tilt and a landing dip; all on top of the Idle clip
		var bob := Vector3(sin(_bob) * 0.022, -absf(cos(_bob)) * 0.018 + sin(_bob * 2.0) * 0.004, 0.0) * move_t
		var lag := Vector3(-_sway.x, _sway.y, 0.0).limit_length(0.11)
		var local_vel := transform.basis.inverse() * velocity
		var target := _hold_base.origin + bob + lag + Vector3(0, -0.06 * _land, 0.02 * _land)
		_hold.position = _hold.position.lerp(target, 1.0 - exp(-delta * 9.0))
		var rot := Vector3(_sway.y * 1.5 + sin(_bob) * 0.012 * move_t - 0.25 * _land,
				-_sway.x * 1.2, -_sway.x * 2.4 - local_vel.x * 0.015 + sin(_bob) * 0.03 * move_t)
		_hold.rotation = _hold.rotation.lerp(rot, 1.0 - exp(-delta * 9.0))
	if not third_person and is_on_floor():
		_camera.position.y = sin(_bob * 2.0) * 0.012 * move_t - 0.05 * _land
		_camera.rotation.z = lerpf(_camera.rotation.z, sin(_bob) * 0.006 * move_t, 1.0 - exp(-delta * 8.0))


func _try_swing() -> void:
	if _swinging:
		return
	if held_item() != "rock":
		message.emit("Возьмите камень в руку (ячейка 1)")
		return
	_swinging = true
	if third_person:
		_body_anim.play("Swing", 0.08)
	else:
		_view_anim.stop()
		_view_anim.play("Swing")
	var tween := create_tween()
	tween.tween_interval(HIT_TIME)
	tween.tween_callback(_hit)
	tween.tween_interval(SWING_TIME - HIT_TIME)
	tween.tween_callback(func() -> void: _swinging = false)


func _ray() -> Dictionary:
	var from := _head.global_position
	var to := from - _camera.global_transform.basis.z * REACH
	var query := PhysicsRayQueryParameters3D.create(from, to)
	query.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_ray(query)


func _hit() -> void:
	var hit := _ray()
	if hit.is_empty():
		return
	_camera.h_offset = 0.0
	var shake := create_tween()
	shake.tween_property(_camera, "v_offset", -0.015, 0.03)
	shake.tween_property(_camera, "v_offset", 0.0, 0.12)
	var node := hit.collider as ResourceNode
	if node == null:
		return
	var items := node.gather(hit.position)
	for item: Array in items:
		var left := inventory.add(item[0], item[1])
		if left > 0:
			message.emit("Инвентарь заполнен")
	if not items.is_empty():
		gathered.emit(items)
	target_changed.emit(node)


func _update_target() -> void:
	var hit := _ray()
	var node: ResourceNode = hit.collider as ResourceNode if not hit.is_empty() else null
	if node and node.hits_left <= 0:
		node = null
	if node != _target:
		_target = node
		target_changed.emit(node)


func _update_stats(delta: float, sprinting: bool) -> void:
	hunger = maxf(hunger - HUNGER_RATE * delta * (1.6 if sprinting else 1.0), 0.0)
	thirst = maxf(thirst - THIRST_RATE * delta * (1.8 if sprinting else 1.0), 0.0)
	if hunger <= 0.0 or thirst <= 0.0:
		health = maxf(health - 0.6 * delta, 0.0)
	elif hunger > 50.0 and thirst > 50.0:
		health = minf(health + 0.15 * delta, 100.0)
	if health <= 0.0:
		message.emit("Вы погибли — возрождение")
		health = 100.0
		hunger = 100.0
		thirst = 100.0
		position = Vector3(0, 30, 0)
	stats_changed.emit()
