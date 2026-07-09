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
# 1. INDUSTRIAL STABILITY & HYPER-SPEED
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

# ==========================================
# 2. EXECUTIVE MINIMAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Version 1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    /* Sidebar: Clean White Style */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }

    /* Minimal Header */
    .thin-header {
        text-align: center; padding: 5px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px; color: #000000;
    }
    .main-names { font-size: 1.4rem; font-weight: 700; margin-bottom: 2px; }
    .title-tag { font-size: 0.9rem; font-weight: 500; color: #64748b; letter-spacing: 3px; }

    /* Circular Electric Logo */
    .logo-container { display: flex; justify-content: center; padding: 15px 0; }
    .circular-s {
        width: 100px; height: 100px; background: radial-gradient(circle, #0f172a 0%, #000000 100%); 
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 20px #00d4ff, inset 0 0 15px #ff007a;
        animation: spinGlow 8s infinite linear;
    }
    @keyframes spinGlow { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 18px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Persistent Identity Data
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead visionary.
Official Version 1.0 Premium Release.
"""

# State Management for Character Consistency
if "char_seed" not in st.session_state:
    st.session_state.char_seed = 786

# ==========================================
# 3. TITAN MOVIE ENGINE (v40 LOGIC)
# ==========================================
def get_v40_prompt(text, style):
    try:
        instr = f"Act as a Film Director: '{text}'. 3D animation, symmetrical features, high detail. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

def create_titan_movie(story, voice, ratio, style, part):
    u_id = f"v1_p{part}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_map = {"Asad (Male)": "ur-PK-AsadNeural", "Uzma (Female)": "ur-PK-UzmaNeural", "Salman (Male)": "ur-PK-SalmanNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_map.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(get_v40_prompt(s, style))}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=girl,female,deformed" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"⚡ Part {part}: Rendering Scene {i+1}/{len(sentences)}...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Part_{part}_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. NAVIGATION & SIDEBAR
# ==========================================
st.sidebar.markdown(f"## ⚙️ SGLOWINA MENU")
page = st.sidebar.radio("Navigate Studio:", ["🏠 Smart Chat", "🎥 Movie Studio (Parts)", "🎨 Image Studio (HD)"])

# PERSISTENT HEADER
st.markdown("""<div class="thin-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
    <div class="title-tag">FOUNDERS & CEOs | SGLOWINA AI</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# --- CHAT ---
if page == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/000000/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "creator", "owner"]) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant", avatar="https://via.placeholder.com/50/000000/ffffff?text=S"):
            st.write(res.replace("ChatGPT", "Sglowina AI")); st.session_state.msgs.append({"role": "assistant", "content": res})

# --- MOVIE STUDIO ---
elif page == "🎥 Movie Studio (Parts)":
    st.write("### 🎥 Industrial Cinematic Production (10 min support)")
    p_num = st.number_input("Part Number:", min_value=1, value=1)
    if st.button("Reset Character for New Project"):
        st.session_state.char_seed = random.randint(1, 999999); st.success("New Identity Locked!")
    
    m_script = st.text_area("Enter Story Part Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Select Voice:", ["Asad (Male)", "Uzma (Female)", "Salman (Male)", "Gul (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button("Generate Part 🚀"):
        v_res = create_titan_movie_v1(m_script, mv, mr, ms, p_num)
        if "mp4" in v_res: st.video(v_res); st.download_button("Download Part ⬇️", open(v_res, 'rb').read(), file_name=v_res)

# --- IMAGE STUDIO ---
elif page == "🎨 Image Studio (HD)":
    st.write("### 🎨 Industrial Visual Studio")
    p_i = st.text_area("Describe images (One per line for batch):", height=150)
    
    ratio_opts = {"1:1 Square": (1024, 1024), "16:9 YouTube": (1280, 720), "9:16 TikTok": (720, 1280), "21:9 Banner": (2560, 1080)}
    ic1, ic2, ic3 = st.columns(3)
    with ic1: is_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: is_size = st.selectbox("Resolution:", list(ratio_opts.keys()))
    with ic3: is_count = st.slider("Quantity:", 1, 10, 1)
    
    char_id = st.text_input("Consistency Lock (Seed):", value=str(st.session_state.char_seed))

    if st.button("Generate HD Visuals 🚀"):
        w, h = ratio_opts[is_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(is_count):
                with st.spinner(f"Painting image..."):
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(single_p + ' ' + is_style)}?width={w}&height={h}&seed={char_id}&nologo=true&negative=girl,female"
                    st.image(url)

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #64748b;'>Sglowina AI Version 1.0 Premium Release | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
