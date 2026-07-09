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

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE DIAMOND UI (WHITE & ELECTRIC)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Diamond V1.2", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }

    @keyframes lightning {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a; color: #fff; }
    }
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        animation: lightning 2.5s infinite;
    }
    .footer-electric {
        font-family: 'Orbitron', sans-serif; font-size: 1rem; font-weight: 900;
        text-align: center; letter-spacing: 2px; animation: lightning 2s infinite;
        background: #0f172a; padding: 15px; border-radius: 25px; margin-top: 50px;
    }
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 20px #00d4ff;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }
    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 12px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container"><div class="circular-s">S</div></div>
    <div style="text-align:center; margin-top:-10px;">
        <h1 style="color:#0f172a; margin-bottom:0;">Sglowina AI</h1>
        <p style="color:#ff007a; font-weight:bold; font-size:1.1rem; text-transform:uppercase;">Founder & CEO: Saba Wahid | COO: Muhammad Essa Awan</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founder & CEO: Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan.
Muhammad Essa Awan is the Chief Operations Officer (COO) and the lead visionary of this industrial-grade intelligence platform.
Official Version 1.0 Premium Release.
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"])

# ==========================================
# 4. TITAN v40 ENGINE (IMAGE DENSITY & ZOOM FIX)
# ==========================================
def get_v40_prompt(text):
    # Rule: Detect Subject to avoid Melting/Wrong Gender
    director_instr = f"Act as a Film Director: '{text}'. Professional 3D cinematic, symmetrical face, sharp eyes, high quality, accurate animals. No humans unless mentioned. Output English prompt."
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
        res = session.get(url, timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

def create_diamond_movie(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status_box = st.empty()
    try:
        # Step 1: Voice
        v_codes = {"Asad (Male)": "ur-PK-AsadNeural", "Salman (Male)": "ur-PK-SalmanNeural", "Uzma (Female)": "ur-PK-UzmaNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        # Step 2: STRICT SCENE SPLITTING (Ensure Image Changes)
        # Split by punctuation OR every 20 words to force density
        raw_sentences = re.split(r'[۔.!]', story)
        sentences = []
        for s in raw_sentences:
            if len(s.split()) > 25: # If sentence is too long, split it by word count
                words = s.split()
                for j in range(0, len(words), 20):
                    sentences.append(" ".join(words[j:j+20]))
            elif len(s.strip()) > 5:
                sentences.append(s.strip())
        
        if not sentences: sentences = [story]

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        clips = []
        dur_per = audio.duration / len(sentences)
        char_seed = random.randint(1, 999999)

        # Parallel Fetch
        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(get_v40_prompt(s) + ' ' + style)}?width={w}&height={h}&seed={char_seed}&nologo=true&negative=distorted,melted,girl,female,deformed" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status_box.info(f"💎 Rendering Scene {i+1}/{len(sentences)} (Diamond Mode)...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                
                # FIXED ZOOM OUT (1.0 -> 1.25) - Image grows bigger (Expansion)
                clip = clip.resize(lambda t: 1.0 + 0.04 * t).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Diamond_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/000000/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_id_call(p): res = SGLOWINA_BIO
        else:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true"
                res = session.get(url, timeout=25).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server busy. Please try again."
        with st.chat_message("assistant", avatar="https://via.placeholder.com/50/000000/ffffff?text=S"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎥 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Diamond Masterpiece 🚀"):
        if m_script:
            v_res = create_diamond_movie(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Image Studio")
    p_i = st.text_area("Describe Image (One per line):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"], key="is")
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        for i in range(count):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + i_style)}?width={w}&height={h}&nologo=true&negative=girl,female,deformed"
            st.image(url)

st.markdown('<div class="footer-electric">SGLOWINA AI v1.0 | CEO: SABA WAHID | COO: MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
