extends Control
## "Персонаж" overlay: the AI-generated survivor turning slowly on a stand (drag to rotate).

signal closed

const BODY := preload("res://assets/models/game/player_ai.glb")

var _pivot := Node3D.new()
var _dragging := false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var parts := UiKit.overlay(self, 760.0)
	var box: VBoxContainer = parts[1]
	var title := UiKit.label("ПЕРСОНАЖ", 52)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var container := SubViewportContainer.new()
	container.stretch = true
	container.custom_minimum_size = Vector2(700, 640)
	box.add_child(container)
	var viewport := SubViewport.new()
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	container.add_child(viewport)
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.58, 0.65)
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	viewport.add_child(world_env)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-30, -35, 0)
	key.light_energy = 1.4
	key.light_color = Color(1.0, 0.9, 0.8)
	viewport.add_child(key)
	var rim := DirectionalLight3D.new()
	rim.rotation_degrees = Vector3(-15, 150, 0)
	rim.light_energy = 1.0
	rim.light_color = Color(0.7, 0.8, 1.0)
	viewport.add_child(rim)
	var camera := Camera3D.new()
	camera.fov = 30.0
	viewport.add_child(camera)
	camera.look_at_from_position(Vector3(0, 1.1, 4.2), Vector3(0, 0.92, 0))
	viewport.add_child(_pivot)
	var body := BODY.instantiate()
	ModelUtil.use_vertex_colors(body, 0.85)
	_pivot.add_child(body)
	var stand := MeshInstance3D.new()
	var disc := CylinderMesh.new()
	disc.top_radius = 0.6
	disc.bottom_radius = 0.65
	disc.height = 0.06
	var stand_mat := StandardMaterial3D.new()
	stand_mat.albedo_color = Color(0.12, 0.13, 0.14)
	disc.material = stand_mat
	stand.mesh = disc
	stand.position.y = -0.03
	viewport.add_child(stand)
	container.gui_input.connect(_on_view_input)
	box.add_child(UiKit.label("Модель сгенерирована ИИ (Hunyuan3D-2) по концепт-арту. Потяните мышью, чтобы повернуть.", 20, UiKit.MUTED))
	var back := UiKit.button("Назад")
	back.pressed.connect(close)
	box.add_child(back)
	back.grab_focus.call_deferred()


func _process(delta: float) -> void:
	if not _dragging:
		_pivot.rotation.y += delta * 0.4


func _on_view_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
	elif event is InputEventMouseMotion and _dragging:
		_pivot.rotation.y += event.relative.x * 0.01


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		close()


func close() -> void:
	closed.emit()
	queue_free()
