extends Control
## In-game HUD: crosshair, 5-slot hotbar, health / hunger / thirst (top right), gather feed,
## target health bar, inventory window (Tab) and pause menu (Esc).

const SettingsPanel := preload("res://scripts/ui/settings_panel.gd")

var player: CharacterBody3D
var inventory: Inventory

var _hotbar: Array[SlotView] = []
var _grid: Array[SlotView] = []
var _bars := {}
var _feed: VBoxContainer
var _target_box: VBoxContainer
var _target_name: Label
var _target_bar: ProgressBar
var _hint: Label
var _message: Label
var _message_tween: Tween
var _fps: Label
var _inventory_window: Control
var _item_info: Label
var _pause: Control


func setup(p: CharacterBody3D, inv: Inventory) -> void:
	player = p
	inventory = inv
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_crosshair()
	_build_hotbar()
	_build_stats()
	_build_feed()
	_build_target()
	_build_inventory()
	_fps = UiKit.label("", 20, Color(0.7, 1.0, 0.7))
	_fps.position = Vector2(16, 12)
	add_child(_fps)
	inventory.changed.connect(_refresh_slots)
	player.stats_changed.connect(_refresh_stats)
	player.gathered.connect(_on_gathered)
	player.target_changed.connect(_on_target)
	player.message.connect(_show_message)
	_refresh_slots()
	_refresh_stats()
	_capture(true)


func _process(_delta: float) -> void:
	if player == null:
		return
	_fps.visible = bool(Settings.get_value("show_fps"))
	if _fps.visible:
		_fps.text = "FPS %d" % Engine.get_frames_per_second()
	for i in _hotbar.size():
		_hotbar[i].selected = i == player.selected


func _unhandled_input(event: InputEvent) -> void:
	if player == null:
		return
	if event.is_action_pressed("inventory") and _pause == null:
		get_viewport().set_input_as_handled()
		_toggle_inventory(not _inventory_window.visible)
	elif event.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		if _inventory_window.visible:
			_toggle_inventory(false)
		elif _pause == null:
			_open_pause()
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED \
			and _pause == null and not _inventory_window.visible:
		_capture(true)


func _capture(on: bool) -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if on else Input.MOUSE_MODE_VISIBLE
	player.controls_enabled = on


# --------------------------------------------------------------------------- widgets
func _build_crosshair() -> void:
	var dot := ColorRect.new()
	dot.color = Color(1, 1, 1, 0.85)
	dot.size = Vector2(4, 4)
	dot.set_anchors_preset(Control.PRESET_CENTER)
	dot.position = -dot.size / 2
	dot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(dot)
	_hint = UiKit.label("", 22, Color(1, 1, 1, 0.8))
	_hint.set_anchors_preset(Control.PRESET_CENTER)
	_hint.position = Vector2(-300, 30)
	_hint.size = Vector2(600, 30)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_hint)


func _build_hotbar() -> void:
	var bar := HBoxContainer.new()
	bar.add_theme_constant_override("separation", 8)
	bar.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	bar.grow_horizontal = Control.GROW_DIRECTION_BOTH
	bar.grow_vertical = Control.GROW_DIRECTION_BEGIN
	bar.offset_top = -112
	bar.offset_bottom = -26
	add_child(bar)
	for i in Inventory.HOTBAR:
		var slot := SlotView.new(i, inventory, 86, true)
		slot.gui_input.connect(func(e: InputEvent) -> void:
			if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				player.select_slot(i))
		bar.add_child(slot)
		_hotbar.append(slot)


