// ChromaDrift360 Ultra Hypno K7 - Refined dithering with reduced intensity
// Features: All Ultra Hypno features + expanded texture scale + subtle pixelated dither

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

// Fractal Brownian Motion - layered noise for organic texture
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    // 3 octaves (reduced from 4 for softer look)
    for (int i = 0; i < 3; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Bayer 8x8 dither matrix for finer structured dithering
float bayer8x8(vec2 p) {
    int x = int(mod(p.x, 8.0));
    int y = int(mod(p.y, 8.0));
    int index = x + y * 8;

    float[64] matrix = float[64](
         0.0/64.0, 32.0/64.0,  8.0/64.0, 40.0/64.0,  2.0/64.0, 34.0/64.0, 10.0/64.0, 42.0/64.0,
        48.0/64.0, 16.0/64.0, 56.0/64.0, 24.0/64.0, 50.0/64.0, 18.0/64.0, 58.0/64.0, 26.0/64.0,
        12.0/64.0, 44.0/64.0,  4.0/64.0, 36.0/64.0, 14.0/64.0, 46.0/64.0,  6.0/64.0, 38.0/64.0,
        60.0/64.0, 28.0/64.0, 52.0/64.0, 20.0/64.0, 62.0/64.0, 30.0/64.0, 54.0/64.0, 22.0/64.0,
         3.0/64.0, 35.0/64.0, 11.0/64.0, 43.0/64.0,  1.0/64.0, 33.0/64.0,  9.0/64.0, 41.0/64.0,
        51.0/64.0, 19.0/64.0, 59.0/64.0, 27.0/64.0, 49.0/64.0, 17.0/64.0, 57.0/64.0, 25.0/64.0,
        15.0/64.0, 47.0/64.0,  7.0/64.0, 39.0/64.0, 13.0/64.0, 45.0/64.0,  5.0/64.0, 37.0/64.0,
        63.0/64.0, 31.0/64.0, 55.0/64.0, 23.0/64.0, 61.0/64.0, 29.0/64.0, 53.0/64.0, 21.0/64.0
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
    // Bias toward the cool/teal side: range ~0.1–0.5 instead of 0.0–1.0
    float temperature = 0.3 + sin(tempPhase) * 0.2;

    // Cool palette ("emulsified" green → teal → blue)
    // Greener teal core that can lean cooler or warmer without feeling neon
    vec3 cool1 = vec3(0.06, 0.16, 0.16);  // deep green-teal shadow
    vec3 cool2 = vec3(0.04, 0.24, 0.20);  // mid teal, slight green bias
    vec3 cool3 = vec3(0.16, 0.30, 0.40);  // deeper ocean blue with teal influence

    // Warm/Accent palette (soft rust + teal-tinted highlight)
    // Orange stays, but pulled back and partially "dissolved" into teal
    vec3 warm1 = vec3(0.62, 0.36, 0.20);  // richer rust, still subdued
    vec3 warm2 = vec3(0.92, 0.54, 0.30);  // warmer, slightly brighter orange highlight
    vec3 warm3 = vec3(0.40, 0.70, 0.60);  // teal-leaning accent (green > blue > red)

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

    // Dark-first: keep overall brightness closer to Dracula background
    // Luminance now varies gently between ~0.6 and ~0.7 instead of ~0.9–1.05
    float luminance = 0.6 + breath * 0.10;
    gradientColor *= luminance;

    // Extra darkening pass so accents pop but base stays subdued
    gradientColor = mix(vec3(0.0), gradientColor, 0.75);

    // === K7 REFINED DITHERING SYSTEM ===
    // Goal: Subtle, expanded texture with pixelated character

    // Micro-pixel grid for dither alignment (subtle pixelation)
    float ditherPixelSize = 2.0;
    vec2 ditherCoord = floor(fragCoord / ditherPixelSize) * ditherPixelSize;

    // Layer 1: Expanded organic FBM (scaled way out for gentle clouds)
    vec2 fbmCoord = ditherCoord * 0.003; // Expanded 2.5x from original
    fbmCoord += vec2(iTime * 0.006, iTime * 0.004); // Slower drift
    float organicNoise = fbm(fbmCoord);

    // Layer 2: 8x8 Bayer dithering (finer pattern than 4x4)
    float bayerNoise = bayer8x8(ditherCoord);

    // Layer 3: Very slow, large-scale hypno wave (almost imperceptible movement)
    float hypnoWave = noise(ditherCoord * 0.005 + vec2(iTime * 0.02, iTime * 0.015));

    // Combine with reduced intensity (~40% of original hypno)
    // Emphasis on Bayer for that classic dithered look
    float combinedDither =
        (organicNoise - 0.5) * 0.010 +    // Gentle cloud (was 0.025)
        (bayerNoise - 0.5) * 0.018 +       // Primary dither pattern
        (hypnoWave - 0.5) * 0.008;         // Whisper of movement (was 0.02)

    gradientColor += combinedDither;

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
