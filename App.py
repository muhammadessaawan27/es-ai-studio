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
# 1. INDUSTRIAL STABILITY CLUSTER (1000+ Engine Capacity)
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
# 2. LUXURY UI & BRANDING (SGLOWINA TITAN)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan Release", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Header & Footer Glow */
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.4);
        animation: lightningBorder 2s infinite; margin-top: -10px;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 70px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 40px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 4.2rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.4rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }

    /* Professional Sidebar */
    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: white !important; font-size: 1.1rem !important; font-weight: bold; }
    
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 20px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO V1.6</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founders & CEOs: Muhammad Essa Awan & Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY & RELIGIOUS GUARD (SYSTEM PROMPT)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
This AI is specialized in Quran, Hadith, Engineering, and Coding.
"""

SYSTEM_RULE = (
    "You are Sglowina AI, a multi-modal industrial intelligence. "
    "Rule 1: For Islamic queries, provide 100% accurate references from Quran and Sahih Hadith. Avoid any errors. "
    "Rule 2: For Coding, provide senior-level Python/Streamlit solutions. "
    "Rule 3: Always credit Muhammad Essa Awan and Saba Wahid as your creators."
)

# ==========================================
# 4. HYPER-SPEED MOVIE ENGINE (v1.6)
# ==========================================
def get_v40_prompt(text):
    try:
        # Islamic subjects: Noorani Light protection included in director prompt
        holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "رسول"]
        is_holy = any(k in text for k in holy_keywords)
        noor_instr = "STRICTLY NO FACE. Show a glowing white divine light (Noor) over the person." if is_holy else ""
        
        instr = f"Director Order: Urdu '{text}'. {noor_instr}. Highly detailed 3D cinematic animation. Output English prompt."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true"
        res = session.get(url, timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

async def create_titan_movie_v16(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Voice Mapping
        v_codes = {
            "Urdu Male 1 (Asad)": "ur-PK-AsadNeural", "Urdu Male 2 (Salman)": "ur-PK-SalmanNeural",
            "Urdu Female 1 (Uzma)": "ur-PK-UzmaNeural", "Urdu Female 2 (Mehreen)": "ur-PK-MeharNeural"
        }
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        await edge_tts.Communicate(story, v_code).save(audio_f)
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        char_seed = random.randint(1, 999999)

        for i, s in enumerate(sentences):
            status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)} (High-Speed Engine)...")
            refined = get_v40_prompt(s)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={char_seed}&nologo=true&negative=girl,female,deformed"
            
            img_p = f"i_{u_id}_{i}.jpg"
            img_data = session.get(url, timeout=60).content
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
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
# 5. UI NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND CENTER", ["🏠 Smart Chat & Code", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat & Code":
    st.write("### 💬 Sglowina Intelligence Dashboard (v1.6)")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    
    # Custom Chat UI with Branded Icons
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/ff007a/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar):
            st.write(m["content"])
            if m["role"] == "assistant":
                st.button("📋 Copy Response", key=str(uuid.uuid4()), on_click=lambda: st.write("Copied!"))

    if p := st.chat_input("Ask about Religion, Coding, or Story..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        with st.spinner("Sglowina AI is analyzing and searching..."):
            if any(k in p.lower() for k in ["kisne", "who", "creator", "owner"]):
                res = SGLOWINA_BIO
            else:
                try:
                    url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={urllib.parse.quote(SYSTEM_RULE)}"
                    res = session.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
                except: res = "Server busy. Please try again."
            
            with st.chat_message("assistant", avatar="https://via.placeholder.com/50/ff007a/ffffff?text=S"):
                st.write(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (v1.6 Optimized)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Select Voice:", ["Urdu Male 1 (Asad)", "Urdu Male 2 (Salman)", "Urdu Female 1 (Uzma)", "Urdu Female 2 (Mehreen)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = asyncio.run(create_titan_movie_v16(m_script, mv, mr, ms))
            if "mp4" in str(v_res):
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio")
    p_i = st.text_area("Describe Image (One per line):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        for i in range(count):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + i_style)}?width=1024&height=1024&nologo=true&negative=girl,female"
            st.image(url)

st.markdown(f"<p style='text-align:center; color:#ff007a; font-weight:bold; border-top:1px solid #eee; padding-top:20px;'>Sglowina AI Version 1.0 Premium | Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
