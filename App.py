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

# Global Session for Speed
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & IDENTITY
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 12px; height: 55px; font-weight: bold; border: none; transition: 0.2s;}
    </style>
    """, unsafe_allow_html=True)

ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"awan", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 2. POWERFUL MULTI-SCENE MOVIE ENGINE
# ==========================================
def create_masterpiece_v24(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    
    try:
        # Step 1: Voice Generation
        status.info("🎙️ آواز تیار کی جا رہی ہے...")
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Full Sentence Splitting (NO LIMITS)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        num_scenes = len(sentences)
        dur_per = voice_audio.duration / num_scenes

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        clips = []

        # Step 3: Loop for EVERY sentence
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} بن رہا ہے: {scene[:30]}...")
            
            # Smart Visual Prompt (Golden Rules Included)
            prompt = f"{style} style, {scene[:100]}, highly detailed, cinematic lighting, 8k, masterpiece, no text, no black bars"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=40).content
            with open(img_path, "wb") as f: f.write(img_data)
            
            # PIL Cleanup to ensure valid data
            img_verify = Image.open(img_path).convert("RGB")
            img_verify.save(img_path)
            
            # Step 4: Zoom OUT Effect (Professional Motion)
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h))
            # Start at 1.1x and end at 1.0x (Zoom Out)
            clip = clip.resize(lambda t: 1.1 - 0.1 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Step 5: High-Quality Concatenation
        status.info("⚙️ فائنل مووی رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Movie_{u_id}.mp4"
        
        # Standard encoding for universal playback
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k", preset="medium")
        
        status.success("✅ شاہکار تیار ہے!")
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>PROFESSIONAL FILM STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Chat", "🎙️ Voice", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    col_a, col_b = st.columns([1, 4])
    with col_a: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='mic')
    with col_b: st.file_uploader("➕", type=["jpg", "png"], key="up")

    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("Voice Studio")
    vt = st.text_area("Yahan likhein:")
    if st.button("Generate Audio 🚀"):
        async def sv(): await edge_tts.Communicate(vt, "ur-PK-UzmaNeural").save("es_v.mp3")
        asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.header("🎬 Master Cinematic Studio v24.0")
    m_script = st.text_area("کہانی لکھیں (ہر جملے پر منظر بدلے گا):", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Male", "Female"])
    with c2: mr = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Unlimited Scene Movie"):
        if m_script:
            video = masterpiece = create_masterpiece_v24(m_script, mv, mr, ms)
            if "mp4" in video:
                st.video(video)
                with open(video, "rb") as f: st.download_button("Download Movie ⬇️", f, file_name=video)
            else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v24.0 | Unlimited Scenes | Multi-User | Muhammad Essa Awan</p>", unsafe_allow_html=True)
