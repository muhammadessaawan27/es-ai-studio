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
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. INDUSTRIAL STABILITY & BACKEND
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

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (LOCKED - NO CHANGES)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.0 Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    .executive-header { text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px; }
    .main-names { font-size: 1.4rem; font-weight: 800; color: #000000; }
    .title-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 3px; text-transform: uppercase; }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 20px #00d4ff, inset 0 0 15px #ff007a;
        animation: spin 8s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    .stButton>button { background: #000000 !important; color: #ffffff !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input { background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 12px !important; color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
    <div class="title-tag">Founders & CEOs | SGLOWINA AI OFFICIAL STUDIO</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY & ISLAMIC RULES (LOCKED)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead visionary.
Official Version 1.0 Premium Release.
"""

def apply_islamic_visual_rules(text):
    """Internal Logic to enforce your 11 rules and Islamic policy."""
    holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "رسول", "Prophet", "Sahaba", "Ahl-e-Bayt", "Wali Allah", "Saint"]
    is_holy = any(k in text for k in holy_keywords)
    
    death_keywords = ["قبر", "کفن", "جنازہ", "مرنے", "grave", "kafan", "shroud", "burial", "death"]
    is_death_story = any(k in text for k in death_keywords)
    
    addon = ""
    # Face Protection (Noorani Light)
    if is_holy:
        addon += ", STRICTLY NO FACE, NO FACIAL FEATURES, person shown with bright white Noorani light, back view only, extremely respectful"
    
    # Grave & Afterlife Logic
    if is_death_story:
        addon += ", traditional Islamic soil grave, white burial shroud (kafan), snakes if mentioned in script, darkness of the grave, atmospheric accountability"
        
    # General Islamic Appearance (No Western Suits)
    if any(k in text for k in ["مسلم", "اسلام", "تاریخ", "Muslim", "Islamic"]) or is_holy:
        addon += ", traditional modest Muslim clothing, robes and turbans, no western suits, no ties, no modern european fashion, historical middle eastern environment"
        
    return addon

def get_v40_prompt(text, style):
    policy_addon = apply_islamic_visual_rules(text)
    try:
        instr = f"Act as a Director: '{text}'. {policy_addon}. 3D character animation, high detail. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url): return session.get(url, timeout=60).content

# ==========================================
# 4. v40 TITAN MOVIE ENGINE (SAFE & LOCKED)
# ==========================================
def create_titan_movie_v1(story, voice, ratio, style, part):
    u_id = f"v1_p{part}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_codes = {"Asad (Male)": "ur-PK-AsadNeural", "Uzma (Female)": "ur-PK-UzmaNeural"}
        v_code = v_codes.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        seed = random.randint(1, 999999)

        for i, s in enumerate(sentences):
            status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)} (Policy Checked)...")
            refined = get_v40_prompt(s, style)
            
            # Additional Negative prompt to ensure no western/suit
            neg = "girl,female,deformed,western+suit,tie,business+man" if "نور" in refined or "Muslim" in refined else "girl,female,deformed"
            
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative={neg}"
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Zoom In Expansion (1.0 to 1.15)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND CENTER", ["🏠 Smart Chat", "🎥 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/000000/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]): res = SGLOWINA_BIO
        else:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true"
            res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎥 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, 1)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image (Islamic rules apply automatically):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        for i in range(count):
            refined = get_v40_prompt(p_i, i_style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width=1024&height=1024&nologo=true&negative=girl,female,woman,revealing"
            st.image(url)

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.0 Premium Release | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
