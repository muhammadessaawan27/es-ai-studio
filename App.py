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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI & PREMIUM DESIGN (CSS)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    /* Importing Modern Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=Orbitron:wght@900&display=swap');

    /* Main Background with Luxury Gradient */
    .stApp {
        background: radial-gradient(circle at top right, #1e1b4b, #0f172a, #020617);
        color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }

    /* Modern Logo - AI Chip / Circuit Design (Requirement 1) */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 40px 0;
        animation: fadeInDown 1s ease-out;
    }
    .ai-logo {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        border-radius: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 42px;
        font-weight: 900;
        color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6), inset 0 0 15px rgba(255, 255, 255, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.1);
        position: relative;
    }
    .ai-logo::before {
        content: '';
        position: absolute;
        width: 120%;
        height: 120%;
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 30px;
        animation: rotate 10s linear infinite;
    }
    
    /* Header Text (Requirement 3) */
    .premium-header {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -1px;
        margin-top: 20px;
        background: linear-gradient(to right, #FFFFFF, #94A3B8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .premium-sub {
        font-size: 0.9rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin-bottom: 20px;
    }

    /* Glassmorphism Tabs & Inputs */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 30px;
        background: rgba(255, 255, 255, 0.03);
        padding: 10px;
        border-radius: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8 !important;
        font-weight: 500;
        transition: 0.3s;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #2563EB !important;
    }

    /* Luxury Buttons (Requirement 6) */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3) !important;
        transition: 0.4s all !important;
    }
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(37, 99, 235, 0.5) !important;
    }

    /* Inputs (Requirement 4) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
    }

    /* Animations */
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

# Logo & Header Section
st.markdown("""
    <div class="logo-container">
        <div class="ai-logo">ES</div>
        <div class="premium-header">ES AI Your Intelligent Assistant</div>
        <div class="premium-sub">Create • Chat • Voice • Video</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (PRESERVED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. MOVIE ENGINE (v27.0 LOGIC PRESERVED)
# ==========================================
def create_accurate_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            prompt = f"{style} style, {scene[:100]}, highly detailed, cinematic 4k, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_path, "wb") as f: f.write(r.content)
                img = Image.open(img_path).convert("RGB")
                img.save(img_path, "JPEG")
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                clip = clip.resize(lambda t: 1.1 - 0.06 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"])
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Describe your idea or ask anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.markdown("### 🎙️ Create Luxury Voiceovers")
    v_text = st.text_area("Enter your text below:", height=150)
    v_col1, v_col2 = st.columns(2)
    with v_col1: gen = st.selectbox("Select Voice:", ["Female", "Male"])
    with v_col2: st.selectbox("Language:", ["Urdu", "English"], index=0)
    if st.button("Generate Premium Audio 🚀"):
        if v_text:
            vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, vc).save("es_v.mp3")
            asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.markdown("### 🎬 Professional Cinematography Studio")
    m_script = st.text_area("Write your cinematic story:", height=200)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Male", "Female"], key="m_v")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="m_r")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="m_s")

    if st.button("🚀 Create High-End Movie"):
        if m_script:
            with st.spinner("Our AI Director is crafting your masterpiece..."):
                video = create_accurate_movie(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download 4K HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #475569;'>ES AI Premium Studio | Engineered by Muhammad Essa Awan</p>", unsafe_allow_html=True)
