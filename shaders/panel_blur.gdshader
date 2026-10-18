// Frosted dark menu panel: blurred copy of the 3D scene behind it.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float blur_lod = 3.2;
uniform vec4 tint : source_color = vec4(0.045, 0.05, 0.06, 0.8);
uniform float edge_shadow = 0.35;

void fragment() {
	vec3 bg = textureLod(screen_tex, SCREEN_UV, blur_lod).rgb;
	float vertical = smoothstep(0.0, 1.0, UV.y);
	vec3 col = mix(bg, tint.rgb, clamp(tint.a + 0.08 * vertical, 0.0, 1.0));
	col *= mix(1.0, 1.0 - edge_shadow, smoothstep(0.97, 1.0, UV.x));
	COLOR = vec4(col, 1.0);
}
