// ChromaDrift360 Breathing - Animated gradient with gentle luminance pulse
// Based on chromadrift360 + slow breathing brightness cycle (~8 seconds)

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

    // Breathing luminance - gentle pulse over ~8 seconds
    // Using smoothed sine for organic feel (not harsh linear)
    float breathCycle = 6.28318530718 / 8.0; // Full breath every 8 seconds
    float breathPhase = iTime * breathCycle;
    // Smoothstep the sine for more organic inhale/exhale curve
    float breathRaw = sin(breathPhase) * 0.5 + 0.5; // 0 to 1
    float breath = smoothstep(0.0, 1.0, breathRaw);
    // Apply subtle brightness variation: 0.9 to 1.05 (15% range)
    float luminance = 0.9 + breath * 0.15;
    gradientColor *= luminance;

    // Noise dithering
    float n = noise(fragCoord * 0.5);
    gradientColor += (n - 0.5) * 0.02;

    vec4 terminalColor = texture(iChannel0, uv);
    vec3 blendedColor = gradientColor + terminalColor.rgb;

    fragColor = vec4(blendedColor, terminalColor.a);
}
