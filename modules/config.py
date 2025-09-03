"""Configuration and constants for the AI Image Generator"""

# Style presets for image generation
STYLE_PRESETS = {
    "None": "",
    "Photorealistic": "ultra-realistic, high-definition, professional photography, sharp details",
    "Digital Art": "digital painting, concept art, detailed illustration, vibrant colors",
    "Cartoon Style": "cartoon, animated style, colorful and fun, playful",
    "Oil Painting": "classical oil painting, artistic brushstrokes, textured canvas",
    "Sketch": "pencil sketch, hand-drawn, artistic lines, monochrome",
    "Vintage": "vintage style, retro aesthetic, aged look, nostalgic",
    "Cyberpunk": "neon lights, futuristic, cyberpunk aesthetic, dark atmosphere",
    "Minimalist": "clean, simple, minimalist design, elegant simplicity"
}

# Aspect ratios supported by Stability AI
ASPECT_RATIOS = {
    "Square (1:1)": "1:1",
    "Portrait (9:16)": "9:16",
    "Landscape (16:9)": "16:9",
    "Wide (21:9)": "21:9"
}

# Quick templates for common use cases
QUICK_TEMPLATES = {
    "Professional Business": [
        "Professional headshot, business attire, confident expression, office background, high quality",
        "Corporate executive portrait, formal suit, leadership pose, modern office environment",
        "LinkedIn profile photo, professional clothing, approachable smile, neutral background",
        "Business team leader, confident stance, professional environment, sharp focus"
    ],
    "Creative & Artistic": [
        "Artist in creative studio, inspiring workspace, natural lighting, thoughtful expression",
        "Designer at modern workspace, creative environment, focused expression, artistic tools",
        "Creative professional, artistic background, innovative pose, contemporary studio"
    ]
}

# API Configuration
STABILITY_API_CONFIG = {
    "base_url": "https://api.stability.ai/v2beta/stable-image/generate/core",
    "cost_per_image": 0.04,
    "timeout": 60
}
