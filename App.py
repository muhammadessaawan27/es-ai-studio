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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import base64
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import concurrent.futures

# ==========================================
# MOVIEPY IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# STREAMLIT PAGE CONFIG & GLOBALS
# ==========================================
st.set_page_config(page_title="Sglowina AI - Cute Mascot Companion", layout="wide", page_icon="🧸")

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "avatar_reply" not in st.session_state:
    st.session_state.avatar_reply = "السلام علیکم! میں آپ کا پیارا AI دوست ہوں۔ کیمرے سے مجھے کچھ دکھائیں یا مائیک پر بات کریں!"

render_semaphore = threading.Semaphore(value=2)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ==========================================
# DATABASE LAYER
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'Free',
            credits INTEGER DEFAULT 50,
            role TEXT DEFAULT 'User',
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db_v21()

# TTS Audio Generator
def save_audio_safe(text, voice, rate, pitch, filename):
    try:
        async def amain():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(filename)
        asyncio.run(amain())
        return True
    except Exception:
        return False

# Multimodal AI Vision
def analyze_image_with_ai(image_bytes, question=""):
    try:
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        prompt_instruction = (
            "You are a friendly, super cute AI companion like a talking teddy mascot. "
            "Look at this image and explain what you see in very friendly, cute, fluent Urdu (اردو). "
            "Describe the objects, vehicles, people, colors, or surroundings in 2 simple, sweet sentences."
        )
        if question.strip():
            prompt_instruction += f" Also answer this user's question: '{question}'"

        url = "https://text.pollinations.ai/openai"
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_instruction},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }
            ],
            "model": "openai"
        }
        res = session.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return "میں نے منظر دیکھ لیا ہے! یہ بہت زبردست اور دلچسپ ہے!"

