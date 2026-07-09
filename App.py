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
# 1. INDUSTRIAL GLOBAL ENGINE CLUSTER (100+ Models Reach)
# ==========================================
session = requests.Session()
# Fail-safe clusters
MODELS = ["openai", "mistral", "llama", "unity", "searchgpt", "hercai", "prodia"]

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

# ==========================================
# 2. SGLOWINA PREMIUM LAUNCH UI (ELECTRIC)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan Release", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.4);
        animation: lightningBorder 2s infinite;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 130px; height: 130px; background: #0f172a; border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 70px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 40px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 4.2rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.4rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 3px; text-transform: uppercase; }

    [data-testid="stSidebar"] { background-color: #0f172a !important; min-width: 280px !important; }
    [data-testid="stSidebar"] * { color: white !important; font-size: 1.1rem !important; font-weight: bold; }
    
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold; border: none;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #e2e8f0 !important; border-radius: 12px !important; color: #0f172a !important; font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI - OFFICIAL PREMIUM EDITION</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founder & CEO: Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
OFFICIAL_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founder & CEO:** Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglowina AI is a high-end industrial intelligence platform. This is the official Version 1.0 Premium Release.
"""

def is_identity_request(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"sglowina", r"maker"])

# ==========================================
# 4. TITAN MOVIE ENGINE (LOCKED & PRECISE)
# ==========================================
def get_titan_prompt(text):
    try:
        # GPT-4 Directed Prompting for 100% Subject Accuracy
        instr = f"Director Order: Extract and describe every object and relationship in Urdu: '{text}'. If it says 'woman on horse', emphasize BOTH woman and horse. No humans unless asked. Accurate 3D cinematic. Output English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie(story, voice, ratio, style):
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
            status.info(f"⚡ Titan Engine Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,woman,deformed"
            
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(session.get(img_url, timeout=60).content)
            Image.open(img_p).convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
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
# 5. SIDEBAR NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

# --- PAGE 1: CHAT ---
if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if is_identity_request(p): res = OFFICIAL_BIO
        else:
            res = "Connection error. Retrying across 100 engines..."
            for model in MODELS:
                try:
                    url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model={model}&cache=true"
                    res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
                    if res: break
                except: continue
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Titan Cinematic Production Engine")
    m_script = st.text_area("Enter Movie Script:", height=150, key="titan_movie")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"], key="titan_v")
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="titan_r")
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="titan_s")
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = create_titan_movie(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

# --- PAGE 3: IMAGE STUDIO (QUANTITY + CONSISTENCY) ---
elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio")
    img_p = st.text_area("Describe the Image or Logo you want:", placeholder="e.g. A woman sitting on a horse, mountain background...")
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: is_img = st.selectbox("Art Style:", ["Realistic", "Logo Design", "Anime", "Sketch"], key="titan_is")
    with ic2: ir_img = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"], key="titan_ir")
    with ic3: count = st.slider("Quantity (Images):", 1, 10, 1) # RESTORED QUANTITY SELECTOR
    
    char_id = st.text_input("Character ID (Seed) for Consistency:", placeholder="e.g. 555")

    if st.button("Generate Titan Images 🚀"):
        if img_p:
            dim_map = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim_map[ir_img]
            seed_base = int(char_id) if char_id.isdigit() else random.randint(1,999999)
            
            # THE DIRECTOR AI - Ensuring subjects are not missing
            refined_p = get_titan_prompt(img_p)
            
            for i in range(count):
                with st.spinner(f"Painting Image {i+1}..."):
                    # Every image gets a unique seed unless user locked it
                    final_seed = seed_base if char_id.isdigit() else seed_base + i
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p + ' ' + is_img)}?width={w}&height={h}&seed={final_seed}&nologo=true&negative=girl,female,deformed"
                    st.image(url, caption=f"Result {i+1} (Seed: {final_seed})")
                    st.download_button(f"Download Result {i+1} ⬇️", requests.get(url).content, file_name=f"sglowina_{final_seed}.jpg")

st.sidebar.markdown("---")
st.sidebar.info(f"Sglowina AI v1.0 | Official Titan Edition | Founder & CEO: Saba Wahid")
