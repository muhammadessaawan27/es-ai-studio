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
# 1. INDUSTRIAL STABILITY & BACKEND
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
# 2. EXECUTIVE UI (WHITE & BLACK MINIMAL)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Launch", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    .executive-header {
        text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    .main-names { font-size: 1.4rem; font-weight: 800; color: #000000; }
    .title-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 3px; text-transform: uppercase; }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spin 10s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 8px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="executive-header">
        <div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
        <div class="title-tag">Founders & CEOs | Sglowina AI Official Studio</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead visionary.
Saba Wahid is the spouse of Muhammad Essa Awan.
"""

def is_id_call(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. TITAN MOVIE & MOTION ENGINES (v40 LOGIC)
# ==========================================
def get_v40_prompt(text, style):
    try:
        instr = f"Act as a Film Director: '{text}'. Professional 3D character animation. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie_v1(story, voice, ratio, style, seed):
    u_id = f"v1_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"⚡ Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_v40_prompt(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,deformed"
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION (TRUE ISOLATION)
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio", "🎬 Image to Motion"])

# --- PAGE 1: CHAT ---
if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if is_id_call(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res.replace("ChatGPT", "Sglowina AI")); st.session_state.msgs.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif menu == "🎥 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production (v40 Locked)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    with mc4: sd = st.number_input("Character ID:", value=786)
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, 1, sd)
            if "mp4" in v_res: st.video(v_res); st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

# --- PAGE 3: IMAGE STUDIO (FULL OPTIONS & UNIQUE VARIATIONS) ---
elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image(s) - One per line for batch:")
    
    # All Ratios Restored
    sz_opts = {
        "Square (1:1)": (1024, 1024), "YouTube HD (16:9)": (1280, 720), 
        "TikTok (9:16)": (720, 1280), "YouTube Banner": (2560, 1080), "Logo Size": (512, 512)
    }
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon", "Sketch"])
    with ic2: i_size = st.selectbox("Resolution:", list(sz_opts.keys()))
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    char_id = st.text_input("Character ID (Lock face):", value="786")

    if st.button("Generate Titan Visuals 🚀"):
        if p_i:
            w, h = sz_opts[i_size]
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
            for idx, single_p in enumerate(prompt_list):
                for q in range(count):
                    with st.spinner(f"Painting image {idx*count + q + 1}..."):
                        # UNIQUE VARIATION LOGIC: Adding internal salt to seed for unique results
                        unique_seed = int(char_id) + q + (idx * 100)
                        # DIRECTOR CALL: Ensuring Subject/Logo Accuracy
                        refined = get_v40_prompt(single_p, i_style)
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={unique_seed}&nologo=true&negative=girl,female"
                        st.image(url, caption=f"Prompt: {single_p[:30]}... (ID: {unique_seed})")

# --- PAGE 4: MOTION ---
elif menu == "🎬 Image to Motion":
    st.write("### 🌊 Universal Motion Engine")
    up_img = st.file_uploader("Upload Image:")
    if up_img:
        st.image(up_img, width=300)
        m_desc = st.text_input("Describe the movement:")
        if st.button("Animate 🚀"):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_desc)}?width=1024&height=1024&model=video&nologo=true"
            st.image(url)

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #64748b;'>Sglowina AI v1.0 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
