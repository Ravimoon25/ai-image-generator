"""AI Image Generator - Single File Version"""

import streamlit as st
import requests
from PIL import Image
import io
from datetime import datetime
from typing import List, Tuple

# Page configuration
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide"
)

# Configuration constants
STYLE_PRESETS = {
    "None": "",
    "Photorealistic": "ultra-realistic, high-definition, professional photography, sharp details",
    "Digital Art": "digital painting, concept art, detailed illustration, vibrant colors",
    "Cartoon Style": "cartoon, animated style, colorful and fun, playful",
    "Oil Painting": "classical oil painting, artistic brushstrokes, textured canvas"
}

ASPECT_RATIOS = {
    "Square (1:1)": "1:1",
    "Portrait (9:16)": "9:16", 
    "Landscape (16:9)": "16:9"
}

QUICK_TEMPLATES = [
    "Professional headshot, business attire, confident expression, office background",
    "Corporate executive portrait, formal suit, leadership pose, modern office",
    "Creative professional, artistic background, innovative pose, studio setting",
    "LinkedIn profile photo, professional clothing, approachable smile, neutral background"
]

def generate_image(prompt: str, style: str, aspect_ratio: str) -> Image.Image:
    """Generate image using Stability AI"""
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    
    if not api_key:
        raise ValueError("API key not configured")
    
    # Enhance prompt
    enhanced_prompt = prompt
    if style != "None" and style in STYLE_PRESETS:
        enhanced_prompt = f"{prompt}, {STYLE_PRESETS[style]}"
    enhanced_prompt = f"{enhanced_prompt}, high quality, detailed, professional"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }
    
    data = {
        "prompt": enhanced_prompt,
        "aspect_ratio": ASPECT_RATIOS[aspect_ratio],
        "output_format": "png"
    }
    
    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/core",
        headers=headers,
        files={"none": ""},
        data=data,
        timeout=60
    )
    
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        raise Exception(f"API Error: {response.text}")

def main():
    st.title("🎨 AI Image Generator")
    st.markdown("Professional image generation powered by Stability AI")
    
    # Check API key
    if not st.secrets.get("STABILITY_API_KEY"):
        st.error("Please add STABILITY_API_KEY to your Streamlit secrets")
        st.stop()
    else:
        st.success("✅ Stability AI Connected")
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        prompt = st.text_area(
            "Describe your image:",
            height=100,
            placeholder="Professional headshot of a confident businesswoman"
        )
        
        col1a, col1b = st.columns(2)
        with col1a:
            style = st.selectbox("Style:", list(STYLE_PRESETS.keys()))
        with col1b:
            aspect_ratio = st.selectbox("Aspect Ratio:", list(ASPECT_RATIOS.keys()))
        
        st.info("💰 Cost: $0.04 per image")
        
        if st.button("🎨 Generate Image", type="primary", disabled=not prompt):
            try:
                with st.spinner("Generating..."):
                    image = generate_image(prompt, style, aspect_ratio)
                
                st.success("✅ Image generated successfully!")
                st.image(image, use_column_width=True)
                
                # Download button
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                st.download_button(
                    "📥 Download Image",
                    buf.getvalue(),
                    "generated_image.png",
                    "image/png"
                )
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.subheader("🚀 Quick Templates")
        for i, template in enumerate(QUICK_TEMPLATES):
            if st.button(template[:30] + "...", key=f"template_{i}"):
                st.session_state.selected_template = template
                st.rerun()
        
        # Apply template
        if "selected_template" in st.session_state:
            prompt = st.session_state.selected_template
            del st.session_state.selected_template

if __name__ == "__main__":
    main()
