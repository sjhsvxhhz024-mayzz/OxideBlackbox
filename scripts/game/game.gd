extends Node3D
## Offline server session: wires the world, the player, the inventory and the HUD.

@onready var _world: Node3D = $World
@onready var _player: CharacterBody3D = $Player
@onready var _hud: Control = $HUD/Root


func _ready() -> void:
	var inventory := Inventory.new()
	inventory.add("rock", 1)
	_player.inventory = inventory
	_player.global_position = _world.spawn_point()
	_player.rotation.y = 0.0
	_hud.setup(_player, inventory)
	_player.select_slot(0)
