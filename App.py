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
# 1. INDUSTRIAL STABILITY & FAIL-SAFE ENGINE
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (LOCKED DESIGN)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Launch", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    .executive-header {
        text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    .main-names { font-size: 1.6rem; font-weight: 800; color: #000000; margin-bottom: 5px; }
    .title-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 3px; text-transform: uppercase; }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 20px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spin 10s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="executive-header">
        <div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
        <div class="title-tag">Founders & CEOs | Sglowina AI Official Studio</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the lead visionary, COO, and Mechanical Engineer who configured this platform's core logic. 
Saba Wahid is the Co-Founder and CEO of Sglowina AI, and the spouse of Muhammad Essa Awan.
"""

def is_id_call(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. MOTION & QUALITY MASTER ENGINE
# ==========================================
def get_verified_prompt(text, style):
    # Added "Cinematic Motion" instructions to force walking/moving
    motion_instr = "Highly dynamic cinematic motion, walking character, moving limbs, flowing hair, 3D animated movement."
    quality_instr = "Symmetrical face, high definition textures, 8k resolution, realistic eyes, masterpiece."
    try:
        instr = f"Director Order: '{text}'. {motion_instr} {quality_instr} Style: {style}. No humans unless asked. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie_v1(story, voice, ratio, style):
    u_id = f"titan_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]

        # Splitting sentences (v40 Stable Logic)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        char_seed = random.randint(1, 999999)

        for i, scene in enumerate(sentences):
            status.info(f"⚡ Sglowina Titan: Animating Scene {i+1}/{len(sentences)}...")
            refined = get_verified_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={char_seed}&nologo=true&negative=melted+face,distorted,deformed"
            
            # STABLE DOWNLOAD & VERIFY
            img_p = f"i_{u_id}_{i}.jpg"
            img_res = session.get(img_url, timeout=60)
            if img_res.status_code == 200:
                with open(img_p, "wb") as f: f.write(img_res.content)
                # PIL VERIFICATION (Fixes 'cannot identify image file' error)
                with Image.open(img_p) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # MOTION: 3D Zoom + Panning (Revealing character movement)
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION (LOCKED)
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", ["🏠 Smart Chat", "🎬 Movie Studio (Parts)", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligent Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_id_call(p): res = SGLOWINA_BIO
        else:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true"
                res = session.get(url, timeout=25).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server is busy. Please try again."
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio (Parts)":
    st.write("### 🎥 Industrial Cinematic Production")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Select Voice:", ["Asad (Male)", "Uzma (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image (Multi-Prompt per line):", height=150)
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate HD Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                with st.spinner(f"Rendering {idx+1}..."):
                    # Using the high-quality verified director prompt
                    refined = get_verified_prompt(single_p, i_style)
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true&negative=girl,female,deformed,low+quality"
                    st.image(url, caption=f"Sglowina HD Result")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.0 Premium Release | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