func _build_stats() -> void:
	# Bottom-right survival bars (health / water / food), Rust-style: icon, value, coloured fill.
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 4)
	box.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	box.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	box.grow_vertical = Control.GROW_DIRECTION_BEGIN
	box.offset_left = -300
	box.offset_right = -22
	box.offset_top = -126
	box.offset_bottom = -28
	add_child(box)
	for spec in [["health", "✚", Color(0.53, 0.66, 0.24)], ["thirst", "💧", Color(0.24, 0.55, 0.78)],
			["hunger", "🍖", Color(0.78, 0.43, 0.16)]]:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 0)
		row.custom_minimum_size = Vector2(0, 30)
		box.add_child(row)
		var icon_bg := PanelContainer.new()
		var icon_style := StyleBoxFlat.new()
		icon_style.bg_color = Color(0.12, 0.12, 0.11, 0.78)
		icon_bg.add_theme_stylebox_override("panel", icon_style)
		icon_bg.custom_minimum_size = Vector2(30, 30)
		row.add_child(icon_bg)
		var icon := UiKit.label(spec[1], 16, Color(0.85, 0.83, 0.78))
		icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		icon_bg.add_child(icon)
		var bar := ProgressBar.new()
		bar.show_percentage = false
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.size_flags_vertical = Control.SIZE_FILL
		var fill := StyleBoxFlat.new()
		fill.bg_color = spec[2]
		bar.add_theme_stylebox_override("fill", fill)
		var bg := StyleBoxFlat.new()
		bg.bg_color = Color(0.1, 0.1, 0.1, 0.6)
		bar.add_theme_stylebox_override("background", bg)
		row.add_child(bar)
		var value := UiKit.label("100", 19, Color(1, 1, 1, 0.92))
		value.add_theme_constant_override("outline_size", 4)
		value.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
		value.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
		value.offset_left = 8
		value.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		bar.add_child(value)
		_bars[spec[0]] = [bar, value]


func _build_feed() -> void:
	_feed = VBoxContainer.new()
	_feed.alignment = BoxContainer.ALIGNMENT_END
	_feed.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_feed.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_feed.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_feed.offset_left = -320
	_feed.offset_right = -24
	_feed.offset_top = -420
	_feed.offset_bottom = -130
	_feed.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_feed)
	_message = UiKit.label("", 26)
	_message.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_message.position = Vector2(-400, 110)
	_message.size = Vector2(800, 40)
	_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_message.add_theme_color_override("font_outline_color", Color.BLACK)
	_message.add_theme_constant_override("outline_size", 6)
	_message.modulate.a = 0.0
	add_child(_message)


func _build_target() -> void:
	_target_box = VBoxContainer.new()
	_target_box.set_anchors_preset(Control.PRESET_CENTER)
	_target_box.position = Vector2(-120, 64)
	_target_box.size = Vector2(240, 40)
	_target_box.visible = false
	add_child(_target_box)
	_target_name = UiKit.label("", 20)
	_target_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_target_name.add_theme_color_override("font_outline_color", Color.BLACK)
	_target_name.add_theme_constant_override("outline_size", 5)
	_target_box.add_child(_target_name)
	_target_bar = ProgressBar.new()
	_target_bar.show_percentage = false
	_target_bar.custom_minimum_size = Vector2(240, 8)
	var fill := StyleBoxFlat.new()
	fill.bg_color = UiKit.ACCENT
	_target_bar.add_theme_stylebox_override("fill", fill)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.5)
	_target_bar.add_theme_stylebox_override("background", bg)
	_target_box.add_child(_target_bar)


func _build_inventory() -> void:
	_inventory_window = Control.new()
	_inventory_window.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_inventory_window.visible = false
	add_child(_inventory_window)
	move_child(_inventory_window, 0)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.5)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_inventory_window.add_child(dim)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", UiKit.panel_style(0.92))
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	panel.offset_top = -380
	panel.offset_bottom = 230
	_inventory_window.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	panel.add_child(box)
	box.add_child(UiKit.label("ИНВЕНТАРЬ", 40))
	var grid := GridContainer.new()
	grid.columns = 6
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	box.add_child(grid)
	for i in Inventory.MAIN:
		var slot := SlotView.new(Inventory.HOTBAR + i, inventory, 92, false)
		slot.hovered.connect(_on_hover)
		grid.add_child(slot)
		_grid.append(slot)
	_item_info = UiKit.label("Перетаскивайте предметы мышью. Нижний ряд — быстрый доступ (1–5).", 20, UiKit.MUTED)
	_item_info.autowrap_mode = TextServer.AUTOWRAP_WORD
	_item_info.custom_minimum_size = Vector2(600, 56)
	box.add_child(_item_info)
	for slot in _hotbar:
		slot.hovered.connect(_on_hover)


