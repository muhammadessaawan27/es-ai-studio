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
    st.error(f"Critical Engine Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI & ANIMATED HEART LOGO
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Soft Luxury Gradient (Not pure white) */
    .stApp {
        background: linear-gradient(135deg, #f8f9ff 0%, #e0e7ff 100%);
        color: #1e1b4b;
        font-family: 'Inter', sans-serif;
    }

    /* 3D Rotating Heart with Independent ES Inside (Requirement) */
    .logo-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 40px 0;
        background: rgba(255, 255, 255, 0.4);
        border-radius: 0 0 50px 50px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-top: -60px;
    }

    .heart {
        position: relative;
        width: 100px;
        height: 90px;
        background: linear-gradient(45deg, #2563EB, #7C3AED);
        transform: rotate(-45deg);
        animation: heartRotate 6s infinite linear;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.5);
    }
    .heart::before, .heart::after {
        content: "";
        position: absolute;
        width: 100px;
        height: 100px;
        background: inherit;
        border-radius: 50%;
    }
    .heart::before { top: -50px; left: 0; }
    .heart::after { left: 50px; top: 0; }

    .logo-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(45deg);
        z-index: 10;
        font-family: 'Orbitron', sans-serif;
        font-size: 30px;
        font-weight: 900;
        color: white;
        text-shadow: 0 0 10px rgba(255,255,255,0.8);
        animation: esRotate 4s infinite linear;
    }

    @keyframes heartRotate {
        0% { transform: scale(1) rotate(-45deg); }
        50% { transform: scale(1.1) rotate(-45deg); }
        100% { transform: scale(1) rotate(-45deg); }
    }

    @keyframes esRotate {
        0% { transform: translate(-50%, -50%) rotate(45deg) rotateY(0deg); }
        100% { transform: translate(-50%, -50%) rotate(45deg) rotateY(360deg); }
    }
    
    .premium-header { font-size: 2.5rem; font-weight: 800; color: #1e1b4b; margin-top: 20px; text-align: center; }
    .premium-sub { font-size: 1rem; color: #4338ca; text-transform: uppercase; letter-spacing: 6px; font-weight: 700; text-align: center; }

    /* Custom Colored Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #312e81; padding: 10px; border-radius: 15px; }
    .stTabs [data-baseweb="tab"] { color: white !important; }
    
    /* Input Styling */
    .stTextArea>div>div>textarea { background: white !important; border: 2px solid #e0e7ff !important; border-radius: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# Logo Display
st.markdown("""
    <div class="logo-section">
        <div class="heart">
            <div class="logo-text">ES</div>
        </div>
        <div class="premium-header">ES AI Master Studio</div>
        <div class="premium-sub">The Future is Here</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (THE TRUTH)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_identity(query):
    patterns = [r"kisne banaya", r"who (made|created) you", r"owner", r"essa", r"awan", r"maker"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. BULLETPROOF ENGINES (NO AUDIO ERROR FIX)
# ==========================================
async def generate_safe_audio(text, voice_code, output_path):
    """Retries audio generation if server fails (Fixes: No audio was received)"""
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice_code)
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
        except:
            await asyncio.sleep(2)
    return False

def create_stable_movie_v33(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Secure Voice
        status.info("🎙️ آواز تیار کی جا رہی ہے...")
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        
        if not asyncio.run(generate_safe_audio(story, v_code, audio_file)):
            raise ValueError("Audio Engine didn't respond. Please try a shorter script.")
        
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Set Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        # Step 4: Visual Generation
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی تصویر بن رہی ہے...")
            director_instr = f"Professional prompt for AI Image: '{scene}'. {style} style, cinematic, 8k, no text."
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(director_instr)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_path, "wb") as f: f.write(r.content)
                # Cleanup Image Data
                img = Image.open(img_path).convert("RGB")
                img.save(img_path, "JPEG")
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # Zoom Out Animation
                clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        # Step 5: High-Stability Render
        status.info("⚙️ فائنل رینڈرنگ ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Movie_{u_id}.mp4"
        
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        time.sleep(1) # Allow file release
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if check_identity(p): res = ESSA_BIO
        else:
            try:
                sys = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer intelligently.")
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&system={sys}", timeout=30).text
            except: res = "Server is slow. Please refresh."
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.write("### 🎙️ Voice Studio (M/F)")
    v_text = st.text_area("Likhein:", key="v_input")
    v_c1, v_c2 = st.columns(2)
    with v_c1: gen = st.selectbox("Gender:", ["Female", "Male"])
    with v_c2: st.selectbox("Language:", ["Urdu", "English"], index=0)
    if st.button("Generate Audio 🚀"):
        if v_text:
            vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            if asyncio.run(generate_safe_audio(v_text, vc, "es_v.mp3")):
                st.audio("es_v.mp3")
            else: st.error("Audio generation failed.")

with tabs[2]:
    st.write("### 🎬 Pro Studio v33.0")
    m_script = st.text_area("Movie Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"])

    if st.button("🚀 Generate Precision Video"):
        if m_script:
            with st.spinner("AI Director is crafting your masterpiece..."):
                video = create_stable_movie_v33(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    st.download_button("Download Full HD ⬇️", open(video, 'rb'), file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #4338ca;'>© 2024 ES AI Master Studio | Production Engine v33.0 | Muhammad Essa Awan</p>", unsafe_allow_html=True)
