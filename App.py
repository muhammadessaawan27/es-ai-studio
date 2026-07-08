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
    st.error(f"Engine Failure: Please Reboot App via 'Manage app'. Detail: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. ELECTRIC SGLOVINA UI & ANIMATED LOGO
# ==========================================
st.set_page_config(page_title="Sglovina AI - The Electric Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }

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
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 20px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
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
Sglovina AI is proudly developed by the Sglovina Team.

Administrator: Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglovina AI is a professional industrial-grade multi-modal intelligence platform designed for high-end cinematic production and precision image generation.
"""

def is_identity_call(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"saba wahid", r"sglovina", r"administrator"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 4. v40 INDUSTRIAL ENGINE (FIXED)
# ==========================================
def get_titan_prompt(urdu_text, mining_mode=False):
    m_instr = "Include microscopic details, ultra-high precision, professional textures." if mining_mode else ""
    try:
        instr = f"Act as a Director: '{urdu_text}'. Describe ONLY the core subject in English. No humans unless asked. {m_instr} Cinematic 8k."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_titan_movie_v72(story, voice_gen, ratio, style, mining):
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
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        for i, s in enumerate(sentences):
            status.info(f"⚡ Sglovina Processing Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s, mining)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,female,woman,human"
            
            img_data = session.get(img_url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            
            with Image.open(img_p) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # ZOOM IN EXPANSION (1.0 to 1.15) - As requested
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglovina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        audio.close()
        final_video.close()
        return out
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 5. IMAGE & LOGO STUDIO
# ==========================================
def image_studio_titan():
    st.write("### 🎨 Sglovina Universal Image Studio")
    mode = st.radio("Select Mode:", ["Text to Image", "Logo Design", "Professional Photo Edit"], horizontal=True)
    
    size_map = {"Square (1:1)": (1024, 1024), "TikTok (9:16)": (720, 1280), "YouTube (16:9)": (1280, 720)}
    p = st.text_area("جو تصویر یا لوگو بنوانا ہے بیان کریں:")
    c1, c2, c3 = st.columns(3)
    with c1: st_sel = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Logo Concept"], key="is")
    with c2: sz_sel = st.selectbox("Size/Ratio:", list(size_map.keys()), key="ir")
    with c3: mining = st.checkbox("Mining Mode (Ultra Precision)")

    if st.button("Generate Masterpiece 🚀", key="img_btn"):
        if p:
            w, h = size_map[sz_sel]
            neg = "&negative=girl,female,woman,distorted" if "girl" not in p.lower() else ""
            with st.spinner("Sglovina Titan is rendering..."):
                refined = get_titan_prompt(p, mining)
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + st_sel)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true{neg}"
                st.image(url, caption="Sglovina Precision Result")
                st.download_button("Download ⬇️", requests.get(url).content, file_name="sglovina_img.jpg")

# ==========================================
# 6. UI ASSEMBLY
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOVINA_BIO if is_identity_call(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Industrial Video Production (v40 Power)")
    m_s = st.text_area("Movie Script:", height=150, key="ms_v72")
    cm1, cm2, cm3 = st.columns(3)
    with cm1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv_v72")
    with cm2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr_v72")
    with cm3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="ms_v72")
    mine_v = st.checkbox("Precision Mining (Industrial Quality)", key="mine_v")
    if st.button("🚀 Generate Master Movie", key="btn_v72"):
        if m_s:
            v_res = create_titan_movie_v72(m_s, mv, mr, ms, mine_v)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

with tab_image:
    image_studio_titan()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglovina AI v72.1 | THE ELECTRIC TITAN | Fixed Syntax | Admin: Saba Wahid</p>", unsafe_allow_html=True)