func _toggle_inventory(open: bool) -> void:
	_inventory_window.visible = open
	_capture(not open)


func _open_pause() -> void:
	_capture(false)
	get_tree().paused = true
	_pause = Control.new()
	_pause.process_mode = Node.PROCESS_MODE_ALWAYS
	_pause.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_pause)
	var parts := UiKit.overlay(_pause, 520.0)
	var box: VBoxContainer = parts[1]
	var title := UiKit.label("ПАУЗА", 52)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var resume := UiKit.button("Продолжить")
	resume.pressed.connect(_close_pause)
	box.add_child(resume)
	var settings := UiKit.button("Настройки")
	settings.pressed.connect(func() -> void:
		var panel: Control = SettingsPanel.new()
		panel.process_mode = Node.PROCESS_MODE_ALWAYS
		_pause.add_child(panel)
		panel.closed.connect(settings.grab_focus))
	box.add_child(settings)
	var leave := UiKit.button("Выйти в меню")
	leave.pressed.connect(func() -> void:
		get_tree().paused = false
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn"))
	box.add_child(leave)
	resume.grab_focus.call_deferred()
	_pause_keys()


func _pause_keys() -> void:
	# Esc closes the pause menu (settings panel handles its own Esc first).
	var catcher := Node.new()
	catcher.process_mode = Node.PROCESS_MODE_ALWAYS
	catcher.set_script(preload("res://scripts/ui/esc_catcher.gd"))
	catcher.pressed.connect(func() -> void:
		if _pause and _pause.get_child_count() <= 2:
			_close_pause())
	_pause.add_child(catcher)


func _close_pause() -> void:
	get_tree().paused = false
	_pause.queue_free()
	_pause = null
	_capture(true)


# --------------------------------------------------------------------------- updates
func _refresh_slots() -> void:
	for slot in _hotbar + _grid:
		slot.refresh()
	player.select_slot(player.selected)


func _refresh_stats() -> void:
	for key in ["health", "hunger", "thirst"]:
		var v: float = player.get(key)
		_bars[key][0].value = v
		_bars[key][1].text = str(ceili(v))


func _on_hover(index: int) -> void:
	var slot := inventory.slots[index]
	if slot.is_empty():
		_item_info.text = "Пустая ячейка"
	else:
		_item_info.text = "%s ×%d — %s" % [Items.display_name(slot.id), slot.count, Items.DB[slot.id].desc]


func _on_gathered(items: Array) -> void:
	for item: Array in items:
		var row := HBoxContainer.new()
		row.alignment = BoxContainer.ALIGNMENT_END
		row.add_theme_constant_override("separation", 8)
		var label := UiKit.label("+%d %s" % [item[1], Items.display_name(item[0])], 24)
		label.add_theme_color_override("font_outline_color", Color.BLACK)
		label.add_theme_constant_override("outline_size", 5)
		row.add_child(label)
		var icon := TextureRect.new()
		icon.texture = Items.icon(item[0])
		icon.custom_minimum_size = Vector2(36, 36)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		row.add_child(icon)
		_feed.add_child(row)
		var tween := row.create_tween()
		tween.tween_interval(2.2)
		tween.tween_property(row, "modulate:a", 0.0, 0.6)
		tween.tween_callback(row.queue_free)
		while _feed.get_child_count() > 6:
			_feed.get_child(0).free()


func _on_target(node: ResourceNode) -> void:
	_target_box.visible = node != null and node.hits_left > 0
	if node:
		_target_name.text = node.display_name()
		_target_bar.value = node.health() * 100.0
	_hint.text = ("ЛКМ — добывать" if player.held_item() == "rock" else "Нужен камень в руке") if _target_box.visible else ""


func _show_message(text: String) -> void:
	_message.text = text
	if _message_tween:
		_message_tween.kill()
	_message_tween = create_tween()
	_message.modulate.a = 1.0
	_message_tween.tween_interval(1.6)
	_message_tween.tween_property(_message, "modulate:a", 0.0, 0.5)
