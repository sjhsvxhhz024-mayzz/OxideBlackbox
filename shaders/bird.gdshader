// Distant birds: wings flap around the body axis.
shader_type spatial;
render_mode cull_disabled, diffuse_burley;

uniform float flap_speed = 9.0;
instance uniform float phase = 0.0;

void vertex() {
	float wing = abs(VERTEX.x);
	VERTEX.y += sin(TIME * flap_speed + phase) * wing * 0.9;
}

void fragment() {
	ALBEDO = vec3(0.035, 0.035, 0.04);
	ROUGHNESS = 0.9;
}
