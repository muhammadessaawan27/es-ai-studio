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
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. THE GRID STATION (MAXIMUM GPU CAPACITY)
# ==========================================
# Opening 50 parallel lanes for 5G speed
executor = ThreadPoolExecutor(max_workers=50)
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
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
# 2. CLEAN PROFESSIONAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Titan V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    /* Minimal Top Header (Requirement: Black Text, Small Space) */
    .minimal-header {
        text-align: center;
        padding: 10px;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
    .main-names {
        font-family: 'Inter', sans-serif; font-size: 1.5rem; font-weight: 700;
        color: #000000; letter-spacing: 1px;
    }
    .brand-id {
        font-family: 'Orbitron', sans-serif; font-size: 1rem; color: #64748b;
        letter-spacing: 4px; font-weight: bold;
    }

    /* Professional Rotating Logo (Small & Unique) */
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 10px 0; }
    .electric-s {
        width: 80px; height: 80px; background: #000000; border-radius: 15px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: #ffffff;
        border: 2px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: rotateY 6s infinite linear;
    }
    @keyframes rotateY { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    /* Button and Input Styling (Minimal) */
    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 8px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; 
        border-radius: 8px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Dashboard Top (Minimalist)
st.markdown("""
    <div class="minimal-header">
        <div class="brand-id">SGLOWINA AI OFFICIAL</div>
        <div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
        <div style="font-size: 0.9rem; color: #64748b; font-weight: bold;">Founders & CEOs</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="logo-container"><div class="electric-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.

Muhammad Essa Awan is the lead visionary, COO, and Mechanical Engineer who configured this platform's core logic. 
Saba Wahid is the Co-Founder and CEO of Sglowina AI, and the spouse of Muhammad Essa Awan (Mrs. Muhammad Essa Awan).

This is the official Version 1.0 Premium Release.
"""

def is_identity_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"])

# ==========================================
# 4. TITAN SPEED ENGINE (50-LANE ROAD)
# ==========================================
if "char_seed" not in st.session_state:
    st.session_state.char_seed = random.randint(1, 999999)

def get_titan_prompt(text):
    try:
        instr = f"Director Call: Urdu '{text}'. Professional 3D animation, symmetrical face. Output English prompt."
        # Using a cluster of high-speed servers
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=15)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_image(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style, part):
    u_id = f"v1_p{part}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_codes = {"Asad (Male)": "ur-PK-AsadNeural", "Salman (Male)": "ur-PK-SalmanNeural", 
                   "Uzma (Female)": "ur-PK-UzmaNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok (9:16)": (720, 1280)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        # Parallel Image Generation (The 50-Lane Road)
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=deformed,missing+limbs"
            img_urls.append(url)

        status.info(f"🚀 Grid Station Rendering {len(sentences)} scenes concurrently...")
        with ThreadPoolExecutor(max_workers=50) as exe:
            images_data = list(exe.map(fetch_image, img_urls))

        for i, img_data in enumerate(images_data):
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Locked Motion: Zoom In Expansion (1.0 to 1.15)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close()
        final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. MODULAR NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["💬 Chat AI", "🎬 Movie Studio (Modular)", "🎨 Pro Image Studio"])

if menu == "💬 Chat AI":
    st.write("### 💬 Smart Chat Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if is_identity_call(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio (Modular)":
    st.write("### 🎥 Industrial Grid Studio")
    part_num = st.number_input("Part Number:", min_value=1, step=1, value=1)
    if st.button("Start New Story (Reset Character)"):
        st.session_state.char_seed = random.randint(1, 999999)
        st.success("Character Identity Locked!")

    m_script = st.text_area(f"Enter Script for Part {part_num}:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"])
    with c2: mr = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, part_num)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial Image Studio")
    p_i = st.text_area("Describe Image (One per line):")
    if st.button("Generate Visuals 🚀"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1024&height=1024&nologo=true&seed={st.session_state.char_seed}"
        st.image(url)

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>Sglowina AI Version 1.0 Premium Release | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
