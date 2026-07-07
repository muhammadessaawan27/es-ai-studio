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

# Senior Engineer Fix: PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Critical Engine Error: {e}")

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
        color: white; border-radius: 12px; height: 50px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.01); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CREATOR IDENTITY (BIO)
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
# 3. MOOD-BASED MUSIC
# ==========================================
def get_bgm(text):
    t = text.lower()
    if any(k in t for k in ["jungle", "sher", "animal"]): return "https://www.chosic.com/wp-content/uploads/2021/07/The-Wild-Animals.mp3"
    if any(k in t for k in ["king", "badshah", "history"]): return "https://www.chosic.com/wp-content/uploads/2020/06/Epic-Adventure.mp3"
    return "https://www.chosic.com/wp-content/uploads/2021/04/Inspiring-Story.mp3"

# ==========================================
# 4. ADVANCED MOVIE ENGINE (v18.2)
# ==========================================
def create_pro_movie_final(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: BGM
        bgm_path = f"{u_id}_bgm.mp3"
        bgm_track = voice_audio
        try:
            r_bgm = requests.get(get_bgm(story), timeout=10)
            with open(bgm_path, "wb") as f: f.write(r_bgm.content)
            bgm_audio = AudioFileClip(bgm_path).volumex(0.12).set_duration(voice_audio.duration)
            bgm_track = CompositeAudioClip([voice_audio, bgm_audio])
        except: pass

        # Step 3: Dimensions
        res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res[ratio]

        # Step 4: Multi-Scene Generation
        sentences = re.split(r'[۔.!]', story)
        sentences = [s.strip() for s in sentences if len(s) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            # Applying Rules for Characters
            prompt = f"{style} style, {scene[:90]}, highly detailed cinematic 3D, natural motion, hair and cloth movement, 8k, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(requests.get(img_url).content)
            
            # Assembly + ZOOM OUT (1.15 -> 1.0)
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h)) 
            clip = clip.resize(lambda t: 1.15 - 0.05 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        final_video = concatenate_videoclips(clips, method="compose").set_audio(bgm_track)
        out_name = f"ES_Final_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Chat & Vision", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("---")
    c1, c2 = st.columns([1, 4])
    with c1: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='mic')
    with c2: st.file_uploader("➕ Upload Image", type=["jpg", "png"], key="up")

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        response = ESSA_BIO if is_creator_query(prompt) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai&cache=true").text
        
        with st.chat_message("assistant"):
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

with tabs[1]:
    st.header("Professional Voiceover")
    v_t = st.text_area("Yahan likhein:")
    v_l, v_g = st.columns(2)
    with v_l: st.selectbox("Language:", ["Urdu", "English", "Hindi"], key="l")
    with v_g: gen = st.selectbox("Gender:", ["Female", "Male"], key="g")
    if st.button("Generate Voice 🚀"):
        vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
        async def sv(): await edge_tts.Communicate(v_t, vc).save("es_v.mp3")
        asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.header("🎬 Master Cinematic Studio")
    m_s = st.text_area("Movie Script:", height=150, placeholder="Har jumlay par aik naya manzar banay ga...")
    mv, mr, ms = st.columns(3)
    with mv: m_voice = st.selectbox("Voice:", ["Male", "Female"])
    with mr: m_ratio = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with ms: m_style = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Master Movie"):
        if m_s:
            with st.spinner("AI مناظر، موسیقی اور اینیمیشن تیار کر رہا ہے..."):
                video = create_pro_movie_final(m_s, m_voice, m_ratio, m_style)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v18.2 | Restored & Optimized | Muhammad Essa Awan</p>", unsafe_allow_html=True)
