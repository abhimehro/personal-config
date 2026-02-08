// ChromaDrift360 Temperature - Animated gradient with slow color temperature drift
// Based on chromadrift360 + glacial palette shift from cool to warm over ~5 minutes

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

    vec2 gradientDirection = vec2(cos(rotationAngle), sin(rotationAngle));
    float gradientFactor = dot(centeredUV, gradientDirection) + 0.5;
    gradientFactor = clamp(gradientFactor, 0.0, 1.0);
    gradientFactor = smoothstep(0.0, 1.0, gradientFactor);

    // Temperature drift: full cycle over 5 minutes (300 seconds)
    float tempCycle = 6.28318530718 / 300.0;
    float tempPhase = iTime * tempCycle;
    float temperature = sin(tempPhase) * 0.5 + 0.5; // 0 = cool, 1 = warm

    // Cool palette (blues, teals, purples)
    vec3 cool1 = vec3(0.08, 0.12, 0.45); // Deep blue
    vec3 cool2 = vec3(0.1, 0.35, 0.4);   // Teal
    vec3 cool3 = vec3(0.25, 0.1, 0.45);  // Purple

    // Warm palette (reds, oranges, magentas)
    vec3 warm1 = vec3(0.5, 0.1, 0.15);   // Deep red
    vec3 warm2 = vec3(0.5, 0.25, 0.08);  // Burnt orange
    vec3 warm3 = vec3(0.45, 0.1, 0.35);  // Magenta

    // Interpolate between cool and warm palettes based on temperature
    vec3 color1 = mix(cool1, warm1, temperature);
    vec3 color2 = mix(cool2, warm2, temperature);
    vec3 color3 = mix(cool3, warm3, temperature);

    // Color cycling (faster than temperature, creates local variation)
    float colorSpeed = 0.1;
    float colorAngle = iTime * colorSpeed;

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
