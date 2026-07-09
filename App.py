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
# 1. INDUSTRIAL GRADE STABILITY & SPEED
# ==========================================
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
# 2. BRANDING & UI (WHITE SIDEBAR + LIGHTNING)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.5", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: bold !important; }

    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 15px #2563eb, 0 0 30px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 45px #ff007a; color: #fff; }
    }

    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        animation: lightningGlow 2.5s infinite;
    }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 60px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 35px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 4rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.3rem; color: #ff007a; text-align: center; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 14px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founders & CEOs: Muhammad Essa Awan & Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.

Muhammad Essa Awan is the lead visionary, Mechanical Engineer, and Chief logical architect. 
Saba Wahid is the Co-Founder and CEO of this platform.

Sglowina AI is a premier industrial intelligence platform. (Version 1.0 Release).
"""

# ==========================================
# 4. ISLAMIC SAFETY & CHARACTER LOCK ENGINE
# ==========================================
def get_titan_prompt(text, char_seed):
    # Detect Religious Terms (Rule 1: Holy Person Protection)
    holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah", "Buzurg", "Saint"]
    is_holy = any(k in text for k in holy_keywords)
    
    # Noorani Light Filter
    noor_instr = "STRICTLY NO FACE. Show a glowing white divine light (Noor) where the face should be. Show followers from behind. Holy and respectful atmosphere." if is_holy else ""
    
    try:
        # GPT-4 Directing the visual accuracy and character locking
        instr = f"Director Order: Urdu '{text}'. {noor_instr}. Describe ONLY the primary subject. 3D animation, symmetrical, reference seed {char_seed}. Output English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v15(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_codes = {"Urdu Male 1": "ur-PK-AsadNeural", "Urdu Male 2": "ur-PK-SalmanNeural", 
                   "Urdu Female 1": "ur-PK-UzmaNeural", "Urdu Female 2": "ur-PK-GulNeural"}
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # INCREASED SCENE DENSITY (20-25 Scenes logic)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if len(sentences) > 25: sentences = sentences[:25] # Cap at 25 for stability
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        char_seed = random.randint(1, 999999) # Fixed seed for character consistency

        # HYPER-SPEED PARALLEL PROCESSING
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s, char_seed)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={char_seed}&nologo=true&negative=girl,female,woman,deformed"
            img_urls.append(url)

        status.info(f"🚀 Sglowina 5G Engine rendering {len(sentences)} scenes...")
        with ThreadPoolExecutor(max_workers=20) as exe:
            images_data = list(exe.map(fetch_img, img_urls))

        for i, img_data in enumerate(images_data):
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # REAL VIDEO EFFECT: Zoom In + Slight Panning (1.0 to 1.15)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position(lambda t: (0.1 * t, 'center'))
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_V15_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close()
        final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. NAVIGATION & TABS
# ==========================================
st.sidebar.markdown(f"## ⚙️ SGLOWINA TITAN")
menu = st.sidebar.radio("Navigate:", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligent Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who", "creator", "owner"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (v1.5 Noorani Edition)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Select Voice:", ["Urdu Male 1", "Urdu Male 2", "Urdu Female 1", "Urdu Female 2"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v15(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio")
    p_i = st.text_area("Describe Image (One per line):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        for i in range(count):
            refined = get_titan_prompt(p_i, random.randint(1,999))
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + i_style)}?nologo=true&negative=girl,female"
            st.image(url)

st.markdown(f"<p style='text-align:center; color:#ff007a; font-weight:bold; border-top:1px solid #eee; padding-top:20px;'>Sglowina AI Version 1.0 Premium | Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
