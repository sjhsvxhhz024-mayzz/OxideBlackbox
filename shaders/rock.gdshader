// Boulders: Blender moss/AO vertex colours with world-space stone grain and bump.
shader_type spatial;
render_mode diffuse_burley;

#include "res://shaders/noise.gdshaderinc"

uniform float grain_scale = 2.4;
uniform float bump_strength = 0.06;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float n = tz_fbm3(world_pos * grain_scale, 4);
	float fine = tz_fbm3(world_pos * grain_scale * 4.0, 3);
	float cracks = smoothstep(0.42, 0.5, abs(tz_noise3(world_pos * grain_scale * 1.7) - 0.5) * 2.0);
	vec3 col = COLOR.rgb * (0.72 + 0.56 * n) * (0.88 + 0.24 * fine);
	col *= mix(0.65, 1.0, cracks);
	ALBEDO = col;
	ROUGHNESS = 0.9;
	SPECULAR = 0.35;
	NORMAL = tz_bump(NORMAL, VERTEX, (n + fine * 0.35 - (1.0 - cracks) * 0.4) * bump_strength);
}
