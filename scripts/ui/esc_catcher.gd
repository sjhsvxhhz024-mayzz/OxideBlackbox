extends Node
## Emits `pressed` for Esc while the tree is paused (pause menu helper).

signal pressed


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		pressed.emit()
