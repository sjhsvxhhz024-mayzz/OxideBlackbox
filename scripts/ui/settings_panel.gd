extends Control
## Settings overlay (menu and pause menu): controls, graphics and sound, applied instantly.

signal closed

var _rows := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var parts := UiKit.overlay(self, 980.0)
	var box: VBoxContainer = parts[1]
	var title := UiKit.label("НАСТРОЙКИ", 52)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var tabs := TabContainer.new()
	tabs.custom_minimum_size = Vector2(0, 520)
	tabs.add_theme_font_size_override("font_size", 26)
	box.add_child(tabs)

	var controls := _page(tabs, "Управление")
	_slider(controls, "mouse_sensitivity", "Чувствительность мыши", 0.02, 1.0, 0.01, func(v: float) -> String: return "%.2f" % v)
	_check(controls, "invert_y", "Инверсия оси Y")
	_slider(controls, "fov", "Поле зрения (FOV)", 60.0, 110.0, 1.0, func(v: float) -> String: return "%d°" % v)

	var graphics := _page(tabs, "Графика")
	_option(graphics, "quality", "Качество графики", Settings.QUALITY_NAMES)
	_slider(graphics, "render_scale", "Разрешение рендера", 50.0, 100.0, 5.0, func(v: float) -> String: return "%d%%" % v)
	_check(graphics, "fullscreen", "Полноэкранный режим")
	_check(graphics, "vsync", "Вертикальная синхронизация")
	_option(graphics, "fps_limit", "Ограничение FPS", ["30", "60", "120", "144", "Без ограничения"])
	_check(graphics, "show_fps", "Показывать FPS")

	var sound := _page(tabs, "Звук")
	_slider(sound, "master_volume", "Общая громкость", 0.0, 100.0, 1.0, func(v: float) -> String: return "%d%%" % v)

	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 16)
	box.add_child(buttons)
	var reset := UiKit.button("Сбросить")
	reset.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	reset.pressed.connect(func() -> void:
		Settings.reset()
		_refresh())
	buttons.add_child(reset)
	var back := UiKit.button("Назад")
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	back.pressed.connect(close)
	buttons.add_child(back)
	back.grab_focus.call_deferred()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		close()


func close() -> void:
	closed.emit()
	queue_free()


func _page(tabs: TabContainer, title: String) -> VBoxContainer:
	var margin := MarginContainer.new()
	margin.name = title
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 22)
	tabs.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	margin.add_child(box)
	return box


func _row(parent: VBoxContainer, text: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	parent.add_child(row)
	var l := UiKit.label(text, 26)
	l.custom_minimum_size = Vector2(380, 0)
	row.add_child(l)
	return row


func _slider(parent: VBoxContainer, key: String, text: String, lo: float, hi: float, step: float, fmt: Callable) -> void:
	var row := _row(parent, text)
	var slider := HSlider.new()
	slider.min_value = lo
	slider.max_value = hi
	slider.step = step
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(slider)
	var value := UiKit.label("", 26, UiKit.ACCENT)
	value.custom_minimum_size = Vector2(110, 0)
	value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(value)
	slider.value_changed.connect(func(v: float) -> void:
		value.text = fmt.call(v)
		Settings.set_value(key, v))
	_rows[key] = func() -> void:
		slider.set_value_no_signal(float(Settings.get_value(key)))
		value.text = fmt.call(slider.value)
	_rows[key].call()


func _check(parent: VBoxContainer, key: String, text: String) -> void:
	var row := _row(parent, text)
	var box := CheckButton.new()
	row.add_child(box)
	box.toggled.connect(func(on: bool) -> void: Settings.set_value(key, on))
	_rows[key] = func() -> void: box.set_pressed_no_signal(bool(Settings.get_value(key)))
	_rows[key].call()


func _option(parent: VBoxContainer, key: String, text: String, items: Array) -> void:
	var row := _row(parent, text)
	var option := OptionButton.new()
	option.add_theme_font_size_override("font_size", 24)
	option.custom_minimum_size = Vector2(300, 48)
	for item: String in items:
		option.add_item(item)
	option.get_popup().add_theme_font_size_override("font_size", 24)
	row.add_child(option)
	option.item_selected.connect(func(i: int) -> void: Settings.set_value(key, i))
	_rows[key] = func() -> void: option.select(int(Settings.get_value(key)))
	_rows[key].call()


func _refresh() -> void:
	for key: String in _rows:
		_rows[key].call()
