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
# 1. INDUSTRIAL STABILITY & POLICY ENGINE
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
# 2. ISLAMIC KEYWORDS & NEGATIVE PROMPTS
# ==========================================
ISLAMIC_KEYWORDS = [
    "allah", "islam", "muslim", "quran", "hadith", "masjid", "salah", "namaz",
    "qabr", "kafan", "janazah", "barzakh", "jannah", "jahannam", "prophet", 
    "nabi", "rasul", "sahabah", "history", "ولی اللہ", "صحابہ", "قبر", "کفن", "جنازہ"
]

STRICT_NEGATIVE_PROMPT = (
    "western clothes, suit, tie, tuxedo, business man, office, modern city, "
    "random people, jeans, uncovered body, mini skirt, nightclub, western cemetery, "
    "unrelated background, fashion model, european features, modern fashion"
)

# ==========================================
# 3. EXECUTIVE UI & BRANDING (LOCKED)
# ==========================================
st.set_page_config(page_title="Sglovina AI - Official Shariah Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 15px; border-radius: 0 0 40px 40px;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        animation: lightningBorder 2s infinite; margin-top: -10px;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 60px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 35px #ff007a;
        animation: rotate3D 8s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 3.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.1rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }

    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: white !important; font-weight: bold !important; }
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL MASTER STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founder & CEO: Saba Wahid | COO: Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. IDENTITY & POLICY ENGINE (LOCKED)
# ==========================================
SGLOWINA_BIO = """
Sglovina AI is proudly developed by the Sglowina Team.
Founder & CEO: Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan.
Muhammad Essa Awan is the COO and the lead visionary behind the platform's core configuration.
Sglovina AI is a professional high-end industrial intelligence platform.
"""

def detect_islamic_mode(text):
    return any(word in text.lower() for word in ISLAMIC_KEYWORDS)

def get_titan_prompt(text):
    is_islamic = detect_islamic_mode(text)
    
    # Step 5: Face Protection Logic
    revered = ["نبی", "رسول", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah"]
    is_revered = any(k in text for k in revered)
    
    face_protection = ""
    if is_revered:
        face_protection = "STRICTLY NO FACE. NO FACIAL FEATURES. Show bright white divine Noor (light) instead of face. Person shown from behind or silhouette. Extremely respectful."

    try:
        # Step 2 & 6: Historical & Cultural Accuracy
        director_instr = (
            f"Act as a Shariah-Compliant Film Director. Subject: '{text}'. "
            f"{face_protection}. "
            f"Mode: {'Islamic Historical' if is_islamic else 'Modern Cinematic'}. "
            "Requirement: Authentic Muslim cultural appearance, traditional modest clothing, "
            "accurate historical architecture, no modern western elements. Output English prompt."
        )
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

# ==========================================
# 5. v40 INDUSTRIAL MOVIE ENGINE (SAFE)
# ==========================================
def create_titan_movie_v1(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status_box = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
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
            status_box.info(f"🛡️ Policy Check & Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s)
            
            # Step 4: Strict Negative Prompt Application
            is_islamic = detect_islamic_mode(s)
            neg_p = STRICT_NEGATIVE_PROMPT if is_islamic else "deformed, blurry"
            
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={seed}&nologo=true&negative={neg_p}"
            
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            
            with Image.open(img_p) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Zoom In Expansion (LOCKED)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglovina_Official_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close(); final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 6. UI ASSEMBLY
# ==========================================
st.sidebar.markdown(f"<h2 style='color:white; text-align:center;'>SGLOVINA MENU</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navigate Studio:", ["💬 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglovina Intelligence")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglovina AI help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if any(k in p.lower() for k in ["kisne banaya", "who made you", "owner", "saba", "essa"]): res = SGLOWINA_BIO
        else:
            sys_p = urllib.parse.quote("You are Sglovina AI. You strictly follow Islamic values and provide accurate information.")
            url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_p}"
            res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglovina AI").replace("OpenAI", "Sglovina Team")
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Engine (Policy-Protected)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Sglovina Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglovina Pro Image Studio")
    p_i = st.text_area("Describe Image (Islamic rules apply automatically):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Official Image 🚀"):
        for i in range(count):
            refined = get_titan_prompt(p_i)
            is_isl = detect_islamic_mode(p_i)
            neg_final = STRICT_NEGATIVE_PROMPT if is_isl else "girl,female"
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + i_style)}?width=1024&height=1024&nologo=true&negative={neg_final}"
            st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglovina AI v1.2 | Official Shariah-Compliant Release | Admin: Saba Wahid</p>", unsafe_allow_html=True)
