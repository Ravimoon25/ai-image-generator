"""AI Image Generator - Enhanced Version (Stability AI API v2beta)"""

import streamlit as st
import requests
from PIL import Image
import io
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor
import base64

# ------------------------
# Page configuration
# ------------------------
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------
# Custom CSS
# ------------------------
st.markdown("""
<style>
.stButton > button {
    width: 100%;
    height: 3rem;
    border-radius: 8px;
    transition: all 0.3s ease;
}
.template-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 0.8rem;
    border-radius: 6px;
    margin: 0.3rem 0;
}
</style>
""", unsafe_allow_html=True)

# ------------------------
# Configuration
# ------------------------
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
    "Square (1:1)": "1:1",
    "Portrait (9:16)": "9:16",
    "Landscape (16:9)": "16:9",
    "Wide (21:9)": "21:9"
}

# ------------------------
# Helpers
# ------------------------
def get_api_key():
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    if not api_key:
        st.error("Please add STABILITY_API_KEY to Streamlit secrets")
        st.stop()
    return api_key


def enhance_prompt(prompt: str, style: str) -> str:
    if style != "None" and style in STYLE_PRESETS:
        prompt = f"{prompt}, {STYLE_PRESETS[style]}"
    return f"{prompt}, high quality, detailed, professional, sharp focus"


# ------------------------
# API Calls
# ------------------------
def generate_images(prompt: str, style: str, aspect_ratio: str, num_variants: int) -> List[Image.Image]:
    api_key = get_api_key()
    enhanced_prompt = enhance_prompt(prompt, style)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    data = {
        "prompt": enhanced_prompt,
        "aspect_ratio": ASPECT_RATIOS[aspect_ratio],
        "output_format": "png"
    }

    def _request():
        resp = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers=headers,
            files={"none": ""},
            data=data,
            timeout=60
        )
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
        else:
            raise Exception(resp.text)

    # Run in parallel
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda _: _request(), range(num_variants)))
    return results


