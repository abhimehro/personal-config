// ChromaDrift360 Aurora - Animated gradient with aurora-like rippling edge
// Based on chromadrift360 + gentle sine wave undulations along gradient boundary

// Hash function for noise generation
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// Smooth value noise
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec2 centeredUV = uv - 0.5;

    // Rotation speed: full rotation in 1 minute
    float rotationSpeed = 6.28318530718 / 60.0;
    float rotationAngle = iTime * rotationSpeed;

    // Base gradient direction
    vec2 gradientDirection = vec2(cos(rotationAngle), sin(rotationAngle));

    // Perpendicular direction for aurora waves
    vec2 perpendicular = vec2(-gradientDirection.y, gradientDirection.x);

    // Position along the perpendicular (for wave variation)
    float perpPos = dot(centeredUV, perpendicular);

    // Aurora wave parameters - multiple slow waves at different frequencies
    float wave1 = sin(perpPos * 8.0 + iTime * 0.3) * 0.015;
    float wave2 = sin(perpPos * 12.0 - iTime * 0.2) * 0.01;
    float wave3 = sin(perpPos * 5.0 + iTime * 0.15) * 0.02;
    float auroraOffset = wave1 + wave2 + wave3;

    // Calculate gradient factor with aurora displacement
    float gradientFactor = dot(centeredUV, gradientDirection) + 0.5 + auroraOffset;
    gradientFactor = clamp(gradientFactor, 0.0, 1.0);
    gradientFactor = smoothstep(0.0, 1.0, gradientFactor);

    // Color cycling
    float colorSpeed = 0.1;
    float colorAngle = iTime * colorSpeed;

    vec3 color1 = vec3(0.1, 0.1, 0.5);
    vec3 color2 = vec3(0.5, 0.1, 0.1);
    vec3 color3 = vec3(0.1, 0.5, 0.1);

    vec3 gradientStartColor = mix(
            mix(color1, color2, smoothstep(0.0, 1.0, sin(colorAngle) * 0.5 + 0.5)),
            color3,
            smoothstep(0.0, 1.0, sin(colorAngle + 2.0) * 0.5 + 0.5)
        );

    vec3 gradientEndColor = mix(
            mix(color2, color3, smoothstep(0.0, 1.0, sin(colorAngle + 1.0) * 0.5 + 0.5)),
            color1,
            smoothstep(0.0, 1.0, sin(colorAngle + 3.0) * 0.5 + 0.5)
        );

    vec3 gradientColor = mix(gradientStartColor, gradientEndColor, gradientFactor);

    // Noise dithering
    float n = noise(fragCoord * 0.5);
    gradientColor += (n - 0.5) * 0.02;

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
