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
# 1. ELECTRIC LUXURY UI & LIGHTNING LOGO
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Professional Midnight Slate (Clear Readability) */
    .stApp {
        background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }

    /* Electric Rotating Heart Logo with Lightning Effect */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 50px 0;
        margin-top: -50px;
    }

    .electric-heart {
        position: relative;
        width: 100px;
        height: 90px;
        background: #2563EB;
        transform: rotate(-45deg);
        animation: heartPulse 1.5s infinite ease-in-out, lightning 0.5s infinite;
        box-shadow: 0 0 40px #2563EB;
    }
    .electric-heart::before, .electric-heart::after {
        content: "";
        position: absolute;
        width: 100px;
        height: 100px;
        background: inherit;
        border-radius: 50%;
    }
    .electric-heart::before { top: -50px; left: 0; }
    .electric-heart::after { left: 50px; top: 0; }

    .logo-text {
        position: absolute;
        top: 30%;
        left: 30%;
        transform: translate(-50%, -50%) rotate(45deg);
        z-index: 10;
        font-family: 'Orbitron', sans-serif;
        font-size: 35px;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 0 20px #00d4ff, 0 0 40px #ffffff;
        animation: esRotate 3s infinite linear;
    }

    @keyframes heartPulse {
        0%, 100% { transform: scale(1) rotate(-45deg); }
        50% { transform: scale(1.1) rotate(-45deg); }
    }

    @keyframes esRotate {
        0% { transform: translate(-50%, -50%) rotate(45deg) rotateY(0deg); }
        100% { transform: translate(-50%, -50%) rotate(45deg) rotateY(360deg); }
    }

    @keyframes lightning {
        0%, 100% { box-shadow: 0 0 30px #2563EB, 0 0 60px #00d4ff; }
        50% { box-shadow: 0 0 50px #ffffff, 0 0 80px #2563EB; }
    }
    
    .owner-tag { font-family: 'Orbitron', sans-serif; font-size: 1.1rem; color: #00d4ff; letter-spacing: 5px; margin-bottom: 10px; text-shadow: 0 0 10px #00d4ff; }
    .main-title { font-size: 2.5rem; font-weight: 800; color: white; text-align: center; }

    /* Input Box Visibility Fix (Light background for typing) */
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border: 2px solid #00d4ff !important;
        border-radius: 15px !important;
        font-weight: 500 !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 20px; padding: 10px; }
    .stTabs [data-baseweb="tab"] { color: #94a3b8 !important; font-weight: bold; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #00d4ff !important; }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #00d4ff) !important;
        color: white !important; border: none !important; border-radius: 15px !important;
        height: 55px; width: 100%; font-size: 18px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Logo & Branding
st.markdown(f"""
    <div class="logo-container">
        <div class="owner-tag">MUHAMMAD ESSA AWAN</div>
        <div class="electric-heart">
            <div class="logo-text">ES</div>
        </div>
        <div class="main-title">ES AI MASTER STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CREATOR BIO & IDENTITY (STRICT)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_essa_query(q):
    patterns = [r"kisne banaya", r"who (made|created) you", r"owner", r"essa", r"awan", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. MOVIE ENGINE (V35 BUG FIX)
# ==========================================
async def generate_v_safe(text, v_code, path):
    try:
        communicate = edge_tts.Communicate(text, v_code)
        await communicate.save(path)
        return os.path.exists(path) and os.path.getsize(path) > 100
    except: return False

def create_pro_movie_v35(story, voice_choice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_choice else "ur-PK-AsadNeural"
        audio_path = f"{u_id}_v.mp3"
        
        status.info("🎙️ آواز تیار ہو رہی ہے...")
        if not asyncio.run(generate_v_safe(story, v_code, audio_path)):
            return "Error: Audio engine failed."
        
        voice_audio = AudioFileClip(audio_path)
        
        # Dimensions
        res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res[ratio]

        # Step 2: Scenes
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} بن رہا ہے...")
            # Word Recognition Prompt
            prompt = f"Professional 3D cinematic, {scene[:100]}, highly detailed, 4k, no text, realistic masterpiece"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            # Secure download
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            img_verify = Image.open(img_path).convert("RGB")
            img_verify.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h))
            # Smooth Zoom Out
            clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Step 3: Final Render
        status.info("⚙️ ویڈیو فائل تیار ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Important: Close clips to free up file
        voice_audio.close()
        final_video.close()
        
        if os.path.exists(out_name):
            return out_name
        else:
            return "Error: Video file was not created."

    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD (REFINED TABS)
# ==========================================
tab_chat, tab_movie = st.tabs(["💬 Smart Chat Assistant", "🎬 Pro Movie Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if is_essa_query(p): res = ESSA_BIO
        else:
            try:
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
            except: res = "Server is slow. Try refreshing."
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎬 Create Cinematic Masterpiece")
    m_script = st.text_area("Yahan apni kahani likhein:", height=200, placeholder="Example: Aik hathi aur choha darya ke kinare baithe thay...")
    
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Select Narrator:", ["Urdu Female (Uzma)", "Urdu Male (Asad)"])
    with col2: mr = st.selectbox("Video Size:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])

    if st.button("🚀 Launch Universal Video Rendering"):
        if m_script:
            with st.spinner("AI Director is processing files..."):
                video_result = create_pro_movie_v35(m_script, mv, mr, ms)
                if "mp4" in video_result and os.path.exists(video_result):
                    with open(video_result, 'rb') as vf:
                        video_bytes = v_data = vf.read()
                    st.video(v_data)
                    st.download_button("Download Full HD ⬇️", v_data, file_name=video_result)
                    st.success("✅ Movie Delivered!")
                else:
                    st.error(video_result)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #00d4ff;'>ES AI Studio v35.0 | High-End Electric Edition | Muhammad Essa Awan</p>", unsafe_allow_html=True)
