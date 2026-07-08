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

# Senior Engineer Optimization
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED ELECTRIC UI (NO CHANGES TO DESIGN)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');

    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }

    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #2563eb, 0 0 40px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a, 0 0 60px #ff007a; color: #fff; }
    }

    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 900;
        text-align: center; letter-spacing: 8px; animation: lightningGlow 1.5s infinite; margin-top: 20px;
    }

    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    
    .ai-shua {
        width: 110px; height: 110px; background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: white;
        box-shadow: 0 0 50px #ff007a, inset 0 0 20px #ffffff;
        animation: rotateShua 4s infinite linear, pulseGlow 2s infinite; border: 5px solid #fff;
    }

    @keyframes rotateShua {
        0% { transform: perspective(1000px) rotateY(0deg) rotateZ(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg) rotateZ(360deg); }
    }

    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 30px #ff007a; }
        50% { box-shadow: 0 0 70px #00d4ff; }
    }

    .main-header { font-size: 3rem; font-weight: 900; color: #0f172a; text-align: center; text-transform: uppercase; margin-bottom: 20px; }

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

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown("""
    <div class="logo-container">
        <div class="ai-shua">ES</div>
        <div class="main-header">ES AI MASTER STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FIXED IDENTITY DATA
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_essa_identity(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa", r"maker", r"developer"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. MOVIE ENGINE (v38 BULLETPROOF FIX)
# ==========================================
def create_masterpiece_v38(story, voice_choice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_choice else "ur-PK-AsadNeural"
        audio_file = f"audio_{u_id}.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)
        
        # Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 2: Multi-Scene
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} کی تخلیق ہو رہی ہے...")
            director_prompt = f"Professional cinematic, {scene[:100]}, {style} style, masterpiece, highly detailed, no text."
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(director_prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            
            img_path = f"img_{u_id}_{i}.jpg"
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            # Sanitization & Dimension Fix (Divisible by 2)
            img_fix = Image.open(img_path).convert("RGB").resize((w if w%2==0 else w+1, h if h%2==0 else h+1))
            img_fix.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # Zoom Out (1.15 to 1.0)
            clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Step 3: High-Stability Render
        status.info("🔥 فائنل مووی رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_MASTER_{u_id}.mp4"
        
        # Standard encoding with yuv420p for universal play
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
tab_chat, tab_movie = st.tabs(["💬 Electric AI Chat", "🎬 Pro Master Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # MANDATORY IDENTITY CHECK (API OVERRIDE)
        if check_essa_identity(p):
            res = ESSA_BIO
        else:
            try:
                # Add Strict Identity Instruction to the API
                sys_role = urllib.parse.quote(f"You are ES AI, a professional agent created by Muhammad Essa Awan. Answer only in Urdu. Current User: {p}")
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system={sys_role}"
                res = session.get(url, timeout=30).text
            except: res = "کنکشن سست ہے، براہ کرم ایک بار ریفریش کریں۔"
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Professional Film Production")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=200, placeholder="Example: Aik hathi aur sher dunya ki sair par nikle...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Awaaz:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])

    if st.button("🚀 Generate Final Master Video"):
        if m_script:
            with st.spinner("⚡ ES AI is creating magic..."):
                video_res = create_masterpiece_v38(m_script, mv, mr, ms)
                if "mp4" in video_res:
                    with open(video_res, 'rb') as f:
                        st.video(f.read())
                    st.download_button("Download Full HD ⬇️", open(video_res, 'rb'), file_name=video_res)
                    st.success("✅ شاہکار تیار ہے!")
                else: st.error(video_res)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v38.0 | Official Production Edition | Muhammad Essa Awan</p>", unsafe_allow_html=True)
