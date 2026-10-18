// Buildings, cranes and ships: Blender vertex colours with soft weathering noise.
shader_type spatial;
render_mode cull_disabled, diffuse_burley;

#include "res://shaders/noise.gdshaderinc"

uniform vec3 tint : source_color = vec3(1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.85;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float noise_scale = 0.15;
uniform float noise_strength : hint_range(0.0, 1.0) = 0.2;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float n = tz_fbm3(world_pos * noise_scale, 3);
	float streaks = tz_noise2(vec2(world_pos.x * 0.8 + world_pos.z * 0.8, world_pos.y * 0.05));
	ALBEDO = COLOR.rgb * tint * (1.0 - noise_strength + 2.0 * noise_strength * n) * (0.9 + 0.1 * streaks);
	ROUGHNESS = roughness;
	METALLIC = metallic;
}
