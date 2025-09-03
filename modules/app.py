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
        
        # Batch prompts
        if batch_mode:
            batch_text = st.text_area(
                "Multiple prompts (one per line):",
                height=80,
                placeholder="Professional headshot\nCasual portrait\nCreative workspace"
            )
        
        # Generate button
        generate_label = "🎨 Generate Images" if not batch_mode else "🎨 Generate Batch"
        can_generate = prompt if not batch_mode else batch_text
        
        if st.button(generate_label, type="primary", disabled=not can_generate):
            try:
                if batch_mode and batch_text:
                    # Batch generation
                    prompts = [p.strip() for p in batch_text.split('\n') if p.strip()]
                    all_images = []
                    
                    progress_bar = st.progress(0)
                    for i, batch_prompt in enumerate(prompts):
                        st.text(f"Generating: {batch_prompt[:40]}...")
                        images = generate_images(batch_prompt, style, aspect_ratio, 1)
                        all_images.extend(images)
                        progress_bar.progress((i + 1) / len(prompts))
                        save_to_history(batch_prompt, style, 1)
                    
                    st.success(f"✅ Generated {len(all_images)} images from {len(prompts)} prompts")
                    
                    # Display batch results
                    cols = st.columns(3)
                    for i, img in enumerate(all_images):
                        with cols[i % 3]:
                            st.image(img, caption=f"Image {i+1}")
                
                else:
                    # Single generation
                    with st.spinner(f"Creating {num_variants} images..."):
                        images = generate_images(prompt, style, aspect_ratio, num_variants)
                    
                    if images:
                        st.success(f"✅ Created {len(images)} images successfully!")
                        
                        # Display images
                        if len(images) == 1:
                            st.image(images[0], use_column_width=True)
                        else:
                            cols = st.columns(min(3, len(images)))
                            for i, img in enumerate(images):
                                with cols[i % 3]:
                                    st.image(img, caption=f"Variant {i+1}")
                        
                        save_to_history(prompt, style, len(images))
                
                # Download buttons
                if 'images' in locals() and images:
                    for i, img in enumerate(images):
                        buf = io.BytesIO()
                        img.save(buf, format='PNG')
                        st.download_button(
                            f"📥 Download Image {i+1}",
                            buf.getvalue(),
                            f"ai_generated_{i+1}.png",
                            "image/png",
                            key=f"download_{i}"
                        )
                
            except Exception as e:
                st.error(f"❌ Generation failed: {str(e)}")
    
    with col2:
        st.subheader("🚀 Quick Templates")
        
        for category, templates in QUICK_TEMPLATES.items():
            with st.expander(f"📁 {category}"):
                for i, template in enumerate(templates):
                    if st.button(template[:35] + "...", key=f"template_{category}_{i}", help=template):
                        st.session_state.selected_prompt = template
                        st.rerun()

if __name__ == "__main__":
    main()
