// ChromaDrift360 Hypno GX - Pixelated glass matrix aesthetic
// Features: All Ultra Hypno features + micro-pixelation overlay + reduced noise intensity

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

// Fractal Brownian Motion
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    for (int i = 0; i < 4; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    return value;
}

// Bayer 4x4 dither matrix
float bayer4x4(vec2 p) {
    int x = int(mod(p.x, 4.0));
    int y = int(mod(p.y, 4.0));
    int index = x + y * 4;

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

    // === GLASS MATRIX PIXELATION ===
    // Create micro-pixel grid (adjust pixelSize for coarser/finer grid)
    float pixelSize = 3.0; // Size of each "glass square" in pixels
    vec2 pixelatedCoord = floor(fragCoord / pixelSize) * pixelSize;
    vec2 pixelatedUV = pixelatedCoord / iResolution.xy;

    // Use pixelated coordinates for the gradient calculation
    vec2 centeredUV = pixelatedUV - 0.5;

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

    // === SUBTLE DITHERING (reduced from hypno version) ===
    // Using pixelated coordinates for dithering to maintain 8-bit feel

    // Organic FBM - very subtle, slow drift
    vec2 fbmCoord = pixelatedCoord * 0.006;
    fbmCoord += vec2(iTime * 0.008, iTime * 0.005);
    float organicNoise = fbm(fbmCoord);

    // Bayer dithering aligned to pixel grid
    float bayerNoise = bayer4x4(pixelatedCoord / pixelSize);

    // Combined dither - much more subtle than hypno
    float combinedDither =
        (organicNoise - 0.5) * 0.012 +    // Gentle cloud variation
        (bayerNoise - 0.5) * 0.015;        // Structured 8-bit dither

    gradientColor += combinedDither;

    // === GLASS SQUARE EDGE EFFECT ===
    // Subtle darkening at the edges of each pixel cell
    vec2 cellPos = fract(fragCoord / pixelSize);
    float edgeDist = min(min(cellPos.x, 1.0 - cellPos.x), min(cellPos.y, 1.0 - cellPos.y));
    float edgeFade = smoothstep(0.0, 0.15, edgeDist);
    gradientColor *= 0.97 + edgeFade * 0.03; // Very subtle grid lines

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
