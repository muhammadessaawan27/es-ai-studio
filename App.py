import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import random
from PIL import Image
import io

# ==========================================
# 1. INDUSTRIAL GRADE STABILITY & MULTI-ENGINE
# ==========================================
session = requests.Session()
# Fail-safe mechanism: List of redundant AI providers
TEXT_ENGINES = ["openai", "mistral", "llama", "unity"]
IMAGE_ENGINES = ["https://image.pollinations.ai/prompt/", "https://hercai.onrender.com/v3/text2image?prompt="]

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error("Technical Setup in progress. Please refresh.")

# ==========================================
# 2. SGLOWINA PREMIUM UI & BRANDING
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .launch-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.4);
        animation: neonGlow 2s infinite alternate;
    }
    @keyframes neonGlow {
        from { border-bottom: 4px solid #ff007a; }
        to { border-bottom: 4px solid #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 120px; height: 120px; background: #0f172a; border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 65px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 40px #ff007a;
        animation: rotate3D 10s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-title { font-size: 4rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-info { font-size: 1.3rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }

    /* Improved Sidebar Navigation */
    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 250px !important; }
    [data-testid="stSidebar"] * { color: white !important; font-size: 1.1rem !important; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 15px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold; border: none;
        box-shadow: 0 10px 20px rgba(0,0,0,0.15); transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 15px 30px rgba(255, 0, 122, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (FOUNDER & CEO)
# ==========================================
SGLOWINA_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founder & CEO:** Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglowina AI is a high-end industrial intelligence platform. This is the official Version 1.0 Premium Release.
"""

def check_identity(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"sglowina"])

# ==========================================
# 4. v40 ENGINE - MASTER RECOGNITION (LOCKED)
# ==========================================
def get_v40_visual_prompt(urdu_text):
    try:
        # Beefed up prompt for perfect anatomy (no missing legs/eyes)
        hd_modifier = "highly detailed cinematic 3D, perfect anatomy, full body, sharp focus, 8k, realistic eyes and limbs"
        instr = f"Director: '{urdu_text}'. Describe ONLY the core subject. Use: {hd_modifier}. No humans unless asked. English only."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_v40_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"🎨 Sglowina AI V1.0 Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_v40_visual_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,female,deformed,missing+legs"
            
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(session.get(img_url, timeout=60).content)
            
            Image.open(img_p).convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Zoom In Expansion (1.0 to 1.15)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_V1_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. SIDEBAR NAVIGATION (TRUE ISOLATION)
# ==========================================
st.sidebar.markdown(f"<h2 style='color:white; text-align:center;'>SGLOWINA MENU</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navigate Studio:", ["🏠 Smart Chat", "🎬 Cinematic Movie Studio", "🎨 Pro Image Studio"])

# Global Header
st.markdown('<div class="launch-header">SGLOWINA AI - VERSION 1.0 PREMIUM RELEASE</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-title">Sglowina AI</div>
        <div class="founder-info">FOUNDER & CEO: SABA WAHID</div>
    </div>
    """, unsafe_allow_html=True)

# --- PAGE 1: SMART CHAT ---
if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you today?"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # Identity Protection Logic
        if check_identity(p):
            res = SGLOWINA_BIO
        else:
            # Multi-Engine Text Fallback
            res = "Server busy. Please try again."
            for eng in TEXT_ENGINES:
                try:
                    url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model={eng}&cache=true"
                    res = requests.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
                    if res: break
                except: continue
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif menu == "🎬 Cinematic Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
    m_script = st.text_area("Enter Movie Script (Every sentence will be a unique scene):", height=200)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"], key="v1_v")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="v1_r")
    with c3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="v1_s")
    if st.button("Generate Official Masterpiece 🚀"):
        if m_script:
            v_res = create_v40_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# --- PAGE 3: IMAGE STUDIO ---
elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Universal Visual Studio")
    img_p = st.text_area("Describe the Image or Logo you want:", height=150)
    
    # Unlimited Professional Ratios
    ratio_opts = {
        "Square (1:1)": (1024, 1024), "YouTube HD (16:9)": (1280, 720), 
        "TikTok/Reels (9:16)": (720, 1280), "21:9 Ultra-Wide Banner": (2560, 1080),
        "Logo Design Concept": (512, 512), "Facebook Cover": (1200, 444)
    }
    
    ic1, ic2 = st.columns(2)
    with ic1: is_img = st.selectbox("Artistic Style:", ["Realistic", "Anime", "Logo Design", "Sketch", "Digital Art"], key="v1_is")
    with ic2: ir_img = st.selectbox("Output Size (Resolution):", list(ratio_opts.keys()), key="v1_ir")
    
    if st.button("Generate Industrial Image 🚀"):
        if img_p:
            w, h = ratio_opts[ir_img]
            with st.spinner("Sglowina AI V1.0 is painting..."):
                # Enhanced Prompt for Image Studio
                hd_p = f"{img_p}, 8k resolution, cinematic lighting, masterpiece, anatomically correct, highly detailed"
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(hd_p + ' ' + is_img)}?width={w}&height={h}&nologo=true&negative=girl,female,deformed,missing+limbs"
                st.image(url, caption="Sglowina V1.0 HD Result")
                st.download_button("Download HD Visual ⬇️", requests.get(url).content, file_name="sglowina_v1.jpg")

st.sidebar.markdown("---")
st.sidebar.info(f"Sglowina AI v1.0 | Official Premium Launch | Founder & CEO: Saba Wahid")
