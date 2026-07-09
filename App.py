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
# 1. INDUSTRIAL GRID STATION (Hyper-Speed Setup)
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

# Multi-Engine Cluster
CLUSTER = ["openai", "mistral", "llama", "unity", "searchgpt", "hercai"]

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

# ==========================================
# 2. LED GLOW UI (WHITE BASE + RGB EFFECTS)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan Release", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    
    /* LED RGB Border Animation */
    @keyframes ledBorder {
        0% { border-color: #ff007a; box-shadow: 0 0 10px #ff007a; }
        33% { border-color: #00d4ff; box-shadow: 0 0 15px #00d4ff; }
        66% { border-color: #2563eb; box-shadow: 0 0 10px #2563eb; }
        100% { border-color: #ff007a; box-shadow: 0 0 10px #ff007a; }
    }

    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* White Sidebar with LED touch */
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 3px solid #0f172a; 
        box-shadow: 5px 0 15px rgba(0,0,0,0.05);
    }

    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #0f172a; padding: 25px; border-radius: 0 0 40px 40px;
        border: 4px solid #ff007a; animation: ledBorder 4s infinite;
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .electric-s {
        width: 120px; height: 120px; background: #0f172a; border-radius: 30px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 65px; color: white;
        border: 5px solid #ff007a; animation: rotate3D 10s infinite linear, ledBorder 3s infinite;
    }
    @keyframes rotate3D { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }

    .brand-name { font-size: 4rem; font-weight: 900; color: #0f172a; text-align: center; }
    .founder-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: 800; text-transform: uppercase; }

    .stButton>button { 
        background: #0f172a !important; color: white !important; 
        border-radius: 12px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold;
        border: 3px solid #00d4ff; animation: ledBorder 5s infinite;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI - VERSION 1.0 OFFICIAL</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founders & CEOs: Muhammad Essa Awan & Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. TITAN MODULAR MEMORY ENGINE
# ==========================================
if "char_seed" not in st.session_state:
    st.session_state.char_seed = random.randint(1, 999999)

def get_titan_prompt(text):
    try:
        # Instruction for perfect anatomy and body
        anatomy_fix = "Full body visible, perfect hands, detailed face, symmetrical limbs, high quality 3D render."
        instr = f"Director: '{text}'. {anatomy_fix}. Accurate subject. No humans unless mentioned. Output English."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def fetch_img(url):
    return session.get(url, timeout=60).content

def create_titan_movie_v10(story, voice, ratio, style, part_num):
    u_id = f"v10_part{part_num}_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        # Increase scene density (Every sentence or max 15 words)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        img_urls = []
        for s in sentences:
            refined = get_titan_prompt(s)
            # Using session seed for character consistency across parts
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={st.session_state.char_seed}&nologo=true&negative=deformed,missing+body,extra+limbs"
            img_urls.append(url)

        status.info(f"🚀 Sglowina Grid Engine rendering Part {part_num} in parallel...")
        with ThreadPoolExecutor(max_workers=20) as exe:
            images_data = list(exe.map(fetch_img, img_urls))

        for i, img_data in enumerate(images_data):
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Part_{part_num}_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. NAVIGATION & MODULAR TABS
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND CENTER", ["🏠 Smart Chat", "🎬 Modular Movie Studio (10 min)", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina Titan help?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = "Titan Cluster processing..."
        for model in CLUSTER:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model={model}&cache=true"
                res = requests.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
                break
            except: continue
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Modular Movie Studio (10 min)":
    st.write("### 🎥 Modular Film Grid (Long Video Support)")
    st.info("آپ بڑی اسٹوری کو حصوں (Parts) میں بنا سکتے ہیں۔ اے آئی کردار کو یاد رکھے گا۔")
    
    part_number = st.number_input("Part Number:", min_value=1, step=1, value=1)
    if st.button("Start New Story (Reset Character)"):
        st.session_state.char_seed = random.randint(1, 999999)
        st.success("New Character Seed Locked!")

    m_script = st.text_area(f"Enter Story Part {part_number}:", height=150)
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with col2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok (9:16)"])
    with col3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    
    if st.button(f"Generate Part {part_number} 🚀"):
        v_res = create_titan_movie_v10(m_script, mv, mr, ms, part_number)
        if "mp4" in v_res:
            st.video(v_res)
            st.download_button(f"Download Part {part_number} ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    # (Existing Image studio logic here, kept identical but white background)
    st.write("### 🎨 Industrial Image Studio")
    p_i = st.text_area("Describe Image:")
    if st.button("Generate Image 🚀"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1024&height=1024&nologo=true&seed={st.session_state.char_seed}"
        st.image(url)

st.markdown("<p style='text-align:center; color:#ff007a; font-weight:bold; border-top:1px solid #eee; padding-top:20px;'>Sglowina AI Version 1.0 Premium | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
