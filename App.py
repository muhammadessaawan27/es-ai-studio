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

# Senior Engineer Optimization: Global compatibility patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM BRANDING & UI (High Version)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio - Pro", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: clamp(40px, 8vw, 90px); font-weight: 900;
        filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.5));
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 15px; height: 55px; width: 100%; 
        font-size: 20px; font-weight: bold; border: none;
        transition: 0.4s ease; box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.3);
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0px 8px 25px rgba(0, 212, 255, 0.5); }
    </style>
    """, unsafe_allow_html=True)

# Identity Data
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 2. PRO CHAT ENGINE (Stable & Detailed)
# ==========================================
def get_pro_response(query):
    if is_creator_query(query): return ESSA_BIO
    
    encoded_q = urllib.parse.quote(query)
    # High-Performance API with 60s Timeout
    url = f"https://text.pollinations.ai/{encoded_q}?model=openai&cache=true"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            return r.text
        else:
            return "سسٹم ابھی پروسیسنگ میں ہے، براہ کرم ایک بار ریفریش کریں۔"
    except:
        return "کنکشن کا مسئلہ ہے، براہ کرم اپنا انٹرنیٹ چیک کریں۔"

# ==========================================
# 3. UI MAIN INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>PREMIUM AI AGENT SYSTEM</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Intelligent Chat", "🎙️ HD Voice Studio", "🎬 Pro Movie Studio"])

# --- CHAT TAB ---
with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    st.write("🎙️ **Voice Typing:**")
    mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop Recording", key='recorder')

    if prompt := st.chat_input("مجھ سے کوئی بھی معلومات پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                response = get_pro_response(prompt)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- VOICE TAB ---
with tab2:
    st.header("HD Voiceover Studio")
    v_text = st.text_area("متن لکھیں جسے آواز میں بدلنا ہے:", height=150)
    c1, c2 = st.columns(2)
    with c1: v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"], key="vlang")
    with c2: v_gen = st.selectbox("Gender:", ["Female", "Male"], key="vgen")
    
    if st.button("Generate HD Audio 🚀"):
        if v_text:
            v_map = {"Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                     "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                     "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}}
            v_code = v_map[v_lang][v_gen]
            async def run_v(): await edge_tts.Communicate(v_text, v_code).save("voice.mp3")
            asyncio.run(run_v())
            st.audio("voice.mp3")
            with open("voice.mp3", "rb") as f:
                st.download_button("Download MP3 ⬇️", f, file_name="es_pro_voice.mp3")

# --- MOVIE TAB (High Version Engine) ---
with tab3:
    st.header("🎬 Cinematic Movie Engine")
    m_script = st.text_area("مووی کی کہانی یہاں لکھیں:", height=200, placeholder="ایک خوبصورت جنگل میں شیر اور ہاتھی کی دوستی...")
    
    col_v, col_r = st.columns(2)
    with col_v: m_voice = st.selectbox("Voice Artist:", ["Female", "Male"], key="ms_v")
    with col_r: m_ratio = st.selectbox("Frame Size:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="ms_r")

    if st.button("🚀 Render High-Quality Video"):
        if m_script:
            with st.spinner("سینیمیٹک مناظر اور آواز تیار ہو رہی ہے..."):
                try:
                    uid = str(uuid.uuid4())[:6]
                    # 1. HD Voice Generation
                    v_code = "ur-PK-UzmaNeural" if m_voice == "Female" else "ur-PK-AsadNeural"
                    async def gv(): await edge_tts.Communicate(m_script, v_code).save(f"{uid}.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip(f"{uid}.mp3")
                    
                    # 2. High-Res Ratio Logic
                    res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
                    w, h = res[m_ratio]

                    # 3. Premium Cinematic Image (No Teacups/Wrong Visuals)
                    img_prompt = f"Professional 3D cinematic animation masterpiece, {m_script[:70]}, lighting by Pixar, vibrant, 8k resolution, no humans, no text"
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_prompt)}?width={w}&height={h}&nologo=true"
                    with open(f"{uid}.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    
                    # 4. Assembly & High-Bitrate Export
                    clip = ImageClip(f"{uid}.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip = clip.resize(newsize=(w, h))
                    
                    out_name = f"es_pro_{uid}.mp4"
                    clip.write_videofile(out_name, codec="libx264", audio_codec="aac", bitrate="8000k")
                    
                    st.video(out_name)
                    with open(out_name, "rb") as f:
                        st.download_button("Download HD Movie ⬇️", f, file_name=f"es_ai_pro_{uid}.mp4")
                    st.success("مبارک ہو! ہائی ورژن ویڈیو تیار ہے۔")
                except Exception as e:
                    st.error(f"تکنیکی خرابی: {e}")
        else: st.warning("کہانی لکھنا لازمی ہے۔")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio Pro | Built for Muhammad Essa Awan</p>", unsafe_allow_html=True)
