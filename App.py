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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (MOBILE OPTIMIZED + v1.0 LOCKED)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Premium V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Responsive Header Fix for Mobile */
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 3px; color: #fff;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        animation: lightningBorder 2s infinite;
        margin-top: -10px;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
        animation: rotate3D 10s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: clamp(2rem, 10vw, 4rem); font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    
    .exec-info { font-size: 1.1rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px; }
    .coo-info { font-size: 1rem; color: #2563eb; text-align: center; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; }

    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="exec-info">Founder & CEO: Saba Wahid</div>
        <div class="coo-info">Chief Operations Officer: Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (EXECUTIVE BIO - LOCKED)
# ==========================================
# Exact professional prompt/bio as per instruction
SGLOWINA_BIO = """
Sglovina AI is proudly developed by the Sglovina Team.

Saba Wahid serves as the Founder & CEO of Sglovina AI.

Muhammad Essa Awan is the Chief Operations Officer (COO) and the visionary behind the platform's core logic and configuration.

Sglovina AI is a high-end industrial intelligence platform. For security reasons, no further personal details can be provided.
"""

def is_identity_request(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"sglowina", r"administrator"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. v40 ENGINE - MASTER RECOGNITION
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Act as a Film Director: Extract core visual from Urdu: '{text}'. Detailed English 3D animation prompt. Accurate subjects. No humans unless asked."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_v40_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
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
            status.info(f"🎨 Sglowina AI V1.0 Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_v40_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,woman,deformed"
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(session.get(img_url, timeout=60).content)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_V1_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION (v1.0 LOCKED)
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_identity_request(p): res = SGLOWINA_BIO
        else:
            try:
                sys_instr = urllib.parse.quote("You are Sglowina AI, owned by Saba Wahid. Answer professionally and ONLY in the user's language.")
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_instr}"
                res = requests.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server is busy. Please try again."
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Official Cinematic Production Engine")
    m_script = st.text_area("Enter Movie Script:", height=150, key="v1_movie")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"], key="v1_v")
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="v1_r")
    with mc3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="v1_s")
    if st.button("Generate Official Masterpiece 🚀"):
        if m_script:
            v_res = create_v40_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio (Multi-Prompt)")
    p_i = st.text_area("Describe images (One per line):", height=150, placeholder="Prompt 1\nPrompt 2...")
    c1, c2 = st.columns(2)
    with c1: i_style = st.selectbox("Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"], key="is")
    with c2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD", "TikTok"], key="ir")
    if st.button("Generate Masterpieces 🚀"):
        if p_i:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim[i_size]
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
            for idx, single_p in enumerate(prompt_list):
                with st.spinner(f"Sglowina AI is painting image {idx+1}..."):
                    hd_p = f"{single_p}, symmetrical face, high quality skin, detailed, 8k"
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(hd_p + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,deformed"
                    st.image(url, caption=f"Prompt {idx+1}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglowina AI v1.0 | Founder & CEO: Saba Wahid | COO: Muhammad Essa Awan</p>", unsafe_allow_html=True)
