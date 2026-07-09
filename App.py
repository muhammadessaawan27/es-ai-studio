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
# 1. INDUSTRIAL STABILITY & SPEED
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
# 2. EXECUTIVE MINIMAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    /* Minimal Header (Black Text) */
    .executive-header {
        text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;
    }
    .name-primary { font-size: 1.6rem; font-weight: 800; color: #000000; margin-bottom: 2px; }
    .name-secondary { font-size: 1.3rem; font-weight: 700; color: #475569; margin-bottom: 5px; }
    .role-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 3px; text-transform: uppercase; }

    /* Small Circular Rotating Logo */
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    .circular-s {
        width: 80px; height: 80px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 35px; color: #ffffff;
        border: 2px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spin 8s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    /* Sidebar Fix */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }

    .stButton>button { 
        background: #000000 !important; color: #ffffff !important; border-radius: 8px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Executive Top Header
st.markdown("""
    <div class="executive-header">
        <div class="name-primary">Muhammad Essa Awan — Founder & CEO</div>
        <div class="name-secondary">Saba Wahid — Co-Founder</div>
        <div class="role-tag">Sglowina AI Official Studio</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founder & CEO:** Muhammad Essa Awan.
**Co-Founder:** Saba Wahid.

Saba Wahid is the spouse of Muhammad Essa Awan (Mrs. Saba) and the daughter of Wahid Bakhsh. 
Muhammad Essa Awan is a professional Mechanical Engineer, Fabricator, and the lead logical architect of this platform.

This is the official Version 1.0 Premium Release.
"""

def is_id_call(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"coo"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. v40 TITAN MOVIE ENGINE (LOCKED LOGIC)
# ==========================================
def get_v40_prompt(text, style):
    try:
        # Strict subject recognition to avoid gender mixing
        gender_lock = "Ensure the character is a WOMAN" if any(k in text for k in ["عورت", "لڑکی", "woman", "girl"]) else "Ensure character is a MAN" if any(k in text for k in ["آدمی", "لڑکا", "man", "boy"]) else ""
        instr = f"Act as a Film Director: '{text}'. {gender_lock}. 3D animation, symmetrical features, high detail. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style, seed):
    u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        # Fixed 2 Voices only
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]

        # v40 Splitting logic - Force Image Change per line
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)

        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(get_v40_prompt(s, style))}?width={w}&height={h}&seed={seed}&nologo=true&negative=deformed,missing+limbs,wrong+gender" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"⚡ Rendering Scene {i+1}/{len(sentences)} (v40 Power)...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # v40 LOCKED ZOOM-IN: 1.0 to 1.15
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION (TRUE ISOLATION)
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
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
    st.write("### 🎥 Industrial Cinematic Engine (v40 Locked)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    with c4: sd = st.number_input("Character ID (Seed):", value=786)
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, sd)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Image Studio")
    p_i = st.text_area("Describe Image (One per line for batch):", height=150)
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    char_id = st.text_input("Consistency Lock ID:", value="786")

    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(single_p + ' ' + i_style)}?width={w}&height={h}&seed={char_id}&nologo=true&negative=girl,female"
                st.image(url, caption=f"Result (Seed: {char_id})")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.0 | Founder & CEO: Muhammad Essa Awan | Co-Founder: Saba Wahid</p>", unsafe_allow_html=True)
