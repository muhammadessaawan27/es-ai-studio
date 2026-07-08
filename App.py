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
# 1. INDUSTRIAL STABILITY & SCALING
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Critical Backend Failure: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. ELECTRIC SGLOVINA UI & ANIMATED LOGO
# ==========================================
st.set_page_config(page_title="Sglovina AI - The Electric Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }

    /* Electric Arc Animation for Logo */
    @keyframes electricPulse {
        0%, 100% { box-shadow: 0 0 20px #ff007a, 0 0 40px #7C3AED; border-color: #fff; }
        50% { box-shadow: 0 0 50px #00d4ff, 0 0 80px #2563eb; border-color: #00d4ff; }
    }
    
    @keyframes textLightning {
        0%, 100% { text-shadow: 0 0 10px #ff007a; color: #ff007a; }
        50% { text-shadow: 0 0 30px #00d4ff, 0 0 50px #2563eb; color: #00d4ff; }
    }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 40px 0; }
    .electric-s {
        width: 120px; height: 120px; 
        background: #0f172a; border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 60px; font-weight: 900;
        color: white; border: 4px solid #ff007a;
        animation: electricPulse 2s infinite ease-in-out, rotateS 10s infinite linear;
    }
    @keyframes rotateS { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .brand-name { font-size: 4rem; font-weight: 900; animation: textLightning 2s infinite; text-align: center; margin-top: 10px; }
    .admin-tag { font-size: 1.2rem; color: #1e293b; text-align: center; font-weight: bold; letter-spacing: 4px; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 15px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold; border: none;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1); transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 15px 30px rgba(255, 0, 122, 0.4); }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglovina AI</div>
        <div class="admin-tag">ADMINISTRATOR: SABA WAHID</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. OFFICIAL SGLOVINA IDENTITY (LOCKED)
# ==========================================
SGLOVINA_BIO = """
**Sglovina AI is proudly developed by the Sglovina Team.**

**Administrator:** Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglovina AI is an industrial-grade multi-modal intelligence platform designed for the highest precision in video and image creation.
"""

def is_identity_call(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"saba wahid", r"sglovina", r"administrator"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 4. v40 INDUSTRIAL ENGINE (ZOOM IN EXPANSION)
# ==========================================
def get_titan_prompt(urdu_text, mining_mode=False):
    mining_instr = "Include microscopic details, textures, and ultra-high precision." if mining_mode else ""
    try:
        instr = f"Director Instruction: '{urdu_text}'. Describe ONLY the core subject in English. No humans unless asked. {mining_instr} Cinematic 8k."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_titan_movie(story, voice_gen, ratio, style, mining):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        clips = []
        dur_per = audio.duration / len(sentences)
        
        for i, s in enumerate(sentences):
            status.info(f"⚡ Sglovina Engine Processing Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s, mining)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,female,woman,human"
            
            img_data = session.get(img_url).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            
            clean_im = Image.open(img_p).convert("RGB").resize((w, h))
            clean_im.save(img_p, "JPEG")
            
            clip