def transform_image(prompt, image: Image.Image, strength=0.8, steps=30, cfg_scale=7, samples=1):
    """
    Transform an image using Stability AI Image-to-Image API
    """
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    if not api_key:
        st.error("Missing Stability API key. Please add it to Streamlit secrets.")
        return []

    api_host = "https://api.stability.ai"
    engine_id = "stable-diffusion-xl-1024-v1-0"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # ✅ Ensure it's really a PIL Image
    if not isinstance(image, Image.Image):
        st.error("Uploaded image could not be processed. Please upload a valid PNG/JPG.")
        return []

    # Convert PIL image into a buffer
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)

    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/image-to-image",
        headers=headers,
        files={
            "init_image": buffered
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
        st.error(f"❌ Transformation failed: {response.text}")
        return []

    data = response.json()
    images = []
    for artifact in data.get("artifacts", []):
        img_data = base64.b64decode(artifact["base64"])
        images.append(Image.open(io.BytesIO(img_data)))

    return images


def transformation_tab():
    st.subheader("🔄 Image Transformation")

    uploaded_file = st.file_uploader("📤 Upload an image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        # ✅ Always convert file to PIL Image
        try:
            image = Image.open(uploaded_file).convert("RGB")
        except Exception:
            st.error("Could not read uploaded file as image.")
            return

        st.image(image, caption="Original Image", use_container_width=True)

        prompt = st.text_area("✏️ Transformation Prompt", placeholder="Describe the transformation...")
        strength = st.slider("🎚️ Strength", 0.1, 1.0, 0.8)

        if st.button("⚡ Transform Image", type="primary", disabled=not prompt):
            with st.spinner("Transforming..."):
                results = transform_image(prompt, image, strength=strength)
                for i, img in enumerate(results):
                    st.image(img, caption=f"Transformed Variant {i+1}", use_container_width=True)

                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.download_button(
                        f"📥 Download Variant {i+1}",
                        buf.getvalue(),
                        f"transformed_{i+1}.png",
                        "image/png"
                    )

def upscale_image(uploaded_image: Image.Image) -> Image.Image:
    api_key = get_api_key()

    img_byte_arr = io.BytesIO()
    uploaded_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    files = {"image": ("image.png", img_byte_arr, "image/png")}
    data = {"output_format": "png"}

    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/upscale/conservative",
        headers=headers,
        files=files,
        data=data,
        timeout=90
    )

    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        raise Exception(response.text)


# ------------------------
# Session State
# ------------------------
def initialize_session_state():
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = ""


def save_to_history(prompt, style):
    history_item = {
        'prompt': prompt,
        'style': style,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.generation_history.insert(0, history_item)
    if len(st.session_state.generation_history) > 20:
        st.session_state.generation_history.pop()


# ------------------------
# Main App
# ------------------------
def main():
    initialize_session_state()

    st.title("🎨 AI Image Generator")
    st.markdown("**Professional image generation powered by Stability AI**")

    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        get_api_key()  # ensures key is set
        st.success("✅ Stability AI Connected")

        st.metric("Images Created", len(st.session_state.generation_history))

        if st.button("🗑️ Clear History"):
            st.session_state.generation_history = []
            st.success("History cleared!")

        if st.session_state.generation_history:
            st.subheader("📚 Recent Generations")
            for i, item in enumerate(st.session_state.generation_history[:5]):
                with st.expander(f"🎨 {item['timestamp'][:10]}"):
                    st.write(f"**Prompt:** {item['prompt'][:50]}...")
                    st.write(f"**Style:** {item['style']}")
                    if st.button("🔄 Use Again", key=f"reuse_{i}"):
                        st.session_state.selected_prompt = item['prompt']
                        st.rerun()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🎨 Generate", "🔄 Transform", "⬆️ Upscale"])

    # ------------------------
    # Tab 1: Generate
    # ------------------------
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            prompt_value = st.session_state.selected_prompt or ""
            st.session_state.selected_prompt = ""

            prompt = st.text_area(
                "✨ Describe your image:",
                value=prompt_value,
                height=120,
                placeholder="Professional headshot of a confident businesswoman in modern office"
            )

            st.subheader("⚙️ Generation Settings")
            col1a, col1b = st.columns(2)
            with col1a:
                style = st.selectbox("Art Style:", list(STYLE_PRESETS.keys()))
                num_variants = st.slider("Number of Images:", 1, 4, 2)
            with col1b:
                aspect_ratio = st.selectbox("Aspect Ratio:", list(ASPECT_RATIOS.keys()))

            if st.button("🎨 Generate Images", type="primary", disabled=not prompt):
                try:
                    with st.spinner("Generating images..."):
                        images = generate_images(prompt, style, aspect_ratio, num_variants)
                    save_to_history(prompt, style)

                    cols = st.columns(len(images))
                    for i, img in enumerate(images):
                        with cols[i % len(cols)]:
                            st.image(img, caption=f"Variant {i+1}", use_container_width=True)
                            buf = io.BytesIO()
                            img.save(buf, format='PNG')
                            st.download_button(
                                f"📥 Download {i+1}",
                                buf.getvalue(),
                                f"generated_{i+1}.png",
                                "image/png"
                            )
                except Exception as e:
                    st.error(f"❌ Generation failed: {str(e)}")

    # ------------------------
    # Tab 2: Transform
    # ------------------------
    with tab2:
        st.header("🔄 Transform Images")
        uploaded_file = st.file_uploader("Upload image to transform:", type=['png', 'jpg', 'jpeg'])

        if uploaded_file:
            uploaded_image = Image.open(uploaded_file)
            st.image(uploaded_image, caption="Original Image", use_container_width=True)

            transform_prompt = st.text_area("Describe the transformation:", height=100)
            col2a, col2b = st.columns(2)
            with col2a:
                transform_style = st.selectbox("Style:", list(STYLE_PRESETS.keys()))
            with col2b:
                strength = st.slider("Transformation Strength:", 0.3, 1.0, 0.7, 0.1)

            if st.button("🔄 Transform Image", type="primary", disabled=not transform_prompt):
                try:
                    with st.spinner("Transforming your image..."):
                        transformed_image = transform_image(uploaded_image, transform_prompt, transform_style, strength)
                    st.success("✅ Image transformed successfully!")

                    col_before, col_after = st.columns(2)
                    with col_before:
                        st.image(uploaded_image, caption="Before", use_container_width=True)
                    with col_after:
                        st.image(transformed_image, caption="After", use_container_width=True)

                    buf = io.BytesIO()
                    transformed_image.save(buf, format='PNG')
                    st.download_button("📥 Download Transformed Image", buf.getvalue(), "transformed.png", "image/png")
                except Exception as e:
                    st.error(f"❌ Transformation failed: {str(e)}")

    # ------------------------
    # Tab 3: Upscale
    # ------------------------
    with tab3:
        st.header("⬆️ Upscale Images")
        upscale_file = st.file_uploader("Upload image to upscale:", type=['png', 'jpg', 'jpeg'], key="upscale_upload")

        if upscale_file:
            upscale_input = Image.open(upscale_file)
            original_size = upscale_input.size
            st.image(upscale_input, caption=f"Original ({original_size[0]}x{original_size[1]})", use_container_width=True)

            if st.button("⬆️ Upscale Image", type="primary"):
                try:
                    with st.spinner("Upscaling your image..."):
                        upscaled_result = upscale_image(upscale_input)
                    new_size = upscaled_result.size
                    st.success(f"✅ Upscaled to {new_size[0]}x{new_size[1]}")

                    col_orig, col_up = st.columns(2)
                    with col_orig:
                        st.image(upscale_input, caption="Original", use_container_width=True)
                    with col_up:
                        st.image(upscaled_result, caption="Upscaled", use_container_width=True)

                    buf = io.BytesIO()
                    upscaled_result.save(buf, format='PNG')
                    st.download_button("📥 Download Upscaled Image", buf.getvalue(), "upscaled.png", "image/png")
                except Exception as e:
                    st.error(f"❌ Upscaling failed: {str(e)}")


if __name__ == "__main__":
    main()
