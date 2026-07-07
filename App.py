import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
from PIL import Image

# Senior Engineer Fix: Patch for Image attribute error
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. DESIGN & BRANDING
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
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Creator Bio - YOUR IDENTITY
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# Hard Identity Check Logic
def check_identity(query):
    query = query.lower()
    # Comprehensive list of keywords for identity
    patterns = [
        r"kisne banaya", r"who (made|created|designed|developed) you", 
        r"your (creator|owner|founder|maker|boss|master|father|abba|baap)",
        r"apka (malik|creator|owner|banane wala|baap) kaun hai",
        r"essa awan", r"muhammad essa", r"creator kon hai", r"tume kisne banaya"
    ]
    return any(re.search(p, query) for p in patterns)

# ==========================================
# 2. UPDATED CHAT ENGINE
# ==========================================
def get_ai_response(query):
    # FIRST PRIORITY: Check for Creator Identity
    if check_identity(query): 
        return ESSA_BIO
    
    # SECOND PRIORITY: AI Engine Request
    encoded = urllib.parse.quote(query)
    # Injecting strict identity instruction into the AI's system prompt
    system_instr = urllib.parse.quote("You are ES AI, created exclusively by Muhammad Essa Awan. If anyone asks who made you, always credit Muhammad Essa Awan.")
    url = f"https://text.pollinations.ai/{encoded}?model=openai&cache=true&system={system_instr}"
    
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            # Double checking if AI tries to lie in the response
            response_text = r.text
            if any(x in response_text.lower() for x in ["openai", "google", "language model"]):
                if any(k in query.lower() for k in ["made you", "who are you", "created"]):
                    return ESSA_BIO
            return response_text
        return "سرور مصروف ہے، دوبارہ کوشش کریں۔"
    except: 
        return "کنکشن کا مسئلہ ہے، انٹرنیٹ چیک کریں۔"

# ==========================================
# 3. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- CHAT TAB ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    st.write("🎙️ **Voice Typing:**")
    mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop", key='recorder')
    
    prompt = st.chat_input("پوچھیں...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            res = get_ai_response(prompt)
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- VOICE TAB ---
with tabs[1]:
    st.header("Voice Studio (M/F)")
    v_text = st.text_area("متن لکھیں:")
    c1, c2 = st.columns(2)
    with c1: v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: v_gen = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Audio 🚀", key="voice_gen_btn"):
        if v_text:
            v_map = {"Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                     "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                     "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}}
            v_code = v_map[v_lang][v_gen]
            async def sv(): await edge_tts.Communicate(v_text, v_code).save("v.mp3")
            asyncio.run(sv())
            st.audio("v.mp3")

# --- MOVIE TAB ---
with tabs[2]:
    st.header("Pro Movie Studio")
    m_script = st.text_area("کہانی لکھیں:", height=150)
    col_v, col_r = st.columns(2)
    with col_v: m_voice = st.selectbox("Voice Selection:", ["Female", "Male"], key="mv")
    with col_r: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr")

    if st.button("Generate HD Video 🚀", key="movie_gen_btn"):
        if m_script:
            with st.spinner("ویڈیو رینڈر ہو رہی ہے..."):
                try:
                    v_code = "ur-PK-UzmaNeural" if m_voice == "Female" else "ur-PK-AsadNeural"
                    async def gv(): await edge_tts.Communicate(m_script, v_code).save("ma.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip("ma.mp3")
                    res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
                    w, h = res[m_ratio]
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_script[:60] + ' 3d cinematic animation')}?width={w}&height={h}&nologo=true"
                    with open("i.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    clip = ImageClip("i.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip = clip.resize(newsize=(w, h))
                    clip.write_videofile("es.mp4", codec="libx264", audio_codec="aac")
                    st.video("es.mp4")
                except Exception as e: st.error(f"Error: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio | Powered by Muhammad Essa Awan</p>", unsafe_allow_html=True)
