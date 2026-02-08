// ChromaDrift360 Ultra - The ultimate combination
// Features: 360° rotation + aurora wisps + breathing luminance + temperature drift

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

    // === ROTATION (60 second cycle) ===
    float rotationSpeed = 6.28318530718 / 60.0;
    float rotationAngle = iTime * rotationSpeed;

    vec2 gradientDirection = vec2(cos(rotationAngle), sin(rotationAngle));

    // === AURORA WISPS ===
    vec2 perpendicular = vec2(-gradientDirection.y, gradientDirection.x);
    float perpPos = dot(centeredUV, perpendicular);

    float wave1 = sin(perpPos * 8.0 + iTime * 0.3) * 0.015;
    float wave2 = sin(perpPos * 12.0 - iTime * 0.2) * 0.01;
    float wave3 = sin(perpPos * 5.0 + iTime * 0.15) * 0.02;
    float auroraOffset = wave1 + wave2 + wave3;

    // Gradient factor with aurora displacement
    float gradientFactor = dot(centeredUV, gradientDirection) + 0.5 + auroraOffset;
    gradientFactor = clamp(gradientFactor, 0.0, 1.0);
    gradientFactor = smoothstep(0.0, 1.0, gradientFactor);

    // === TEMPERATURE DRIFT (5 minute cycle) ===
    float tempCycle = 6.28318530718 / 300.0;
    float tempPhase = iTime * tempCycle;
    float temperature = sin(tempPhase) * 0.5 + 0.5;

    // Cool palette
    vec3 cool1 = vec3(0.08, 0.12, 0.45);
    vec3 cool2 = vec3(0.1, 0.35, 0.4);
    vec3 cool3 = vec3(0.25, 0.1, 0.45);

    // Warm palette
    vec3 warm1 = vec3(0.5, 0.1, 0.15);
    vec3 warm2 = vec3(0.5, 0.25, 0.08);
    vec3 warm3 = vec3(0.45, 0.1, 0.35);

    // Blend palettes based on temperature
    vec3 color1 = mix(cool1, warm1, temperature);
    vec3 color2 = mix(cool2, warm2, temperature);
    vec3 color3 = mix(cool3, warm3, temperature);

    // Color cycling
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

    // === BREATHING LUMINANCE (8 second cycle) ===
    float breathCycle = 6.28318530718 / 8.0;
    float breathPhase = iTime * breathCycle;
    float breathRaw = sin(breathPhase) * 0.5 + 0.5;
    float breath = smoothstep(0.0, 1.0, breathRaw);
    float luminance = 0.9 + breath * 0.15;
    gradientColor *= luminance;

    // Noise dithering (increased to reduce banding)
    float n = noise(fragCoord * 0.5);
    gradientColor += (n - 0.5) * 0.03;

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
