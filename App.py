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
# 1. INDUSTRIAL STABILITY & BACKEND
# ==========================================
session = requests.Session()
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (WHITE SIDEBAR + ELECTRIC GLOW)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Version 1.0 Official", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Sidebar: Clean White Style */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: bold !important; }

    /* Electric Lightning Animation */
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a; color: #fff; }
    }

    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
        animation: lightningGlow 2s infinite;
    }
    
    .footer-electric {
        font-family: 'Orbitron', sans-serif; font-size: 1rem; font-weight: 900;
        text-align: center; letter-spacing: 2px; animation: lightningGlow 2s infinite;
        background: #0f172a; padding: 12px; border-radius: 20px; margin-top: 50px;
    }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
        animation: rotate3D 10s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 3.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.1rem; color: #ff007a; text-align: center; font-weight: bold; text-transform: uppercase; }

    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founder & CEO: Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED)
# ==========================================
SGLOWINA_BIO = """
Sglovina AI is proudly developed by the Sglovina Team.
Saba Wahid serves as the Founder & CEO of Sglovina AI.
Muhammad Essa Awan is the Chief Operations Officer (COO) and the visionary behind the platform's core logic.
Sglovina AI is a professional high-end industrial intelligence platform.
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder"])

# ==========================================
# 4. v40 MOVIE ENGINE (LOCKED)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Act as a Director: '{text}'. Professional 3D animation, symmetrical face, sharp eyes. Accurate subjects. No humans unless asked."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)} (v40 Stable)...")
            refined = get_v40_prompt(s)
            neg = "distorted+face,melted+face,deformed+eyes,ugly,blurry,bad+anatomy"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative={neg}"
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(session.get(img_url, timeout=60).content)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. NAVIGATION & PAGES (TRUE ISOLATION)
# ==========================================
st.sidebar.markdown("## ⚙️ SGLOWINA MENU")
page = st.sidebar.radio("Navigate:", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Image Studio"])

if page == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if is_id_call(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team"))
            st.session_state.msgs.append({"role": "assistant", "content": res})

elif page == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (v40 Locked)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Movie 🚀"):
        res = create_titan_movie(m_script, mv, mr, ms)
        if "mp4" in res:
            st.video(res)
            st.download_button("Download Movie ⬇️", open(res, 'rb').read(), file_name=res)

elif page == "🎨 Image Studio":
    st.write("### 🎨 Sglowina Pro Image Studio (Multi-Prompt)")
    st.info("ایک ساتھ 10 تصویریں بنوائیں۔ ہر لائن میں ایک نئی تصویر کی تفصیل لکھیں۔")
    p_i = st.text_area("Describe images (One per line):", height=150, placeholder="Prompt 1\nPrompt 2...")
    
    sz_opts = {
        "Square (1:1)": (1024, 1024), "YouTube HD (16:9)": (1280, 720), 
        "TikTok (9:16)": (720, 1280), "YouTube Banner": (2560, 1080), "Logo Size": (512, 512)
    }
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"], key="is")
    with ic2: i_size = st.selectbox("Resolution:", list(sz_opts.keys()), key="ir")
    with ic3: char_id = st.text_input("Character Lock ID:", placeholder="e.g. 786")

    if st.button("Generate Masterpieces 🚀"):
        if p_i:
            w, h = sz_opts[i_size]
            seed_base = int(char_id) if char_id.isdigit() else random.randint(1,99999)
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
            
            for idx, single_p in enumerate(prompt_list):
                with st.spinner(f"Painting image {idx+1}..."):
                    final_seed = seed_base if char_id.isdigit() else seed_base + idx
                    hd_refined = f"{single_p}, symmetrical face, high quality, sharp eyes, 8k"
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(hd_refined + ' ' + i_style)}?width={w}&height={h}&seed={final_seed}&nologo=true&negative=distorted,melted,girl,female"
                    st.image(url, caption=f"Prompt {idx+1}: {single_p[:40]}...")
                    st.download_button(f"Download {idx+1} ⬇️", requests.get(url).content, file_name=f"sglowina_{idx}.jpg", key=f"dl_{idx}")

# FOOTER
st.markdown('<div class="footer-electric">SGLOWINA AI v1.0 | FOUNDER & CEO: SABA WAHID</div>', unsafe_allow_html=True)
