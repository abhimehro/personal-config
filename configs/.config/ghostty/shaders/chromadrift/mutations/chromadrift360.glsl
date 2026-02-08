// ChromaDrift360 - Animated gradient with rotating direction
// Based on: https://github.com/unkn0wncode
// Modified: 360-degree rotating gradient direction (1 full rotation per minute)
//           + slower color cycling + noise dithering

// Hash function for noise generation
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// Smooth value noise
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f); // smoothstep

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord.xy / iResolution.xy;

    // Center the UV coordinates for rotation calculation
    vec2 centeredUV = uv - 0.5;

    // Rotation speed: 2*PI radians per 60 seconds = full rotation in 1 minute
    float rotationSpeed = 6.28318530718 / 60.0; // 2*PI / 60 seconds
    float rotationAngle = iTime * rotationSpeed;

    // Calculate gradient factor based on rotating direction
    // This projects the position onto a rotating direction vector
    vec2 gradientDirection = vec2(cos(rotationAngle), sin(rotationAngle));
    float gradientFactor = dot(centeredUV, gradientDirection) + 0.5;
    gradientFactor = clamp(gradientFactor, 0.0, 1.0);
    gradientFactor = smoothstep(0.0, 1.0, gradientFactor);

    // Color cycling speed (slower than rotation)
    float colorSpeed = 0.1;
    float colorAngle = iTime * colorSpeed;

    vec3 color1 = vec3(0.1, 0.1, 0.5); // Deep blue
    vec3 color2 = vec3(0.5, 0.1, 0.1); // Deep red
    vec3 color3 = vec3(0.1, 0.5, 0.1); // Deep green

    // Smooth interpolation between colors using multiple mix operations
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

    // Noise dithering to reduce color banding
    float n = noise(fragCoord * 0.5);
    gradientColor += (n - 0.5) * 0.02;

    // Sample the terminal screen texture
    vec4 terminalColor = texture(iChannel0, uv);

    // Add gradient behind all terminal content
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
