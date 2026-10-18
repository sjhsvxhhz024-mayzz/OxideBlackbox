extends Node
## Main menu: intro animation, focus-follows-mouse buttons, server browser and settings overlays.

const ServerPanel := preload("res://scripts/ui/server_panel.gd")
const SettingsPanel := preload("res://scripts/ui/settings_panel.gd")
const CharacterPanel := preload("res://scripts/ui/character_panel.gd")

const TOAST_TIME := 2.4

var _toast_tween: Tween

@onready var _title: Label = $UI/Root/Panel/Title
@onready var _buttons: VBoxContainer = $UI/Root/Panel/Buttons
@onready var _version: Label = $UI/Root/Panel/Version
@onready var _toast: PanelContainer = $UI/Root/Toast
@onready var _toast_label: Label = $UI/Root/Toast/Label
@onready var _fade: ColorRect = $UI/Root/Fade


func _ready() -> void:
	_version.text = "v%s" % ProjectSettings.get_setting("application/config/version", "0.1")
	for node in _buttons.get_children():
		var button := node as Button
		button.mouse_entered.connect(button.grab_focus)
		button.focus_entered.connect(_on_button_focus.bind(button, true))
		button.focus_exited.connect(_on_button_focus.bind(button, false))
		button.resized.connect(func() -> void: button.pivot_offset = button.size * 0.5)
	$UI/Root/Panel/Buttons/Play.pressed.connect(_open.bind(ServerPanel))
	$UI/Root/Panel/Buttons/Character.pressed.connect(_open.bind(CharacterPanel))
	$UI/Root/Panel/Buttons/Settings.pressed.connect(_open.bind(SettingsPanel))
	$UI/Root/Panel/Buttons/Exit.pressed.connect(_on_exit_pressed)
	_play_intro()


func _open(script: GDScript) -> void:
	var panel: Control = script.new()
	panel.theme = load("res://ui/menu_theme.tres")
	$UI/Root.add_child(panel)
	$UI/Root.move_child(panel, $UI/Root/Fade.get_index())
	var focused := get_viewport().gui_get_focus_owner()
	panel.closed.connect(func() -> void: if is_instance_valid(focused): focused.grab_focus())


func _play_intro() -> void:
	_fade.color.a = 1.0
	_title.modulate.a = 0.0
	var tween := create_tween().set_parallel(true)
	tween.tween_property(_fade, "color:a", 0.0, 1.6).set_trans(Tween.TRANS_SINE)
	tween.tween_property(_title, "modulate:a", 1.0, 1.0).set_delay(0.35)
	var delay := 0.55
	for button in _buttons.get_children():
		button.modulate.a = 0.0
		tween.tween_property(button, "modulate:a", 1.0, 0.6).set_delay(delay)
		delay += 0.1
	($UI/Root/Panel/Buttons/Play as Button).grab_focus.call_deferred()


func _on_button_focus(button: Button, focused: bool) -> void:
	var tween := button.create_tween()
	tween.tween_property(button, "scale", Vector2.ONE * (1.03 if focused else 1.0), 0.15) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)


func _show_toast(text: String) -> void:
	_toast_label.text = text
	if _toast_tween:
		_toast_tween.kill()
	_toast_tween = create_tween()
	_toast_tween.tween_property(_toast, "modulate:a", 1.0, 0.25)
	_toast_tween.tween_interval(TOAST_TIME)
	_toast_tween.tween_property(_toast, "modulate:a", 0.0, 0.5)


func _on_exit_pressed() -> void:
	var tween := create_tween()
	tween.tween_property(_fade, "color:a", 1.0, 0.45)
	tween.tween_callback(get_tree().quit)
