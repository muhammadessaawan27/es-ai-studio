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
# 1. INDUSTRIAL STABILITY (LOCKED)
# ==========================================
session = requests.Session()
CLUSTER_MODELS = ["openai", "mistral", "llama", "unity"]

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (SGLOWINA BRANDING - LOCKED)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan Release", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.4);
        animation: lightningBorder 2s infinite; margin-top: -10px;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; }
    }
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 70px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 40px #ff007a;
        animation: rotate3D 10s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }
    .brand-name { font-size: clamp(2.5rem, 10vw, 4.2rem); font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .ceo-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; }
    .coo-tag { font-size: 1.1rem; color: #2563eb; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #e2e8f0 !important; border-radius: 12px !important; color: #0f172a !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="ceo-tag">Founder & CEO: Saba Wahid</div>
        <div class="coo-tag">Chief Operations Officer: Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
OFFICIAL_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founder & CEO:** Saba Wahid serves as the Founder & CEO of Sglowina AI.

**Chief Operations Officer (COO):** Muhammad Essa Awan is the COO and the lead visionary responsible for the industrial-grade configuration and logical architecture of this platform.

Sglowina AI is a high-end industrial intelligence platform. This is the official Version 1.0 Premium Release.
"""

def is_identity_request(q):
    p = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"coo", r"maker", r"sglowina"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 4. v40 INDUSTRIAL MOVIE ENGINE (SUBJECT LOCKED)
# ==========================================
def get_titan_prompt(text):
    """
    Enhanced Subject Recognition. 
    Strictly prevents random humans/women in religious or general subjects.
    """
    # Detect if user specifically mentioned women/girls
    human_keywords = ["عورت", "لڑکی", "خاتون", "بیوی", "ماں", "woman", "girl", "female", "lady"]
    is_human_requested = any(k in text.lower() for k in human_keywords)
    
    # Force negative constraint if no human mentioned
    neg_enforce = "" if is_human_requested else ", STRICTLY NO HUMANS, NO FACES, NO WOMEN, NO GIRLS"

    try:
        model = random.choice(CLUSTER_MODELS)
        instr = f"Strict Director Order: Extract visual subject from Urdu: '{text}'. Description must be accurate to history/religion. {neg_enforce}. Highly detailed 3D cinematic. Output ONLY English."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true"
        res = session.get(url, timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_titan_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # Split by line/sentence accurately
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            status.info(f"⚡ Titan Engine Rendering Scene {i+1}/{len(sentences)} (Subject Locked)...")
            refined = get_titan_prompt(s)
            seed = random.randint(1, 999999)
            # Final Safety Negative Prompt
            neg_fix = "girl,female,woman,modern,deformed,blurry"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={seed}&nologo=true&negative={neg_fix}"
            
            img_p = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # Zoom In Expansion (1.0 to 1.15) - LOCKED
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close()
        final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN COMMAND", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_identity_request(p): res = OFFICIAL_BIO
        else:
            for model in MODELS:
                try:
                    url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model={model}&cache=true"
                    res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI")
                    break
                except: continue
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Titan Industrial Production Engine")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio")
    p_i = st.text_area("Describe images (One per line):", height=150)
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate Titan Industrial Visuals 🚀"):
        if p_i:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim[i_size]
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
            for idx, single_p in enumerate(prompt_list):
                for q in range(count):
                    refined = get_titan_prompt(single_p)
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true&negative=girl,female,woman"
                    st.image(url, caption=f"Result {idx+1}")

st.markdown(f"<p style='text-align:center; color:#ff007a; font-weight:bold; border-top:1px solid #eee; padding-top:20px;'>Sglowina AI Version 1.0 Premium Release | Founder & CEO: Saba Wahid | COO: Muhammad Essa Awan</p>", unsafe_allow_html=True)
