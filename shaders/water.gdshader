// Sea surface: slow drifting waves that reflect the sky.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

#include "res://shaders/noise.gdshaderinc"

uniform vec3 water_color : source_color = vec3(0.07, 0.1, 0.12);
uniform float wave_scale = 0.018;
uniform float wave_speed = 0.025;
uniform float wave_bump = 2.5;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float t = TIME * wave_speed;
	vec2 p = world_pos.xz;
	float h = tz_fbm2(p * wave_scale + vec2(t, t * 0.6), 4);
	h += 0.6 * tz_fbm2(p * wave_scale * 3.3 - vec2(t * 1.4, -t * 0.9), 3);
	float dist = length(VERTEX);
	float fade = 1.0 - smoothstep(1500.0, 6000.0, dist);
	NORMAL = tz_bump(NORMAL, VERTEX, h * wave_bump * fade);
	ALBEDO = water_color;
	ROUGHNESS = 0.07;
	SPECULAR = 0.55;
}
