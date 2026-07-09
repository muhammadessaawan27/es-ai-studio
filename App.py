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
# 1. INDUSTRIAL STABILITY & BACKEND
# ==========================================
session = requests.Session()
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

# ==========================================
# 2. SGLOWINA MINIMAL LUXURY UI
# ==========================================
st.set_page_config(page_title="Sglowina AI - Titan Release", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Small Minimal Header */
    .top-bar {
        display: flex; align-items: center; justify-content: center;
        padding: 10px; border-bottom: 2px solid #f1f5f9; margin-bottom: 20px;
    }
    
    .ai-icon {
        width: 60px; height: 60px; background: #0f172a; border-radius: 15px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 30px; color: white;
        border: 3px solid #ff007a; box-shadow: 0 0 15px #ff007a;
        animation: rotateY 6s infinite linear; margin-right: 15px;
    }
    @keyframes rotateY { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .brand-title { font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 900; color: #0f172a; }

    /* Button and Input Styling */
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    
    /* Footer */
    .footer-diamond {
        font-family: 'Inter', sans-serif; font-size: 0.9rem; text-align: center;
        padding: 20px; border-top: 1px solid #eee; margin-top: 50px; color: #64748b;
    }
    </style>
    """, unsafe_allow_html=True)

# Small Minimal Top Header
st.markdown("""
    <div class="top-bar">
        <div class="ai-icon">S</div>
        <div class="brand-title">Sglowina AI</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED)
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the lead visionary and Mechanical Engineer. Saba Wahid is the Founder & CEO.
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa"])

# ==========================================
# 4. TITAN MOVIE & IMAGE ENGINE (v40 LOCKED)
# ==========================================
RATIO_MAP = {
    "Square (1:1)": (1024, 1024),
    "YouTube HD (16:9)": (1280, 720),
    "TikTok/Shorts (9:16)": (720, 1280),
    "YouTube Banner": (2560, 1080)
}

def get_titan_prompt(text, style):
    try:
        # Strict instructions for high quality anatomy
        quality = "highly detailed, symmetrical face, sharp eyes, 8k resolution, cinematic lighting, masterpiece"
        instr = f"Director Call: '{text}'. {quality}. Style: {style}. No humans unless mentioned. Output English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie(story, voice, ratio, style, seed):
    u_id = str(uuid.uuid4())[:8]
    status = st.status("🎬 Sglowina Titan Engine is working...", expanded=True)
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        w, h = RATIO_MAP[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.write(f"🖼️ Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative=melted,distorted,girl,female"
            
            img_p = f"i_{u_id}_{i}.jpg"
            img_data = session.get(url, timeout=60).content
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        status.update(label="✅ Masterpiece Rendered!", state="complete")
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA MENU", ["💬 Smart Chat", "🎥 Movie Studio", "🎨 Image Studio"])

if menu == "💬 Smart Chat":
    st.write("### 💬 Sglowina Intelligence")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGL_BIO if is_id_call(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎥 Movie Studio":
    st.write("### 🎥 Industrial Video Production")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with c2: mr = st.selectbox("Format:", list(RATIO_MAP.keys()))
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    with c4: sd = st.number_input("Character ID:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        v_res = create_titan_movie(m_script, mv, mr, ms, sd)
        if "mp4" in v_res:
            st.video(v_res)
            st.download_button("Download", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 HD Image Studio")
    img_p = st.text_area("Describe Image(s):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_s = st.selectbox("Art Style:", ["Realistic", "Logo Design", "Anime"])
    with ic2: i_r = st.selectbox("Resolution:", list(RATIO_MAP.keys()))
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    char_id = st.number_input("Consistency ID:", value=123)

    if st.button("Generate HD Visuals 🚀"):
        w, h = RATIO_MAP[i_r]
        for i in range(count):
            with st.spinner(f"Rendering image {i+1}..."):
                refined = get_titan_prompt(img_p, i_s)
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={char_id+i}&nologo=true&negative=girl,female,deformed"
                st.image(url, caption=f"Result {i+1}")

# FOOTER
st.markdown(f"""
    <div class="footer-diamond">
        Sglowina AI v1.0 Premium Release | Administrator: Saba Wahid | Lead: Muhammad Essa Awan
    </div>
    """, unsafe_allow_html=True)
