class_name Inventory
extends RefCounted
## Slots 0..4 are the hotbar, 5..28 the main inventory. Each slot is {} or {"id", "count"}.

signal changed

const HOTBAR := 5
const MAIN := 24

var slots: Array[Dictionary] = []


func _init() -> void:
	slots.resize(HOTBAR + MAIN)
	for i in slots.size():
		slots[i] = {}


## Returns how many items did not fit.
func add(id: String, count: int) -> int:
	var max_stack := Items.stack(id)
	for slot in slots:
		if count > 0 and slot.get("id") == id and slot.count < max_stack:
			var moved := mini(count, max_stack - slot.count)
			slot.count += moved
			count -= moved
	for i in slots.size():
		if count <= 0:
			break
		if slots[i].is_empty():
			var moved := mini(count, max_stack)
			slots[i] = {"id": id, "count": moved}
			count -= moved
	changed.emit()
	return count


func count_of(id: String) -> int:
	var total := 0
	for slot in slots:
		if slot.get("id") == id:
			total += slot.count
	return total


## Drag & drop: merge equal stacks, otherwise swap.
func move(from: int, to: int) -> void:
	if from == to or slots[from].is_empty():
		return
	var a := slots[from]
	var b := slots[to]
	if not b.is_empty() and b.id == a.id and b.count < Items.stack(a.id):
		var moved := mini(a.count, Items.stack(a.id) - b.count)
		b.count += moved
		a.count -= moved
		if a.count <= 0:
			slots[from] = {}
	else:
		slots[from] = b
		slots[to] = a
	changed.emit()
