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

# Senior Engineer Fix: Persistent Session with Optimized Retries
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
session.mount('https://', adapter)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & IDENTITY (MUHAMMAD ESSA AWAN)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 80px; font-weight: 900;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 55px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"awan", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 2. FAIL-SAFE IMAGE DOWNLOADER
# ==========================================
def download_and_clean_image(url, path):
    for attempt in range(3):
        try:
            r = session.get(url, timeout=90)
            if r.status_code == 200:
                with open(path, "wb") as f: f.write(r.content)
                # Verify and Sanitize Image
                img = Image.open(path).convert("RGB")
                img.save(path, "JPEG", quality=95)
                return True
        except:
            time.sleep(2)
    return False

# ==========================================
# 3. ADVANCED MOVIE ENGINE v26.0 (PLAYBACK FIX)
# ==========================================
def create_bulletproof_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    
    try:
        # Step 1: Secure Voice
        status.info("🎙️ آواز تیار کی جا رہی ہے...")
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Set Strict Even Dimensions (Required by Ffmpeg)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        # Step 4: Robust Scene Generation
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی تصویر بن رہی ہے...")
            prompt = f"{style} style, {scene[:100]}, highly detailed, cinematic 4k, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            if download_and_clean_image(img_url, img_path):
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # Cinematic Zoom Out Fix
                clip = clip.resize(lambda t: 1.1 - 0.06 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))
            else:
                continue

        if not clips: raise ValueError("تصویریں ڈاؤن لوڈ نہیں ہوسکیں۔ انٹرنیٹ چیک کریں۔")

        # Step 5: Final Rendering with Mobile-Friendly Encoding
        status.info("⚙️ فائنل رینڈرنگ (Mobile-Friendly Mode)...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Movie_{u_id}.mp4"
        
        # KEY FIX: pix_fmt="yuv420p" allows video to play on ALL devices
        final_video.write_videofile(
            out_name, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            preset="medium", 
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        
        # Cleanup
        for i in range(len(sentences)):
            p = f"{u_id}_{i}.jpg"
            if os.path.exists(p): os.remove(p)
        
        status.success("✅ ویڈیو پلے ہونے کے لیے تیار ہے!")
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>PROFESSIONAL CINEMATIC STUDIO</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Chat", "🎙️ Voice", "🎬 Pro Movie Studio"])

with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab3:
    st.header("🎬 Pro Movie Studio v26.0")
    m_script = st.text_area("کہانی یہاں لکھیں:", height=150)
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Final Playable Video"):
        if m_script:
            video = create_bulletproof_movie(m_script, mv, mr, ms)
            if "mp4" in video:
                st.video(video)
                with open(video, "rb") as f: st.download_button("Download Full HD", f, file_name=video)
            else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v26.0 | Playback & Color Fixed | Muhammad Essa Awan</p>", unsafe_allow_html=True)
