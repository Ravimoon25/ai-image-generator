import base64
import io
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
import streamlit as st
from PIL import Image

"""
Streamlit AI Image Studio (Stability API v1)
- Tabs: Generate, Transform, Inpaint, Upscale, Variations
- Models: SDXL 1.0, SD 1.6 (text/img), ESRGAN x2 (upscale)
- Uses Stability REST API v1 endpoints only (stable + consistent)

Deployment notes:
- Add your API key to Streamlit Secrets as STABILITY_API_KEY
- This app keeps costs down by defaulting to SDXL single-sample runs
- Dimensions validated for SDXL; SD1.6 accepts broader ranges

Docs used:
- /v1/generation/{engine_id}/text-to-image
- /v1/generation/{engine_id}/image-to-image
- /v1/generation/{engine_id}/image-to-image/masking
- /v1/generation/{engine_id}/image-to-image/upscale (ESRGAN or Latent)
"""

# ----------------------------
# Config & Constants
# ----------------------------
PAGE_TITLE = "🎨 AI Image Studio — Stability API"
DEFAULT_ENGINE = "stable-diffusion-xl-1024-v1-0"  # SDXL 1.0
FALLBACK_ENGINE = "stable-diffusion-v1-6"          # SD 1.6
ESRGAN_ENGINE = "esrgan-v1-x2plus"                 # Upscale

STYLE_PRESETS = [
    "enhance", "photographic", "digital-art", "cinematic", "anime", "comic-book",
    "fantasy-art", "line-art", "analog-film", "neon-punk", "isometric", "low-poly",
    "origami", "3d-model", "pixel-art", "tile-texture"
]

# SDXL-valid width/height combos (multiples of 64; official list)
SDXL_DIM_CHOICES = {
    "Square 1024x1024": (1024, 1024),
    "Landscape 1344x768": (1344, 768),
    "Landscape Tall 1536x640": (1536, 640),
    "Portrait 768x1344": (768, 1344),
    "Portrait Slim 640x1536": (640, 1536),
    "Near-Square 1152x896": (1152, 896),
    "Near-Square 896x1152": (896, 1152),
    "Near-Square 1216x832": (1216, 832),
    "Near-Square 832x1216": (832, 1216),
}

NEGATIVE_DEFAULT = (
    "low quality, worst quality, jpeg artifacts, blurry, deformed, extra fingers, extra limbs,"
    " watermark, text, logo"
)

# ----------------------------
# Helpers — API plumbing
# ----------------------------

def _get_api_host() -> str:
    return os.getenv("API_HOST", "https://api.stability.ai")


def _get_api_key() -> str:
    # Prefer Streamlit secrets for deployments
    key = st.secrets.get("STABILITY_API_KEY", None)
    if not key:
        key = os.getenv("STABILITY_API_KEY", "")
    return key


def _headers(accept_png: bool = False) -> Dict[str, str]:
    h = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Accept": "image/png" if accept_png else "application/json",
    }
    # Optional client metadata (helps org dashboards)
    h["Stability-Client-ID"] = "streamlit-ai-image-studio"
    h["Stability-Client-Version"] = "1.0.0"
    return h


def _assert_api_key():
    if not _get_api_key():
        st.error("Missing STABILITY_API_KEY — set it in Streamlit Secrets.")
        st.stop()


def _decode_artifacts_to_pil(json_resp: dict) -> List[Image.Image]:
    imgs: List[Image.Image] = []
    arts = json_resp.get("artifacts", [])
    for art in arts:
        b64 = art.get("base64")
        if not b64:
            continue
        img_bytes = base64.b64decode(b64)
        imgs.append(Image.open(io.BytesIO(img_bytes)))
    return imgs


