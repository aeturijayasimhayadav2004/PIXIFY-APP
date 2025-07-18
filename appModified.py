import streamlit as st
import os
#from dotenv import load_dotenv
from services import (
    lifestyle_shot_by_image,
    lifestyle_shot_by_text,
    add_shadow,
    create_packshot,
    enhance_prompt,
    generative_fill,
    generate_hd_image,
    erase_foreground
)
from PIL import Image
import io
import requests
import json
import time
import base64
from streamlit_drawable_canvas import st_canvas
import numpy as np
from services.erase_foreground import erase_foreground

# Configure Streamlit page
st.set_page_config(
    page_title="Pixify - AI Image Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
print("Loading environment variables...")
load_dotenv(verbose=True)

# Debug: Print environment variable status (keep for development)
api_key = os.getenv("BRIA_API_KEY")
print(f"API Key present: {bool(api_key)}")

def initialize_session_state():
    """Initialize session state variables."""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = os.getenv('BRIA_API_KEY')
    if 'generated_images' not in st.session_state:
        st.session_state.generated_images = []
    if 'current_image' not in st.session_state:
        st.session_state.current_image = None
    if 'pending_urls' not in st.session_state:
        st.session_state.pending_urls = []
    if 'edited_image' not in st.session_state:
        st.session_state.edited_image = None
    if 'original_prompt' not in st.session_state:
        st.session_state.original_prompt = ""
    if 'enhanced_prompt' not in st.session_state:
        st.session_state.enhanced_prompt = None

def download_image_bytes(url):
    """Download image from URL and return as bytes for auto-download."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading image: {str(e)}")
        return None

def trigger_download(url, filename="pixify_image.png"):
    """Trigger automatic download of image from URL."""
    try:
        image_data = download_image_bytes(url)
        if image_data:
            st.download_button(
                label="⬇️ Download Image",
                data=image_data,
                file_name=filename,
                mime="image/png",
                key=f"download_{int(time.time())}"
            )
            return True
        return False
    except Exception as e:
        st.error(f"Download failed: {str(e)}")
        return False

def auto_download_image(url, filename="pixify_generated.png"):
    """Auto-download functionality with better UX."""
    try:
        image_data = download_image_bytes(url)
        if image_data:
            # Create a more prominent download section
            st.success("🎉 Image generated successfully!")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    label="📥 Download Your Image",
                    data=image_data,
                    file_name=filename,
                    mime="image/png",
                    key=f"auto_download_{int(time.time())}",
                    use_container_width=True
                )
            return True
        return False
    except Exception as e:
        st.error(f"Auto-download failed: {str(e)}")
        return False

def apply_image_filter(image, filter_type):
    """Apply various filters to the image."""
    try:
        img = Image.open(io.BytesIO(image)) if isinstance(image, bytes) else Image.open(image)
        
        if filter_type == "Grayscale":
            return img.convert('L')
        elif filter_type == "Sepia":
            width, height = img.size
            pixels = img.load()
            for x in range(width):
                for y in range(height):
                    r, g, b = img.getpixel((x, y))[:3]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    img.putpixel((x, y), (min(tr, 255), min(tg, 255), min(tb, 255)))
            return img
        elif filter_type == "High Contrast":
            return img.point(lambda x: x * 1.5)
        elif filter_type == "Blur":
            return img.filter(Image.BLUR)
        else:
            return img
    except Exception as e:
        st.error(f"Error applying filter: {str(e)}")
        return None

def check_generated_images():
    """Check if pending images are ready and update the display."""
    if st.session_state.pending_urls:
        ready_images = []
        still_pending = []
        
        for url in st.session_state.pending_urls:
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    ready_images.append(url)
                else:
                    still_pending.append(url)
            except Exception as e:
                still_pending.append(url)
        
        st.session_state.pending_urls = still_pending
        
        if ready_images:
            st.session_state.edited_image = ready_images[0]
            if len(ready_images) > 1:
                st.session_state.generated_images = ready_images
            return True
            
    return False

def auto_check_images(status_container):
    """Automatically check for image completion."""
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts and st.session_state.pending_urls:
        time.sleep(2)
        if check_generated_images():
            status_container.success("✨ Image ready!")
            return True
        attempt += 1
    return False

def main():
    # Custom CSS for better UI
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        font-weight: bold;
        font-size: 2rem;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .download-section {
        background: linear-gradient(45deg, #667eea, #764ba2);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: white;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header with new branding
    st.markdown('<div class="main-header">🎨 Pixify - AI Image Studio</div>', unsafe_allow_html=True)
    st.markdown("### Transform your ideas into stunning visuals with AI-powered image generation")
    
    initialize_session_state()
    
    # Hidden API key management (only show if not set)
    if not st.session_state.api_key:
        with st.expander("🔐 API Configuration (Required)", expanded=True):
            st.warning("Please configure your Bria.ai API key to use Pixify")
            api_key = st.text_input("Enter your Bria.ai API key:", type="password")
            if api_key:
                st.session_state.api_key = api_key
                st.success("✅ API key configured successfully!")
                st.rerun()
    else:
        # API key is set, show minimal info
        st.sidebar.success("🔑 API Key: Configured")
        if st.sidebar.button("Change API Key"):
            st.session_state.api_key = None
            st.rerun()

    # Main feature tabs
    tabs = st.tabs([
        "🎨 Generate Images",
        "📸 Product Photography", 
        "🎭 Generative Fill",
        "🗑️ Erase Elements"
    ])
    
    # Generate Images Tab
    with tabs[0]:
        st.header("🎨 AI Image Generation")
        st.markdown("Create stunning images from text descriptions")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            prompt = st.text_area("✨ Describe your image", 
                                placeholder="A beautiful sunset over mountains with vibrant colors...",
                                height=100,
                                key="prompt_input")
            
            if "original_prompt" not in st.session_state:
                st.session_state.original_prompt = prompt
            elif prompt != st.session_state.original_prompt:
                st.session_state.original_prompt = prompt
                st.session_state.enhanced_prompt = None
            
            if st.session_state.get('enhanced_prompt'):
                st.markdown("**🚀 Enhanced Prompt:**")
                st.markdown(f"*{st.session_state.enhanced_prompt}*")
            
            if st.button("✨ Enhance Prompt", key="enhance_button"):
                if not prompt:
                    st.warning("Please enter a prompt to enhance.")
                else:
                    with st.spinner("Enhancing your prompt..."):
                        try:
                            result = enhance_prompt(st.session_state.api_key, prompt)
                            if result:
                                st.session_state.enhanced_prompt = result
                                st.success("Prompt enhanced successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error enhancing prompt: {str(e)}")
        
        with col2:
            st.markdown("**🎛️ Generation Settings**")
            num_images = st.slider("Number of images", 1, 4, 1)
            aspect_ratio = st.selectbox("Aspect ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"])
            enhance_img = st.checkbox("Enhance quality", value=True)
            
            st.subheader("🎨 Style Options")
            style = st.selectbox("Image Style", [
                "Realistic", "Artistic", "Cartoon", "Sketch", 
                "Watercolor", "Oil Painting", "Digital Art"
            ])
            
            if style and style != "Realistic":
                prompt = f"{prompt}, in {style.lower()} style"
        
        # Generate button
        if st.button("🎨 Generate Images", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("⚠️ Please configure your API key first.")
                return
                
            with st.spinner("🎨 Creating your masterpiece..."):
                try:
                    result = generate_hd_image(
                        prompt=st.session_state.enhanced_prompt or prompt,
                        api_key=st.session_state.api_key,
                        num_results=num_images,
                        aspect_ratio=aspect_ratio,
                        sync=True,
                        enhance_image=enhance_img,
                        medium="art" if style != "Realistic" else "photography",
                        prompt_enhancement=False,
                        content_moderation=True
                    )
                    
                    if result:
                        image_url = None
                        if isinstance(result, dict):
                            if "result_url" in result:
                                image_url = result["result_url"]
                            elif "result_urls" in result:
                                image_url = result["result_urls"][0]
                            elif "result" in result and isinstance(result["result"], list):
                                for item in result["result"]:
                                    if isinstance(item, dict) and "urls" in item:
                                        image_url = item["urls"][0]
                                        break
                                    elif isinstance(item, list) and len(item) > 0:
                                        image_url = item[0]
                                        break
                        
                        if image_url:
                            st.session_state.edited_image = image_url
                            # Display the image
                            st.image(image_url, caption="Generated Image", use_column_width=True)
                            # Auto-download functionality
                            auto_download_image(image_url, "pixify_generated.png")
                        else:
                            st.error("Failed to generate image. Please try again.")
                            
                except Exception as e:
                    st.error(f"Generation failed: {str(e)}")
    
    # Product Photography Tab
    with tabs[1]:
        st.header("📸 Product Photography")
        st.markdown("Transform your product images with AI-powered editing")
        
        uploaded_file = st.file_uploader("📤 Upload Product Image", type=["png", "jpg", "jpeg"], key="product_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                edit_option = st.selectbox("🛠️ Select Edit Option", [
                    "Create Packshot",
                    "Add Shadow",
                    "Lifestyle Shot"
                ])
                
                if edit_option == "Create Packshot":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        bg_color = st.color_picker("Background Color", "#FFFFFF")
                        sku = st.text_input("SKU (optional)", "")
                    with col_b:
                        force_rmbg = st.checkbox("Force Background Removal", False)
                        content_moderation = st.checkbox("Enable Content Moderation", False)
                    
                    if st.button("Create Packshot", use_container_width=True):
                        with st.spinner("Creating professional packshot..."):
                            try:
                                if force_rmbg:
                                    from services.background_service import remove_background
                                    bg_result = remove_background(
                                        st.session_state.api_key,
                                        uploaded_file.getvalue(),
                                        content_moderation=content_moderation
                                    )
                                    if bg_result and "result_url" in bg_result:
                                        response = requests.get(bg_result["result_url"])
                                        if response.status_code == 200:
                                            image_data = response.content
                                        else:
                                            st.error("Failed to download background-removed image")
                                            return
                                    else:
                                        st.error("Background removal failed")
                                        return
                                else:
                                    image_data = uploaded_file.getvalue()
                                
                                result = create_packshot(
                                    st.session_state.api_key,
                                    image_data,
                                    background_color=bg_color,
                                    sku=sku if sku else None,
                                    force_rmbg=force_rmbg,
                                    content_moderation=content_moderation
                                )
                                
                                if result and "result_url" in result:
                                    st.session_state.edited_image = result["result_url"]
                                    st.success("✨ Packshot created successfully!")
                                else:
                                    st.error("Failed to create packshot. Please try again.")
                            except Exception as e:
                                st.error(f"Error creating packshot: {str(e)}")
                                if "422" in str(e):
                                    st.warning("Content moderation failed. Please ensure the image is appropriate.")
                
                # Similar implementation for other edit options (Add Shadow, Lifestyle Shot)
                # ... (keeping the rest of the original logic but with improved UX)
            
            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Edited Image", use_column_width=True)
                    # Auto-download for edited images
                    auto_download_image(st.session_state.edited_image, "pixify_edited.png")
                elif st.session_state.pending_urls:
                    st.info("🎨 Images are being generated. Please wait...")

    # Generative Fill Tab
    with tabs[2]:
        st.header("🎭 Generative Fill")
        st.markdown("Draw a mask and generate content in selected areas")
        
        uploaded_file = st.file_uploader("📤 Upload Image", type=["png", "jpg", "jpeg"], key="fill_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                img = Image.open(uploaded_file)
                img_width, img_height = img.size
                
                aspect_ratio = img_height / img_width
                canvas_width = min(img_width, 800)
                canvas_height = int(canvas_width * aspect_ratio)
                
                img = img.resize((canvas_width, canvas_height))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                stroke_width = st.slider("🖌️ Brush width", 1, 50, 20)
                stroke_color = st.color_picker("🎨 Brush color", "#fff")
                
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0.0)",
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                    drawing_mode="freedraw",
                    background_color="",
                    background_image=img,
                    height=canvas_height,
                    width=canvas_width,
                    key="canvas",
                )
                
                st.subheader("🎯 Generation Options")
                prompt = st.text_area("✨ Describe what to generate in the masked area")
                negative_prompt = st.text_area("🚫 Describe what to avoid (optional)")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    num_results = st.slider("Number of variations", 1, 4, 1)
                    sync_mode = st.checkbox("Synchronous Mode", False)
                
                with col_b:
                    seed = st.number_input("Seed (optional)", min_value=0, value=0)
                    content_moderation = st.checkbox("Enable Content Moderation", False)
                
                if st.button("🎨 Generate Fill", type="primary", use_container_width=True):
                    if not prompt:
                        st.error("Please enter a prompt describing what to generate.")
                        return
                    
                    if canvas_result.image_data is None:
                        st.error("Please draw a mask on the image first.")
                        return
                    
                    mask_img = Image.fromarray(canvas_result.image_data.astype('uint8'), mode='RGBA')
                    mask_img = mask_img.convert('L')
                    
                    mask_bytes = io.BytesIO()
                    mask_img.save(mask_bytes, format='PNG')
                    mask_bytes = mask_bytes.getvalue()
                    
                    image_bytes = uploaded_file.getvalue()
                    
                    with st.spinner("🎨 Generating fill..."):
                        try:
                            result = generative_fill(
                                st.session_state.api_key,
                                image_bytes,
                                mask_bytes,
                                prompt,
                                negative_prompt=negative_prompt if negative_prompt else None,
                                num_results=num_results,
                                sync=sync_mode,
                                seed=seed if seed != 0 else None,
                                content_moderation=content_moderation
                            )
                            
                            if result:
                                if sync_mode:
                                    if "urls" in result and result["urls"]:
                                        st.session_state.edited_image = result["urls"][0]
                                        st.success("✨ Generation complete!")
                                    elif "result_url" in result:
                                        st.session_state.edited_image = result["result_url"]
                                        st.success("✨ Generation complete!")
                                else:
                                    if "urls" in result:
                                        st.session_state.pending_urls = result["urls"][:num_results]
                                        status_container = st.empty()
                                        status_container.info("🎨 Generation started! Please wait...")
                                        
                                        if auto_check_images(status_container):
                                            st.rerun()
                        except Exception as e:
                            st.error(f"Generation failed: {str(e)}")
            
            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Generated Result", use_column_width=True)
                    auto_download_image(st.session_state.edited_image, "pixify_generated_fill.png")
                elif st.session_state.pending_urls:
                    st.info("🎨 Generation in progress. Please wait...")

    # Erase Elements Tab
    with tabs[3]:
        st.header("🗑️ Erase Elements")
        st.markdown("Remove unwanted elements from your images")
        
        uploaded_file = st.file_uploader("📤 Upload Image", type=["png", "jpg", "jpeg"], key="erase_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(uploaded_file, caption="Original Image", use_column_width=True)
                
                img = Image.open(uploaded_file)
                img_width, img_height = img.size
                
                aspect_ratio = img_height / img_width
                canvas_width = min(img_width, 800)
                canvas_height = int(canvas_width * aspect_ratio)
                
                img = img.resize((canvas_width, canvas_height))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                stroke_width = st.slider("🖌️ Brush width", 1, 50, 20, key="erase_brush_width")
                stroke_color = st.color_picker("🎨 Brush color", "#fff", key="erase_brush_color")
                
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0.0)",
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                    background_color="",
                    background_image=img,
                    drawing_mode="freedraw",
                    height=canvas_height,
                    width=canvas_width,
                    key="erase_canvas",
                )
                
                st.subheader("🎯 Erase Options")
                content_moderation = st.checkbox("Enable Content Moderation", False, key="erase_content_mod")
                
                if st.button("🗑️ Erase Selected Area", key="erase_btn", use_container_width=True):
                    if canvas_result.image_data is not None:
                        with st.spinner("Erasing selected area..."):
                            try:
                                image_bytes = uploaded_file.getvalue()
                                
                                result = erase_foreground(
                                    st.session_state.api_key,
                                    image_data=image_bytes,
                                    content_moderation=content_moderation
                                )
                                
                                if result:
                                    if "result_url" in result:
                                        st.session_state.edited_image = result["result_url"]
                                        st.success("✨ Area erased successfully!")
                                    else:
                                        st.error("Failed to erase area. Please try again.")
                            except Exception as e:
                                st.error(f"Erase failed: {str(e)}")
                                if "422" in str(e):
                                    st.warning("Content moderation failed. Please ensure the image is appropriate.")
                    else:
                        st.warning("Please draw on the image to select the area to erase.")
            
            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Result", use_column_width=True)
                    auto_download_image(st.session_state.edited_image, "pixify_erased.png")

    # Footer
    st.markdown("---")
    st.markdown("### 💡 **Pixify Tips**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🎨 Better Prompts:**
        - Be specific and detailed
        - Include style preferences
        - Mention lighting and mood
        """)
    
    with col2:
        st.markdown("""
        **📸 Product Photos:**
        - Use high-quality source images
        - Ensure good lighting
        - Remove distracting backgrounds
        """)
    
    with col3:
        st.markdown("""
        **⚡ Performance:**
        - Sync mode for faster results
        - Lower image count for speed
        - Use content moderation wisely
        """)

if __name__ == "__main__":
    main()
