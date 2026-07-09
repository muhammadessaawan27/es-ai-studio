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
st.set_page_config(page_title="Sglowina AI - Official V1.0 Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Responsive Header Fix */
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 1.8rem); font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        animation: lightningGlow 2s infinite; margin-top: -10px;
    }
    @keyframes lightningGlow {
        0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
    }

    /* Sidebar: Clean White Style */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: bold !important; }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
        animation: rotate3D 10s infinite linear;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: clamp(2rem, 10vw, 4rem); font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.1rem; color: #ff007a; text-align: center; font-weight: bold; text-transform: uppercase; }
    .coo-tag { font-size: 1rem; color: #2563eb; text-align: center; font-weight: bold; text-transform: uppercase; }

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
        <div class="coo-tag">Muhammad Essa Awan — Chief Operations Officer (COO)</div>
        <div class="founder-tag">Saba Wahid — Founder & CEO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founders & Owners:** Muhammad Essa Awan & Saba Wahid.

Saba Wahid is the Founder & CEO of Sglowina AI. She is the daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan (Mrs. Muhammad Essa Awan).

Muhammad Essa Awan is the Co-Founder & Chief Operations Officer (COO), a professional Mechanical Engineer and the lead visionary behind the platform's configuration.

Sglowina AI is a high-end industrial intelligence platform. (Version 1.0).
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"maker"])

# ==========================================
# 4. TITAN PARALLEL ENGINE (v1.0 POWER)
# ==========================================
if "char_seed" not in st.session_state:
    st.session_state.char_seed = random.randint(1, 999999)

def get_titan_prompt(text, style):
    try:
        # Islamic & Content Safety included
        instr = f"Director Instruction: '{text}'. Professional 3D character animation. High detail anatomy. Ensure accurate subject recognition. Seed: {st.session_state.char_seed}. Output English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v1(story, voice, ratio, style, part):
    u_id = f"v1_p{part}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_map = {"Asad (Male)": "ur-PK-AsadNeural", "Salman (Male)": "ur-PK-SalmanNeural", 
                 "Uzma (Female)": "ur-PK-UzmaNeural", "Gul (Female)": "ur-PK-GulNeural"}
        v_code = v_map.get(voice, "ur-PK-AsadNeural")
        
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # Split by sentences (One image per line)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=girl,female,woman,deformed"
            img_urls.append(url)

        # PARALLEL PROCESSING FOR 5G SPEED
        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"⚡ Titan Parallel Engine Rendering Scene {i+1}/{len(sentences)}...")
                img_p = f"i_{u_id}_{i}.jpg"
                with Image.open(io.BytesIO(img_data)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
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
# 5. NAVIGATION & ISOLATION
# ==========================================
st.sidebar.markdown(f"## ⚙️ SGLOWINA NAVIGATION")
page = st.sidebar.radio("Go To:", ["🏠 Smart Chat", "🎬 Movie Studio (Modular)", "🎨 Pro Image Studio"])

if page == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligent Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        avatar = "https://via.placeholder.com/50/0f172a/ffffff?text=S" if m["role"]=="assistant" else None
        with st.chat_message(m["role"], avatar=avatar):
            st.write(m["content"])
    
    if p := st.chat_input("How can Sglowina AI help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        with st.spinner("Sglowina AI searching and analyzing..."):
            if is_id_call(p): res = SGLOWINA_BIO
            else:
                sys_instr = urllib.parse.quote("You are Sglowina AI. Founders: Muhammad Essa Awan and Saba Wahid. Answer 100% accurately.")
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_instr}"
                res = requests.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            
            with st.chat_message("assistant", avatar="https://via.placeholder.com/50/0f172a/ffffff?text=S"):
                st.write(res)
                st.session_state.msgs.append({"role": "assistant", "content": res})

elif page == "🎬 Movie Studio (Modular)":
    st.write("### 🎥 Industrial Cinematic Engine (10 min support)")
    part_num = st.number_input("Part Number:", min_value=1, step=1, value=1)
    if st.button("Start New Project (Reset Character)"):
        st.session_state.char_seed = random.randint(1, 999999)
        st.success("New Character Identity Locked!")

    m_script = st.text_area(f"Enter Script for Part {part_num}:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Asad (Male)", "Salman (Male)", "Uzma (Female)", "Gul (Female)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button("Generate Master Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms, part_num)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif page == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Pro Image Studio")
    p_i = st.text_area("Describe Image (One per line for batch):", height=150)
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720)}
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                with st.spinner(f"Rendering image..."):
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(single_p + ' ' + i_style)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=girl,female"
                    st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglowina AI v1.0 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
