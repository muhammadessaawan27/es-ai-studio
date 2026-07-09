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
# 1. INDUSTRIAL STABILITY & SPEED CLUSTER
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
# 2. CLEAN MINIMAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    /* Rotating S Icon */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 10px 0; }
    .rotating-s {
        width: 80px; height: 80px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        border: 3px solid #ff007a; box-shadow: 0 0 15px #ff007a;
        animation: rotateIcon 6s infinite linear;
    }
    @keyframes rotateIcon { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .brand-name { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; letter-spacing: 2px; }

    /* Clean Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #f1f5f9; padding: 10px; border-radius: 50px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { font-size: 16px !important; font-weight: bold !important; color: #64748b !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #2563eb !important; }

    /* Button and Input */
    .stButton>button { 
        background: #0f172a !important; color: white !important; border-radius: 12px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 10px !important; color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Minimal Top Section
st.markdown("""
    <div class="logo-container">
        <div class="rotating-s">S</div>
        <div class="brand-name">Sglowina AI</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_OFFICIAL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founder & CEO: Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan.
Muhammad Essa Awan is the COO and the lead logical architect of this platform.
This is the official Version 1.0.
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder"])

# ==========================================
# 4. v40 TITAN ENGINE (SCENE DENSITY FIX)
# ==========================================
def get_v40_prompt(text):
    # Subject Guard: If text is about a woman, force it in English
    gender_instr = "Ensure the character is a WOMAN. No men should be visible." if any(k in text for k in ["عورت", "لڑکی", "خاتون", "woman", "girl"]) else ""
    try:
        instr = f"Act as a Film Director: '{text}'. {gender_instr}. Professional 3D animation, symmetrical features, high detail. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

def create_masterpiece_v1(story, voice, ratio, style):
    u_id = f"v1_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        # Step 1: Voice
        v_map = {"Asad (Male)": "ur-PK-AsadNeural", "Salman (Male)": "ur-PK-SalmanNeural", 
                 "Uzma (Female)": "ur-PK-UzmaNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_map.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        # Step 2: High scene density (Split every 3-4 words for more images)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if len(sentences) < 5: # If few sentences, split by words to get more scenes
            words = story.split()
            n = max(1, len(words) // 6)
            sentences = [" ".join(words[i:i+n]) for i in range(0, len(words), n)]

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        char_seed = random.randint(1, 999999) # Lock seed for character consistency

        img_urls = []
        for s in sentences:
            refined = get_v40_prompt(s)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={char_seed}&nologo=true"
            img_urls.append(url)

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)}...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # v40 Locked Zoom-In
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI TABS (CLEAN & ISOLATED)
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Chat Assistant", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    st.write("### 💬 Sglowina Intelligence")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/0f172a/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar): st.write(m["content"])
    
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_id_call(p): res = SGLOWINA_OFFICIAL_BIO
        else:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true"
                res = requests.get(url, timeout=25).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server is busy. Please try again."
        with st.chat_message("assistant", avatar="https://via.placeholder.com/50/0f172a/ffffff?text=S"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Official Movie Production Engine")
    m_script = st.text_area("Enter Movie Script:", height=150, placeholder="Example: Aik hathi nadi par pani pee raha tha...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Select Voice:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_masterpiece_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with tab_image:
    st.write("### 🎨 Industrial Image Studio")
    p_i = st.text_area("Describe Image (One per line):")
    if st.button("Generate HD Image 🚀"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1024&height=1024&nologo=true&seed={random.randint(1,9999)}"
        st.image(url)

# SIMPLE FOOTER
st.markdown("<p style='text-align:center; color:#000000; font-weight:bold; border-top:1px solid #eee; padding-top:20px;'>Sglowina AI Version 1.0 Premium Release | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
