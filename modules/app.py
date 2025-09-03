"""AI Image Generator - Enhanced Version"""

import streamlit as st
import requests
from PIL import Image
import io
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
.template-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 0.8rem;
    border-radius: 6px;
    margin: 0.3rem 0;
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
    "Square (1:1)": "1:1",
    "Portrait (9:16)": "9:16", 
    "Landscape (16:9)": "16:9",
    "Wide (21:9)": "21:9"
}

QUICK_TEMPLATES = {
    "Professional": [
        "Professional headshot, business attire, confident expression, office background",
        "Corporate executive portrait, formal suit, leadership pose, modern office",
        "LinkedIn profile photo, professional clothing, approachable smile, neutral background",
        "Business team leader, confident stance, professional environment"
    ],
    "Creative": [
        "Artist in creative studio, inspiring workspace, natural lighting, thoughtful expression",
        "Designer at modern workspace, creative environment, focused expression, artistic tools",
        "Creative professional, artistic background, innovative pose, contemporary studio",
        "Content creator workspace, colorful setup, engaging personality"
    ],
    "Social Media": [
        "Instagram-ready portrait, trendy outfit, engaging smile, vibrant background",
        "Lifestyle photo, casual but polished, authentic moment, natural lighting",
        "Social media influencer style, fashionable clothing, dynamic pose",
        "Story-worthy content, relatable expression, modern aesthetic"
    ]
}

def initialize_session_state():
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = ""

def generate_images(prompt: str, style: str, aspect_ratio: str, num_variants: int) -> List[Image.Image]:
    """Generate multiple image variants"""
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    
    if not api_key:
        raise ValueError("API key not configured")
    
    # Enhance prompt
    enhanced_prompt = prompt
    if style != "None" and style in STYLE_PRESETS:
        enhanced_prompt = f"{prompt}, {STYLE_PRESETS[style]}"
    enhanced_prompt = f"{enhanced_prompt}, high quality, detailed, professional, sharp focus"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }
    
    data = {
        "prompt": enhanced_prompt,
        "aspect_ratio": ASPECT_RATIOS[aspect_ratio],
        "output_format": "png"
    }
    
    images = []
    for i in range(num_variants):
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers=headers,
            files={"none": ""},
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            images.append(Image.open(io.BytesIO(response.content)))
        else:
            raise Exception(f"API Error: {response.text}")
    
    return images


def transform_image(uploaded_image: Image.Image, prompt: str, style: str, strength: float = 0.7) -> Image.Image:
    """Transform an existing image using Stability AI image-to-image"""
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    
    if not api_key:
        raise ValueError("API key not configured")
    
    # Enhance prompt
    enhanced_prompt = prompt
    if style != "None" and style in STYLE_PRESETS:
        enhanced_prompt = f"{prompt}, {STYLE_PRESETS[style]}"
    enhanced_prompt = f"{enhanced_prompt}, high quality, detailed, professional"
    
    # Convert PIL image to bytes
    img_byte_arr = io.BytesIO()
    uploaded_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }
    
    files = {
        "image": ("image.png", img_byte_arr, "image/png")
    }
    
    data = {
        "prompt": enhanced_prompt,
        "output_format": "png",
        "strength": strength
    }
    
    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/core/image-to-image",
        headers=headers,
        files=files,
        data=data,
        timeout=60
    )
    
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        raise Exception(f"Image-to-Image API Error: {response.text}")


def upscale_image(uploaded_image: Image.Image) -> Image.Image:
    """Upscale an image using Stability AI upscaling"""
    api_key = st.secrets.get("STABILITY_API_KEY", "")
    
    if not api_key:
        raise ValueError("API key not configured")
    
    # Convert PIL image to bytes
    img_byte_arr = io.BytesIO()
    uploaded_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }
    
    files = {
        "image": ("image.png", img_byte_arr, "image/png")
    }
    
    data = {
        "output_format": "png"
    }
    
    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/upscale/conservative",
        headers=headers,
        files=files,
        data=data,
        timeout=90  # Upscaling takes longer
    )
    
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        raise Exception(f"Upscaling API Error: {response.text}")



