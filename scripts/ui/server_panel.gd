extends Control
## Server browser overlay: one offline server for now.

signal closed

var _selected := -1
var _join: Button
var _cards: Array[Button] = []


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var parts := UiKit.overlay(self, 980.0)
	var box: VBoxContainer = parts[1]
	var title := UiKit.label("ВЫБОР СЕРВЕРА", 52)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var header := HBoxContainer.new()
	box.add_child(header)
	for column in [["Название", 560], ["Режим", 170], ["Игроки", 120]]:
		var l := UiKit.label(column[0], 22, UiKit.MUTED)
		l.custom_minimum_size = Vector2(column[1], 0)
		header.add_child(l)
	for i in Session.SERVERS.size():
		box.add_child(_card(i, Session.SERVERS[i]))
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 160)
	box.add_child(spacer)
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 16)
	box.add_child(buttons)
	var back := UiKit.button("Назад")
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	back.pressed.connect(close)
	buttons.add_child(back)
	_join = UiKit.button("Подключиться")
	_join.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_join.disabled = true
	_join.pressed.connect(_on_join)
	buttons.add_child(_join)
	_cards[0].grab_focus.call_deferred()


func _card(index: int, server: Dictionary) -> Button:
	var card := Button.new()
	card.toggle_mode = true
	card.custom_minimum_size = Vector2(0, 96)
	card.alignment = HORIZONTAL_ALIGNMENT_LEFT
	var row := HBoxContainer.new()
	row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	row.offset_left = 24
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(row)
	var names := VBoxContainer.new()
	names.custom_minimum_size = Vector2(536, 0)
	names.alignment = BoxContainer.ALIGNMENT_CENTER
	names.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_child(UiKit.label(server.name, 32))
	names.add_child(UiKit.label(server.description, 20, UiKit.MUTED))
	row.add_child(names)
	var mode := UiKit.label("● " + server.mode, 26, Color(0.55, 0.85, 0.55))
	mode.custom_minimum_size = Vector2(170, 0)
	mode.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	mode.size_flags_vertical = Control.SIZE_FILL
	row.add_child(mode)
	var players := UiKit.label(server.players, 26)
	players.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	players.size_flags_vertical = Control.SIZE_FILL
	row.add_child(players)
	for child in row.get_children():
		child.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.toggled.connect(func(on: bool) -> void: if on: _select(index))
	card.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.double_click:
			_select(index)
			_on_join())
	_cards.append(card)
	return card


func _select(index: int) -> void:
	_selected = index
	for i in _cards.size():
		_cards[i].set_pressed_no_signal(i == index)
	_join.disabled = false


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		close()


func _on_join() -> void:
	if _selected >= 0:
		Session.join(_selected)


func close() -> void:
	closed.emit()
	queue_free()
