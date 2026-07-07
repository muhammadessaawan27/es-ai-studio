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
from PIL import Image, ImageDraw

# Senior Engineer Fix for Image and MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Critical Engine Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. CORE BRANDING & UI (Metallic Neon)
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
        color: white; border-radius: 12px; height: 50px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.01); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CREATOR IDENTITY (YOUR BIO)
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
    patterns = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns) if q else False

# ==========================================
# 3. ADVANCED ENGINES (CHAT & VIDEO)
# ==========================================

def get_ai_brain_response(query):
    if is_creator_query(query): return ESSA_BIO
    encoded = urllib.parse.quote(query)
    system_instr = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer professionally and smartly.")
    url = f"https://text.pollinations.ai/{encoded}?model=openai&cache=true&system={system_instr}"
    try:
        r = requests.get(url, timeout=30)
        return r.text if r.status_code == 200 else "سرور مصروف ہے، دوبارہ کوشش کریں۔"
    except: return "کنکشن سست ہے، انٹرنیٹ چیک کریں۔"

def create_master_movie_v18(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # 1. Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        audio = AudioFileClip(audio_file)
        
        # 2. Split by Sentences
        sentences = re.split(r'[۔.!]', story)
        sentences = [s.strip() for s in sentences if len(s) > 5]
        
        # 3. Dimension Setup
        res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res[ratio]

        clips = []
        dur_per_scene = audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            # Prompting for Natural Motion (Hair, blinking, wind)
            prompt = f"{style} style, {scene[:80]}, high quality 3d animation, moving hair, blinking eyes, wind blowing, realistic motion, masterpiece, 8k, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(requests.get(img_url).content)
            
            # Assembly + Zoom In (Image gets bigger to cover black bars)
            clip = ImageClip(img_path).set_duration(dur_per_scene).set_fps(24)
            clip = clip.resize(newsize=(w, h)) # Auto Fill Screen
            # Gradually increase size from 1.0 to 1.15
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t / dur_per_scene)).set_position('center')
            clips.append(fadein(clip, 0.4))

        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_Movie_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. FINAL UNIFIED UI
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>MUHAMMAD ESSA'S OFFICIAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Chat & Vision", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# TAB 1: SMART CHAT
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("---")
    col_mic, col_up = st.columns([1, 4])
    with col_mic: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='mic')
    with col_up: up_img = st.file_uploader("➕ Upload Image", type=["jpg", "png"])

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("ES AI Souch raha hai..."):
                response = get_ai_brain_response(prompt)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# TAB 2: VOICE STUDIO
with tabs[1]:
    st.header("🎙️ Professional Voiceover")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:", height=100)
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Awaaz (Gender):", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        if v_text:
            v_code = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, v_code).save("es_v.mp3")
            asyncio.run(sv()); st.audio("es_v.mp3")

# TAB 3: MOVIE STUDIO (v18.1)
with tabs[2]:
    st.header("🎬 Master Cinematic Studio")
    m_script = st.text_area("Movie Script:", height=150, placeholder="Har jumlay par aik naya manzar banay ga...")
    mv, mr, ms = st.columns(3)
    with mv: m_voice = st.selectbox("Voice:", ["Male", "Female"])
    with mr: m_ratio = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with ms: m_style = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Professional Movie"):
        if m_script:
            with st.spinner("AI مناظر اور اینیمیشن تیار کر رہا ہے..."):
                video = create_master_video_v18(m_script, m_voice, m_ratio, m_style)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download Movie ⬇️", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v18.1 | Full Feature Restoration | Muhammad Essa Awan</p>", unsafe_allow_html=True)
