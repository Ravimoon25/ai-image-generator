"""
AI Image Generator - Fixed + Enhanced
- Supports: Generate, Transform, Upscale
- Stability AI API v1 endpoints
"""

import streamlit as st
import requests
from PIL import Image
import io
import base64
from datetime import datetime
from typing import List

# Page configuration
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.stButton > button {
    width: 100%;
    height: 3rem;
    border-radius: 8px;
    transition: all 0.3s ease;
}
</style>
""", unsafe_allow_html=True)

# Configuration
STYLE_PRESETS = {
    "None": "",
    "Photorealistic": "ultra-realistic, high-definition, professional photography, sharp details",
    "Digital Art": "digital painting, concept art, detailed illustration, vibrant colors",
    "Cartoon Style": "cartoon, animated style, colorful and fun, playful",
    "Oil Painting": "classical oil painting, artistic brushstrokes, textured canvas",
    "Sketch": "pencil sketch, hand-drawn, artistic lines, monochrome",
    "Vintage": "vintage style, retro aesthetic, aged look, nostalgic",
    "Cyberpunk": "neon lights, futuristic, cyberpunk aesthetic, dark atmosphere"
}

ASPECT_RATIOS = {
    "Square (1:1)": "1024x1024",
    "Portrait (9:16)": "1024x1792", 
    "Landscape (16:9)": "1792x1024",
}

# --- API Helpers ---
def generate_images(prompt: str, style: str, aspect_ratio: str, num_variants: int = 1) -> List[Image.Image]:
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    if not api_key:
        raise ValueError("API key not configured")

    api_host = "https://api.stability.ai"
    engine_id = "stable-diffusion-xl-1024-v1-0"

    enhanced_prompt = prompt
    if style != "None" and style in STYLE_PRESETS:
        enhanced_prompt = f"{prompt}, {STYLE_PRESETS[style]}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    images = []
    for _ in range(num_variants):
        response = requests.post(
            f"{api_host}/v1/generation/{engine_id}/text-to-image",
            headers=headers,
            json={
                "text_prompts": [{"text": enhanced_prompt}],
                "cfg_scale": 7,
                "height": int(aspect_ratio.split("x")[1]),
                "width": int(aspect_ratio.split("x")[0]),
                "samples": 1,
                "steps": 30,
            },
            timeout=60
        )
        if response.status_code != 200:
            raise Exception(f"Generation failed: {response.text}")

        data = response.json()
        for artifact in data.get("artifacts", []):
            img_data = base64.b64decode(artifact["base64"])
            images.append(Image.open(io.BytesIO(img_data)))

    return images


def transform_image(prompt: str, image: Image.Image, strength=0.8, steps=30, cfg_scale=7, samples=1) -> List[Image.Image]:
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    if not api_key:
        raise ValueError("API key not configured")

    api_host = "https://api.stability.ai"
    engine_id = "stable-diffusion-xl-1024-v1-0"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)

    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/image-to-image",
        headers=headers,
        files={
            "init_image": ("init.png", buffered, "image/png")
        },
        data={
            "image_strength": strength,
            "init_image_mode": "IMAGE_STRENGTH",
            "text_prompts[0][text]": prompt,
            "cfg_scale": cfg_scale,
            "samples": samples,
            "steps": steps,
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Transformation failed: {response.text}")

    data = response.json()
    images = []
    for artifact in data.get("artifacts", []):
        img_data = base64.b64decode(artifact["base64"])
        images.append(Image.open(io.BytesIO(img_data)))

    return images


def upscale_image(image: Image.Image) -> Image.Image:
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    if not api_key:
        raise ValueError("API key not configured")

    api_host = "https://api.stability.ai"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)

    response = requests.post(
        f"{api_host}/v1/generation/esrgan-v1-x2plus/image-to-image",
        headers=headers,
        files={
            "init_image": ("image.png", buffered, "image/png")
        },
        data={
            "text_prompts[0][text]": "upscale",
            "cfg_scale": 7,
            "samples": 1,
            "steps": 50,
        },
        timeout=90
    )

    if response.status_code != 200:
        raise Exception(f"Upscale failed: {response.text}")

    data = response.json()
    artifact = data["artifacts"][0]
    img_data = base64.b64decode(artifact["base64"])
    return Image.open(io.BytesIO(img_data))


# --- Streamlit UI ---
def main():
    st.title("🎨 AI Image Generator")
    st.markdown("**Professional image generation powered by Stability AI**")

    if not st.secrets.get("STABILITY_API_KEY"):
        st.error("Please add STABILITY_API_KEY to secrets")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["🎨 Generate", "🔄 Transform", "⬆️ Upscale"])

    # --- Generate ---
    with tab1:
        prompt = st.text_area("✨ Describe your image:", height=120)
        style = st.selectbox("Art Style:", list(STYLE_PRESETS.keys()))
        aspect_ratio = st.selectbox("Aspect Ratio:", list(ASPECT_RATIOS.values()))
        num_variants = st.slider("Number of Images", 1, 4, 1)

        if st.button("⚡ Generate Image", type="primary"):
            try:
                with st.spinner("Generating..."):
                    images = generate_images(prompt, style, aspect_ratio, num_variants)

                for i, img in enumerate(images):
                    st.image(img, caption=f"Variant {i+1}")
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.download_button(f"📥 Download Variant {i+1}", buf.getvalue(), f"gen_{i+1}.png", "image/png")

            except Exception as e:
                st.error(str(e))

    # --- Transform ---
    with tab2:
        uploaded_file = st.file_uploader("📤 Upload an image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file).convert("RGB")
            st.image(image, caption="Original", use_container_width=True)

            prompt = st.text_area("✏️ Transformation Prompt")
            strength = st.slider("🎚️ Strength", 0.1, 1.0, 0.8)

            if st.button("🔄 Transform Image", type="primary"):
                try:
                    with st.spinner("Transforming..."):
                        results = transform_image(prompt, image, strength)
                    for i, img in enumerate(results):
                        st.image(img, caption=f"Transformed {i+1}")
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        st.download_button(f"📥 Download {i+1}", buf.getvalue(), f"transform_{i+1}.png", "image/png")
                except Exception as e:
                    st.error(str(e))

    # --- Upscale ---
    with tab3:
        up_file = st.file_uploader("📤 Upload an image to upscale", type=["png", "jpg", "jpeg"])
        if up_file:
            up_file.seek(0)
            image = Image.open(up_file).convert("RGB")
            st.image(image, caption="Original", use_container_width=True)

            if st.button("⬆️ Upscale Image", type="primary"):
                try:
                    with st.spinner("Upscaling..."):
                        upscaled = upscale_image(image)
                    st.image(upscaled, caption="Upscaled")
                    buf = io.BytesIO()
                    upscaled.save(buf, format="PNG")
                    st.download_button("📥 Download Upscaled", buf.getvalue(), "upscaled.png", "image/png")
                except Exception as e:
                    st.error(str(e))


if __name__ == "__main__":
    main()
