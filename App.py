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

# Senior Engineer Stability Configuration
session = requests.Session()

# PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. SGLOVINA BRANDING & UI (LUXURY THEME)
# ==========================================
st.set_page_config(page_title="Sglovina AI - Official Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .owner-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 900;
        text-align: center; letter-spacing: 3px; color: #ff007a;
        background: #fdf2f8; padding: 10px; border-bottom: 3px solid #ff007a;
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .s-logo {
        width: 130px; height: 130px; 
        background: linear-gradient(135deg, #ff007a, #7C3AED);
        border-radius: 30px; display: flex; align-items: center; justify-content: center;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.3);
        border: 5px solid #fff; animation: float 3s ease-in-out infinite;
    }
    @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    
    .brand-title { font-size: 3.5rem; font-weight: 900; color: #ff007a; text-align: center; margin-top: 10px; letter-spacing: -1px; }
    .powered-by { font-size: 1rem; color: #64748b; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #7C3AED) !important; 
        color: white !important; border-radius: 50px !important; height: 50px; font-weight: bold; border: none;
    }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 15px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-header">SGLOVINA AI - PRODUCT BY SGLOVINA TEAM</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="s-logo">
            <span style="color:white; font-family:'Orbitron'; font-size:50px; font-weight:900;">S</span>
        </div>
        <div class="brand-title">Sglovina AI</div>
        <div class="powered-by">Administrator: Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. NEW OFFICIAL IDENTITY (SGLOVINA BIO)
# ==========================================
SGLOVINA_BIO = """
**Sglovina AI is proudly developed by the Sglovina Team.**

**Administrator:** Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglovina AI is a professional multi-modal intelligence platform designed for high-end cinematic production, image generation, and intelligent consultation.
"""

def is_identity_query(q):
    patterns = [
        r"kisne banaya", r"who made you", r"creator", r"owner", 
        r"saba wahid", r"sglovina", r"administrator", r"founder", r"maker"
    ]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 3. v40 MOVIE ENGINE (LOCKED & PRESERVED)
# ==========================================
def get_v40_prompt(urdu_text):
    try:
        instr = f"Director Call: Extract core visual from Urdu: '{urdu_text}'. Detailed English 3D animation prompt. Accurate animals/objects. No humans unless mentioned."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_v40_movie_engine(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"🎬 Scene {i+1}/{len(sentences)} rendering...")
            refined = get_v40_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            img_data = session.get(img_url).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            clean_im = Image.open(img_p).convert("RGB").resize((w, h))
            clean_im.save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglovina_Movie_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. IMAGE STUDIO (UNIVERSAL & PRECISE)
# ==========================================
def image_studio_module():
    st.write("### 🎨 Sglovina Artistic Studio")
    mode = st.radio("Choose Mode:", ["Text to Image", "Professional Photo Edit"], horizontal=True)
    size_opts = {"YouTube Thumbnail": (1280, 720), "TikTok/Reel": (720, 1280), "Instagram Post": (1024, 1024), "YouTube Banner": (2560, 1080)}
    if mode == "Text to Image":
        p = st.text_area("جو تصویر بنوانی ہے بیان کریں:")
        c1, c2 = st.columns(2)
        with c1: st_sel = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Sketch"], key="i_s")
        with c2: sz_sel = st.selectbox("Size/Ratio:", list(size_opts.keys()), key="i_r")
        if st.button("Generate Masterpiece 🚀"):
            w, h = size_opts[sz_sel]
            with st.spinner("Sglovina AI is painting..."):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p + ' ' + st_sel)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female"
                st.image(url)
    else:
        f = st.file_uploader("Upload Image:", type=["jpg", "png"])
        if f:
            st.image(f, width=300)
            edit_req = st.text_area("تبدیلی بیان کریں:")
            if st.button("Apply AI Surgery 🚀"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_req)}?width=1024&height=1024&nologo=true&negative=girl,female"
                st.image(url)

# ==========================================
# 5. UI ASSEMBLY
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Sglovina Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Admin..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # New Identity Logic
        if is_identity_query(p):
            res = SGLOVINA_BIO
        else:
            sys_instr = urllib.parse.quote("You are Sglovina AI, developed by Sglovina Team. Admin is Saba Wahid. Answer professionally.")
            res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&system={sys_instr}").text
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Sglovina Cinematic Engine")
    m_s = st.text_area("Movie Script:", height=150, key="movie_s")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="ms")
    if st.button("Generate Sglovina Movie 🚀"):
        if m_s:
            v_res = create_v40_movie_engine(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with tab_image:
    image_studio_module()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglovina AI v71.0 | Developed by Sglovina Team | Admin: Saba Wahid</p>", unsafe_allow_html=True)
