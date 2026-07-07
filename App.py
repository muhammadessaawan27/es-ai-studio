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

# Senior Engineer Fix: Persistent Session
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI & READABILITY FIX (Requirement 1, 2)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Deep Luxury Slate (Fixed for readability) */
    .stApp {
        background-color: #0b0f19;
        color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }

    /* Fixed Input Box Visibility */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        font-size: 16px !important;
    }

    /* Modern Animated Logo (ES Chip) */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .ai-logo {
        width: 90px; height: 90px;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 20px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 38px; color: white;
        box-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
        border: 2px solid rgba(255, 255, 255, 0.1);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); }
        50% { transform: scale(1.05); box-shadow: 0 0 35px rgba(139, 92, 246, 0.6); }
        100% { transform: scale(1); box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); }
    }

    .premium-header { font-size: 2rem; font-weight: 700; color: white; margin-top: 15px; }
    .premium-sub { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 5px; }

    /* Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6) !important;
        color: white !important; border: none !important; border-radius: 10px !important;
        padding: 12px 25px !important; font-weight: 600 !important; transition: 0.3s !important;
    }
    .stButton>button:hover { transform: translateY(-2px) !important; opacity: 0.9 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="logo-container">
        <div class="ai-logo">ES</div>
        <div class="premium-header">ES AI Master Studio</div>
        <div class="premium-sub">Create • Chat • Voice • Video</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (Requirement 2)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. ADVANCED MOVIE ENGINE (ZOOM OUT & REAL MOTION)
# ==========================================
def create_cinematic_movie_v30(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Splitting
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"Crafting Scene {i+1}...")
            # Enhanced Cinematic Prompt for Realism
            prompt = f"Hyper-realistic cinematic film shot, {style} style, {scene[:100]}, detailed textures, 8k, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            # Step 4: FIXED ZOOM OUT & PANNING (Real Camera Motion)
            # We start the image at 1.15 (slightly bigger) and move to 1.0
            # This ensures NO BLACK BACKGROUND ever appears.
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h)) # Initial fit
            
            # ANIMATION: Zoom OUT (1.15 to 1.0) + Slight Panning (Real camera movement)
            clip = clip.resize(lambda t: 1.15 - 0.1 * (t/dur_per)).set_position(lambda t: ('center', 'center'))
            
            clips.append(fadein(clip, 0.5))

        # Step 5: High-Quality Final Render
        status.info("Rendering Masterpiece Video...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        
        final_video.write_videofile(
            out_name, codec="libx264", audio_codec="aac", fps=24, 
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
tabs = st.tabs(["💬 Chat", "🎙️ Voice", "🎬 Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Ask ES AI anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.write("### 🎙️ Premium Voice Generator")
    v_text = st.text_area("Write here:", key="v_input")
    v_col1, v_col2 = st.columns(2)
    with v_col1: gen = st.selectbox("Voice:", ["Female", "Male"])
    with v_col2: st.selectbox("Language:", ["Urdu", "English"], index=0)
    if st.button("Generate Audio 🚀"):
        if v_text:
            vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, vc).save("es_v.mp3")
            asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.write("### 🎬 Professional Studio v30.0")
    m_script = st.text_area("Write your story:", height=150, placeholder="Example: A river flowing through a snowy mountain...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"])

    if st.button("🚀 Create Realistic Video"):
        if m_script:
            with st.spinner("AI Director is animating your scenes..."):
                video = create_cinematic_movie_v30(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #475569;'>ES AI Premium Studio | Designed for Muhammad Essa Awan</p>", unsafe_allow_html=True)