def save_to_history(prompt, style, variants):
    """Save generation to history"""
    history_item = {
        'prompt': prompt,
        'style': style,
        'variants': variants,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.generation_history.insert(0, history_item)
    if len(st.session_state.generation_history) > 20:
        st.session_state.generation_history.pop()

def main():
    initialize_session_state()
    
    st.title("🎨 AI Image Generator")
    st.markdown("**Professional image generation powered by Stability AI**")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        if not st.secrets.get("STABILITY_API_KEY"):
            st.error("Please add STABILITY_API_KEY to secrets")
            st.stop()
        else:
            st.success("✅ Stability AI Connected")
        
        st.metric("Images Created", len(st.session_state.generation_history))
        
        if st.button("🗑️ Clear History"):
            st.session_state.generation_history = []
            st.success("History cleared!")
        
        # Recent generations
        if st.session_state.generation_history:
            st.subheader("📚 Recent Generations")
            for i, item in enumerate(st.session_state.generation_history[:5]):
                with st.expander(f"🎨 {item['timestamp'][:10]}"):
                    st.write(f"**Prompt:** {item['prompt'][:50]}...")
                    st.write(f"**Style:** {item['style']}")
                    if st.button("🔄 Use Again", key=f"reuse_{i}"):
                        st.session_state.selected_prompt = item['prompt']
                        st.rerun()
    
    # Main content
    # Main content with tabs
    tab1, tab2, tab3 = st.tabs(["🎨 Generate", "🔄 Transform", "⬆️ Upscale"])
    
    with tab1:
        # Your existing generation code goes here
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Use selected prompt if available
            prompt_value = st.session_state.selected_prompt if st.session_state.selected_prompt else ""
            if st.session_state.selected_prompt:
                st.session_state.selected_prompt = ""  # Clear after use
            
            prompt = st.text_area(
                "✨ Describe your image:",
                value=prompt_value,
                height=120,
                placeholder="Professional headshot of a confident businesswoman in modern office"
            )
            
            # Settings
            st.subheader("⚙️ Generation Settings")
            col1a, col1b, col1c = st.columns(3)
            
            with col1a:
                style = st.selectbox("Art Style:", list(STYLE_PRESETS.keys()))
                num_variants = st.slider("Number of Images:", 1, 4, 2)
            
            with col1b:
                aspect_ratio = st.selectbox("Aspect Ratio:", list(ASPECT_RATIOS.keys()))
                quality_boost = st.checkbox("Enhanced Quality", True)
            
            with col1c:
                batch_mode = st.checkbox("Batch Mode", False)
            
            # ... rest of your existing generation code ...
    
    with tab2:
        # New Image-to-Image tab
        st.header("🔄 Transform Images")
        st.markdown("Upload an image and transform it with AI")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Upload image to transform:",
                type=['png', 'jpg', 'jpeg'],
                help="Upload a clear image for best results"
            )
            
            if uploaded_file:
                uploaded_image = Image.open(uploaded_file)
                st.image(uploaded_image, caption="Original Image", use_column_width=True)
                
                transform_prompt = st.text_area(
                    "Describe the transformation:",
                    height=100,
                    placeholder="Convert to professional headshot style, business attire, office background"
                )
                
                col2a, col2b = st.columns(2)
                with col2a:
                    transform_style = st.selectbox("Style:", list(STYLE_PRESETS.keys()), key="transform_style")
                with col2b:
                    strength = st.slider("Transformation Strength:", 0.3, 1.0, 0.7, 0.1)
                
                if st.button("🔄 Transform Image", type="primary", disabled=not transform_prompt):
                    try:
                        with st.spinner("Transforming your image..."):
                            transformed_image = transform_image(uploaded_image, transform_prompt, transform_style, strength)
                        
                        st.success("✅ Image transformed successfully!")
                        
                        # Before/After comparison
                        col_before, col_after = st.columns(2)
                        with col_before:
                            st.image(uploaded_image, caption="Before", use_column_width=True)
                        with col_after:
                            st.image(transformed_image, caption="After", use_column_width=True)
                        
                        # Download button
                        buf = io.BytesIO()
                        transformed_image.save(buf, format='PNG')
                        st.download_button(
                            "📥 Download Transformed Image",
                            buf.getvalue(),
                            "transformed_image.png",
                            "image/png"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Transformation failed: {str(e)}")
        
        with col2:
            st.subheader("💡 Transform Tips")
            st.markdown("""
            **Strength Settings:**
            - 0.3-0.5: Subtle changes
            - 0.6-0.7: Moderate transformation
            - 0.8-1.0: Strong changes
            
            **Best Results:**
            - Use clear, well-lit images
            - Be specific in descriptions
            - Try different strength values
            """)
    
    with tab3:
        # Upscale tab
        st.header("⬆️ Upscale Images")
        st.markdown("Enhance image resolution up to 4x with AI")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            upscale_file = st.file_uploader(
                "Upload image to upscale:",
                type=['png', 'jpg', 'jpeg'],
                help="Works best with images 512x512 or larger",
                key="upscale_upload"
            )
            
            if upscale_file:
                upscale_image_input = Image.open(upscale_file)
                original_size = upscale_image_input.size
                st.image(upscale_image_input, caption=f"Original ({original_size[0]}x{original_size[1]})", use_column_width=True)
                
                if st.button("⬆️ Upscale Image", type="primary"):
                    try:
                        with st.spinner("Upscaling your image... This may take a minute"):
                            upscaled_result = upscale_image(upscale_image_input)
                        
                        new_size = upscaled_result.size
                        st.success(f"✅ Image upscaled from {original_size[0]}x{original_size[1]} to {new_size[0]}x{new_size[1]}")
                        
                        # Before/After comparison
                        col_orig, col_upscaled = st.columns(2)
                        with col_orig:
                            st.image(upscale_image_input, caption=f"Original ({original_size[0]}x{original_size[1]})", use_column_width=True)
                        with col_upscaled:
                            st.image(upscaled_result, caption=f"Upscaled ({new_size[0]}x{new_size[1]})", use_column_width=True)
                        
                        # Download button
                        buf = io.BytesIO()
                        upscaled_result.save(buf, format='PNG')
                        st.download_button(
                            "📥 Download Upscaled Image",
                            buf.getvalue(),
                            "upscaled_image.png",
                            "image/png"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Upscaling failed: {str(e)}")
        
        with col2:
            st.subheader("ℹ️ Upscaling Info")
            st.markdown("""
            **What it does:**
            - Increases resolution up to 4x
            - Enhances details and sharpness
            - Reduces blur and artifacts
            
            **Best for:**
            - Generated AI images
            - Photos that need enhancement
            - Images for printing
            
            **Tips:**
            - Works best on images 512px+
            - May take 30-60 seconds
            - Larger files will be created
            """)




if __name__ == "__main__":
    main()
