class_name Items
extends RefCounted
## Item database.

const DB := {
	"rock": {"name": "Камень", "desc": "Простейший инструмент. Добывает дерево, камни, серу и железо.", "stack": 1, "tool": true},
	"wood": {"name": "Дерево", "desc": "Добывается из деревьев.", "stack": 1000},
	"stones": {"name": "Камни", "desc": "Добываются из каменных глыб.", "stack": 1000},
	"sulfur_ore": {"name": "Серная руда", "desc": "Жёлтые глыбы. Пригодится позже.", "stack": 1000},
	"metal_ore": {"name": "Железная руда", "desc": "Рыжие глыбы с металлическими вкраплениями.", "stack": 1000},
}
const ICONS := {
	"rock": "res://assets/icons/rock.png", "wood": "res://assets/icons/wood.png", "stones": "res://assets/icons/stone.png",
	"sulfur_ore": "res://assets/icons/sulfur_ore.png", "metal_ore": "res://assets/icons/metal_ore.png",
}


static func display_name(id: String) -> String:
	return DB[id].name


static func icon(id: String) -> Texture2D:
	return load(ICONS[id])


static func stack(id: String) -> int:
	return DB[id].stack
