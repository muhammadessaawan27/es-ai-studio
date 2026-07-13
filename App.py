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
# 1. CORE STABILITY SETUP
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error("Technical Engine loading... Please Refresh.")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. SHARED LOGIC & ENGINES (LOCKED)
# ==========================================
def get_v40_prompt(text, style):
    try:
        instr = f"Act as a Film Director: '{text}'. Professional 3D character animation. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

# --- MOVIE ENGINE ---
def create_titan_movie_v1(story, voice, ratio, style, seed):
    u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(get_v40_prompt(s, style))}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,deformed" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)}...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# --- PIXEL-PERFECT MOTION ENGINE ---
def animate_pixels(image_input, style, duration, speed_mode):
    u_id = str(uuid.uuid4())[:8]
    try:
        img = Image.open(image_input).convert("RGB")
        w, h = img.size
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        img_path = f"t_{u_id}.jpg"
        img.save(img_path)

        duration_sec = int(duration.split()[0])
        s_val = {"Slow": 0.05, "Normal": 0.1, "Fast": 0.2}.get(speed_mode, 0.1)

        clip = ImageClip(img_path).set_duration(duration_sec).set_fps(24).resize((w, h))
        if "In" in style: clip = clip.resize(lambda t: 1.0 + s_val * (t/duration_sec))
        elif "Out" in style: clip = clip.resize(lambda t: 1.2 - s_val * (t/duration_sec))
        
        out = f"mot_{u_id}.mp4"
        clip.write_videofile(out, codec="libx264", audio=False, fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 3. EXECUTIVE UI DESIGN
# ==========================================
st.set_page_config(page_title="Sglowina AI Official", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff; background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
    }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 20px 0; }
    .circular-s {
        width: 90px; height: 90px; background: #0f172a; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: #ffffff; border: 3px solid #00d4ff; animation: spin 10s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 50px; width: 100%; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# IDENTITY DATA
SGLOWINA_BIO = "Sglowina AI: Developed by Team Sglowina. Founders: Muhammad Essa Awan & Saba Wahid."

# ==========================================
# 4. MAIN NAVIGATION (SIDEBAR)
# ==========================================
menu = st.sidebar.radio("SGLOWINA MENU", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio", "🎬 Image Motion"])

# Shared Header
st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)
st.markdown('<h2 style="text-align:center;">Founders & CEOs: Muhammad Essa Awan & Saba Wahid</h2>', unsafe_allow_html=True)

# --- PAGE 1: CHAT ---
if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who", "owner"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"): st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif menu == "🎥 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production")
    m_s = st.text_area("Movie Script:")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    sd = st.number_input("Character ID:", value=786)
    if st.button("Generate Master Movie 🚀"):
        res = create_titan_movie_v1(m_s, mv, mr, ms, 1, sd)
        if "mp4" in res: st.video(res); st.download_button("Download", open(res, 'rb').read(), file_name=res)

# --- PAGE 3: IMAGE STUDIO ---
elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image(s):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Style:", ["Realistic", "Anime", "Logo Design"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate HD Visuals 🚀"):
        w, h = (1024, 1024) if "1:1" in i_size else (1280, 720)
        for i in range(count):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + i_style)}?width={w}&height={h}&nologo=true"
            st.image(url)

# --- PAGE 4: IMAGE MOTION ---
elif menu == "🎬 Image Motion":
    st.write("### 🎬 Professional Pixel Motion")
    col1, col2 = st.columns(2)
    with col1:
        mst = st.selectbox("Motion Style:", ["Slow Zoom In", "Slow Zoom Out", "Auto Motion"])
        msp = st.selectbox("Speed:", ["Slow", "Normal", "Fast"])
    with col2:
        mdur = st.selectbox("Duration:", ["5 Seconds", "10 Seconds"])
    
    f = st.file_uploader("Upload Image:", type=["jpg", "png", "jpeg"])
    if f and st.button("🚀 Animate Original Image"):
        res = animate_pixels(f, mst, mdur, msp)
        if "mp4" in res: st.video(res); st.download_button("Download", open(res, 'rb').read(), file_name=res)

st.markdown("<p style='text-align:center; padding:20px;'>Sglowina AI v2.0 Official</p>", unsafe_allow_html=True)
