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

# Senior Engineer Fix: Persistent Session for stability
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM LIGHT UI & 3D AI CORE LOGO
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@900&display=swap');

    /* Background: Luxury Silver/Light Blue Gradient (Not Black) */
    .stApp {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        color: #0f172a;
        font-family: 'Inter', sans-serif;
    }

    /* 3D Rotating Hexagonal AI Core Logo (Requirement) */
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px 0;
        margin-top: 10px;
    }

    .ai-core {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #2563EB, #FF4B2B);
        clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 38px;
        font-weight: 900;
        color: white;
        box-shadow: 0 10px 30px rgba(37, 99, 235, 0.4);
        animation: rotate3D 6s infinite linear;
        border: 4px solid #ffffff;
    }

    @keyframes rotate3D {
        0% { transform: perspective(1000px) rotateY(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg); }
    }
    
    .owner-title { font-family: 'Orbitron', sans-serif; font-size: 1.2rem; color: #2563eb; letter-spacing: 4px; font-weight: bold; margin-bottom: 5px; }
    .main-header { font-size: 2.5rem; font-weight: 800; color: #1e293b; text-align: center; border-bottom: 3px solid #FF4B2B; padding-bottom: 10px; }

    /* Input Box Visibility (High Contrast) */
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 15px !important;
        font-weight: 500 !important;
    }

    /* Professional Buttons (Orange/Blue) */
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #FF4B2B) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        height: 55px; width: 100%; font-size: 18px; font-weight: bold;
        box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(255, 75, 43, 0.4); }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { background: #cbd5e1; border-radius: 20px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: #1e293b !important; font-weight: bold; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #FF4B2B !important; }
    </style>
    """, unsafe_allow_html=True)

# Logo & Branding Header
st.markdown(f"""
    <div class="logo-container">
        <div class="owner-title">MUHAMMAD ESSA AWAN</div>
        <div class="ai-core">ES</div>
        <div class="main-header">ES AI MASTER STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BIO & IDENTITY (THE PERSISTENT PROMPT)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_essa_query(q):
    patterns = [r"kisne banaya", r"who (made|created) you", r"owner", r"essa", r"awan", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 3. MOVIE ENGINE (FIXING DIVISIBLE BY 2 ERROR)
# ==========================================
def create_master_movie_v36(story, voice_choice, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_choice else "ur-PK-AsadNeural"
        audio_path = f"{u_id}_v.mp3"
        
        status.info("🎙️ آواز کی لہریں تیار ہو رہی ہیں...")
        communicate = edge_tts.Communicate(story, v_code)
        asyncio.run(communicate.save(audio_path))
        
        voice_audio = AudioFileClip(audio_path)
        
        # Dimensions (Ensuring Even Numbers for H.264)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 2: Multi-Scene Recognition
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کا مشاہدہ ہو رہا ہے...")
            # Precision Word Recognition Prompt (v27 Style)
            director_prompt = f"Professional 3D cinematic scene of {scene[:100]}, {style} style, accurate animals or objects, no text, 4k."
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(director_prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            with open(img_path, "wb") as f: f.write(r.content)
            
            # Clean Image
            img_verify = Image.open(img_path).convert("RGB")
            # Force size to even numbers
            img_verify = img_verify.resize((w, h))
            img_verify.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # ZOOM OUT FIX: Starting slightly bigger and shrinking, but keeping dimensions EVEN
            clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Step 3: Final Render
        status.info("⚙️ سنیماٹک رینڈرنگ شروع ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_{u_id}.mp4"
        
        # Critical Fix: Ensuring all dimensions are divisible by 2
        final_video = final_video.resize(newsize=(w, h))
        
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
tab_chat, tab_movie = st.tabs(["💬 Smart AI Chat", "🎬 Pro Movie Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        if is_essa_query(p): res = ESSA_BIO
        else:
            try:
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
            except: res = "Connection slow. Try refreshing."
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 AI Cinematic Production")
    m_script = st.text_area("Yahan apni script likhein (Har jumlay par scene badlay ga):", height=200)
    
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Narrator:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with col2: mr = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])

    if st.button("🚀 Generate Final Master Video"):
        if m_script:
            with st.spinner("Creating your masterpiece..."):
                video_result = create_master_movie_v36(m_script, mv, mr, ms)
                if "mp4" in video_result and os.path.exists(video_result):
                    with open(video_result, 'rb') as vf:
                        v_data = vf.read()
                    st.video(v_data)
                    st.download_button("Download Full HD ⬇️", v_data, file_name=video_result)
                    st.success("✅ Movie Successfully Rendered!")
                else:
                    st.error(video_result)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb;'>ES AI Studio v36.0 | Master Multi-Modal System | Muhammad Essa Awan</p>", unsafe_allow_html=True)
