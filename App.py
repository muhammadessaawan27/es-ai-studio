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
except Exception as e:
    st.error("Engine Load Error. Please Reboot.")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. SGLOWINA OFFICIAL UI (ELECTRIC BRANDING)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Founder Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 8px; color: #fff;
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
        animation: rotate3D 8s infinite linear, glowPulse 2s infinite;
    }
    @keyframes rotate3D { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    @keyframes glowPulse { 0%, 100% { box-shadow: 0 0 20px #ff007a; } 50% { box-shadow: 0 0 50px #00d4ff; } }

    .brand-name { font-size: 3.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: bold; letter-spacing: 3px; text-transform: uppercase; }

    .stTabs [data-baseweb="tab-list"] { background-color: #1e293b; padding: 10px; border-radius: 50px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 15px; font-weight: bold; }
    
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; border: 2px solid #e2e8f0 !important; border-radius: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown("""
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
**Sglowina AI is proudly developed by the Sglowina Team.**

**Founder & CEO:** Saba Wahid, daughter of Wahid Bakhsh and the spouse of Muhammad Essa.

Sglowina AI is a professional high-end industrial intelligence platform.
"""

def check_identity_v14(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo", r"sglowina"])

# ==========================================
# 4. v40 PRECISION ENGINE (RE-LOCKED)
# ==========================================
def get_v40_director_prompt(text):
    """The successful precision logic from v40."""
    try:
        instr = f"Direct Command: Extract the main visual subject from: '{text}'. Describe it in detail for a 3D animation. Ensure 100% accuracy of animals and objects. NO HUMANS unless requested. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

def create_stable_movie_v14(story, voice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
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
        for i, s in enumerate(sentences):
            status.info(f"🎨 Sglowina AI Rendering Scene {i+1}/{len(sentences)} (v40 Precision)...")
            refined = get_v40_director_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,woman,human"
            
            # --- IMAGE DOWNLOAD & VERIFICATION (Fix for 'cannot identify image') ---
            img_p = f"i_{u_id}_{i}.jpg"
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_p, "wb") as f: f.write(r.content)
                # Cleanup and Verify with PIL
                with Image.open(img_p) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # v40 Zoom 1.2 to 1.0
                clip = clip.resize(lambda t: 1.2 - 0.2 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        audio.close()
        final_video.close()
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI TABS (TRUE ISOLATION)
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 SMART CHAT", "🎥 MOVIE STUDIO", "🎨 IMAGE STUDIO"])

with tab_chat:
    st.write("### 💬 Sglowina Intelligence Assistant")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglowina AI help you?"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if check_identity_v14(p): res = SGLOWINA_BIO
        else:
            sys_instr = urllib.parse.quote("You are Sglowina AI, founded by Saba Wahid. Admin is Saba Wahid. Answer professionally and only in Urdu/English.")
            url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_instr}"
            res = requests.get(url, timeout=30).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Official Cinematic Movie Studio")
    m_script = st.text_area("Enter Movie Script:", height=150, key="v14_movie")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"], key="v14_v")
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="v14_r")
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"], key="v14_s")
    if st.button("Generate Master Movie 🚀", key="v14_btn"):
        if m_script:
            res = create_stable_movie_v14(m_script, mv, mr, ms)
            if "mp4" in res:
                st.video(res)
                st.download_button("Download ⬇️", open(res, 'rb').read(), file_name=res)
            else: st.error(res)

with tab_image:
    st.write("### 🎨 Sglowina Pro-Visual Image Studio")
    img_p = st.text_area("Describe Image/Logo:", key="v14_img_p")
    ratio_opts = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok/Reel": (720, 1280), "YouTube Banner": (2560, 1080)}
    ic1, ic2 = st.columns(2)
    with ic1: is_img = st.selectbox("Style:", ["Realistic", "Logo Concept", "Anime", "Sketch"], key="v14_is")
    with ic2: ir_img = st.selectbox("Size:", list(ratio_opts.keys()), key="v14_ir")
    
    if st.button("Generate HD Image 🚀", key="v14_img_btn"):
        if img_p:
            w, h = ratio_opts[ir_img]
            with st.spinner("Sglowina AI is painting..."):
                # RESTORING v40 PRECISION FOR IMAGE STUDIO
                refined_img_p = get_v40_director_prompt(img_p)
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_img_p + ' ' + is_img)}?width={w}&height={h}&nologo=true&negative=girl,female"
                st.image(url)
                st.download_button("Download ⬇️", requests.get(url).content, file_name="sglowina_hd.jpg")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglowina AI v1.4 | Founder & CEO: Saba Wahid | v40 Precision Restored</p>", unsafe_allow_html=True)
