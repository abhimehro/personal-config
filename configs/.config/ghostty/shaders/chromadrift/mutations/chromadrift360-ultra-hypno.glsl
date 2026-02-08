// ChromaDrift360 Ultra Hypno - Enhanced organic dithering for hypnotic texture
// Features: All Ultra features + multi-layered animated dithering system

// Hash function for noise generation
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// Second hash with different seeds for variety
float hash2(vec2 p) {
    return fract(sin(dot(p, vec2(269.5, 183.3))) * 43758.5453);
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

// Fractal Brownian Motion - layered noise for organic texture
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    // 4 octaves of noise
    for (int i = 0; i < 4; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Ordered dither matrix (Bayer 4x4) for structured dithering
float bayer4x4(vec2 p) {
    int x = int(mod(p.x, 4.0));
    int y = int(mod(p.y, 4.0));
    int index = x + y * 4;

    // Bayer matrix values normalized to 0-1
    float[16] matrix = float[16](
         0.0/16.0,  8.0/16.0,  2.0/16.0, 10.0/16.0,
        12.0/16.0,  4.0/16.0, 14.0/16.0,  6.0/16.0,
         3.0/16.0, 11.0/16.0,  1.0/16.0,  9.0/16.0,
        15.0/16.0,  7.0/16.0, 13.0/16.0,  5.0/16.0
    );

    return matrix[index];
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

    // === HYPNO DITHERING SYSTEM ===

    // Layer 1: Slow-drifting organic FBM noise (creates cloudy texture)
    vec2 fbmCoord = fragCoord * 0.008;
    fbmCoord += vec2(iTime * 0.01, iTime * 0.007); // Slow drift
    float organicNoise = fbm(fbmCoord);

    // Layer 2: Fine grain static noise (breaks up micro-banding)
    float fineNoise = hash(fragCoord + fract(iTime * 0.1) * 100.0);

    // Layer 3: Bayer dithering (structured pattern for smooth gradients)
    float bayerNoise = bayer4x4(fragCoord);

    // Layer 4: Slow-moving noise waves (hypnotic ripple effect)
    float hypnoWave = noise(fragCoord * 0.02 + vec2(iTime * 0.05, iTime * 0.03));

    // Combine layers with different weights
    // - Organic FBM for large-scale texture variation
    // - Fine noise for micro-detail
    // - Bayer for structured anti-banding
    // - Hypno wave for subtle movement in the texture itself
    float combinedDither =
        (organicNoise - 0.5) * 0.025 +      // Soft cloudy variation
        (fineNoise - 0.5) * 0.015 +          // Fine grain
        (bayerNoise - 0.5) * 0.02 +          // Structured dither
        (hypnoWave - 0.5) * 0.02;            // Moving texture

    gradientColor += combinedDither;

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
