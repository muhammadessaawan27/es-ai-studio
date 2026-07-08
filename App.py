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
# 1. SGLOWNINA BRANDING & LUXURY UI
# ==========================================
st.set_page_config(page_title="Sglownina - Powered by ES AI", layout="wide", page_icon="🎬")

# Pink, Gold and Silver Theme for Sglownina
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    .owner-header {
        font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 900;
        text-align: center; letter-spacing: 3px; color: #ff007a;
        background: #fdf2f8; padding: 10px; border-bottom: 3px solid #ff007a;
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .s-logo {
        width: 130px; height: 130px; 
        background: linear-gradient(135deg, #ff007a, #f472b6);
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        box-shadow: 0 15px 35px rgba(255, 0, 122, 0.3);
        border: 5px solid #fff; animation: float 3s ease-in-out infinite;
    }
    @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    
    .brand-title { font-size: 3rem; font-weight: 900; color: #ff007a; text-align: center; margin-top: 10px; }
    .powered-by { font-size: 1rem; color: #64748b; text-align: center; font-weight: bold; }

    /* Buttons & Inputs */
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #db2777) !important; 
        color: white !important; border-radius: 50px !important; height: 50px; font-weight: bold; border: none;
    }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 50px; padding: 10px; gap: 15px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-header">SGLOWNINA - PRODUCT BY ES AI</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="s-logo">
            <span style="color:white; font-family:'Orbitron'; font-size:45px; font-weight:900;">S</span>
        </div>
        <div class="brand-title">Sglownina</div>
        <div class="powered-by">Powered by Saba Wahid</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (LOCKED)
# ==========================================
SGLOWNINA_BIO = """
مجھے **Sglownina** کی ٹیم نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔ 
ہماری ایڈمن **صبا واحد** صاحبہ ہیں، جو محمد عیسیٰ اعوان کی وائف ہیں اور واحد بخش کی بیٹی ہیں۔ 
اس سے زیادہ تفصیل ہم آپ کو نہیں بتا سکتے۔
"""

def is_sglownina_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"saba wahid", r"sglownina"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 3. v40 MOVIE ENGINE (LOCKED - NO CHANGES)
# ==========================================
session = requests.Session()
def get_v40_prompt(urdu_text):
    try:
        instr = f"Act as a Film Director. Extract core visual from: '{urdu_text}'. Detailed English 3D prompt. No humans unless asked."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_v40_movie_engine(story, voice_gen, ratio, style):
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        clips = []
        dur_per = audio.duration / len(sentences)
        
        for i, s in enumerate(sentences):
            status.info(f"🎬 Scene {i+1}/{len(sentences)} rendering...")
            refined = get_v40_prompt(s)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            img_data = session.get(img_url).content
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(img_data)
            
            clean_im = Image.open(img_p).convert("RGB").resize((w, h))
            clean_im.save(img_p, "JPEG")
            
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglownina_V40_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. IMAGE STUDIO (SURGEON & UNLIMITED RATIOS)
# ==========================================
def image_studio_module():
    st.write("### 🎨 Sglownina Artistic Surgeon")
    mode = st.radio("Chose Mode:", ["Text to Image", "Professional Photo Edit"], horizontal=True)
    
    size_options = {
        "YouTube Thumbnail (16:9)": (1280, 720),
        "YouTube Banner (21:9)": (2560, 1080),
        "TikTok/Reels (9:16)": (720, 1280),
        "Instagram Post (1:1)": (1024, 1024),
        "Facebook Cover": (1200, 444),
        "Profile Pic": (512, 512)
    }

    if mode == "Text to Image":
        p = st.text_area("جو تصویر بنوانی ہے بیان کریں:")
        c1, c2, c3 = st.columns(3)
        with c1: st_sel = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Sketch"], key="i_s")
        with c2: sz_sel = st.selectbox("Size/Ratio:", list(size_options.keys()), key="i_r")
        with c3: num = st.slider("Quantity:", 1, 4, 1)
        
        if st.button("Generate World-Class Images 🚀"):
            w, h = size_options[sz_sel]
            for i in range(num):
                with st.spinner("Sglownina AI is painting..."):
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p + ' ' + st_sel)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female"
                    st.image(url, caption=f"Sglownina Masterpiece {i+1}")

    else:
        st.write("#### 🖼️ Identity-Safe Image Surgeon")
        f = st.file_uploader("تصویر اپ لوڈ کریں:", type=["jpg", "png"])
        if f:
            st.image(f, width=200)
            edit_p = st.text_area("تبدیلی بیان کریں (کپڑے، بیک گراؤنڈ، بال، رنگ):")
            sz_edit = st.selectbox("سائز کیا ہو؟", list(size_options.keys()), key="e_r")
            if st.button("Apply Surgery 🚀"):
                with st.spinner("AI is modifying..."):
                    w, h = size_options[sz_edit]
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_p)}?width={w}&height={h}&nologo=true&negative=girl,female"
                    st.image(url, caption="Modified Result")

# ==========================================
# 5. UI TABS (STRICT ISOLATION)
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Smart Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Admin..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWNINA_BIO if is_sglownina_query(p) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 v40 Cinematic Production")
    m_s = st.text_area("Movie Script:", height=150, key="movie_script")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="ms")
    if st.button("Generate Sglownina Movie 🚀"):
        if m_s:
            v_res = create_v40_movie_engine(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with tab_image:
    image_studio_module()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #ff007a; font-weight: bold;'>Sglownina v70.0 | Product by ES AI | Admin: Saba Wahid</p>", unsafe_allow_html=True)