def _post_json(url: str, payload: dict) -> dict:
    r = requests.post(url, headers=_headers(accept_png=False), json=payload, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return r.json()


def _post_multipart(url: str, files: dict, data: dict) -> dict:
    r = requests.post(url, headers=_headers(accept_png=False), files=files, data=data, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return r.json()


# ----------------------------
# API wrappers (v1)
# ----------------------------

def txt2img(
    engine_id: str,
    prompt: str,
    negative_prompt: Optional[str],
    width: int,
    height: int,
    cfg_scale: float = 7,
    steps: int = 30,
    samples: int = 1,
    style_preset: Optional[str] = None,
    seed: int = 0,
) -> List[Image.Image]:
    url = f"{_get_api_host()}/v1/generation/{engine_id}/text-to-image"
    text_prompts = [{"text": prompt, "weight": 1.0}]
    if negative_prompt:
        text_prompts.append({"text": negative_prompt, "weight": -1.0})

    payload = {
        "text_prompts": text_prompts,
        "cfg_scale": cfg_scale,
        "height": height,
        "width": width,
        "steps": steps,
        "samples": samples,
    }
    if style_preset:
        payload["style_preset"] = style_preset
    if seed:
        payload["seed"] = seed

    resp = _post_json(url, payload)
    return _decode_artifacts_to_pil(resp)


def img2img(
    engine_id: str,
    init_image: Image.Image,
    prompt: str,
    negative_prompt: Optional[str],
    image_strength: float = 0.65,
    steps: int = 30,
    samples: int = 1,
    style_preset: Optional[str] = None,
    seed: int = 0,
    init_image_mode: str = "IMAGE_STRENGTH",  # or STEP_SCHEDULE
) -> List[Image.Image]:
    url = f"{_get_api_host()}/v1/generation/{engine_id}/image-to-image"

    # Convert image to bytes
    buf = io.BytesIO()
    init_image.save(buf, format="PNG")
    buf.seek(0)

    files = {
        "init_image": ("init.png", buf, "image/png"),
    }

    data = {
        "image_strength": str(image_strength),
        "init_image_mode": init_image_mode,
        "steps": str(steps),
        "samples": str(samples),
        "text_prompts[0][text]": prompt,
        "text_prompts[0][weight]": "1",
    }
    if negative_prompt:
        data["text_prompts[1][text]"] = negative_prompt
        data["text_prompts[1][weight]"] = "-1"
    if style_preset:
        data["style_preset"] = style_preset
    if seed:
        data["seed"] = str(seed)

    resp = _post_multipart(url, files=files, data=data)
    return _decode_artifacts_to_pil(resp)


def inpaint(
    engine_id: str,
    init_image: Image.Image,
    mask_image: Image.Image,
    prompt: str,
    negative_prompt: Optional[str],
    mask_source: str = "MASK_IMAGE_WHITE",  # or MASK_IMAGE_BLACK, INIT_IMAGE_ALPHA
    steps: int = 30,
    samples: int = 1,
    style_preset: Optional[str] = None,
    seed: int = 0,
    cfg_scale: float = 7,
) -> List[Image.Image]:
    # Ensure same size
    if init_image.size != mask_image.size:
        mask_image = mask_image.resize(init_image.size, Image.NEAREST)

    url = f"{_get_api_host()}/v1/generation/{engine_id}/image-to-image/masking"

    # Bytes
    buf_init = io.BytesIO(); init_image.save(buf_init, format="PNG"); buf_init.seek(0)
    buf_mask = io.BytesIO(); mask_image.save(buf_mask, format="PNG"); buf_mask.seek(0)

    files = {
        "init_image": ("init.png", buf_init, "image/png"),
        "mask_image": ("mask.png", buf_mask, "image/png"),
    }

    data = {
        "mask_source": mask_source,
        "steps": str(steps),
        "samples": str(samples),
        "cfg_scale": str(cfg_scale),
        "text_prompts[0][text]": prompt,
        "text_prompts[0][weight]": "1",
    }
    if negative_prompt:
        data["text_prompts[1][text]"] = negative_prompt
        data["text_prompts[1][weight]"] = "-1"
    if style_preset:
        data["style_preset"] = style_preset
    if seed:
        data["seed"] = str(seed)

    resp = _post_multipart(url, files=files, data=data)
    return _decode_artifacts_to_pil(resp)


def upscale_esrgan(
    image: Image.Image,
    desired_w: Optional[int] = None,
    desired_h: Optional[int] = None,
) -> Image.Image:
    """Two ways: ESRGAN x2 (default), or supply either width OR height (>=512)."""
    url = f"{_get_api_host()}/v1/generation/{ESRGAN_ENGINE}/image-to-image/upscale"

    buf = io.BytesIO(); image.save(buf, format="PNG"); buf.seek(0)
    files = {"image": ("img.png", buf, "image/png")}
    data = {}
    if desired_w:
        data["width"] = str(desired_w)
    if desired_h:
        data["height"] = str(desired_h)

    resp = _post_multipart(url, files=files, data=data)
    imgs = _decode_artifacts_to_pil(resp)
    if not imgs:
        raise RuntimeError("Upscale returned no images")
    return imgs[0]


# ----------------------------
# UI helpers
# ----------------------------

def sidebar_status():
    st.sidebar.header("📊 Dashboard")
    if not _get_api_key():
        st.sidebar.error("Add STABILITY_API_KEY in Secrets")
    else:
        st.sidebar.success("✅ API Connected")

    if "history" not in st.session_state:
        st.session_state.history = []  # list of dict

    st.sidebar.metric("Images Created", sum(len(h.get("images", [])) for h in st.session_state.history))

    if st.sidebar.button("🗑️ Clear History"):
        st.session_state.history = []
        st.sidebar.success("History cleared")

    if st.session_state.history:
        st.sidebar.subheader("📚 Recent")
        for i, item in enumerate(st.session_state.history[:5]):
            with st.sidebar.expander(f"{item['ts']}"):
                st.write(f"**Mode:** {item['mode']}")
                st.write(f"**Model:** {item['engine']}")
                st.write(f"**Prompt:** {item['prompt'][:80]}...")


def dim_selector(engine_choice: str) -> Tuple[int, int]:
    if engine_choice == DEFAULT_ENGINE:
        label = st.selectbox("Aspect / Size (SDXL)", list(SDXL_DIM_CHOICES.keys()))
        w, h = SDXL_DIM_CHOICES[label]
        return w, h
    else:
        # SD 1.6 — allow more freeform (still keep multiples of 64)
        colw, colh = st.columns(2)
        with colw:
            w = st.number_input("Width (64-step)", min_value=320, max_value=1536, step=64, value=768)
        with colh:
            h = st.number_input("Height (64-step)", min_value=320, max_value=1536, step=64, value=768)
        return int(w), int(h)


def add_to_history(mode: str, engine: str, prompt: str, images: List[Image.Image]):
    st.session_state.history.insert(0, {
        "mode": mode,
        "engine": engine,
        "prompt": prompt,
        "count": len(images),
        "images": images[:4],
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    # Cap history
    st.session_state.history = st.session_state.history[:20]


# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title=PAGE_TITLE, page_icon="🎨", layout="wide", initial_sidebar_state="expanded")
st.title("🎨 AI Image Studio — Stability API v1")
st.caption("Generate • Transform • Inpaint • Upscale • Variations")

# Sidebar
sidebar_status()

# Global model choice for T2I & I2I
ENGINE = st.sidebar.selectbox(
    "Model (text & transform)",
    [DEFAULT_ENGINE, FALLBACK_ENGINE],
    format_func=lambda x: "SDXL 1.0 (high quality)" if x == DEFAULT_ENGINE else "SD 1.6 (fast & cheap)",
)

with st.sidebar.expander("⚙️ Advanced defaults"):
    default_cfg = st.slider("CFG Scale", 0.0, 20.0, 7.0, 0.5)
    default_steps = st.slider("Steps", 10, 50, 30, 1)

# Tabs
TAB_GEN, TAB_I2I, TAB_INPAINT, TAB_UPSCALE, TAB_VARIATIONS = st.tabs([
    "🎨 Generate", "🔄 Transform", "🎯 Inpaint / Edit", "⬆️ Upscale", "🧬 Variations"
])

# ----------------------------
# Tab: Generate (Text-to-Image)
# ----------------------------
with TAB_GEN:
    st.subheader("Text → Image")
    prompt = st.text_area("Prompt", placeholder="A cinematic portrait of a traveler under neon rain")
    negative = st.text_input("Negative prompt (optional)", value=NEGATIVE_DEFAULT)
    w, h = dim_selector(ENGINE)

    col1, col2, col3 = st.columns(3)
    with col1:
        style = st.selectbox("Style preset (optional)", ["None"] + STYLE_PRESETS)
        style = None if style == "None" else style
    with col2:
        samples = st.slider("Number of images", 1, 4, 1)
    with col3:
        seed = st.number_input("Seed (0=random)", min_value=0, max_value=2_147_483_647, value=0, step=1)

    go = st.button("🚀 Generate", type="primary", disabled=not prompt)

    if go:
        _assert_api_key()
        try:
            with st.spinner("Generating..."):
                imgs = txt2img(
                    engine_id=ENGINE,
                    prompt=prompt,
                    negative_prompt=negative or None,
                    width=w, height=h,
                    cfg_scale=default_cfg,
                    steps=default_steps,
                    samples=samples,
                    style_preset=style,
                    seed=seed,
                )
            if not imgs:
                st.warning("No images returned.")
            else:
                cols = st.columns(min(4, len(imgs)))
                for i, im in enumerate(imgs):
                    with cols[i % len(cols)]:
                        st.image(im, use_column_width=True)
                        buf = io.BytesIO(); im.save(buf, format="PNG")
                        st.download_button(
                            f"📥 Download #{i+1}", buf.getvalue(), file_name=f"gen_{i+1}.png", mime="image/png"
                        )
                add_to_history("Generate", ENGINE, prompt, imgs)
        except Exception as e:
            st.error(f"❌ Generation failed: {e}")

# ----------------------------
# Tab: Transform (Image-to-Image)
# ----------------------------
with TAB_I2I:
    st.subheader("Image → Image (Stylize / Modify)")
    up = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"], key="i2i_up")
    t_prompt = st.text_area("Describe the target style/content", placeholder="Professional headshot, soft light, clean background")
    t_negative = st.text_input("Negative prompt (optional)", value=NEGATIVE_DEFAULT, key="i2i_neg")

    c1, c2, c3 = st.columns(3)
    with c1:
        t_style = st.selectbox("Style preset", ["None"] + STYLE_PRESETS, key="i2i_style")
        t_style = None if t_style == "None" else t_style
    with c2:
        strength = st.slider("Transformation strength", 0.10, 0.95, 0.65, 0.05)
    with c3:
        t_seed = st.number_input("Seed (0=random)", 0, 2_147_483_647, 0, key="i2i_seed")

    go_t = st.button("🔄 Transform", type="primary", disabled=not (up and t_prompt))

    if go_t and up and t_prompt:
        _assert_api_key()
        try:
            init = Image.open(up).convert("RGBA")
            with st.spinner("Transforming..."):
                imgs = img2img(
                    engine_id=ENGINE,
                    init_image=init,
                    prompt=t_prompt,
                    negative_prompt=t_negative or None,
                    image_strength=float(strength),
                    steps=default_steps,
                    samples=1,
                    style_preset=t_style,
                    seed=int(t_seed),
                )
            if not imgs:
                st.warning("No image returned.")
            else:
                before, after = st.columns(2)
                with before:
                    st.image(init, caption="Original", use_column_width=True)
                with after:
                    st.image(imgs[0], caption="Transformed", use_column_width=True)
                    buf = io.BytesIO(); imgs[0].save(buf, format="PNG")
                    st.download_button("📥 Download", buf.getvalue(), file_name="transformed.png", mime="image/png")
                add_to_history("Transform", ENGINE, t_prompt, imgs)
        except Exception as e:
            st.error(f"❌ Transformation failed: {e}")

# ----------------------------
# Tab: Inpaint / Edit (Masking)
# ----------------------------
with TAB_INPAINT:
    st.subheader("Inpaint / Edit with Mask")
    base = st.file_uploader("Upload base image", type=["png", "jpg", "jpeg"], key="mask_base")
    mask = st.file_uploader("Upload mask (white = replace, black = keep)", type=["png", "jpg", "jpeg"], key="mask_mask")
    p = st.text_area("Describe what to add/replace", placeholder="Replace the sky with dramatic storm clouds")
    n = st.text_input("Negative prompt (optional)", value=NEGATIVE_DEFAULT, key="mask_neg")

    m1, m2, m3 = st.columns(3)
    with m1:
        mask_source = st.selectbox("Mask interpretation", ["MASK_IMAGE_WHITE", "MASK_IMAGE_BLACK", "INIT_IMAGE_ALPHA"], index=0)
    with m2:
        i_steps = st.slider("Steps", 10, 50, default_steps)
    with m3:
        i_seed = st.number_input("Seed (0=random)", 0, 2_147_483_647, 0, key="mask_seed")

    go_m = st.button("🎯 Inpaint", type="primary", disabled=not (base and (mask or mask_source == "INIT_IMAGE_ALPHA") and p))

    if go_m and base and p:
        _assert_api_key()
        try:
            base_im = Image.open(base).convert("RGBA")
            if mask_source != "INIT_IMAGE_ALPHA":
                if not mask:
                    st.error("Mask image required unless using INIT_IMAGE_ALPHA.")
                    st.stop()
                mask_im = Image.open(mask).convert("L")  # grayscale
            else:
                # Use alpha channel of the base image
                mask_im = Image.new("L", base_im.size, 0)  # placeholder (API requires a field; not used when INIT_IMAGE_ALPHA)

            with st.spinner("Inpainting..."):
                imgs = inpaint(
                    engine_id=ENGINE,
                    init_image=base_im,
                    mask_image=mask_im,
                    prompt=p,
                    negative_prompt=n or None,
                    mask_source=mask_source,
                    steps=int(i_steps),
                    samples=1,
                    style_preset=None,
                    seed=int(i_seed),
                    cfg_scale=float(default_cfg),
                )
            if not imgs:
                st.warning("No image returned.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.image(base_im, caption="Original", use_column_width=True)
                with c2:
                    st.image(imgs[0], caption="Inpainted", use_column_width=True)
                    buf = io.BytesIO(); imgs[0].save(buf, format="PNG")
                    st.download_button("📥 Download", buf.getvalue(), file_name="inpainted.png", mime="image/png")
                add_to_history("Inpaint", ENGINE, p, imgs)
        except Exception as e:
            st.error(f"❌ Inpaint failed: {e}")

# ----------------------------
# Tab: Upscale
# ----------------------------
with TAB_UPSCALE:
    st.subheader("Upscale (ESRGAN x2 or to target size)")
    u = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"], key="up_up")

    up1, up2 = st.columns(2)
    with up1:
        target_w = st.number_input("Target width (>=512, optional)", min_value=0, max_value=4096, value=0, step=64)
    with up2:
        target_h = st.number_input("Target height (>=512, optional)", min_value=0, max_value=4096, value=0, step=64)

    go_u = st.button("⬆️ Upscale", type="primary", disabled=not u)

    if go_u and u:
        _assert_api_key()
        try:
            src = Image.open(u).convert("RGBA")
            w = int(target_w) if target_w and target_w >= 512 else None
            h = int(target_h) if target_h and target_h >= 512 else None
            with st.spinner("Upscaling (ESRGAN)..."):
                out = upscale_esrgan(src, desired_w=w, desired_h=h)
            c1, c2 = st.columns(2)
            with c1:
                st.image(src, caption=f"Original {src.size[0]}x{src.size[1]}", use_column_width=True)
            with c2:
                st.image(out, caption=f"Upscaled {out.size[0]}x{out.size[1]}", use_column_width=True)
                buf = io.BytesIO(); out.save(buf, format="PNG")
                st.download_button("📥 Download", buf.getvalue(), file_name="upscaled.png", mime="image/png")
            add_to_history("Upscale", ESRGAN_ENGINE, "(upscale)", [out])
        except Exception as e:
            st.error(f"❌ Upscale failed: {e}")

# ----------------------------
# Tab: Variations (quick re-rolls)
# ----------------------------
with TAB_VARIATIONS:
    st.subheader("Create Variations from an Image")
    v_up = st.file_uploader("Upload base image", type=["png", "jpg", "jpeg"], key="var_up")
    v_prompt = st.text_area("Prompt tweak (optional)", placeholder="Keep style, slightly different angle")
    v_negative = st.text_input("Negative prompt (optional)", value=NEGATIVE_DEFAULT, key="var_neg")

    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        v_strength = st.slider("Variation strength", 0.10, 0.95, 0.45, 0.05)
    with vc2:
        v_count = st.slider("How many?", 1, 4, 2)
    with vc3:
        v_seed = st.number_input("Seed (0=random)", 0, 2_147_483_647, 0, key="var_seed")

    go_v = st.button("🧬 Make Variations", type="primary", disabled=not v_up)

    if go_v and v_up:
        _assert_api_key()
        try:
            base_im = Image.open(v_up).convert("RGBA")
            with st.spinner("Generating variations..."):
                imgs = img2img(
                    engine_id=ENGINE,
                    init_image=base_im,
                    prompt=v_prompt or "",
                    negative_prompt=v_negative or None,
                    image_strength=float(v_strength),
                    steps=default_steps,
                    samples=int(v_count),
                    style_preset=None,
                    seed=int(v_seed),
                )
            if not imgs:
                st.warning("No images returned.")
            else:
                cols = st.columns(min(4, len(imgs)))
                for i, im in enumerate(imgs):
                    with cols[i % len(cols)]:
                        st.image(im, use_column_width=True)
                        buf = io.BytesIO(); im.save(buf, format="PNG")
                        st.download_button(
                            f"📥 Download #{i+1}", buf.getvalue(), file_name=f"variation_{i+1}.png", mime="image/png"
                        )
                add_to_history("Variations", ENGINE, v_prompt or "(no prompt)", imgs)
        except Exception as e:
            st.error(f"❌ Variations failed: {e}")

# ----------------------------
# Footer
# ----------------------------
st.markdown(
    """
    <hr/>
    <small>
    Models: SDXL 1.0 / SD 1.6 via Stability REST API v1; Upscale via ESRGAN x2. 
    Use negative prompts to steer quality. White-on-black masks: white = replace.
    </small>
    """,
    unsafe_allow_html=True,
)
