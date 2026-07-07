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

# Senior Engineer Fix: Persistent Session for stability
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI (NEW ROTATING CHIP LOGO + WHITE BG)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Professional White */
    .stApp {
        background-color: #F8FAFC;
        color: #111827;
        font-family: 'Inter', sans-serif;
    }

    /* 3D Rotating AI Chip Logo (Professional Choice) */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 40px 0;
    }
    .ai-chip {
        width: 100px;
        height: 100px;
        background: #0f172a;
        border: 4px solid #3b82f6;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 40px;
        font-weight: 900;
        color: #3b82f6;
        box-shadow: 0 0 20px #3b82f6, inset 0 0 10px #3b82f6;
        position: relative;
        transform-style: preserve-3d;
        animation: rotate3D 5s linear infinite;
    }
    
    @keyframes rotate3D {
        0% { transform: perspective(1000px) rotateY(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg); }
    }

    .ai-chip::after {
        content: 'ES';
        position: absolute;
        color: #ffffff;
        text-shadow: 0 0 10px #3b82f6;
    }

    .premium-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 20px;
        letter-spacing: -1px;
    }
    .premium-sub {
        font-size: 0.9rem;
        color: #3b82f6;
        text-transform: uppercase;
        letter-spacing: 5px;
        font-weight: bold;
    }

    /* Professional Buttons */
    .stButton>button {
        background: #2563EB !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        transition: 0.3s all;
    }
    .stButton>button:hover {
        background: #1e40af !important;
        box-shadow: 0 5px 15px rgba(37, 99, 235, 0.4) !important;
    }

    /* Readable Inputs */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff !important;
        border: 2px solid #E2E8F0 !important;
        border-radius: 12px !important;
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="logo-container">
        <div class="ai-chip"></div>
        <div class="premium-header">ES AI Master Studio</div>
        <div class="premium-sub">MUHAMMAD ESSA AWAN</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (PRESERVED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. v31 PRECISION VIDEO ENGINE (OBJECT ISOLATION)
# ==========================================
def get_isolated_visual_prompt(urdu_text, style_choice):
    try:
        # STRONGER INSTRUCTIONS for accurate object detection
        director_instr = (
            f"Strict Instruction: Analyze this Urdu text: '{urdu_text}'. "
            "Identify the single most important object, animal, or building. "
            "Describe ONLY that subject in detail. If no human is mentioned, DO NOT include any people. "
            "Focus on textures and lighting. Output ONLY a clean English prompt."
        )
        encoded_instr = urllib.parse.quote(director_instr)
        res = session.get(f"https://text.pollinations.ai/{encoded_instr}?model=openai&cache=true", timeout=30)
        visual_desc = res.text if res.status_code == 200 else urdu_text
        
        # Adding negative enforcement to avoid random humans
        neg = ""
        human_indicators = ["احمد", "لڑکا", "لڑکی", "آدمی", "عورت", "بچہ", "انسان", "boy", "man", "girl", "person"]
        if not any(k in urdu_text for k in human_indicators):
            neg = ", no humans, no faces, no people"

        return f"{style_choice} style, {visual_desc}{neg}, high resolution cinematic 4k, realistic, masterpiece"
    except: return urdu_text

def create_accurate_movie_v31(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        status.info("🎙️ آواز تیار کی جا رہی ہے...")
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        # Step 4: Scene Generation (ISOLATED)
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کا مشاہدہ ہو رہا ہے...")
            strict_prompt = get_isolated_visual_prompt(scene, style)
            
            # UNIQUE SEED for every image to prevent repetition
            seed = random.randint(1, 1000000)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strict_prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_path, "wb") as f: f.write(r.content)
                img = Image.open(img_path).convert("RGB")
                img.save(img_path, "JPEG")
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # Professional ZOOM OUT (v30 Fix)
                clip = clip.resize(lambda t: 1.15 - 0.1 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        # Step 5: Render
        status.info("⚙️ فائنل مووی تیار ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"])
        
        status.success("✅ شاہکار تیار ہے!")
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. UI INTERFACE
# ==========================================
tabs = st.tabs(["💬 Chat", "🎙️ Voice", "🎬 Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.write("### 🎙️ Create Professional Voiceover")
    v_text = st.text_area("Yahan likhein:", key="v_input")
    v_col1, v_col2 = st.columns(2)
    with v_col1: gen = st.selectbox("Voice:", ["Female", "Male"])
    with v_col2: st.selectbox("Language:", ["Urdu", "English"], index=0)
    if st.button("Generate Audio 🚀"):
        if v_text:
            vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, vc).save("es_v.mp3")
            asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.write("### 🎬 Pro Studio v31.0")
    m_script = st.text_area("Write your story:", height=150, placeholder="Example: Aik hathi nadi ke kinare pani pee raha hai...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"])

    if st.button("🚀 Generate Precision Video"):
        if m_script:
            with st.spinner("Identifying objects and animating scenes..."):
                video = create_accurate_movie_v31(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>ES AI Premium Studio | Designed for Muhammad Essa Awan</p>", unsafe_allow_html=True)
