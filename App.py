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

# Senior Engineer Fix: Persistent Session
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. INTENSE NEON UI & LIGHTNING EFFECTS
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');

    .stApp {
        background-color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }

    /* Lightning Animation for Name */
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #2563eb, 0 0 40px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a, 0 0 60px #ff007a; color: #fff; }
    }

    .owner-lightning {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.5rem;
        font-weight: 900;
        text-align: center;
        letter-spacing: 8px;
        animation: lightningGlow 1.5s infinite;
        margin-top: 20px;
    }

    /* Intense 3D Rotating Logo */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    
    .ai-shua {
        width: 110px;
        height: 110px;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: white;
        box-shadow: 0 0 50px #ff007a, inset 0 0 20px #ffffff;
        animation: rotateShua 4s infinite linear, pulseGlow 2s infinite;
        border: 5px solid #fff;
    }

    @keyframes rotateShua {
        0% { transform: perspective(1000px) rotateY(0deg) rotateZ(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg) rotateZ(360deg); }
    }

    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 30px #ff007a; }
        50% { box-shadow: 0 0 70px #00d4ff; }
    }

    .main-header {
        font-size: 3rem; font-weight: 900; color: #0f172a; text-align: center;
        text-transform: uppercase; margin-bottom: 20px;
    }

    /* Professional Buttons & Tabs */
    .stButton>button {
        background: linear-gradient(90deg, #ff007a, #2563eb) !important;
        color: white !important; border: none !important; border-radius: 50px !important;
        height: 60px; width: 100%; font-size: 22px; font-weight: 900;
        box-shadow: 0 10px 20px rgba(255, 0, 122, 0.4);
    }
    
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# UI Display
st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="ai-shua">ES</div>
        <div class="main-header">ES AI MASTER STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (THE TRUTH)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔ وہ صوفی محمد انور صاحب کے صاحبزادے، ایک ماہر مکینیکل انجینئر، فیبرکیٹر اور سلسلہ نقشبندیہ اویسیہ کے کارکن ہیں۔
"""

def is_essa_query(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"essa", r"awan"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. PRECISION MOVIE ENGINE v37.0 (STRICT SUBJECT)
# ==========================================
def get_intense_visual_prompt(urdu_text, style):
    # Strict Subject Mapping to avoid hallucinations (e.g. Mermaid vs Lion)
    director_instr = (
        f"Act as a Film Director. Analyze Urdu: '{urdu_text}'. "
        "Identity the EXACT singular subject (Animal, Person, or Object). "
        "Describe it in vivid English. If it's a Mermaid, show ONLY a mermaid in water. "
        "If it's a Lion, show ONLY a lion. Exclude all random humans. 8k, cinematic lighting."
    )
    url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
    try:
        res = session.get(url, timeout=30)
        visual_desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} film style, {visual_desc}, masterpiece, high definition, realistic"
    except: return urdu_text

def create_electric_movie_v37(story, voice_choice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_choice else "ur-PK-AsadNeural"
        audio_path = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_path)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_path)
        
        # Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 2: Scene Generation (Per Sentence)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"⚡ Processing Scene {i+1}...")
            # Precision Prompting
            prompt = get_intense_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            # Image Sanitization
            img = Image.open(img_path).convert("RGB").resize((w, h))
            img.save(img_path, "JPEG")
            
            # Step 3: CINEMATIC ZOOM OUT (1.15 to 1.0)
            # This ensures frame is always full and revealing the scene
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.15 - 0.1 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.5))

        # Step 4: Final Render
        status.info("🔥 Finalizing Electric Masterpiece...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. TABS
# ==========================================
tab1, tab2 = st.tabs(["💬 Electric AI Chat", "🎬 Pro Master Studio"])

with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_essa_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab2:
    st.write("### 🎥 Professional Film Production")
    m_script = st.text_area("Yahan apni story likhein (Har jumlay par tasveer badlay gi):", height=200)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])

    if st.button("🚀 Generate Final Master Video"):
        if m_script:
            with st.spinner("⚡ ES AI is rendering your masterpiece..."):
                video_result = create_electric_movie_v37(m_script, mv, mr, ms)
                if "mp4" in video_result:
                    with open(video_result, 'rb') as vf:
                        st.video(vf.read())
                    st.download_button("Download Full HD ⬇️", open(video_result, 'rb'), file_name=video_result)
                    st.success("✅ Masterpiece Delivered!")
                else: st.error(video_result)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v37.0 | Electric Launch Edition | Muhammad Essa Awan</p>", unsafe_allow_html=True)
