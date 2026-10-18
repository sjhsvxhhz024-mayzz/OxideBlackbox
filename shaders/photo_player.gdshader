// Player relief from the concept art: soft matte edges, pulsing cyan device, shared cloud shadows.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_prepass_alpha;

#include "res://shaders/noise.gdshaderinc"

uniform sampler2D photo : source_color, filter_linear, repeat_disable;
uniform vec4 crop_in_plate = vec4(0.6177, 0.0859, 0.234, 0.8776); // x, y, width, height in plate UV
uniform float glow_strength = 2.2;
uniform float shadow_strength = 0.08;

void fragment() {
	vec4 c = texture(photo, UV);
	float cyan = smoothstep(0.06, 0.22, min(c.g, c.b) - c.r) * smoothstep(0.3, 0.55, c.g);
	float pulse = 0.6 + 0.4 * sin(TIME * 1.8);
	vec2 plate_uv = crop_in_plate.xy + UV * crop_in_plate.zw;
	float n = tz_fbm2(plate_uv * vec2(2.2, 5.0) + vec2(TIME * 0.012, TIME * 0.002), 4);
	vec3 col = c.rgb * (1.0 - shadow_strength * smoothstep(0.42, 0.72, n));
	ALBEDO = col + c.rgb * cyan * pulse * glow_strength;
	ALPHA = c.a;
}
