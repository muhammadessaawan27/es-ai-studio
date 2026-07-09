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
# 1. INDUSTRIAL GRID STATION (Hyper-Speed)
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
# 2. LUXURY MINIMAL UI (WHITE BG + ELECTRIC LOGO)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Premium V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Clean Sidebar */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: bold !important; }

    /* Modern Rotating Electric Logo (Requirement 4) */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 100px; height: 100px; 
        background: radial-gradient(circle, #2563eb, #0f172a); 
        border-radius: 20px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: white;
        border: 3px solid #00d4ff; 
        box-shadow: 0 0 25px #00d4ff, inset 0 0 15px #ff007a;
        animation: rotate3D 6s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 3rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .ceo-tag { font-size: 1.1rem; color: #64748b; text-align: center; font-weight: bold; letter-spacing: 2px; }

    /* Professional Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #f1f5f9; padding: 10px; border-radius: 50px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; font-weight: 700 !important; color: #1e293b !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #2563eb !important; }

    /* Button and Input Styling */
    .stButton>button { 
        background: #0f172a !important; color: white !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 12px !important; color: #0f172a !important;
    }
    
    /* Progress Text Styling */
    .progress-text { color: #2563eb; font-weight: bold; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# Persistent Header (Minimal & Professional)
st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="ceo-tag">FOUNDERS & CEOs: SABA WAHID & MUHAMMAD ESSA AWAN</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED v1.0)
# ==========================================
SGLOWINA_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founders & CEOs:** Saba Wahid & Muhammad Essa Awan.

Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead logical architect (Professional Mechanical Engineer & Fabricator).

Sglowina AI is an industrial-grade intelligence platform. For security reasons, no further personal details can be disclosed.
"""

def is_identity_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"maker"])

# ==========================================
# 4. TITAN PARALLEL ENGINE (v1.0 POWER)
# ==========================================
if "char_seed" not in st.session_state:
    st.session_state.char_seed = random.randint(1, 999999)

def get_titan_prompt(text, style):
    try:
        # Islamic & Content Safety: Noorani Light logic
        holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba"]
        is_holy = any(k in text for k in holy_keywords)
        noor_instr = "STRICTLY NO FACE. Show a glowing divine white light (Noor) over the person. Realistic Islamic atmosphere." if is_holy else "Highly detailed symmetrical 3D character."
        
        instr = f"Director Instruction: '{text}'. {noor_instr}. Ensure full body and accurate subject recognition. Style: {style}. Output English prompt for AI Image Generator."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style):
    u_id = f"v1_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        # Voice Selection
        v_codes = {"Urdu Male 1": "ur-PK-AsadNeural", "Urdu Male 2": "ur-PK-SalmanNeural", 
                   "Urdu Female 1": "ur-PK-UzmaNeural", "Urdu Female 2": "ur-PK-GulNeural"}
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # EVERY SENTENCE = ONE UNIQUE SCENE
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s, style)
            # Subject Accuracy Check
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=girl,female,woman,deformed"
            img_urls.append(url)

        # PARALLEL RENDERING WITH PROGRESS TRACKING
        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.markdown(f"<p class='progress-text'>⚡ Scene {i+1}/{len(sentences)} is being rendered...</p>", unsafe_allow_html=True)
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # REAL CINEMATIC MOTION: 1.0 to 1.15 Zoom + Slight Pan
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position(lambda t: (0.05 * t, 'center'))
                clips.append(vfx.fadein(clip, 0.4))
            
        status.info("⚙️ Finalizing high-quality MP4 file...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close()
        final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI TABS (TRUE ISOLATION)
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Smart Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/0f172a/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar):
            st.write(m["content"])
    
    if p := st.chat_input("How can Sglowina help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # IDENTITY & KNOWLEDGE ENGINE
        with st.spinner("Sglowina AI analyzing..."):
            if is_identity_call(p): res = SGLOWINA_BIO
            else:
                try:
                    sys_p = urllib.parse.quote("You are Sglowina AI, owned by Saba Wahid & Muhammad Essa Awan. Answer accurately in Urdu.")
                    url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_p}"
                    res = requests.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
                except: res = "Server busy. Please try again."
            
            with st.chat_message("assistant", avatar="https://via.placeholder.com/50/0f172a/ffffff?text=S"):
                st.write(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Professional Cinematic Production")
    m_script = st.text_area("Yahan apni کہانی لکھیں (Every line will be a unique scene):", height=150, placeholder="Example: A king is sitting on a golden throne in his castle...")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Select Voice:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"], key="mv_v1")
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr_v1")
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="ms_v1")
    
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with tab_image:
    st.write("### 🎨 Sglowina Industrial Image Studio")
    p_i = st.text_area("Describe the Image or Logo (Use text in quotes for Logos):", placeholder='Example: A modern logo for "Sglowina" with electric effects...')
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "Digital Art"], key="is_v1")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD", "TikTok"], key="ir_v1")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        for i in range(count):
            with st.spinner(f"Painting image {i+1}..."):
                # DIRECTOR CALL: Ensuring Subject/Logo Accuracy
                refined = get_titan_prompt(p_i, i_style)
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&nologo=true&seed={random.randint(1,9999)}"
                st.image(url, caption=f"Sglowina V1.0 Result {i+1}")

st.markdown("<p style='text-align: center; color: #0f172a; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>Sglowina AI v1.0 | Founders & CEOs: Saba Wahid & Muhammad Essa Awan</p>", unsafe_allow_html=True)
