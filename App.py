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
# 1. LUXURY UI (v29 LOGO + WHITE BACKGROUND)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Professional White (v27 Style) */
    .stApp {
        background-color: #F8FAFC;
        color: #111827;
        font-family: 'Inter', sans-serif;
    }

    /* Modern Logo - v29 Luxury Animated Design */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 40px 0;
    }
    .ai-logo {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        border-radius: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 42px;
        font-weight: 900;
        color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6), inset 0 0 15px rgba(255, 255, 255, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.1);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 20px rgba(37, 99, 235, 0.5); }
        50% { transform: scale(1.05); box-shadow: 0 0 40px rgba(124, 58, 237, 0.7); }
        100% { transform: scale(1); box-shadow: 0 0 20px rgba(37, 99, 235, 0.5); }
    }
    
    .premium-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #111827;
        margin-top: 20px;
    }
    .premium-sub {
        font-size: 0.9rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin-bottom: 20px;
    }

    /* Luxury Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        transition: 0.4s all !important;
    }
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(37, 99, 235, 0.5) !important;
    }

    /* Fixed Input Box for Readability */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="logo-container">
        <div class="ai-logo">ES</div>
        <div class="premium-header">ES AI Master Studio</div>
        <div class="premium-sub">Create • Chat • Voice • Video</div>
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
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"awan", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. v27 ACCURATE VIDEO ENGINE (RESTORED)
# ==========================================
def get_strict_visual_prompt_v27(urdu_text, style_choice):
    try:
        director_instr = (
            f"Task: Extract the core physical subject from this Urdu text: '{urdu_text}'. "
            "Rule 1: If it mentions an object (house, stone, mountain), describe ONLY that object. "
            "Rule 2: If it mentions an animal, describe ONLY that animal. "
            "Rule 3: If no human is mentioned, STERNLY EXCLUDE them. "
            "Output only a detailed English prompt. No preamble."
        )
        encoded_instr = urllib.parse.quote(director_instr)
        res = session.get(f"https://text.pollinations.ai/{encoded_instr}?model=openai&cache=true", timeout=30)
        visual_desc = res.text if res.status_code == 200 else urdu_text
        
        neg = ""
        if not any(k in urdu_text for k in ["احمد", "لڑکا", "لڑکی", "آدمی", "عورت", "بچہ", "انسان"]):
            neg = ", no humans, no people, no faces"

        return f"{style_choice} style, {visual_desc}{neg}, cinematic 4k, masterpiece"
    except: return urdu_text

def create_v27_movie(story, voice_gen, ratio, style):
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

        # Step 3: Scene Generation
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی پہچان ہو رہی ہے...")
            strict_prompt = get_strict_visual_prompt_v27(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strict_prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_path, "wb") as f: f.write(r.content)
                img = Image.open(img_path).convert("RGB")
                img.save(img_path, "JPEG")
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # v27 Cinematic Zoom Out
                clip = clip.resize(lambda t: 1.1 - 0.06 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        # Step 4: Final Render
        status.info("⚙️ ویڈیو رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"])
        
        status.success("✅ ویڈیو تیار ہے!")
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Ask ES AI anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.markdown("### 🎙️ Voiceover Generator")
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
    st.markdown("### 🎬 Movie Studio v27 Engine Restored")
    m_script = st.text_area("Write your story:", height=150, placeholder="Paharon ke peeche suraj doob raha hai...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Accurate Video"):
        if m_script:
            with st.spinner("AI Director is crafting your scenes..."):
                video = create_v27_movie(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #475569;'>ES AI Premium Studio | Designed for Muhammad Essa Awan</p>", unsafe_allow_html=True)
