import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
from PIL import Image

# Senior Engineer Fix: Global patch for ANTIALIAS removal in newer Pillow versions
if not hasattr(Image, 'ANTIALIAS'):
    # This makes the code compatible with BOTH old and new Pillow versions
    if hasattr(Image, 'LANCZOS'):
        Image.ANTIALIAS = Image.LANCZOS
    else:
        Image.ANTIALIAS = 1 # Fallback for very old versions

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
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
        font-size: clamp(40px, 8vw, 80px); font-weight: 900;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0px 8px 20px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# Creator Data
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa awan", r"muhammad essa"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# AI Chat Engine
def get_intelligent_response(query):
    if is_creator_query(query): return ESSA_BIO
    encoded_q = urllib.parse.quote(query)
    url = f"https://text.pollinations.ai/{encoded_q}?model=openai&cache=true"
    try:
        r = requests.get(url, timeout=30)
        return r.text if r.status_code == 200 else "AI سرور اس وقت جواب نہیں دے رہا۔"
    except: return "کنکشن کا مسئلہ ہے۔"

# UI Header
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MULTI-FORMAT STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- TAB 1: CHAT ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    
    mic_recorder(start_prompt="Record Command", stop_prompt="Stop", key='recorder')
    
    if user_p := st.chat_input("پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": user_p})
        with st.chat_message("user"): st.write(user_p)
        with st.chat_message("assistant"):
            res = get_intelligent_response(user_p)
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- TAB 2: VOICE STUDIO ---
with tabs[1]:
    st.header("Voiceover Generator")
    v_text = st.text_area("متن لکھیں:")
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        if v_text:
            v_code = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def run_v(): await edge_tts.Communicate(v_text, v_code).save("voice.mp3")
            asyncio.run(run_v())
            st.audio("voice.mp3")

# --- TAB 3: MOVIE STUDIO ---
with tabs[2]:
    st.header("🎬 Pro Movie Engine")
    m_script = st.text_area("کہانی لکھیں:", height=150)
    col_v, col_r = st.columns(2)
    with col_v: m_voice = st.selectbox("Voice Gender:", ["Female", "Male"], key="mv")
    with col_r: m_ratio = st.selectbox("Size:", ["YouTube (16:9)", "TikTok (9:16)", "Instagram (1:1)"], key="mr")

    if st.button("Generate Final Video 🚀"):
        if m_script:
            with st.spinner("ویڈیو رینڈر ہو رہی ہے..."):
                try:
                    uid = str(uuid.uuid4())[:6]
                    # 1. Voice
                    v_code = "ur-PK-UzmaNeural" if m_voice == "Female" else "ur-PK-AsadNeural"
                    async def gv(): await edge_tts.Communicate(m_script, v_code).save(f"{uid}.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip(f"{uid}.mp3")
                    
                    # 2. Dimensions
                    res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
                    w, h = res[m_ratio]

                    # 3. Cinematic Image
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_script[:60] + ' 3d disney pixar style animation')}?width={w}&height={h}&nologo=true"
                    with open(f"{uid}.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    
                    # 4. Assembly (Correct scaling to avoid error)
                    clip = ImageClip(f"{uid}.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip = clip.resize(newsize=(w, h))
                    
                    out_name = f"video_{uid}.mp4"
                    clip.write_videofile(out_name, codec="libx264", audio_codec="aac")
                    st.video(out_name)
                    st.success("ویڈیو تیار ہے!")
                except Exception as e:
                    st.error(f"تکنیکی خرابی: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio v8.0 | Stable Production</p>", unsafe_allow_html=True)
