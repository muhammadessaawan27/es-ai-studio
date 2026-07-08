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
import io

# Senior Engineer Stability Configuration
session = requests.Session()

# PIL Patch to prevent any image related crashes
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Backend Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 25px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 45px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; animation: lightningGlow 1.5s infinite;
        background: #1e293b; padding: 10px; border-radius: 0 0 20px 20px;
    }
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 10px 0; }
    .ai-shua {
        width: 80px; height: 80px; background: linear-gradient(135deg, #ff007a, #2563eb);
        border-radius: 20px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 30px; color: white;
        box-shadow: 0 0 20px rgba(37, 99, 235, 0.6); animation: rotateShua 6s infinite linear; border: 3px solid #fff;
    }
    @keyframes rotateShua { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    .main-header { font-size: 2rem; font-weight: 900; color: #0f172a; text-align: center; margin-bottom: 10px; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: #1e293b !important; color: white; }
    [data-testid="stSidebar"] * { color: white !important; font-weight: bold; }
    
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 12px !important; height: 50px; width: 100%; font-weight: 900;
    }
    </style>
    """, unsafe_allow_html=True)

# Top Persistent Header
st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. BULLETPROOF ENGINE LOGIC (FIXING AVCODEC ERRORS)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Identify core subject in Urdu: '{text}'. Create a detailed English 3D animation prompt. No humans unless asked."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_stable_v40_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        # Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        
        for i, scene in enumerate(sentences):
            status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)}...")
            prompt = get_v40_prompt(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_res = session.get(img_url, timeout=60)
            
            # --- CRITICAL FIX FOR AVCODEC ERROR ---
            if img_res.status_code == 200:
                with open(img_path, "wb") as f: f.write(img_res.content)
                # Re-opening and cleaning image with PIL ensures MoviePy doesn't crash on invalid data
                clean_img = Image.open(img_path).convert("RGB")
                clean_img.save(img_path, "JPEG", quality=95)
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24).resize(newsize=(w, h))
                clip = clip.resize(lambda t: 1.2 - 0.2 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V59_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. SIDEBAR NAVIGATION (TRUE ISOLATION)
# ==========================================
st.sidebar.markdown("## 🛠️ Menu Selection")
page = st.sidebar.radio("Go To:", ["💬 Chat & Info", "🎬 Movie Studio", "🎨 Image Studio"])

# --- PAGE 1: CHAT ---
if page == "💬 Chat & Info":
    st.write("### 💬 ES AI Assistant")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
        
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- PAGE 2: MOVIE STUDIO ---
elif page == "🎬 Movie Studio":
    st.write("### 🎥 v40 Cinematic Production")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=150)
    mv_col, mr_col, ms_col = st.columns(3)
    with mv_col: m_voice = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mr_col: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with ms_col: m_style = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"])
    
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_stable_v40_movie(m_script, m_voice, m_ratio, m_style)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Movie ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(f"Render Failed: {v_res}")

# --- PAGE 3: IMAGE STUDIO ---
elif page == "🎨 Image Studio":
    st.write("### 🎨 ES AI Image Surgeon")
    mode = st.radio("Choose Mode:", ["Text to Image", "Edit Photo"], horizontal=True)
    if mode == "Text to Image":
        p_img = st.text_area("Describe Image:")
        if st.button("Generate 🚀"):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_img)}?width=1024&height=1024&nologo=true"
            st.image(url)
    else:
        f_up = st.file_uploader("Upload Image:", type=["jpg", "png"])
        if f_up:
            st.image(f_up, width=300)
            edit_req = st.text_input("Change what?")
            if st.button("Apply Surgery 🚀"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_req)}?width=1024&height=1024&nologo=true&negative=girl,female"
                st.image(url)

st.sidebar.markdown("---")
st.sidebar.info(f"Version: 59.0 | Muhammad Essa Awan")