# ==========================================
# 🧸 CUTE 3D ANIMATED MASCOT COMPONENT
# ==========================================
def render_cute_3d_mascot(is_speaking=False):
    speaking_anim = "speaking" if is_speaking else ""
    mascot_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            .mascot-card {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: linear-gradient(180deg, #fdfbf7 0%, #fae8d4 100%);
                border-radius: 25px;
                padding: 15px;
                box-shadow: 0 10px 30px rgba(245, 158, 11, 0.25);
                border: 3px solid #fbbf24;
                margin-bottom: 10px;
            }}
            
            /* Fluffy 3D Character Body */
            .fluffy-body {{
                width: 140px;
                height: 160px;
                background: radial-gradient(circle at 35% 30%, #fef3c7, #fde68a 60%, #f59e0b 100%);
                border-radius: 70px 70px 60px 60px;
                position: relative;
                box-shadow: 0 15px 25px rgba(217, 119, 6, 0.35), inset 0 -8px 15px rgba(180, 83, 9, 0.2);
                animation: gentleFloat 3s infinite ease-in-out alternate;
            }}
            
            /* Fluffy Ears */
            .ear {{
                width: 32px;
                height: 40px;
                background: #f59e0b;
                border-radius: 50%;
                position: absolute;
                top: -8px;
            }}
            .ear-left {{ left: 10px; transform: rotate(-20deg); }}
            .ear-right {{ right: 10px; transform: rotate(20deg); }}
            
            /* Sleeping Mask on Head */
            .sleep-mask {{
                width: 95px;
                height: 28px;
                background: #fed7aa;
                border-radius: 15px;
                position: absolute;
                top: 15px;
                left: 22px;
                border: 2px solid #f97316;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .mask-strap {{
                width: 130px;
                height: 6px;
                background: #f97316;
                position: absolute;
                top: 26px;
                left: 5px;
                z-index: -1;
            }}

            /* Face Elements */
            .face {{
                width: 110px;
                height: 90px;
                background: #fffbeb;
                border-radius: 50%;
                position: absolute;
                top: 45px;
                left: 15px;
            }}
            .eyes-row {{
                display: flex;
                justify-content: space-around;
                width: 65px;
                position: absolute;
                top: 28px;
                left: 22px;
            }}
            .eye {{
                width: 12px;
                height: 8px;
                background: #451a03;
                border-radius: 0 0 12px 12px;
                animation: cuteBlink 4s infinite;
            }}
            .blush {{
                width: 16px;
                height: 8px;
                background: #fca5a5;
                border-radius: 50%;
                position: absolute;
                top: 36px;
            }}
            .blush-l {{ left: 10px; }}
            .blush-r {{ right: 10px; }}
            
            .mouth {{
                width: 16px;
                height: 8px;
                background: #e11d48;
                border-radius: 0 0 10px 10px;
                position: absolute;
                bottom: 22px;
                left: 47px;
                transition: all 0.2s ease;
            }}
            
            /* Talking Animation */
            .speaking .mouth {{
                animation: talkAnim 0.25s infinite alternate;
            }}
            .speaking .fluffy-body {{
                animation: bounceTalk 0.3s infinite alternate;
            }}

            @keyframes gentleFloat {{
                0% {{ transform: translateY(0px); }}
                100% {{ transform: translateY(-8px); }}
            }}
            @keyframes cuteBlink {{
                0%, 90%, 100% {{ transform: scaleY(1); }}
                95% {{ transform: scaleY(0.1); }}
            }}
            @keyframes talkAnim {{
                0% {{ height: 6px; border-radius: 0 0 6px 6px; }}
                100% {{ height: 20px; border-radius: 12px; transform: scaleX(1.3); }}
            }}
            @keyframes bounceTalk {{
                0% {{ transform: scale(1); }}
                100% {{ transform: scale(1.04); }}
            }}
        </style>
    </head>
    <body style="margin:0; background:transparent;">
        <div class="mascot-card {speaking_anim}">
            <div class="fluffy-body">
                <div class="ear ear-left"></div>
                <div class="ear ear-right"></div>
                <div class="mask-strap"></div>
                <div class="sleep-mask"></div>
                <div class="face">
                    <div class="blush blush-l"></div>
                    <div class="blush blush-r"></div>
                    <div class="eyes-row">
                        <div class="eye"></div>
                        <div class="eye"></div>
                    </div>
                    <div class="mouth"></div>
                </div>
            </div>
            <div style="font-weight:900; color:#b45309; margin-top:8px; font-size:16px;">🧸 SGLOWINA CUTE COMPANION</div>
        </div>
    </body>
    </html>
    """
    st.components.v1.html(mascot_html, height=240)

# ==========================================
# MOVIE GENERATOR (Standard Full HD)
# ==========================================
def translate_ur_to_en(text):
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote('Translate to 8k video prompt: ' + text)}?model=openai"
        res = session.get(url, timeout=12)
        if res.status_code == 200: return res.text.strip()
    except Exception: pass
    return text

def create_cinematic_v40(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    progress_bar = st.progress(0.0)
    temporary_audio_tracks = []
    generated_images = []
    
    try:
        status.info("🎙️ Processing Voiceovers...")
        progress_bar.progress(0.2)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        for idx, scene in enumerate(sentences):
            v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
            sub_audio_path = f"a_{u_id}_{idx}.mp3"
            save_audio_safe(scene, v_code_scene, "+0%", "+0Hz", sub_audio_path)
            temporary_audio_tracks.append(sub_audio_path)
            
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        
        clips = []
        for i, scene in enumerate(sentences):
            en_p = translate_ur_to_en(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(en_p)}?width={w}&height={h}&nologo=true&model=flux"
            res_img = session.get(img_url, timeout=30)
            img_path = f"i_{u_id}_{i}.jpg"
            if res_img.status_code == 200:
                with open(img_path, "wb") as f: f.write(res_img.content)
            else:
                Image.new("RGB", (w, h), color=(20, 25, 40)).save(img_path, "JPEG")
            generated_images.append(img_path)
            
            sub_audio_path = temporary_audio_tracks[i]
            dur_scene = AudioFileClip(sub_audio_path).duration if os.path.exists(sub_audio_path) else 4.0
            clip = ImageClip(img_path).set_duration(dur_scene).resize((w, h))
            if os.path.exists(sub_audio_path):
                clip = clip.set_audio(AudioFileClip(sub_audio_path))
            clips.append(clip)
            
        progress_bar.progress(0.85)
        final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
        out_name = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, logger=None)
        final_video.close()
        
        for sub_voice in temporary_audio_tracks:
            if os.path.exists(sub_voice): os.remove(sub_voice)
        for file_p in generated_images:
            if os.path.exists(file_p): os.remove(file_p)
            
        progress_bar.progress(1.0)
        status.success("🚀 Video Generated Successfully!")
        return out_name
    except Exception as e:
        progress_bar.empty()
        return f"Error: {e}"

# ==========================================
# UI STYLING & MOBILE RESPONSIVENESS
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    
    .main-title {
        font-size: 1.8rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(45deg, #f59e0b, #ec4899, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .stButton>button {
        background: #f59e0b !important;
        color: #000000 !important;
        border-radius: 14px !important;
        height: 52px;
        width: 100%;
        font-size: 18px;
        font-weight: 900;
        border: none;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🧸 SGLOWINA AI COMPANION</div>', unsafe_allow_html=True)

tab_companion, tab_movie, tab_image, tab_chat = st.tabs([
    "🧸 Live Mascot Companion",
    "🎬 Pro Movie Studio", 
    "🎨 Pro Image Studio",
    "💬 Electric AI Chat"
])

# -----------------
# TAB 1: CUTE COMPANION & VISION
# -----------------
with tab_companion:
    # 1. Show Cute 3D Character
    render_cute_3d_mascot(is_speaking=False)
    
    # 2. Friendly Speech Display Box
    st.info(f"🗣️ **AI دوست:** {st.session_state.avatar_reply}")
    
    # 3. Mobile Camera Input
    st.write("#### 📸 کیمرے سے مجھے کچھ دکھائیں:")
    cam_shot = st.camera_input("کیمرے کا منظر (Take Snapshot):")
    
    user_ask = st.text_input("ساتھ کچھ پوچھنا چاہیں؟ (Optional):", placeholder="مثال: دیکھو اور بتاؤ یہ کیا چیز ہے؟")
    
    if cam_shot is not None:
        if st.button("👀 دیکھو اور بول کر بتاؤ (Look & Speak Aloud) 🚀"):
            with st.spinner("🧸 دوست دیکھ رہا ہے اور جواب بول رہا ہے..."):
                img_data = cam_shot.getvalue()
                reply_text = analyze_image_with_ai(img_data, user_ask)
                st.session_state.avatar_reply = reply_text
                
                # Play Voice Aloud Automatically
                temp_voice_f = f"mascot_{uuid.uuid4().hex[:6]}.mp3"
                if save_audio_safe(reply_text, "ur-PK-UzmaNeural", "+0%", "+0Hz", temp_voice_f):
                    st.audio(temp_voice_f, format="audio/mp3", autoplay=True)
                st.rerun()

# -----------------
# TAB 2: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎬 Cinematic Video Production")
    m_script = st.text_area("کہانی درج کریں (Story Script):", height=100, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے اور کھیت میں کام کر رہا ہے...")
    c1, c2 = st.columns(2)
    with c1: voice_pick = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: format_pick = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    
    if st.button("Generate Master Movie 🚀"):
        if m_script.strip():
            with st.spinner("🎬 Generating cinematic video..."):
                v_res = create_cinematic_v40(m_script, voice_pick, format_pick)
                if v_res and v_res.endswith(".mp4") and os.path.exists(v_res):
                    st.video(v_res)
                    with open(v_res, "rb") as vf:
                        st.download_button("Download Full HD 📥", vf.read(), file_name=v_res)
                else:
                    st.error(v_res)

# -----------------
# TAB 3: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 HD Visual Studio")
    prompt_txt = st.text_area("Describe Image:", height=80)
    if st.button("Generate Image 🚀"):
        if prompt_txt.strip():
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_txt)}?width=1024&height=1024&nologo=true&model=flux"
            res_img = session.get(img_url, timeout=30)
            if res_img.status_code == 200:
                with Image.open(io.BytesIO(res_img.content)) as im:
                    st.image(im, caption=prompt_txt[:30])

# -----------------
# TAB 4: CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Chat")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true", timeout=15).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

st.markdown("<p style='text-align: center; font-weight: bold; margin-top: 25px; color: #b45309;'>Sglowina AI Companion | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
