import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re

# MoviePy Import Fix
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. CORE CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 80px; font-weight: 900;
        margin-bottom: 0px;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Creator Bio
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_identity(query):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"creator", r"essa awan", r"muhammad essa"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns) if query else False

# Chat Engine
def get_ai_response(query):
    if check_identity(query): return ESSA_BIO
    encoded = urllib.parse.quote(query)
    url = f"https://text.pollinations.ai/{encoded}?model=openai&cache=true"
    try:
        r = requests.get(url, timeout=30)
        return r.text if r.status_code == 200 else "سرور اس وقت جواب نہیں دے رہا۔"
    except: return "کنکشن کا مسئلہ ہے۔"

# UI
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("🎙️ Voice Typing:")
    mic_recorder(start_prompt="Record", stop_prompt="Stop", key='recorder')
    
    prompt = st.chat_input("پوچھیں...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            res = get_ai_response(prompt)
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voice Studio")
    v_text = st.text_area("متن لکھیں:")
    if st.button("Generate Voice 🚀"):
        if v_text:
            async def sv(): await edge_tts.Communicate(v_text, "ur-PK-UzmaNeural").save("temp_v.mp3")
            asyncio.run(sv())
            st.audio("temp_v.mp3")

with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    m_script = st.text_area("کہانی لکھیں:", height=150)
    m_ratio = st.selectbox("سائز:", ["YouTube (16:9)", "TikTok (9:16)", "Instagram (1:1)"])
    
    if st.button("Generate Video Now 🚀"):
        if m_script:
            with st.spinner("ویڈیو بن رہی ہے..."):
                try:
                    # Voice
                    async def gv(): await edge_tts.Communicate(m_script, "ur-PK-UzmaNeural").save("m_audio.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip("m_audio.mp3")
                    # Image
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_script[:50])}?width=1280&height=720&nologo=true"
                    with open("img.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    # Video
                    clip = ImageClip("img.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip.write_videofile("es_movie.mp4", codec="libx264", audio_codec="aac")
                    st.video("es_movie.mp4")
                except Exception as e: st.error(f"Error: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio | Muhammad Essa Awan</p>", unsafe_allow_html=True)
