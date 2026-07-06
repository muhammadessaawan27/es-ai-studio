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

# Senior Engineer Fix: Independent scaling for high-traffic apps
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PRODUCTION GRADE CONFIGURATION
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

# ==========================================
# 2. CREATOR DATA & LOGIC
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa awan", r"muhammad essa", r"maker", r"founder"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 3. HIGH-STABILITY CHAT ENGINE (NO TIMEOUT)
# ==========================================
def get_professional_response(query, history):
    if is_creator_query(query): return ESSA_BIO
    
    encoded_q = urllib.parse.quote(query)
    # Persisting the System Role for Every User
    system_role = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer professionally and smartly.")
    
    urls = [
        f"https://text.pollinations.ai/{encoded_q}?model=openai&system={system_role}&cache=true",
        f"https://hercai.onrender.com/v3/hercai?question={encoded_q}"
    ]
    
    for url in urls:
        try:
            r = requests.get(url, timeout=60) # High timeout for complex queries
            if r.status_code == 200:
                data = r.json() if 'hercai' in url else r.text
                return data.get('reply') if isinstance(data, dict) else data
        except: continue
    return "سسٹم اپ ڈیٹ ہو رہا ہے۔ براہ کرم تھوڑی دیر بعد دوبارہ کوشش کریں۔"

# ==========================================
# 4. PREMIUM UI INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ULTIMATE AI AGENT SYSTEM</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- TAB 1: CHAT ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    st.write("🎙️ **Voice Command:**")
    mic_recorder(start_prompt="Speak Now", stop_prompt="Stop", key='recorder')

    if user_p := st.chat_input("مجھ سے کچھ بھی پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": user_p})
        with st.chat_message("user"): st.write(user_p)
        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                response = get_professional_response(user_p, st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- TAB 2: VOICE STUDIO ---
with tabs[1]:
    st.header("Professional Voiceover")
    v_text = st.text_area("متن لکھیں جسے آواز میں بدلنا ہے:", height=100)
    col_l, col_g = st.columns(2)
    with col_l: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"], key="v_l")
    with col_g: gen = st.selectbox("Gender:", ["Female", "Male"], key="v_g")
    
    if st.button("Generate Audio 🚀", key="v_btn"):
        if v_text:
            v_map = {"Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                     "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                     "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}}
            v_code = v_map[lang][gen]
            async def run_v(): await edge_tts.Communicate(v_text, v_code).save("voice.mp3")
            asyncio.run(run_v())
            st.audio("voice.mp3")
            with open("voice.mp3", "rb") as f: st.download_button("Download", f, file_name="es_voice.mp3")

# --- TAB 3: MOVIE STUDIO (THE MILLION-USER ENGINE) ---
with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    m_script = st.text_area("مووی اسکرپٹ یہاں لکھیں:", height=150, placeholder="مثال: ایک بہادر شیر کی کہانی جو پہاڑوں پر رہتا تھا...")
    
    m_col1, m_col2 = st.columns(2)
    with m_col1: m_voice_gen = st.selectbox("Voice Selection:", ["Female", "Male"], key="ms_gen")
    with m_col2: m_ratio = st.selectbox("Video Size:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="ms_ratio")

    if st.button("🚀 Generate High-Quality Video"):
        if m_script:
            with st.spinner("سینیمیٹک مناظر تیار ہو رہے ہیں..."):
                try:
                    # Unique ID for concurrent users
                    uid = str(uuid.uuid4())[:8]
                    # 1. Voice Generation
                    v_code = "ur-PK-UzmaNeural" if m_voice_gen == "Female" else "ur-PK-AsadNeural"
                    async def gv(): await edge_tts.Communicate(m_script, v_code).save(f"{uid}_a.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip(f"{uid}_a.mp3")
                    
                    # 2. Dimensions Logic
                    res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
                    w, h = res[m_ratio]

                    # 3. Smart Image Generation (Anti-Woman-Teacup Logic)
                    # We add a strong modifier to ensure it matches the script
                    img_prompt = f"Professional 3D cinematic animation style, {m_script[:70]}, vibrant lighting, 8k resolution, masterpiece, no text"
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_prompt)}?width={w}&height={h}&nologo=true"
                    with open(f"{uid}_i.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    
                    # 4. Assembly (Safe PIL Handling)
                    clip = ImageClip(f"{uid}_i.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip = clip.resize(newsize=(w, h)) # Correct scaling method
                    
                    output_name = f"es_movie_{uid}.mp4"
                    clip.write_videofile(output_name, codec="libx264", audio_codec="aac")
                    
                    st.video(output_name)
                    with open(output_name, "rb") as f:
                        st.download_button("Download Movie ⬇️", f, file_name=f"es_ai_studio_{uid}.mp4")
                    st.success("مبارک ہو! ویڈیو پروفیشنل رزلٹ کے ساتھ تیار ہے۔")
                except Exception as e:
                    st.error(f"تکنیکی خرابی: {str(e)}")
        else: st.warning("پہلے کہانی لکھیں۔")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>© 2024 ES AI Master Studio | Production Engine v7.0</p>", unsafe_allow_html=True)
