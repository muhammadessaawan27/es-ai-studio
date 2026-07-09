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
# 1. INDUSTRIAL GRID ENGINE (MAX CAPACITY)
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
# 2. LUXURY MINIMAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Launch", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    /* Executive Header */
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        animation: lightningBorder 2s infinite; margin-top: -10px;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 100px; height: 100px; background: #000000; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: clamp(2rem, 10vw, 4rem); font-weight: 900; color: #000000; text-align: center; margin-top: 10px; }
    .founder-info { font-size: 1.3rem; color: #ff007a; text-align: center; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
    .coo-info { font-size: 1.1rem; color: #2563eb; text-align: center; font-weight: bold; text-transform: uppercase; margin-bottom: 20px; }

    /* Button and Input Styling */
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 12px !important; 
        height: 60px; width: 100%; font-size: 22px; font-weight: bold; border: none;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; 
        border-radius: 12px !important; color: #000000 !important; font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-info">Founders & CEOs: Muhammad Essa Awan & Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
OFFICIAL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.

Muhammad Essa Awan is the lead visionary, Mechanical Engineer, and Chief logical architect. 
Saba Wahid is the Co-Founder and CEO of this platform, the daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan.

Sglowina AI is a professional high-end industrial intelligence platform. (Version 1.0 Official Release).
"""

def is_identity_request(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. TITAN MOVIE ENGINE (v40 LOCKED)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Act as a Film Director: Extract core visual subject from Urdu: '{text}'. Description must be accurate. 3D animation, symmetrical face. No humans unless asked. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"🎨 Titan Engine Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_v40_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,woman,deformed"
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(session.get(img_url, timeout=60).content)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # Zoom In Expansion (LOCKED)
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
# 5. UI NAVIGATION (TRUE ISOLATION)
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_identity_request(p): res = OFFICIAL_BIO
        else:
            try:
                res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server is busy. Please refresh."
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production Engine")
    m_script = st.text_area("Enter Movie Script:", height=150, key="movie_input_v1")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio (Full Options)")
    p_i = st.text_area("Describe images (One per line for batch generation):", height=150, key="img_input_v1")
    
    # ALL RATIOS & OPTIONS RESTORED
    sz_opts = {
        "Square (1:1)": (1024, 1024), "YouTube HD (16:9)": (1280, 720), 
        "TikTok (9:16)": (720, 1280), "YouTube Banner": (2560, 1080), "Logo Size": (512, 512)
    }
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"], key="is_v1")
    with ic2: i_size = st.selectbox("Size/Resolution:", list(sz_opts.keys()), key="ir_v1")
    with ic3: count = st.slider("Quantity:", 1, 10, 1, key="ic_v1")
    
    char_id = st.text_input("Character ID (Seed) for Consistency:", placeholder="e.g. 786", key="seed_v1")

    if st.button("Generate Professional Visuals 🚀"):
        if p_i:
            w, h = sz_opts[i_size]
            seed_base = int(char_id) if char_id.isdigit() else random.randint(1,99999)
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
            for idx, single_p in enumerate(prompt_list):
                for q in range(count):
                    with st.spinner(f"AI painting image {idx*count + q + 1}..."):
                        final_seed = seed_base if char_id.isdigit() else seed_base + idx + q
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(single_p + ' ' + i_style)}?width={w}&height={h}&seed={final_seed}&nologo=true&negative=girl,female"
                        st.image(url, caption=f"Prompt: {single_p[:40]}... (Seed: {final_seed})")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>Sglowina AI Version 1.0 Premium Release | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
