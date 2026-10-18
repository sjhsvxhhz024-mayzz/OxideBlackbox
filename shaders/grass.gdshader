// Grass blades from Blender: UV.y is the height along the blade (0 root, 1 tip).
shader_type spatial;
render_mode cull_disabled, diffuse_burley;

uniform float wind_strength = 0.14;
uniform float wind_speed = 1.5;
uniform vec2 wind_direction = vec2(1.0, 0.35);

void vertex() {
	float h = UV.y;
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float wave = sin(TIME * wind_speed + dot(wp.xz, vec2(0.9, 0.35))) * 0.5 + 0.5;
	wave += 0.35 * sin(TIME * wind_speed * 2.9 + dot(wp.xz, vec2(-1.7, 2.3)));
	float gust = smoothstep(0.25, 1.0, sin(TIME * 0.33 + wp.x * 0.07 - wp.z * 0.05) * 0.5 + 0.5);
	vec2 offset = normalize(wind_direction) * wave * (0.55 + gust) * wind_strength * h * h;
	VERTEX.xz += offset;
	VERTEX.y -= length(offset) * 0.35 * h;
}

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.7;
	SPECULAR = 0.3;
	BACKLIGHT = COLOR.rgb * 0.7;
	AO = mix(0.35, 1.0, UV.y);
	AO_LIGHT_AFFECT = 0.6;
}
