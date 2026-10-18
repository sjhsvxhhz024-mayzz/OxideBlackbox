// Game terrain: vertex colours from the world generator plus world-space detail noise and bump.
shader_type spatial;
render_mode diffuse_burley;

#include "res://shaders/noise.gdshaderinc"

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float n1 = tz_fbm2(world_pos.xz * 0.35, 4);
	float n2 = tz_fbm2(world_pos.xz * 2.7, 3);
	float fade = 1.0 - smoothstep(25.0, 80.0, length(VERTEX));
	ALBEDO = COLOR.rgb * (0.78 + 0.44 * n1) * mix(1.0, 0.85 + 0.3 * n2, fade);
	ROUGHNESS = 0.95;
	SPECULAR = 0.3;
	NORMAL = tz_bump(NORMAL, VERTEX, (n1 * 0.12 + n2 * 0.03) * fade);
}
