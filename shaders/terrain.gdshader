// Ground and valley terrain: Blender vertex colours plus distance-faded procedural detail.
shader_type spatial;
render_mode diffuse_burley;

#include "res://shaders/noise.gdshaderinc"

uniform float detail_scale = 0.9;
uniform float macro_scale = 0.08;
uniform float detail_strength : hint_range(0.0, 1.0) = 0.35;
uniform float bump_strength = 0.05;
uniform float detail_fade = 40.0;
uniform float brightness = 1.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float dist = length(VERTEX);
	float fade = 1.0 - smoothstep(detail_fade * 0.4, detail_fade, dist);
	float macro = tz_fbm2(world_pos.xz * macro_scale, 3);
	float n1 = tz_fbm2(world_pos.xz * detail_scale, 4);
	float n2 = tz_fbm2(world_pos.xz * detail_scale * 7.0, 3);
	vec3 col = COLOR.rgb * (0.8 + 0.4 * macro);
	col *= mix(1.0, (1.0 - detail_strength + 2.0 * detail_strength * n1) * (0.85 + 0.3 * n2), fade);
	ALBEDO = col * brightness;
	ROUGHNESS = 0.96;
	SPECULAR = 0.3;
	if (bump_strength > 0.0) {
		NORMAL = tz_bump(NORMAL, VERTEX, (n1 + 0.5 * n2) * bump_strength * fade);
	}
}
