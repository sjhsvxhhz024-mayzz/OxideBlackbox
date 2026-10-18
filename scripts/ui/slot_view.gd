class_name SlotView
extends PanelContainer
## One inventory / hotbar cell; supports drag & drop between any two cells.

signal hovered(index: int)

var index := 0
var inventory: Inventory
var selected := false:
	set(value):
		selected = value
		_restyle()

var _icon := TextureRect.new()
var _count := Label.new()
var _number := Label.new()


func _init(slot_index: int, inv: Inventory, size_px: float, show_number: bool) -> void:
	index = slot_index
	inventory = inv
	custom_minimum_size = Vector2(size_px, size_px)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_icon)
	_count.add_theme_font_size_override("font_size", 20)
	_count.add_theme_color_override("font_outline_color", Color.BLACK)
	_count.add_theme_constant_override("outline_size", 6)
	_count.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_count.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_count.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_count)
	if show_number:
		_number.text = str(index + 1)
		_number.add_theme_font_size_override("font_size", 16)
		_number.add_theme_color_override("font_color", Color(1, 1, 1, 0.5))
		_number.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_number)
	mouse_entered.connect(func() -> void: hovered.emit(index))
	_restyle()
	refresh()


func refresh() -> void:
	var slot := inventory.slots[index]
	_icon.texture = Items.icon(slot.id) if not slot.is_empty() else null
	_count.text = str(slot.count) if not slot.is_empty() and slot.count > 1 else ""


func _restyle() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.17, 0.42, 0.66, 0.75) if selected else Color(0.2, 0.2, 0.19, 0.55)
	style.border_color = Color(0.45, 0.7, 0.95, 0.9) if selected else Color(1, 1, 1, 0.05)
	style.set_border_width_all(2 if selected else 1)
	style.set_corner_radius_all(0)
	style.set_content_margin_all(6)
	add_theme_stylebox_override("panel", style)


func _get_drag_data(_at: Vector2) -> Variant:
	if inventory.slots[index].is_empty():
		return null
	var preview := TextureRect.new()
	preview.texture = _icon.texture
	preview.size = custom_minimum_size * 0.8
	preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	preview.modulate.a = 0.85
	set_drag_preview(preview)
	return {"slot": index}


func _can_drop_data(_at: Vector2, data: Variant) -> bool:
	return data is Dictionary and data.has("slot")


func _drop_data(_at: Vector2, data: Variant) -> void:
	inventory.move(data.slot, index)
