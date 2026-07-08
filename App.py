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

# Senior Engineer Optimization: Persistent Session and Error Handling
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Critical Engine Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI (v29 LOGO + WHITE BACKGROUND)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Professional Light Background */
    .stApp {
        background-color: #F8FAFC;
        color: #111827;
        font-family: 'Inter', sans-serif;
    }

    /* v29 Premium Animated Logo */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px 0;
    }
    .ai-logo {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        border-radius: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 42px;
        color: white;
        box-shadow: 0 15px 35px rgba(37, 99, 235, 0.4);
        border: 2px solid rgba(255, 255, 255, 0.2);
        animation: glowPulse 2s infinite ease-in-out;
    }
    @keyframes glowPulse {
        0% { transform: scale(1); box-shadow: 0 0 20px rgba(37, 99, 235, 0.4); }
        50% { transform: scale(1.05); box-shadow: 0 0 40px rgba(124, 58, 237, 0.6); }
        100% { transform: scale(1); box-shadow: 0 0 20px rgba(37, 99, 235, 0.4); }
    }
    
    .premium-header { font-size: 2.2rem; font-weight: 800; color: #0F172A; margin-top: 15px; }
    .premium-sub { font-size: 0.9rem; color: #3B82F6; text-transform: uppercase; letter-spacing: 5px; font-weight: 700; }

    /* Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 12px !important; border: none !important;
        padding: 12px 30px !important; font-weight: 600 !important; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4) !important; }

    /* Input Styling */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff !important; border: 2px solid #E2E8F0 !important;
        border-radius: 12px !important; color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="logo-container">
        <div class="ai-logo">ES</div>
        <div class="premium-header">ES AI Master Studio</div>
        <div class="premium-sub">MUHAMMAD ESSA AWAN</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (THE PERSISTENT PROMPT)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_identity(query):
    patterns = [r"kisne banaya", r"who (made|created) you", r"owner", r"essa", r"awan", r"maker"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. v27 PRECISION VIDEO ENGINE (WITH STORAGE FIX)
# ==========================================
def get_precise_visual_prompt(urdu_text, style_choice):
    try:
        # Strict isolation logic
        director_instr = (
            f"Extract the core subject from Urdu: '{urdu_text}'. "
            "Identify building, animal, or object. Describe ONLY that. "
            "If no human mentioned, STERNLY EXCLUDE humans. No text. 8k cinematic."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
        res = session.get(url, timeout=30)
        visual_desc = res.text if res.status_code == 200 else urdu_text
        
        neg = ""
        human_keys = ["احمد", "لڑکا", "لڑکی", "آدمی", "عورت", "بچہ", "انسان", "boy", "girl", "man", "woman"]
        if not any(k in urdu_text for k in human_keys):
            neg = ", no humans, no people, no faces, no boys, no girls"
            
        return f"{style_choice} style, {visual_desc}{neg}, high resolution cinematic 4k, realistic, masterpiece"
    except: return urdu_text

def create_stable_movie_v32(story, voice_gen, ratio, style):
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

        # Step 3: Sentence Processing
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        # Step 4: Robust Scene Generation
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی پہچان ہو رہی ہے...")
            strict_prompt = get_precise_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strict_prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            # Triple retry for image download
            img_success = False
            for _ in range(3):
                try:
                    r = session.get(img_url, timeout=60)
                    if r.status_code == 200:
                        with open(img_path, "wb") as f: f.write(r.content)
                        # Sanitize image
                        Image.open(img_path).convert("RGB").save(img_path, "JPEG")
                        img_success = True
                        break
                except: time.sleep(1)
            
            if img_success:
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # v27 Cinematic Zoom Out
                clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        if not clips: raise ValueError("Could not generate scenes. Check internet.")

        # Step 5: Rendering with Fix for MediaFileStorageError
        status.info("⚙️ فائنل مووی تیار ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        
        # Cleanup temporary images BEFORE rendering to save disk space
        voice_audio.close()
        for i in range(len(sentences)):
            p = f"{u_id}_{i}.jpg"
            # We don't remove yet because concatenate needs them, but we clear RAM
        
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Final Verification
        if os.path.exists(out_name) and os.path.getsize(out_name) > 0:
            time.sleep(1) # Final release wait
            status.success("✅ شاہکار تیار ہے!")
            return out_name
        else:
            raise ValueError("Video file creation failed.")

    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Ask ES AI anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if check_identity(p):
            res = ESSA_BIO
        else:
            try:
                # Persistent System Prompt
                sys = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer intelligently.")
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&system={sys}", timeout=30).text
            except: res = "Connection slow. Please try again."
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.write("### 🎙️ Create Premium Voiceover")
    v_text = st.text_area("Yahan likhein:", key="v_input")
    v_col1, v_col2 = st.columns(2)
    with v_col1: gen = st.selectbox("Voice Gender:", ["Female", "Male"])
    with v_col2: st.selectbox("Language:", ["Urdu", "English"], index=0)
    if st.button("Generate Audio 🚀"):
        if v_text:
            vc = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, vc).save("es_v.mp3")
            asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.write("### 🎬 Pro Studio v32.0 (Bulletproof)")
    m_script = st.text_area("Write your story:", height=150, placeholder="Example: A mermaid in the deep blue sea...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"])

    if st.button("🚀 Generate Precision Video"):
        if m_script:
            with st.spinner("AI Director is processing and verifying files..."):
                video = create_stable_movie_v32(m_script, mv, mr, ms)
                if "mp4" in video and os.path.exists(video):
                    st.video(video, format="video/mp4")
                    st.download_button("Download Full HD ⬇️", open(video, 'rb'), file_name=video)
                else:
                    st.error(f"Render Issue: {video}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>ES AI Master Studio v32.0 | Engineered for Muhammad Essa Awan</p>", unsafe_allow_html=True)
