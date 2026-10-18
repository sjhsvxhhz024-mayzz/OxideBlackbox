// Living photo plate: clouds drift, grass and trees sway, the sea shimmers and cloud shadows roll over the land.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

#include "res://shaders/noise.gdshaderinc"

uniform sampler2D plate : source_color, filter_linear, repeat_disable;
// R sky, G vegetation sway, B water, A land (receives cloud shadows)
uniform sampler2D masks : filter_linear, repeat_disable;
uniform float cloud_speed = 0.035;
uniform vec2 cloud_flow = vec2(0.024, -0.002);
uniform float wind_strength = 0.0012;
uniform float wind_speed = 1.4;
uniform float water_strength = 0.0006;
uniform float shadow_strength = 0.08;
uniform float sharpen = 0.3;

vec3 sharp_sample(vec2 uv) {
	vec2 px = 1.0 / vec2(textureSize(plate, 0));
	vec3 c = texture(plate, uv).rgb;
	vec3 blur = (texture(plate, uv + vec2(px.x, 0.0)).rgb + texture(plate, uv - vec2(px.x, 0.0)).rgb
			+ texture(plate, uv + vec2(0.0, px.y)).rgb + texture(plate, uv - vec2(0.0, px.y)).rgb) * 0.25;
	return max(c + (c - blur) * sharpen, vec3(0.0));
}

float cloud_shadow(vec2 uv, float t) {
	float n = tz_fbm2(uv * vec2(2.2, 5.0) + vec2(t * 0.012, t * 0.002), 4);
	return smoothstep(0.42, 0.72, n);
}

void fragment() {
	vec2 uv = UV;
	vec4 m = texture(masks, uv);
	float t = TIME;
	float gust = 0.55 + 0.45 * sin(t * 0.37 + uv.x * 3.0);
	float wave = sin(t * wind_speed + uv.x * 60.0 + uv.y * 25.0) + 0.5 * sin(t * wind_speed * 2.3 + uv.x * 140.0 - uv.y * 40.0);
	uv.x += m.g * wave * wind_strength * gust;
	uv.y += m.g * abs(wave) * wind_strength * 0.25;
	uv.x += m.b * sin(uv.y * 1400.0 + t * 1.7) * water_strength;
	vec3 col = sharp_sample(uv);
	if (m.r > 0.002) {
		// two-phase flow: the sky drifts forever without stretching
		float p0 = fract(t * cloud_speed);
		float p1 = fract(t * cloud_speed + 0.5);
		vec2 wobble = (vec2(tz_fbm2(uv * 6.0 + t * 0.02, 3), tz_fbm2(uv * 6.0 - t * 0.02 + 7.0, 3)) - 0.5) * 0.006;
		vec3 c0 = texture(plate, uv - cloud_flow * (p0 - 0.5) + wobble).rgb;
		vec3 c1 = texture(plate, uv - cloud_flow * (p1 - 0.5) - wobble).rgb;
		vec3 sky = mix(c1, c0, 1.0 - abs(2.0 * p0 - 1.0));
		col = mix(col, sky, m.r);
	}
	col *= 1.0 - shadow_strength * cloud_shadow(UV, t) * m.a;
	ALBEDO = col;
}
