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
# 1. INDUSTRIAL SPEED & STABILITY (LOCKED)
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200)
session.mount('https://', adapter)

# Parallel Processing for 5G-like speed
executor = ThreadPoolExecutor(max_workers=20)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. INTERNATIONAL LUXURY UI (SLATE & SILVER)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.0 Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;800&display=swap');
    
    /* Main Background: Luxury Slate */
    .stApp { background-color: #f8fafc; color: #1e293b; font-family: 'Inter', sans-serif; }
    
    /* Sidebar: Premium Glass Effect */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%) !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: 600 !important; }

    /* Intense Lightning Glow (Header & Footer) */
    @keyframes lightning {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #2563eb; color: #fff; }
        50% { text-shadow: 0 0 25px #ff007a, 0 0 45px #ff007a; color: #fff; }
    }

    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1.2rem, 5vw, 2rem); font-weight: 900;
        text-align: center; letter-spacing: 4px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        animation: lightning 2s infinite; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .footer-diamond {
        font-family: 'Orbitron', sans-serif; font-size: 1rem; font-weight: 900;
        text-align: center; letter-spacing: 2px; animation: lightning 2s infinite;
        background: #0f172a; padding: 15px; border-radius: 25px; margin-top: 50px;
    }

    /* 3D Rotating Logo */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 28px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 60px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 35px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: clamp(2.5rem, 10vw, 4.5rem); font-weight: 900; color: #0f172a; text-align: center; }
    .founder-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 14px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.2); transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 12px 25px rgba(255, 0, 122, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# UI Elements
st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founders & CEOs: Saba Wahid & Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founders & CEOs:** Saba Wahid & Muhammad Essa Awan.

Saba Wahid is the Founder & Chief Executive Officer. 
Muhammad Essa Awan is the Co-Founder & Chief Operations Officer (COO), a professional Mechanical Engineer and the lead logical architect of this platform.

Sglowina AI is a premier industrial intelligence platform. (Official Version 1.0).
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder"])

# ==========================================
# 4. v40 TITAN SPEED ENGINE (LOCKED)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Director: '{text}'. Professional 3D animation, symmetrical features. No humans unless asked. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_image_data(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # Step 2: Smart Scene Detection (Limited for high speed)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 10]
        # Optimization: Limit to max 12 scenes for hyper-speed on long stories
        if len(sentences) > 12: sentences = sentences[:12]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        # Parallel Image Generation (The 5G Speed Fix)
        image_urls = []
        for s in sentences:
            refined = get_v40_prompt(s)
            seed = random.randint(1, 999999)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,woman,deformed"
            image_urls.append(url)

        status.info(f"🚀 Hyper-Speed Engine processing {len(sentences)} scenes in parallel...")
        
        # Multithreaded downloading
        with ThreadPoolExecutor(max_workers=10) as download_exec:
            images_data = list(download_exec.map(fetch_image_data, image_urls))

        for i, img_data in enumerate(images_data):
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Zoom In Expansion (LOCKED)
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
# 5. NAVIGATION
# ==========================================
st.sidebar.markdown(f"## ⚙️ SGLOWINA TITAN")
menu = st.sidebar.radio("Navigate Studio:", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_id_call(p): res = SGLOWINA_BIO
        else:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true"
            res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (Hyper-Speed)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Masterpiece 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio (Multi-Prompt)")
    p_i = st.text_area("Describe images (One per line):", height=150)
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(single_p + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female"
                st.image(url)

st.markdown('<div class="footer-diamond">SGLOWINA AI v1.0 | FOUNDERS & CEOs: SABA WAHID & MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
