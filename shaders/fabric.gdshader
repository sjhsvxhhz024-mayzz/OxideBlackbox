// Character cloth, armour and leather: vertex AO from Blender, grain, grime and worn edges.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

#include "res://shaders/noise.gdshaderinc"

uniform vec3 albedo : source_color = vec3(0.2);
uniform float roughness : hint_range(0.0, 1.0) = 0.88;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float grain_scale = 70.0;
uniform float grain_strength : hint_range(0.0, 1.0) = 0.16;
uniform float dirt_amount : hint_range(0.0, 1.0) = 0.25;
uniform vec3 dirt_color : source_color = vec3(0.3, 0.26, 0.2);
uniform float wear : hint_range(0.0, 1.0) = 0.0;
uniform float bump_strength = 0.0012;

varying vec3 obj_pos;

void vertex() {
	obj_pos = VERTEX;
}

void fragment() {
	float grain = tz_fbm3(obj_pos * grain_scale, 3);
	float blotch = tz_fbm3(obj_pos * 6.0 + 3.1, 3);
	vec3 col = albedo * COLOR.rgb;
	float low = 1.0 - smoothstep(0.05, 0.8, obj_pos.y);
	float grime = clamp(dirt_amount * (smoothstep(0.5, 0.8, blotch) + low * 0.9), 0.0, 1.0);
	col = mix(col, dirt_color * mix(0.5, 1.0, COLOR.r), grime * 0.6);
	col *= 1.0 - grain_strength + 2.0 * grain_strength * grain;
	float scratches = smoothstep(0.66, 0.78, tz_fbm3(obj_pos * 28.0 + 7.7, 2));
	col = mix(col, col * 1.7 + vec3(0.025), wear * scratches);
	ALBEDO = col;
	ROUGHNESS = clamp(roughness + (grain - 0.5) * 0.12 - wear * scratches * 0.2, 0.0, 1.0);
	METALLIC = metallic;
	NORMAL = tz_bump(NORMAL, VERTEX, (grain + blotch * 0.6) * bump_strength);
}
