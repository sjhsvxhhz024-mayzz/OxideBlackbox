extends Node
## What the player chose in the menu, carried across scene changes.

const GAME_SCENE := "res://scenes/game.tscn"
const SERVERS := [
	{"name": "Сервер 1", "mode": "Оффлайн", "description": "Одиночная игра · карта 240×240 м · добыча ресурсов",
		"players": "1/1", "scene": GAME_SCENE},
]

var server: Dictionary = {}


func join(index: int) -> void:
	server = SERVERS[index]
	get_tree().change_scene_to_file("res://scenes/loading.tscn")
