class_name ResourceNode
extends StaticBody3D
## Tree or ore node: each hit with the rock yields items, shakes the model and spits chips.
## Depleted nodes fall (trees) or crumble (ores) and respawn later.

signal depleted

const KINDS := {
	"tree": {"name": "Дерево", "hits": 8, "yield": [["wood", 12]], "chips": Color(0.55, 0.4, 0.25)},
	"stone": {"name": "Каменная глыба", "hits": 10, "yield": [["stones", 15]], "chips": Color(0.6, 0.6, 0.58)},
	"sulfur": {"name": "Серная глыба", "hits": 10, "yield": [["sulfur_ore", 8], ["stones", 3]], "chips": Color(0.85, 0.78, 0.25)},
	"metal": {"name": "Железная глыба", "hits": 10, "yield": [["metal_ore", 6], ["stones", 3]], "chips": Color(0.55, 0.35, 0.25)},
}
const RESPAWN_TIME := 120.0

@export var kind := "stone"

var hits_left := 0
var model: Node3D
var _base_scale := Vector3.ONE
var _chips: CPUParticles3D


func setup(kind_name: String, scene: PackedScene, shape: Shape3D, shape_offset: Vector3, model_scale: float) -> void:
	kind = kind_name
	add_to_group("resource")
	model = scene.instantiate()
	model.scale = Vector3.ONE * model_scale
	_base_scale = model.scale
	add_child(model)
	var collision := CollisionShape3D.new()
	collision.shape = shape
	collision.position = shape_offset
	add_child(collision)
	_chips = CPUParticles3D.new()
	_chips.emitting = false
	_chips.one_shot = true
	_chips.amount = 14
	_chips.lifetime = 0.8
	_chips.explosiveness = 1.0
	_chips.direction = Vector3(0, 1, 0)
	_chips.spread = 60.0
	_chips.initial_velocity_min = 2.0
	_chips.initial_velocity_max = 4.5
	_chips.scale_amount_min = 0.04
	_chips.scale_amount_max = 0.09
	var mesh := BoxMesh.new()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = KINDS[kind].chips
	mesh.material = mat
	_chips.mesh = mesh
	add_child(_chips)
	hits_left = KINDS[kind].hits


func display_name() -> String:
	return KINDS[kind].name


func health() -> float:
	return float(hits_left) / KINDS[kind].hits


## Returns [[item_id, count], ...]; empty when already depleted.
func gather(hit_point: Vector3) -> Array:
	if hits_left <= 0:
		return []
	hits_left -= 1
	_chips.global_position = hit_point
	_chips.restart()
	var tween := create_tween()
	if kind == "tree":
		var axis := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized()
		tween.tween_property(model, "quaternion", Quaternion(axis, 0.03), 0.06)
		tween.tween_property(model, "quaternion", Quaternion.IDENTITY, 0.35).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	else:
		tween.tween_property(model, "scale", _base_scale * 0.95, 0.05)
		tween.tween_property(model, "scale", _base_scale * (0.6 + 0.4 * health()), 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	if hits_left <= 0:
		_deplete()
	return KINDS[kind].yield.duplicate(true)


func _deplete() -> void:
	depleted.emit()
	collision_layer = 0
	var tween := create_tween()
	if kind == "tree":
		var axis := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized()
		tween.tween_property(model, "quaternion", Quaternion(axis, PI * 0.48), 1.6).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		tween.tween_interval(1.5)
	tween.tween_property(model, "scale", Vector3.ZERO, 0.6)
	tween.tween_callback(func() -> void: model.visible = false)
	tween.tween_interval(RESPAWN_TIME)
	tween.tween_callback(_respawn)


func _respawn() -> void:
	hits_left = KINDS[kind].hits
	model.quaternion = Quaternion.IDENTITY
	model.visible = true
	collision_layer = 1
	var tween := create_tween()
	tween.tween_property(model, "scale", _base_scale, 1.0).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
