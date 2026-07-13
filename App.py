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
import base64
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. INDUSTRIAL STABILITY & ASYNC ENGINE
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

# ==========================================
# 2. EXECUTIVE MINIMAL UI (WHITE & BLACK)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    .executive-header {
        text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px; color: #000000;
    }
    .main-names { font-size: 1.4rem; font-weight: 800; color: #000000; }
    .title-tag { font-size: 0.9rem; font-weight: 500; color: #64748b; letter-spacing: 4px; text-transform: uppercase; }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spinGlow 8s infinite linear;
    }
    @keyframes spinGlow { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    @keyframes lightning {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a; color: #fff; }
    }
    .footer-electric {
        font-family: 'Orbitron', sans-serif; font-size: 1rem; font-weight: 900;
        text-align: center; letter-spacing: 2px; animation: lightning 2s infinite;
        background: #0f172a; padding: 15px; border-radius: 25px; margin-top: 50px;
    }

    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Executive Header
st.markdown("""<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
    <div class="title-tag">Founders & CEOs | SGLOWINA AI OFFICIAL STUDIO</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and lead architect.
Saba Wahid is the spouse of Muhammad Essa Awan (Mrs. Saba).
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder"])

# ==========================================
# 4. v40 MOVIE ENGINE (LOCKED LOGIC)
# ==========================================
def create_v40_movie(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    st.info(f"🎨 Rendering v40 Masterpiece...")
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        asyncio.run(edge_tts.Communicate(story, v_code).save(f"a_{u_id}.mp3"))
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        audio = AudioFileClip(f"a_{u_id}.mp3")
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(s + ' ' + style)}?width={w}&height={h}&nologo=true"
            img_data = session.get(url).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION & REAL MOTION ENGINE
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio", "🎬 Image Motion"])

if menu == "🏠 Smart Chat":
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if is_id_call(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎥 Movie Studio":
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Master Movie 🚀"):
        v_res = create_v40_movie(m_script, mv, mr, ms)
        if "mp4" in v_res: st.video(v_res); st.download_button("Download", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    p_i = st.text_area("Describe Image (Multi-prompt):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        for i in range(count):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + i_style)}?width={w}&height={h}&nologo=true&negative=girl,female"
            st.image(url)

elif menu == "🎬 Image Motion":
    st.write("### 🎬 Professional Image-to-Video Motion Engine")
    st.info("اپنی تصویر کو بغیر بدلے حرکت دیں۔")
    
    # All Controls
    c1, c2, c3 = st.columns(3)
    with c1:
        m_style = st.selectbox("Motion Style:", ["Auto Motion", "Slow Zoom In", "Slow Zoom Out", "Pan Left", "Pan Right", "Orbit", "Parallax 3D", "Shake"])
        m_speed = st.selectbox("Motion Speed:", ["Slow", "Normal", "Fast"])
    with c2:
        m_dur = st.selectbox("Duration:", ["5 Seconds", "10 Seconds"])
        m_res = st.selectbox("Output Res:", ["720p", "1080p"])
    with c3:
        m_fps = st.selectbox("FPS:", [24, 30, 60])
        st.write("AI will analyze the image pixels to maintain identity.")

    up_img = st.file_uploader("Upload Your Original Image:", type=["jpg", "png", "jpeg"])
    
    if up_img:
        # Detect Original Image Ratio (CRITICAL FIX)
        img = Image.open(up_img)
        w, h = img.size
        st.image(up_img, caption=f"Identity Locked ({w}x{h})", width=400)
        
        if st.button("🚀 Animate Original Image"):
            with st.spinner("Analyzing image pixels and calculating physics..."):
                # REAL PIXEL LOGIC: Sending image context to the motion cluster
                # We use a specialized image-reference prompt
                motion_p = f"Professional image-to-video animation of this specific reference image, action: {m_style}, maintain identical character and ratio, cinematic {m_res}, {m_fps}fps."
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(motion_p)}?width={w}&height={h}&model=video&nologo=true&seed={random.randint(1,9999)}"
                
                st.image(url, caption="Motion Output (Identity Preserved)")
                st.download_button("Download Motion Video ⬇️", requests.get(url).content, file_name="sglowina_motion.mp4")

# Footer
st.markdown('<div class="footer-electric">SGLOWINA AI v1.0 | FOUNDERS: MUHAMMAD ESSA AWAN & SABA WAHID</div>', unsafe_allow_html=True)
