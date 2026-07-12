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

# ==========================================
# 2. SGLOWINA POLICY-DRIVEN UI
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Launch", layout="wide", page_icon="🎬")

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

    .brand-name { font-size: 4rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .founder-tag { font-size: 1.2rem; color: #ff007a; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; }

    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: white !important; font-weight: bold !important; }
    
    .stButton>button { 
        background: linear-gradient(90deg, #ff007a, #2563eb) !important; 
        color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 22px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="logo-container">
        <div class="electric-s">S</div>
        <div class="brand-name">Sglowina AI</div>
        <div class="founder-tag">Founder & CEO: Saba Wahid | COO: Muhammad Essa Awan</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. POLICY ENFORCEMENT ENGINE (LOCKED)
# ==========================================
def apply_shariah_policy(text):
    text_lower = text.lower()
    policy_addons = ""
    
    # 1. Prophets & Sahaba Protection
    revered_keywords = ["نبی", "رسول", "صحابی", "ولی اللہ", "امام", "پیمبر", "Prophet", "Sahaba", "Ahl-e-Bayt", "Wali Allah"]
    if any(k in text for k in revered_keywords):
        policy_addons += ", NO VISIBLE FACE, face hidden, person shown from behind or silhouette, respectful distance, symbolic representation, bright white glowing atmosphere"

    # 2. Islamic Appearance & Clothing
    islamic_context = ["اسلام", "مسلمان", "تاریخ", "جنت", "دوزخ", "Muslim", "Islamic", "History"]
    if any(k in text for k in islamic_context) or any(k in text for k in revered_keywords):
        policy_addons += ", modest Islamic clothing, traditional Muslim robes, turbans for men, modest hijab for women, historically accurate attire, strictly no western suits"

    # 3. Environment (Grave / Historical)
    if any(k in text_lower for k in ["قبر", "دفن", "برزخ", "grave", "burial", "death"]):
        policy_addons += ", respectful Islamic graveyard, simple soil grave, traditional burial shroud kafan, atmospheric accountability, no gore"

    return policy_addons

def get_titan_prompt(text):
    policy_filter = apply_shariah_policy(text)
    try:
        # GPT-4 Director ensures the policy is translated into the prompt
        instr = (f"Act as an Islamic Film Director. Analyze Urdu: '{text}'. "
                 f"Requirement: {policy_filter}. Describe the core scene in English for 3D animation. "
                 "Prioritize modest clothing and historical authenticity. Output ONLY English prompt.")
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

# ==========================================
# 4. v40 INDUSTRIAL MOVIE ENGINE (LOCKED)
# ==========================================
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
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        seed = random.randint(1, 999999)

        for i, s in enumerate(sentences):
            status.info(f"⚡ Policy Check & Rendering Scene {i+1}/{len(sentences)}...")
            refined = get_titan_prompt(s)
            
            # Combine Policy + User Style
            final_p = f"{refined} {style} cinematic animation style, highly detailed 8k"
            
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_p)}?width={w}&height={h}&seed={seed}&nologo=true&negative=modern+western+clothes,man+in+suit,revealing+clothes,deformed"
            
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(session.get(img_url, timeout=60).content)) as im:
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
# 5. UI NAVIGATION
# ==========================================
menu = st.sidebar.radio("SGLOVINA COMMAND MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglovina Intelligent Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can Sglovina Titan help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # Policy-Aware Chat Response
        sys_instr = urllib.parse.quote("You are Sglovina AI. You strictly follow Islamic values. Answer accurately in the user's language.")
        url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_instr}"
        res = session.get(url, timeout=20).text.replace("ChatGPT", "Sglovina AI").replace("OpenAI", "Sglovina Team")
        
        with st.chat_message("assistant"):
            st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Official Cinematic Studio (Policy Applied)")
    m_script = st.text_area("Enter Movie Script:", height=150)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male", "Urdu Female"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    if st.button("Generate Official Titan Movie 🚀"):
        if m_script:
            v_res = create_titan_movie_v1(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download Full HD ⬇️", open(v_res, 'rb').read(), file_name=v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Sglovina Industrial Visual Studio (Policy Applied)")
    p_i = st.text_area("Describe Image (One per line):")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"], key="is")
    with ic2: i_size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"], key="ir")
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    if st.button("Generate Titan Visuals 🚀"):
        for i in range(count):
            refined = get_titan_prompt(p_i)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined + ' ' + i_style)}?width=1024&height=1024&nologo=true&negative=girl,female,woman,revealing,modern+suit"
            st.image(url)

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #64748b;'>Sglovina AI Version 1.0 Premium Release | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
