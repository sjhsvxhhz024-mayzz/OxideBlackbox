// Sky dome with a drifting overcast layer and a warm sunset band.
shader_type spatial;
render_mode unshaded, cull_front, fog_disabled, shadows_disabled, depth_draw_never;

#include "res://shaders/noise.gdshaderinc"

uniform vec3 zenith_color : source_color = vec3(0.16, 0.2, 0.27);
uniform vec3 horizon_color : source_color = vec3(0.86, 0.63, 0.43);
uniform vec3 sun_color : source_color = vec3(1.0, 0.7, 0.4);
uniform vec3 cloud_shadow : source_color = vec3(0.12, 0.14, 0.18);
uniform vec3 cloud_lit : source_color = vec3(0.36, 0.38, 0.43);
uniform vec3 sun_direction = vec3(0.1, 0.12, -1.0);
uniform float coverage : hint_range(0.0, 1.0) = 0.62;
uniform float drift_speed = 0.006;
uniform vec2 drift_direction = vec2(1.0, 0.35);
uniform float brightness = 1.0;

varying vec3 dir_model;

void vertex() {
	dir_model = VERTEX;
}

void fragment() {
	vec3 d = normalize(dir_model);
	vec3 s = normalize(sun_direction);
	float elev = d.y;
	float sun_amt = max(dot(d, s), 0.0);
	vec3 sky = mix(horizon_color, zenith_color, smoothstep(-0.02, 0.45, elev));
	sky += sun_color * (pow(sun_amt, 10.0) * 0.5 + pow(sun_amt, 64.0) * 1.4);

	vec2 uv = d.xz / (max(elev, 0.0) + 0.06) * 0.55;
	vec2 wind = normalize(drift_direction) * TIME * drift_speed;
	float base = tz_fbm2(uv * 0.9 + wind, 5);
	float detail = tz_fbm2(uv * 3.3 + wind * 1.7 + vec2(4.1, 1.3), 4);
	float shape = base * 0.75 + detail * 0.35;
	float cov = smoothstep(1.0 - coverage, 1.0 - coverage + 0.28, shape);
	float dens = smoothstep(0.45, 0.85, shape + detail * 0.15);
	vec3 ccol = mix(cloud_lit, cloud_shadow, dens);
	ccol += sun_color * (1.0 - dens) * pow(sun_amt, 5.0) * 1.2;
	ccol = mix(ccol, horizon_color * 0.75, smoothstep(0.18, 0.0, elev) * 0.55);
	vec3 col = mix(sky, ccol, cov * smoothstep(-0.01, 0.08, elev));
	ALBEDO = col * brightness;
}
