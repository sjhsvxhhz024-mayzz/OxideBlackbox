// Pine needles and bark: sway grows with height, phase varies per tree.
shader_type spatial;
render_mode diffuse_burley;

uniform float tree_height = 18.0;
uniform float sway_strength = 0.35;
uniform float sway_speed = 0.8;
uniform vec2 wind_direction = vec2(1.0, 0.35);
uniform vec3 tint : source_color = vec3(1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.85;
uniform bool is_bark = false;

void vertex() {
	vec3 origin = NODE_POSITION_WORLD;
	float h = max(VERTEX.y, 0.0) / tree_height;
	float phase = dot(origin.xz, vec2(0.11, 0.07));
	float gust = sin(TIME * sway_speed + phase) * 0.6 + sin(TIME * sway_speed * 2.3 + phase * 1.7) * 0.25 + 0.35;
	vec2 offset = normalize(wind_direction) * gust * sway_strength * h * h;
	VERTEX += (vec4(offset.x, 0.0, offset.y, 0.0) * MODEL_MATRIX).xyz;
	VERTEX.xz += vec2(sin(TIME * 2.6 + VERTEX.y * 0.8 + phase), cos(TIME * 2.1 + VERTEX.y * 0.6 + phase)) * 0.035 * h;
}

void fragment() {
	ALBEDO = COLOR.rgb * tint;
	ROUGHNESS = roughness;
	SPECULAR = 0.25;
	if (!is_bark) {
		BACKLIGHT = COLOR.rgb * 0.5;
	}
}
