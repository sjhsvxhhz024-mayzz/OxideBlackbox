extends Node
## Player settings: saved to user://settings.cfg and applied on change. Also registers input actions.

signal changed

const PATH := "user://settings.cfg"
const QUALITY_NAMES := ["Низкое", "Среднее", "Высокое", "Ультра"]
const FPS_LIMITS := [30, 60, 120, 144, 0]
const DEFAULTS := {
	"mouse_sensitivity": 0.25,
	"invert_y": false,
	"fov": 80.0,
	"quality": 2,
	"render_scale": 100.0,
	"fullscreen": false,
	"vsync": true,
	"fps_limit": 1,
	"show_fps": false,
	"master_volume": 80.0,
}

var values := DEFAULTS.duplicate()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_register_inputs()
	var file := ConfigFile.new()
	if file.load(PATH) == OK:
		for key: String in DEFAULTS:
			values[key] = file.get_value("settings", key, DEFAULTS[key])
	apply()


func get_value(key: String) -> Variant:
	return values[key]


func set_value(key: String, value: Variant) -> void:
	if values[key] == value:
		return
	values[key] = value
	apply()
	save()


func reset() -> void:
	values = DEFAULTS.duplicate()
	apply()
	save()


func save() -> void:
	var file := ConfigFile.new()
	for key: String in values:
		file.set_value("settings", key, values[key])
	file.save(PATH)


## 0 low .. 3 ultra
func quality() -> int:
	return int(values.quality)


func apply() -> void:
	var window := get_window()
	if not DisplayServer.get_name() == "headless":
		var fullscreen: bool = values.fullscreen
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != mode and not (mode == DisplayServer.WINDOW_MODE_WINDOWED
				and DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MAXIMIZED):
			DisplayServer.window_set_mode(mode)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if values.vsync else DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = FPS_LIMITS[clampi(int(values.fps_limit), 0, FPS_LIMITS.size() - 1)]
	var q := quality()
	window.scaling_3d_scale = clampf(float(values.render_scale) / 100.0, 0.5, 1.0)
	window.msaa_3d = [Viewport.MSAA_DISABLED, Viewport.MSAA_2X, Viewport.MSAA_4X, Viewport.MSAA_8X][q]
	window.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if q == 0 else Viewport.SCREEN_SPACE_AA_DISABLED
	RenderingServer.directional_shadow_atlas_set_size([1024, 2048, 4096, 8192][q], true)
	RenderingServer.directional_soft_shadow_filter_set_quality([0, 2, 3, 4][q])
	var volume := float(values.master_volume) / 100.0
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(volume, 0.0001)))
	AudioServer.set_bus_mute(0, volume <= 0.001)
	changed.emit()


func _register_inputs() -> void:
	var keys := {
		"move_forward": KEY_W, "move_back": KEY_S, "move_left": KEY_A, "move_right": KEY_D,
		"jump": KEY_SPACE, "sprint": KEY_SHIFT, "inventory": KEY_TAB, "pause": KEY_ESCAPE,
		"slot_1": KEY_1, "slot_2": KEY_2, "slot_3": KEY_3, "slot_4": KEY_4, "slot_5": KEY_5, "toggle_view": KEY_V,
	}
	for action: String in keys:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		var event := InputEventKey.new()
		event.physical_keycode = keys[action]
		InputMap.action_add_event(action, event)
	if not InputMap.has_action("attack"):
		InputMap.add_action("attack")
		var click := InputEventMouseButton.new()
		click.button_index = MOUSE_BUTTON_LEFT
		InputMap.action_add_event("attack", click)
