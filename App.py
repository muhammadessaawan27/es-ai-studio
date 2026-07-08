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

# Senior Engineer Stability Fix
session = requests.Session()

# Global PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error("Engine Load Warning: Please reboot the app via 'Manage app'.")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM UI (v29 LOGO + WHITE BG)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 15px #2563eb, 0 0 30px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 25px #ff007a, 0 0 50px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 10px; animation: lightningGlow 1.5s infinite;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
    }
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .ai-shua {
        width: 110px; height: 110px; background: linear-gradient(135deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 25px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        box-shadow: 0 0 35px rgba(37, 99, 235, 0.6); animation: rotate3D 5s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotate3D { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    .main-header { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 20px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 50px !important; height: 55px; width: 100%; font-weight: 900;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. BIO & SUBJECT ENGINE
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def get_v40_prompt(text):
    try:
        instr = f"Director Instruction: Extract the core subject from Urdu: '{text}'. Create a detailed English 3D animation prompt. No humans unless mentioned."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

# ==========================================
# 3. STABLE MOVIE ENGINE (v64 Optimized)
# ==========================================
def create_safe_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # 1. Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        # 2. Dimensions Logic
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # 3. Sentence Splitting (Memory Safe)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎬 منظر {i+1}/{len(sentences)} تیار ہو رہا ہے...")
            refined_p = get_v40_prompt(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            with open(img_path, "wb") as f: f.write(img_data)
            
            # PIL Image cleaning (Important for MoviePy)
            with Image.open(img_path) as im:
                im.convert("RGB").resize((w, h)).save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # Zoom Out Fix (1.2 to 1.0)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))

        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V64_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Memory Cleanup
        voice_audio.close()
        final_video.close()
        for i in range(len(sentences)):
            if os.path.exists(f"i_{u_id}_{i}.jpg"): os.remove(f"i_{u_id}_{i}.jpg")
        
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD ASSEMBLY
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("---")
    c_f, c_v = st.columns(2)
    with c_f: st.file_uploader("➕ Upload Image", type=["jpg", "png"], key="chat_up")
    with c_v: mic_recorder(start_prompt="🎙️ Voice", stop_prompt="🛑 Stop", key="chat_mic")

    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if any(k in p.lower() for k in ["kisne", "creator", "essa"]) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 v40 Logic - Bulletproof Engine")
    m_s = st.text_area("Movie Script:", height=150, key="ms_v64")
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv_v64")
    with col2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr_v64")
    with col3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="ms_v64")
    if st.button("Generate Master Movie 🚀", key="btn_v64"):
        if m_s:
            v_res = create_safe_movie(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Movie ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

with tab_image:
    st.write("### 🎨 ES AI Image Studio")
    p_img = st.text_area("Describe Image:", key="img_v64")
    if st.button("Generate Image 🚀"):
        if p_img:
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_img)}?width=1024&height=1024&nologo=true&negative=girl,female"
            st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v64.0 | Safety Reset | v40 Engine Fixed | Muhammad Essa Awan</p>", unsafe_allow_html=True)
