import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
from PIL import Image

# Senior Engineer Fix: Patch for PIL ANTIALIAS error in newer versions
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

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
        font-size: 80px; font-weight: 900;
        margin-bottom: 0px;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. IDENTITY DATA
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_identity(query):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"creator", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns) if query else False

# ==========================================
# 3. ADVANCED AI ENGINE (WITH RETRY LOGIC)
# ==========================================
def get_ai_response(query, history):
    if check_identity(query): return ESSA_BIO
    
    # Prepare context and encode
    chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
    system_prompt = "You are ES AI created by Muhammad Essa Awan. Answer professionally and intelligently."
    full_prompt = f"{system_prompt}\n{chat_context}\nUser: {query}\nAssistant:"
    encoded = urllib.parse.quote(full_prompt)

    # Multi-Engine Silent Retry
    urls = [
        f"https://text.pollinations.ai/{encoded}?model=openai&cache=true",
        f"https://hercai.onrender.com/v3/hercai?question={encoded}"
    ]
    
    for url in urls:
        for _ in range(2): # 2 retries per URL
            try:
                r = requests.get(url, timeout=90) # Increased timeout
                if r.status_code == 200:
                    data = r.json() if 'hercai' in url else r.text
                    return data.get('reply') if isinstance(data, dict) else data
            except:
                time.sleep(1)
                continue
    return "معذرت، ابھی سرور جواب نہیں دے رہا۔ براہ کرم دوبارہ کوشش کریں۔"

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MULTI-MODAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- TAB 1: CHAT ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    st.write("🎙️ **Voice Typing:**")
    mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop", key='recorder')
    
    if prompt := st.chat_input("مجھ سے کچھ بھی پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                res = get_ai_response(prompt, st.session_state.messages)
                st.write(res)
                st.session_state.messages.append({"role": "assistant", "content": res})

# --- TAB 2: VOICE STUDIO ---
with tabs[1]:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("متن لکھیں:", height=100, key="v_area")
    c1, c2 = st.columns(2)
    with c1: v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"], key="v_lang")
    with c2: v_gen = st.selectbox("Gender:", ["Female", "Male"], key="v_gen")
    
    if st.button("Generate Voice 🚀"):
        if v_text:
            v_map = {
                "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
            }
            v_code = v_map[v_lang][v_gen]
            async def sv(): await edge_tts.Communicate(v_text, v_code).save("voice_tab.mp3")
            asyncio.run(sv())
            st.audio("voice_tab.mp3")

# --- TAB 3: MOVIE STUDIO (FIXED) ---
with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    m_script = st.text_area("Movie Story:", height=150, placeholder="یہاں کہانی لکھیں...")
    
    col_v, col_r = st.columns(2)
    with col_v:
        m_gen = st.selectbox("Voice Gender:", ["Female", "Male"], key="m_v_gen") # Restored Feature
    with col_r:
        m_ratio = st.selectbox("Video Size:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="m_ratio")

    if st.button("Generate Video Now 🚀"):
        if m_script:
            with st.spinner("ویڈیو تیار ہو رہی ہے..."):
                try:
                    # 1. Voice
                    v_code = "ur-PK-UzmaNeural" if m_gen == "Female" else "ur-PK-AsadNeural"
                    async def gv(): await edge_tts.Communicate(m_script, v_code).save("m_audio.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip("m_audio.mp3")
                    
                    # 2. Dimensions Logic
                    res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
                    w, h = res_map[m_ratio]

                    # 3. Image Generation
                    img_prompt = f"3D Disney Pixar style, {m_script[:60]}, cinematic, high quality, vibrant"
                    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_prompt)}?width={w}&height={h}&nologo=true"
                    with open("temp_img.jpg", "wb") as f: f.write(requests.get(img_url).content)
                    
                    # 4. Video Composition (Fixing ANTIALIAS bug by using proper resize)
                    clip = ImageClip("temp_img.jpg").set_duration(audio.duration).set_fps(24).set_audio(audio)
                    clip = clip.resize(newsize=(w, h))
                    
                    clip.write_videofile("final_movie.mp4", codec="libx264", audio_codec="aac")
                    st.video("final_movie.mp4")
                    with open("final_movie.mp4", "rb") as f:
                        st.download_button("Download Movie ⬇️", f, file_name="es_movie.mp4")
                except Exception as e:
                    st.error(f"Error occurred: {str(e)}")
        else:
            st.warning("پہلے کہانی لکھیں۔")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio v6.0 | Professional Engineer Fixed</p>", unsafe_allow_html=True)
