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
# 1. INDUSTRIAL GRID STATION (Hyper-Speed)
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
# 2. LED RGB UI & PROFESSIONAL BRANDING
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Launch", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    /* Global LED RGB Glow */
    @keyframes ledPulse {
        0% { border-color: #ff007a; box-shadow: 0 0 15px #ff007a; }
        50% { border-color: #00d4ff; box-shadow: 0 0 25px #00d4ff; }
        100% { border-color: #ff007a; box-shadow: 0 0 15px #ff007a; }
    }

    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Header with Electric Animation */
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 25px; border-radius: 0 0 50px 50px;
        border: 4px solid #ff007a; animation: ledPulse 3s infinite;
    }

    /* Sidebar - Large Icons */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 2px solid #e2e8f0; }
    [data-testid="stSidebar"] * { font-size: 1.2rem !important; font-weight: bold !important; color: #0f172a !important; }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 120px; height: 120px; background: #0f172a; border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 70px; color: white;
        border: 5px solid #ff007a; animation: rotate3D 10s infinite linear, ledPulse 2s infinite;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 4.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .footer-electric {
        font-family: 'Orbitron', sans-serif; font-size: 1.1rem; font-weight: 900;
        text-align: center; letter-spacing: 2px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 30px; margin-top: 50px;
        border: 3px solid #00d4ff; animation: ledPulse 4s infinite;
    }
    
    /* Button Customization */
    .stButton>button { 
        background: #0f172a !important; color: white !important; border-radius: 15px !important; 
        height: 60px; width: 100%; font-size: 22px; font-weight: bold; border: 3px solid #ff007a;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI - VERSION 1.0 OFFICIAL</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div style="text-align:center; font-weight:bold; color:#ff007a; font-size:1.3rem;">Founder & CEO: صبا واحد | COO: Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (CEO & COO BIO)
# ==========================================
OFFICIAL_BIO = """
مجھے **Sglowina AI** کی ٹیم نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔

ہماری **Founder & CEO صبا واحد** صاحبہ ہیں، جو واحد بخش کی صاحبزادی اور **محمد عیسیٰ اعوان** کی اہلیہ (Mrs. Muhammad Essa Awan) ہیں۔

محمد عیسیٰ اعوان اس پروجیکٹ کے **Chief Operations Officer (COO)** اور لیڈ وژنری ہیں، جو خود ایک مکینیکل انجینئر، فیبرکیٹر اور دینی و اسلامی شعبہ جات کے ماہر ہیں۔ 

Sglowina AI ایک انڈسٹریل گریڈ انٹیلیجنس پلیٹ فارم ہے جو ان مخلصین کی محنت کا نتیجہ ہے۔
"""

def is_identity_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"maker"])

# ==========================================
# 4. TITAN PARALLEL ENGINE (SCENE PER LINE)
# ==========================================
if "char_seed" not in st.session_state:
    st.session_state.char_seed = random.randint(1, 999999)

def get_titan_prompt(text):
    holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "رسول", "Prophet", "Sahaba"]
    is_holy = any(k in text for k in holy_keywords)
    noor_instr = "STRICTLY NO FACE. Show a glowing divine white light (Noor) over the person. Respectful Islamic atmosphere." if is_holy else "Symmetrical professional 3D character animation."
    
    try:
        instr = f"Director Order: Urdu '{text}'. {noor_instr}. Full body, 8k render, seed {st.session_state.char_seed}. Output English."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style, part_num):
    u_id = f"v1_p{part_num}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        # Voice Mapping
        v_map = {"Asad (Male)": "ur-PK-AsadNeural", "Salman (Male)": "ur-PK-SalmanNeural", 
                 "Uzma (Female)": "ur-PK-UzmaNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_map.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # ONE IMAGE PER LINE / SENTENCE
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=girl,female,deformed"
            img_urls.append(url)

        status.info(f"🚀 Sglowina Parallel Grid rendering {len(sentences)} scenes...")
        with ThreadPoolExecutor(max_workers=20) as exe:
            images_data = list(exe.map(fetch_img, img_urls))

        for i, img_data in enumerate(images_data):
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # REAL MOTION: Zoom + Panning
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position(lambda t: (0.05 * t, 'center'))
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_V1_{part_num}_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. NAVIGATION & SMART TABS
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND", ["💬 Smart Chat & Stories", "🎬 Modular Movie Studio", "🎨 Pro Image Studio"])

if menu == "💬 Smart Chat & Stories":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/ff007a/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar):
            st.write(m["content"])
            if m["role"] == "assistant":
                st.button("📋 Copy Text", key=str(uuid.uuid4()))

    if p := st.chat_input("Ask about Stories, Quran, Hadith, or Python Code..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        with st.spinner("Sglowina AI analyzing sources..."):
            if is_identity_call(p): res = OFFICIAL_BIO
            else:
                # High-intelligence query logic
                sys_p = urllib.parse.quote("You are Sglowina AI. Give 100% accurate Islamic answers and Senior Python coding help. Language: Urdu.")
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_p}"
                res = requests.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            
            with st.chat_message("assistant", avatar="https://via.placeholder.com/50/ff007a/ffffff?text=S"):
                st.write(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Modular Movie Studio":
    st.write("### 🎥 Industrial Modular Film Grid")
    part_num = st.number_input("حصہ نمبر (Part Number):", min_value=1, step=1, value=1)
    if st.button("Reset Character for New Story"):
        st.session_state.char_seed = random.randint(1, 999999)
        st.success("New Character Identity Locked!")

    m_script = st.text_area(f"Enter Story Part {part_num}:", height=200)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Select Voice:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button(f"Generate Part {part_num} 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, part_num)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio")
    p_i = st.text_area("Describe images (One per line):")
    if st.button("Generate Titan Visuals 🚀"):
        refined = get_titan_prompt(p_i)
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width=1024&height=1024&nologo=true&seed={st.session_state.char_seed}"
        st.image(url, caption=f"ID: {st.session_state.char_seed}")

st.markdown('<div class="footer-electric">SGLOWINA AI v1.0 | FOUNDERS: MUHAMMAD ESSA AWAN & صبا واحد</div>', unsafe_allow_html=True)
