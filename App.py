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

# ==========================================
# LOCKED CORE ENGINE - INDUSTRIAL GRADE
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Critical Backend Failure: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM UI & LIGHTNING LOGO (LOCKED)
# ==========================================
st.set_page_config(page_title="ES AI Master SaaS", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Lightning Animation for Name */
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 15px #2563eb, 0 0 30px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 25px #ff007a, 0 0 50px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 10px; animation: lightningGlow 1s infinite;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    
    /* v29 Electric Rotating Logo (Restored) */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .ai-shua {
        width: 120px; height: 120px; 
        background: linear-gradient(135deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 25px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: white;
        box-shadow: 0 0 40px rgba(255, 0, 122, 0.6);
        animation: rotate3D 4s infinite linear, glowPulse 2s infinite ease-in-out;
        border: 4px solid #fff;
    }
    @keyframes rotate3D { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    @keyframes glowPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; box-shadow: 0 0 60px #00d4ff; } }
    
    .main-header { font-size: 2.8rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; text-transform: uppercase; }

    /* Premium Floating Action Icons Style */
    .action-bar { display: flex; justify-content: center; gap: 20px; margin-top: 10px; }
    .icon-btn { font-size: 24px; cursor: pointer; padding: 10px; background: #e2e8f0; border-radius: 50%; transition: 0.3s; }
    .icon-btn:hover { background: #2563EB; color: white; }

    /* Button and Input Scaling */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 15px !important; height: 60px; width: 100%; font-size: 22px; font-weight: 900;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.3);
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        border: 2px solid #e2e8f0 !important; border-radius: 15px !important; padding: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (LOCKED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def is_creator_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 3. LOCKED MOVIE ENGINE (v40 LOGIC)
# ==========================================
def locked_v40_movie_engine(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status_bar = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # v40 Splitting logic
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status_bar.info(f"🏗️ Scene {i+1}/{len(sentences)} building...")
            # Locked v40 Director Call
            director_p = f"Extract core subject from Urdu: '{scene}'. Detailed 3D prompt, no humans unless asked."
            res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(director_p)}?model=openai", timeout=30).text
            
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(res + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            img_data = session.get(img_url, timeout=60).content
            img_path = f"i_{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(img_data)
            
            # Clean and Resize for Stability
            clean_img = Image.open(img_path).convert("RGB").resize((w, h))
            clean_img.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # v40 Zoom 1.2 -> 1.0
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))

        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_MASTER_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Immediate cleanup of images to save RAM
        for i in range(len(sentences)): os.remove(f"i_{u_id}_{i}.jpg")
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. TABS & PROFESSIONAL INTERFACE
# ==========================================
tab1, tab2, tab3 = st.tabs(["💬 Intelligent Chat", "🎬 Pro Movie Studio", "🎨 Image Studio"])

with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    # Premium Interface Icons (Requirement 4)
    st.markdown("""
        <div class="action-bar">
            <div class="icon-btn">➕</div>
            <div class="icon-btn">🎙️</div>
            <div class="icon-btn">⚙️</div>
        </div>
        """, unsafe_allow_html=True)
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab2:
    st.write("### 🎥 Industrial Grade Movie Production")
    m_script = st.text_area("Movie Script:", height=150, key="v62_m")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="v62_mv")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="v62_mr")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="v62_ms")
    if st.button("🚀 Generate Master Movie", key="v62_btn"):
        if m_script:
            video_res = locked_v40_movie_engine(m_script, mv, mr, ms)
            if "mp4" in video_res:
                st.video(video_res)
                st.download_button("Download ⬇️", open(video_res, 'rb').read(), file_name=video_res)

with tab3:
    st.write("### 🎨 Professional Image Surgeon")
    img_p = st.text_area("Describe Image:", key="v62_i")
    if st.button("Generate Image 🚀", key="v62_ibtn"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(img_p)}?width=1024&height=1024&nologo=true&negative=girl,female"
        st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v62.0 | THE IRON ENGINE | LOCKED | Muhammad Essa Awan</p>", unsafe_allow_html=True)
