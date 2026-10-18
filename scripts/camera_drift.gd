extends Camera3D
## Slow handheld-style drift plus a gentle mouse parallax for the menu camera.

@export var drift := Vector2(0.05, 0.03)
@export var parallax := Vector2(0.08, 0.04)
@export var parallax_rotation := Vector2(0.006, 0.004)

var _base: Transform3D
var _mouse := Vector2.ZERO
var _mouse_seen := false
var _time := 0.0


func _ready() -> void:
	_base = transform


func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse_seen = true


func _process(delta: float) -> void:
	_time += delta
	var target := Vector2.ZERO
	if _mouse_seen:
		var viewport := get_viewport()
		var size := viewport.get_visible_rect().size
		target = (viewport.get_mouse_position() / size * 2.0 - Vector2.ONE).clamp(-Vector2.ONE, Vector2.ONE)
	_mouse = _mouse.lerp(target, 1.0 - exp(-delta * 2.0))
	var offset := Vector3(
		sin(_time * 0.21) * drift.x + _mouse.x * parallax.x,
		sin(_time * 0.27 + 1.3) * drift.y - _mouse.y * parallax.y,
		0.0)
	transform = _base.translated_local(offset)
	rotate_object_local(Vector3.UP, -_mouse.x * parallax_rotation.x)
	rotate_object_local(Vector3.RIGHT, -_mouse.y * parallax_rotation.y)
