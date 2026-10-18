// Shared value-noise helpers for the TEZEROK shaders.

float tz_hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float tz_hash13(vec3 p3) {
	p3 = fract(p3 * 0.1031);
	p3 += dot(p3, p3.zyx + 31.32);
	return fract((p3.x + p3.y) * p3.z);
}

float tz_noise2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(tz_hash12(i), tz_hash12(i + vec2(1.0, 0.0)), u.x),
			mix(tz_hash12(i + vec2(0.0, 1.0)), tz_hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}

float tz_noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float a = mix(tz_hash13(i), tz_hash13(i + vec3(1.0, 0.0, 0.0)), u.x);
	float b = mix(tz_hash13(i + vec3(0.0, 1.0, 0.0)), tz_hash13(i + vec3(1.0, 1.0, 0.0)), u.x);
	float c = mix(tz_hash13(i + vec3(0.0, 0.0, 1.0)), tz_hash13(i + vec3(1.0, 0.0, 1.0)), u.x);
	float d = mix(tz_hash13(i + vec3(0.0, 1.0, 1.0)), tz_hash13(i + vec3(1.0, 1.0, 1.0)), u.x);
	return mix(mix(a, b, u.y), mix(c, d, u.y), u.z);
}

// Fractal sums normalised to roughly 0..1.
float tz_fbm2(vec2 p, int octaves) {
	float sum = 0.0;
	float amp = 0.5;
	float norm = 0.0;
	for (int i = 0; i < octaves; i++) {
		sum += amp * tz_noise2(p);
		norm += amp;
		p = p * 2.03 + vec2(17.1, 9.2);
		amp *= 0.5;
	}
	return sum / norm;
}

float tz_fbm3(vec3 p, int octaves) {
	float sum = 0.0;
	float amp = 0.5;
	float norm = 0.0;
	for (int i = 0; i < octaves; i++) {
		sum += amp * tz_noise3(p);
		norm += amp;
		p = p * 2.03 + vec3(17.1, 9.2, 4.7);
		amp *= 0.5;
	}
	return sum / norm;
}

// Bump mapping without tangents (Mikkelsen, "Bump Mapping Unparametrized Surfaces on the GPU").
vec3 tz_bump(vec3 normal, vec3 view_pos, float height) {
	vec3 dpdx = dFdx(view_pos);
	vec3 dpdy = dFdy(view_pos);
	vec3 r1 = cross(dpdy, normal);
	vec3 r2 = cross(normal, dpdx);
	float det = dot(dpdx, r1);
	vec3 grad = sign(det) * (dFdx(height) * r1 + dFdy(height) * r2);
	return normalize(abs(det) * normal - grad);
}
