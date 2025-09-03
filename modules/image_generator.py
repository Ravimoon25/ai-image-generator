"""Core image generation functionality using Stability AI API"""

import requests
import streamlit as st
from PIL import Image
import io
from typing import List, Tuple, Optional
from datetime import datetime

from .config import STABILITY_API_CONFIG, STYLE_PRESETS, ASPECT_RATIOS

class StabilityImageGenerator:
    """Handle image generation using Stability AI API"""
    
    def __init__(self):
        self.api_key = st.secrets.get("STABILITY_API_KEY", "")
        self.base_url = STABILITY_API_CONFIG["base_url"]
        self.cost_per_image = STABILITY_API_CONFIG["cost_per_image"]
        
    def check_api_key(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    def enhance_prompt(self, prompt: str, style: str = "None", quality_boost: bool = True) -> str:
        """Enhance user prompt with style and quality improvements"""
        enhanced = prompt.strip()
        
        if style != "None" and style in STYLE_PRESETS:
            style_text = STYLE_PRESETS[style]
            if style_text:
                enhanced = f"{enhanced}, {style_text}"
        
        if quality_boost:
            enhanced = f"{enhanced}, high quality, detailed, professional, sharp focus"
        
        return enhanced
    
    def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> Image.Image:
        """Generate a single image using Stability AI API"""
        if not self.check_api_key():
            raise ValueError("Stability AI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/*"
        }
        
        data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png"
        }
        
        try:
            response = requests.post(
                self.base_url, 
                headers=headers, 
                files={"none": ""}, 
                data=data,
                timeout=STABILITY_API_CONFIG["timeout"]
            )
            
            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content))
            else:
                raise Exception(f"API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Generation failed: {str(e)}")
    
    def generate_multiple(self, prompt: str, num_variants: int, style: str, aspect_ratio: str) -> Tuple[List[Image.Image], float]:
        """Generate multiple image variants"""
        enhanced_prompt = self.enhance_prompt(prompt, style, True)
        api_aspect_ratio = ASPECT_RATIOS.get(aspect_ratio, "1:1")
        
        results = []
        total_cost = 0.0
        
        for i in range(num_variants):
            image = self.generate_image(enhanced_prompt, api_aspect_ratio)
            results.append(image)
            total_cost += self.cost_per_image
        
        return results, total_cost
