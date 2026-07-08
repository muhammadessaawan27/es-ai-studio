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
# 1. INDUSTRIAL STABILITY & BACKEND
# ==========================================
session = requests.Session()

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Failure: Please Reboot App. Detail: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. SGLOWINA ELECTRIC UI & LOGO (v29 + v37 STYLE)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Master Studio", layout="wide", page_icon="🎬")

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
        0%, 100% { text-shadow: 0 0 10px #ff007a, 0 0 20px #ff007a; color: #ff007a; }
        50% { text-shadow: 0 0 30px #00d4ff, 0 0 50px #2563eb; color: #00d4ff; }
    }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 110px; height: 110px; 
        background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; font-weight: 900;
        color: white; border: 4px solid #ff007a;
        animation: electricPulse 2s infinite ease-in-out, rotateS 8s infinite linear;
    }
    @keyframes rotateS { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .brand-name { font-size: 3.5rem; font-weight: 900; animation: textLightning 1.5s infinite; text-align: center; margin-top: 10px; }
    .admin-tag { font-size: 1.1rem; color: #1e293b; text-align: center; font-weight: bold; letter-spacing: 3px; margin-bottom: 20px; }

    /* Sidebar and Menu */
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: white !important; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. SGLOWINA OFFICIAL IDENTITY (STRICT)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

Administrator: Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglowina AI is a high-end industrial intelligence platform. (No further details can be provided).
"""

def check_identity(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"owner", r"saba", r"essa", r"sglowina", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. v40 MOVIE ENGINE (LOCKED & PRESERVED)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Director: Extract core subject from Urdu: '{text}'. Create a detailed English 3D prompt. No humans unless asked."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_v40_movie_v73(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        for i, s in enumerate(sentences):
            status.info(f"⚡ Sglowina Engine Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_v40_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,female,woman"
            
            img_data = session.get(img_url).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            
            Image.open(img_p).convert("RGB").resize((w, h)).save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Zoom In Expansion (1.0 to 1.15)
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
# 5. UI ASSEMBLY (SIDEBAR PAGE ISOLATION)
# ==========================================
st.sidebar.markdown(f"<h2 style='color:white; text-align:center;'>Sglowina AI</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Main Menu:", ["💬 Smart Chat", "🎥 Movie Studio", "🎨 Image Studio"])

# --- PERSISTENT LOGO ---
st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="admin-tag">ADMINISTRATOR: SABA WAHID</div>
    </div>
    """, unsafe_allow_html=True)

# --- PAGE 1: SMART CHAT ---
if menu == "💬 Smart Chat":
    st.write("### 💬 Sglowina Intelligent Assistant")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
        
    if p := st.chat_input("How can Sglowina AI help you?", key="chat_input"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # Identity Check Override
        if check_identity(p):
            res = SGLOWINA_BIO
        else:
            # Persistent System Prompt to AI Engine
            sys_instr = urllib.parse.quote("You are Sglowina AI, developed by Sglowina Team. Admin is Saba Wahid. Answer professionally and ONLY in the user's language.")
            url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_instr}"
            try:
                res = session.get(url, timeout=30).text
                # Extra check to remove "OpenAI/ChatGPT" claims from response
                res = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server busy. Please refresh Sglowina AI."
            
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif menu == "🎥 Movie Studio":
    st.write("### 🎥 v40 Cinematic Video Production")
    m_s = st.text_area("Enter Movie Script:", height=150, key="v73_movie_area")
    v_c1, v_c2, v_c3 = st.columns(3)
    with v_c1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="v73_v")
    with v_c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="v73_r")
    with v_c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="v73_s")
    
    if st.button("🚀 Generate Sglowina Movie", key="v73_movie_btn"):
        if m_s:
            v_res = create_v40_movie_v73(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# --- PAGE 3: IMAGE STUDIO ---
elif menu == "🎨 Image Studio":
    st.write("### 🎨 Sglowina Artistic Surgeon")
    mode = st.radio("Chose:", ["Text to Image", "Logo/Banner Design", "Edit Photo"], horizontal=True, key="v73_mode")
    
    # Ratios for Image Studio
    sz_map = {"Square (1:1)": (1024, 1024), "YouTube Banner": (2560, 1080), "Thumbnail": (1280, 720), "TikTok": (720, 1280)}
    
    if mode == "Text to Image" or mode == "Logo/Banner Design":
        p_i = st.text_area("Describe the Image/Logo you want:", key="v73_img_p")
        c1, c2 = st.columns(2)
        with c1: i_s = st.selectbox("Style:", ["Realistic", "Logo Concept", "Anime", "Sketch"], key="v73_is")
        with c2: i_r = st.selectbox("Size:", list(sz_map.keys()), key="v73_ir")
        if st.button("Generate Masterpiece 🚀", key="v73_img_btn"):
            if p_i:
                w, h = sz_map[i_r]
                with st.spinner("Painting..."):
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + i_s)}?width={w}&height={h}&nologo=true&negative=girl,female"
                    st.image(url, caption="Sglowina Masterpiece")
    else:
        f = st.file_uploader("Upload Image:", type=["jpg", "png"], key="v73_f")
        if f:
            st.image(f, width=250)
            e_p = st.text_input("What to change?", key="v73_e")
            if st.button("Apply Surgery 🚀", key="v73_ebtn"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(e_p)}?width=1024&height=1024&nologo=true&negative=girl,female"
                st.image(url)

st.sidebar.markdown("---")
st.sidebar.info(f"Sglowina AI v73.0 | Admin: Saba Wahid")
