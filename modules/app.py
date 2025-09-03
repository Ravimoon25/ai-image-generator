"""Main Streamlit application for AI Image Generator"""

import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.image_generator import StabilityImageGenerator
from modules.config import STYLE_PRESETS, ASPECT_RATIOS, QUICK_TEMPLATES
import io
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0.0

def create_download_button(image, filename, key):
    """Create download button for image"""
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return st.download_button(
        f"📥 Download {filename}",
        buf.getvalue(),
        f"{filename}.png",
        "image/png",
        key=key
    )

def main():
    # Initialize
    initialize_session_state()
    generator = StabilityImageGenerator()
    
    # Header
    st.title("🎨 AI Image Generator")
    st.markdown("**Professional image generation powered by Stability AI**")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        if not generator.check_api_key():
            st.error("⚠️ Please add your Stability AI API key to secrets")
            st.code('STABILITY_API_KEY = "your-key-here"')
            st.stop()
        else:
            st.success("✅ Stability AI Connected")
        
        st.metric("Session Cost", f"${st.session_state.total_cost:.3f}")
        st.metric("Images Generated", len(st.session_state.generation_history))
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        prompt = st.text_area(
            "✨ Describe your image:",
            height=100,
            placeholder="Professional headshot of a confident businesswoman in modern office"
        )
        
        # Settings
        col1a, col1b = st.columns(2)
        with col1a:
            style = st.selectbox("Style:", list(STYLE_PRESETS.keys()))
            num_variants = st.slider("Variants:", 1, 4, 2)
        
        with col1b:
            aspect_ratio = st.selectbox("Aspect Ratio:", list(ASPECT_RATIOS.keys()))
        
        # Cost estimation
        estimated_cost = num_variants * 0.04
        st.info(f"💰 Estimated cost: ${estimated_cost:.2f} for {num_variants} images")
        
        # Generate button
        if st.button("🎨 Generate Images", type="primary", disabled=not prompt):
            try:
                with st.spinner("Generating..."):
                    images, cost = generator.generate_multiple(prompt, num_variants, style, aspect_ratio)
                
                if images:
                    st.success(f"✅ Generated {len(images)} images for ${cost:.3f}")
                    
                    # Display images
                    if len(images) == 1:
                        st.image(images[0], use_column_width=True)
                        create_download_button(images[0], "generated_image", "download_0")
                    else:
                        cols = st.columns(len(images))
                        for i, img in enumerate(images):
                            with cols[i]:
                                st.image(img, caption=f"Image {i+1}")
                                create_download_button(img, f"image_{i+1}", f"download_{i}")
                    
                    # Update session state
                    st.session_state.total_cost += cost
                    st.session_state.generation_history.append({
                        "prompt": prompt,
                        "style": style,
                        "variants": len(images),
                        "cost": cost,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.subheader("🚀 Quick Templates")
        
        for category, templates in QUICK_TEMPLATES.items():
            with st.expander(f"📁 {category}"):
                for i, template in enumerate(templates):
                    if st.button(f"{template[:40]}...", key=f"template_{category}_{i}"):
                        st.session_state.template_selected = template
                        st.rerun()
        
        # Apply selected template
        if hasattr(st.session_state, 'template_selected'):
            prompt = st.session_state.template_selected
            del st.session_state.template_selected

if __name__ == "__main__":
    main()
