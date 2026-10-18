extends Control
## Loading screen: streams the game scene in the background and shows progress and tips.

const TIPS := [
	"Держите камень в руке и бейте по деревьям и рудам — так добываются первые ресурсы.",
	"Серная и железная руда встречаются реже обычного камня — ищите жёлтые и рыжие глыбы.",
	"Следите за голодом и жаждой в правом верхнем углу.",
	"Tab — инвентарь. Перетаскивайте предметы между ячейками мышью.",
	"Клавиши 1–5 и колесо мыши выбирают ячейку быстрого доступа.",
]
const STAGES := ["Подключение к серверу…", "Загрузка мира…", "Генерация местности…", "Почти готово…"]

var _path: String
var _shown := 0.0
var _elapsed := 0.0

@onready var _bar: ProgressBar = %Bar
@onready var _status: Label = %Status


func _ready() -> void:
	var server: Dictionary = Session.server if not Session.server.is_empty() else Session.SERVERS[0]
	_path = server.scene
	%Server.text = "%s · %s" % [server.name, server.mode]
	%Tip.text = TIPS[randi() % TIPS.size()]
	ResourceLoader.load_threaded_request(_path)


func _process(delta: float) -> void:
	_elapsed += delta
	var progress := []
	var state := ResourceLoader.load_threaded_get_status(_path, progress)
	var target := minf(float(progress[0]) if progress.size() > 0 else 0.0, _elapsed / 2.0)
	if state == ResourceLoader.THREAD_LOAD_FAILED or state == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
		_status.text = "Не удалось загрузить мир"
		set_process(false)
		return
	_shown = move_toward(_shown, target, delta * 0.9)
	_bar.value = _shown * 100.0
	_status.text = STAGES[mini(int(_shown * STAGES.size()), STAGES.size() - 1)]
	if state == ResourceLoader.THREAD_LOAD_LOADED and _shown >= 0.999:
		set_process(false)
		get_tree().change_scene_to_packed(ResourceLoader.load_threaded_get(_path))
