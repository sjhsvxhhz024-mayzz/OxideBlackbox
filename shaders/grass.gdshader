// Grass blades (MultiMesh): UV.y is the height along the blade, sway grows towards the tip.
shader_type spatial;
render_mode cull_disabled, diffuse_burley;

uniform float wind_strength = 0.12;
uniform float wind_speed = 1.6;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float h = 1.0 - UV.y;
	float wave = sin(TIME * wind_speed + wp.x * 0.6 + wp.z * 0.3) + 0.4 * sin(TIME * wind_speed * 2.7 + wp.x * 1.7 - wp.z * 1.3);
	float gust = 0.6 + 0.4 * sin(TIME * 0.4 + wp.x * 0.05);
	VERTEX.x += wave * gust * wind_strength * h * h;
	VERTEX.z += wave * gust * wind_strength * 0.4 * h * h;
}

void fragment() {
	ALBEDO = COLOR.rgb * mix(0.45, 1.0, 1.0 - UV.y);
	ROUGHNESS = 0.75;
	SPECULAR = 0.25;
	BACKLIGHT = COLOR.rgb * 0.5;
}
