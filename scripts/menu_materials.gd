extends RefCounted
## Replacement materials for the plain Blender materials in the .glb files, keyed by material name.

const FABRIC := preload("res://shaders/fabric.gdshader")
const TERRAIN := preload("res://shaders/terrain.gdshader")
const ROCK := preload("res://shaders/rock.gdshader")
const GRASS := preload("res://shaders/grass.gdshader")
const PINE := preload("res://shaders/pine.gdshader")
const VERTEX_COLOR := preload("res://shaders/vertex_color.gdshader")
const WATER := preload("res://shaders/water.gdshader")

## Animated by the menu world: red tower beacon and the cyan hip device.
var beacon := StandardMaterial3D.new()
var glow := StandardMaterial3D.new()


func _init() -> void:
	beacon.albedo_color = Color(0.35, 0.03, 0.02)
	beacon.emission_enabled = true
	beacon.emission = Color(1.0, 0.16, 0.08)
	beacon.emission_energy_multiplier = 8.0
	glow.albedo_color = Color(0.03, 0.12, 0.12)
	glow.emission_enabled = true
	glow.emission = Color(0.25, 0.97, 0.9)
	glow.emission_energy_multiplier = 4.0


func for_environment() -> Dictionary:
	var glass := standard(Color(0.09, 0.11, 0.13), 0.15, 0.2)
	glass.cull_mode = BaseMaterial3D.CULL_DISABLED
	var lit := standard(Color(1.0, 0.8, 0.55), 0.6)
	lit.cull_mode = BaseMaterial3D.CULL_DISABLED
	lit.emission_enabled = true
	lit.emission = Color(1.0, 0.72, 0.42)
	lit.emission_energy_multiplier = 2.5
	return {
		"Ground": shader(TERRAIN, {"detail_scale": 0.9, "bump_strength": 0.05, "detail_fade": 40.0}),
		"Terrain": shader(TERRAIN, {"detail_scale": 0.06, "macro_scale": 0.004, "detail_strength": 0.25,
				"bump_strength": 0.0, "detail_fade": 2500.0}),
		"Grass": shader(GRASS),
		"Rock": shader(ROCK),
		"PineNeedles": shader(PINE),
		"Bark": shader(PINE, {"is_bark": true, "roughness": 0.95}),
		"Brick": shader(VERTEX_COLOR, {"roughness": 0.92, "noise_strength": 0.22}),
		"Concrete": shader(VERTEX_COLOR, {"roughness": 0.9, "noise_strength": 0.18}),
		"Roof": shader(VERTEX_COLOR, {"roughness": 0.75, "noise_strength": 0.15}),
		"SteelPaint": shader(VERTEX_COLOR, {"roughness": 0.6, "metallic": 0.25, "noise_strength": 0.12}),
		"Glass": glass,
		"WindowLit": lit,
		"Beacon": beacon,
		"Water": shader(WATER),
	}


func for_player() -> Dictionary:
	var skin := standard(Color("#c4906f"), 0.55)
	skin.vertex_color_use_as_albedo = true
	skin.subsurf_scatter_enabled = true
	skin.subsurf_scatter_strength = 0.3
	skin.subsurf_scatter_skin_mode = true
	var visor := standard(Color(0.02, 0.022, 0.025), 0.06, 0.5)
	visor.clearcoat_enabled = true
	return {
		"Jacket": fabric(Color("#36393c"), 0.9, {"dirt_amount": 0.22}),
		"Pants": fabric(Color("#393c3f"), 0.92, {"dirt_amount": 0.45}),
		"Vest": fabric(Color("#26292c"), 0.85, {"grain_scale": 90.0, "dirt_amount": 0.2}),
		"Plate": fabric(Color("#3f4245"), 0.6, {"grain_scale": 30.0, "wear": 0.4, "dirt_amount": 0.15}),
		"Webbing": fabric(Color("#2c2e30"), 0.9, {"grain_scale": 110.0, "grain_strength": 0.22}),
		"Boots": fabric(Color("#2b2521"), 0.5, {"grain_scale": 40.0, "dirt_amount": 0.55, "wear": 0.25}),
		"Sole": fabric(Color("#151515"), 0.9, {"dirt_amount": 0.4}),
		"Skin": skin,
		"Hair": fabric(Color("#211a14"), 0.6, {"grain_scale": 180.0, "grain_strength": 0.3, "dirt_amount": 0.0}),
		"EyeWhite": standard(Color("#cfc8bd"), 0.2),
		"Iris": standard(Color("#2b1d13"), 0.15),
		"Helmet": fabric(Color("#5a5e4b"), 0.45, {"grain_scale": 25.0, "wear": 0.35, "dirt_amount": 0.15}),
		"Visor": visor,
		"Metal": standard(Color(0.5, 0.52, 0.53), 0.35, 0.85),
		"Glow": glow,
		"Patch": fabric(Color("#8a7748"), 0.85, {"dirt_amount": 0.1}),
	}


static func shader(source: Shader, params: Dictionary = {}) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = source
	for key: String in params:
		material.set_shader_parameter(key, params[key])
	return material


static func fabric(color: Color, roughness: float, extra: Dictionary = {}) -> ShaderMaterial:
	var params := {"albedo": color, "roughness": roughness}
	params.merge(extra, true)
	return shader(FABRIC, params)


static func standard(color: Color, roughness: float, metallic: float = 0.0) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material
