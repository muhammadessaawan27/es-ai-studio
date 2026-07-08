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

# PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI & BRANDING (LOCKED)
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
        text-align: center; letter-spacing: 8px; animation: lightningGlow 1.5s infinite;
        background: #1e293b; padding: 10px; border-radius: 0 0 20px 20px;
    }
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .ai-shua {
        width: 100px; height: 100px; background: linear-gradient(135deg, #ff007a, #2563eb);
        border-radius: 22px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6); animation: rotateShua 6s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotateShua { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    .main-header { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    
    /* Clean Tab Isolation */
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
    
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 50px !important; height: 55px; font-weight: 900;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. ESSA IDENTITY & v40 ENGINE (SECURED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

def get_v40_visual_prompt(urdu_text):
    try:
        instr = f"Extract core subject from Urdu: '{urdu_text}'. Detailed English 3D animation prompt. Accurate animals/objects. No humans unless mentioned."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_v40_movie_engine(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status_container = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        
        for i, scene in enumerate(sentences):
            status_container.info(f"🎬 Scene {i+1}/{len(sentences)} rendering...")
            refined_p = get_v40_visual_prompt(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_data = session.get(img_url, timeout=60).content
            img_path = f"i_{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(img_data)
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24).resize(newsize=(w, h))
            clip = clip.resize(lambda t: 1.2 - 0.2 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V40_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. UI ASSEMBLY (WITH STRICT ISOLATION)
# ==========================================
t_chat, t_movie, t_img = st.tabs(["💬 Chat & Information", "🎬 Movie Studio", "🎨 Image Studio"])

# --- TAB 1: CHAT (Isolated) ---
with t_chat:
    st.write("### 💬 ES AI Smart Chat")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    # Persistent Chat bubbles
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
        
    if p := st.chat_input("Hukum karein Essa bhai...", key="chat_in"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- TAB 2: MOVIE STUDIO (Isolated & Robust) ---
with t_movie:
    st.write("### 🎥 Pro Movie Engine (v40 Power)")
    m_s = st.text_area("Movie Script:", height=150, placeholder="Write your story here...", key="movie_script")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="ms")
    
    if st.button("Generate Master Movie 🚀", key="movie_btn"):
        if m_s:
            v_res = create_v40_movie_engine(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Movie ⬇️", open(v_res, 'rb').read(), file_name=v_res)
                st.success("✅ Movie Delivered!")
            else:
                st.error(f"Render Failed: {v_res}")

# --- TAB 3: IMAGE STUDIO (Isolated) ---
with t_img:
    st.write("### 🎨 ES AI Image Surgeon")
    mode = st.radio("Mode:", ["Text to Image", "Professional Edit"], horizontal=True, key="img_mode")
    if mode == "Text to Image":
        p_img = st.text_area("Describe Image:", key="p_img")
        if st.button("Generate Image 🚀", key="gen_img"):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_img)}?width=1024&height=1024&nologo=true"
            st.image(url)
    else:
        f = st.file_uploader("Upload Image:", type=["jpg", "png"], key="up_img")
        if f:
            st.image(f, width=200)
            edit_p = st.text_input("Change what?", key="edit_p")
            if st.button("Apply Edit 🚀", key="apply_edit"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_p)}?width=1024&height=1024&nologo=true&negative=girl,female"
                st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v58.0 | Isolated Architecture | v40 Engine Fixed | Muhammad Essa Awan</p>", unsafe_allow_html=True)
