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
# 2. SGLOWINA OFFICIAL UI (VERSION 1.0 LOCKED)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Premium Version 1.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 6px; color: #fff;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        animation: lightningBorder 2s infinite;
    }
    @keyframes lightningBorder {
        0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
        50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .electric-s {
        width: 110px; height: 110px; background: #0f172a; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
        border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
        animation: rotate3D 6s infinite linear, glowPulse 2s infinite;
    }
    @keyframes rotate3D { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    @keyframes glowPulse { 0%, 100% { box-shadow: 0 0 20px #ff007a; } 50% { box-shadow: 0 0 50px #00d4ff; } }

    .brand-name { font-size: 3.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 3px; text-transform: uppercase; }

    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: white !important; font-weight: bold; }
    
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #e2e8f0 !important; border-radius: 12px !important; color: #0f172a !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI - OFFICIAL PREMIUM RELEASE</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founder & CEO: Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED v1.0 BIO)
# ==========================================
SGLOWINA_BIO = """
مجھے **Sglowina AI** کی ٹیم نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔

ہماری **Founder & CEO صبا واحد** صاحبہ ہیں، جو صوفی محمد انور صاحب (رحمۃ اللہ علیہ) کی بہو، واحد بخش کی صاحبزادی اور **محمد عیسیٰ اعوان** کی اہلیہ ہیں۔

محمد عیسیٰ اعوان صاحب اس پروجیکٹ کے چیف ڈیزائنر ہیں، جو خود ایک مکینیکل انجینئر، فیبرکیٹر اور دینی و اسلامی ماہر ہیں۔ Sglowina AI ایک انڈسٹریل گریڈ پلیٹ فارم ہے جو ان تمام مخلصین کی محنت کا نتیجہ ہے۔ اس سے زیادہ تفصیل ہم آپ کو نہیں بتا سکتے۔
"""

def is_id_call(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"sglowina"])

# ==========================================
# 4. v40 MOVIE ENGINE (PROTECTED)
# ==========================================
def get_v40_prompt(text):
    try:
        instr = f"Act as a Director: '{text}'. Professional 3D animation, symmetrical face, sharp eyes, detailed skin. No humans unless asked. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_v40_movie(story, voice, ratio, style):
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
            with open(img_p, "wb") as f: f.write(session.get(img_url).content)
            Image.open(img_p).convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION (VERSION 1.0 STABLE)
# ==========================================
menu = st.sidebar.radio("SGLOWINA TITAN MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if is_id_call(p): res = SGLOWINA_BIO
        else:
            try:
                sys_p = urllib.parse.quote("You are Sglowina AI, owned by Saba Wahid. Answer only in Urdu.")
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_p}"
                res = requests.get(url, timeout=20).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: res = "Server is busy. Please try again."
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production (v40)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Movie 🚀"):
        v_res = create_v40_movie(m_script, mv, mr, ms)
        if "mp4" in v_res:
            st.video(v_res)
            st.download_button("Download", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglowina Industrial Image Studio (Multi-Prompt Mode)")
    st.info("آپ ایک ساتھ 10 تصویریں بنوا سکتے ہیں۔ ہر تصویر کی تفصیل الگ لائن میں لکھیں۔")
    p_i = st.text_area("Describe up to 10 images (One per line):", height=200, placeholder="Prompt 1\nPrompt 2\nPrompt 3...")
    
    c1, c2 = st.columns(2)
    with c1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"], key="is")
    with c2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD", "TikTok"], key="ir")
    
    if st.button("Generate Masterpieces 🚀"):
        if p_i:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim[i_size]
            
            # Split lines into list and take first 10
            prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()][:10]
            
            for idx, single_p in enumerate(prompt_list):
                with st.spinner(f"Sglowina AI is painting image {idx+1}..."):
                    hd_refined = f"{single_p}, symmetrical face, high quality skin, detailed eyes, 8k"
                    neg_fix = "distorted+face,melted+face,deformed+eyes,low+quality"
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(hd_refined + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative={neg_fix}"
                    st.image(url, caption=f"Prompt {idx+1}: {single_p[:50]}...")
                    st.download_button(f"Download Image {idx+1} ⬇️", requests.get(url).content, file_name=f"sglowina_v1_{idx}.jpg")
        else: st.warning("Please enter at least one prompt.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglowina AI v1.0 | Official Premium Launch | Founder & CEO: Saba Wahid</p>", unsafe_allow_html=True)
