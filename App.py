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

# Senior Engineer Fix: Persistent Session for stability
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. ORANGE & RED LUXURY UI (Master Design)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Deep Red to Dark Slate */
    .stApp {
        background: linear-gradient(135deg, #1a0505 0%, #000000 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    /* Fixed Heart Logo (Perfect Size) */
    .logo-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px 0;
        margin-top: 10px;
    }

    .heart-container {
        position: relative;
        width: 80px;
        height: 80px;
        margin-bottom: 20px;
    }

    .heart {
        position: absolute;
        width: 80px;
        height: 70px;
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        transform: rotate(-45deg);
        animation: heartPulse 2s infinite ease-in-out;
        box-shadow: 0 0 25px rgba(255, 75, 43, 0.6);
        z-index: 1;
    }
    .heart::before, .heart::after {
        content: "";
        position: absolute;
        width: 80px;
        height: 80px;
        background: inherit;
        border-radius: 50%;
    }
    .heart::before { top: -40px; left: 0; }
    .heart::after { left: 40px; top: 0; }

    .logo-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(45deg);
        z-index: 10;
        font-family: 'Orbitron', sans-serif;
        font-size: 26px;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 0 10px rgba(0,0,0,0.5);
        animation: esSpin 4s infinite linear;
    }

    @keyframes heartPulse {
        0%, 100% { transform: scale(1) rotate(-45deg); }
        50% { transform: scale(1.05) rotate(-45deg); }
    }

    @keyframes esSpin {
        0% { transform: translate(-50%, -50%) rotate(45deg) rotateY(0deg); }
        100% { transform: translate(-50%, -50%) rotate(45deg) rotateY(360deg); }
    }
    
    .owner-name { font-family: 'Orbitron', sans-serif; font-size: 1.2rem; color: #FF4B2B; letter-spacing: 3px; font-weight: bold; margin-bottom: 5px; }
    .premium-header { font-size: 2.2rem; font-weight: 800; color: #ffffff; text-shadow: 0 0 15px rgba(255, 75, 43, 0.4); }

    /* Orange/Red Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #FF4B2B, #FF416C) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        padding: 12px 30px !important; font-weight: 600 !important; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.03); box-shadow: 0 0 20px rgba(255, 75, 43, 0.6); }

    /* Colored Tab Section */
    .stTabs [data-baseweb="tab-list"] { background: #1a0505; border-bottom: 2px solid #FF4B2B; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: #FF4B2B !important; }
    
    /* Input Visibility Fix */
    .stTextArea>div>div>textarea { background: #2d0a0a !important; color: white !important; border: 1px solid #FF4B2B !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# Logo & Branding Header
st.markdown(f"""
    <div class="logo-section">
        <div class="owner-name">MUHAMMAD ESSA AWAN</div>
        <div class="heart-container">
            <div class="heart">
                <div class="logo-text">ES</div>
            </div>
        </div>
        <div class="premium-header">ES AI MASTER STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FAIL-SAFE ENGINE LOGIC
# ==========================================
async def generate_v_safe(text, voice_code, path):
    try:
        communicate = edge_tts.Communicate(text, voice_code)
        await communicate.save(path)
        return os.path.exists(path) and os.path.getsize(path) > 100
    except: return False

def create_pro_video_v34(story, voice_choice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Multiple Voices (Mapping)
        voices = {
            "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
            "Urdu Male (Asad)": "ur-PK-AsadNeural",
            "English Male (Guy)": "en-US-GuyNeural",
            "English Female (Aria)": "en-US-AriaNeural",
            "Hindi Male (Madhur)": "hi-IN-MadhurNeural",
            "Hindi Female (Swara)": "hi-IN-SwaraNeural"
        }
        v_code = voices.get(voice_choice, "ur-PK-UzmaNeural")
        
        status.info("🎙️ آواز اور مناظر کی تیاری شروع...")
        audio_path = f"{u_id}_v.mp3"
        if not asyncio.run(generate_v_safe(story, v_code, audio_path)):
            raise ValueError("Audio Generation Failed.")
        
        voice_audio = AudioFileClip(audio_path)
        
        # Dimensions Setup
        res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res[ratio]

        # Multi-Scene Generation
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی تصویر بن رہی ہے...")
            prompt = f"{style} style, {scene[:100]}, high quality cinematic 4k, no text, realistic"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            # Sanitize Image Data
            img = Image.open(img_path).convert("RGB")
            img.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h))
            clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Final Render with Storage Error Fix
        status.info("⚙️ ویڈیو رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_{u_id}.mp4"
        
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Release Files from RAM
        voice_audio.close()
        final_video.close()
        
        time.sleep(2) # Release Wait
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. TABS INTERFACE
# ==========================================
tabs = st.tabs(["💬 Chat", "🎙️ Standalone Voice", "🎬 Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.write("### 🎙️ Standalone Voiceovers")
    v_t = st.text_area("Yahan likhein jo bulwana hai:", key="standalone_v")
    v_c1, v_c2 = st.columns(2)
    with v_c1: v_gen = st.selectbox("Narrator:", ["Urdu Female (Uzma)", "Urdu Male (Asad)", "English Male (Guy)", "English Female (Aria)"])
    if st.button("Generate Audio 🚀"):
        vc = "ur-PK-UzmaNeural" if "Uzma" in v_gen else "ur-PK-AsadNeural" if "Asad" in v_gen else "en-US-GuyNeural" if "Guy" in v_gen else "en-US-AriaNeural"
        if asyncio.run(generate_v_safe(v_t, vc, "test.mp3")): st.audio("test.mp3")

with tabs[2]:
    st.write("### 🎬 Pro Movie Studio (Orange Theme)")
    m_s = st.text_area("Write your script below:", height=200)
    c1, c2, c3 = st.columns(3)
    with c1: m_v = st.selectbox("Select Voice:", ["Urdu Female (Uzma)", "Urdu Male (Asad)", "Hindi Male (Madhur)", "English Male (Guy)"])
    with c2: m_r = st.selectbox("Video Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: m_st = st.selectbox("Scene Style:", ["Realistic", "Cinematic", "3D Cartoon"])

    if st.button("🚀 Generate Final Master Video"):
        if m_s:
            with st.spinner("Processing... Please wait."):
                video = create_pro_video_v34(m_s, m_v, m_r, m_st)
                if "mp4" in video:
                    # THE STORAGE ERROR FIX: Reading as bytes
                    with open(video, 'rb') as v_file:
                        video_bytes = v_file.read()
                    st.video(video_bytes)
                    st.download_button("Download High Quality ⬇️", video_bytes, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #FF4B2B;'>ES AI Master Studio v34.0 | Official Launch Edition</p>", unsafe_allow_html=True)
