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

# Senior Engineer Optimization
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED ELECTRIC UI (Metallic Neon)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');
    
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 25px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 45px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 900;
        text-align: center; letter-spacing: 8px; animation: lightningGlow 1.5s infinite;
        background: #1e293b; padding: 10px; border-radius: 0 0 20px 20px;
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .ai-shua {
        width: 110px; height: 110px; background: linear-gradient(135deg, #ff007a, #2563eb);
        border-radius: 22px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6); animation: rotateShua 6s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotateShua { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    
    .main-header { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    
    .stButton>button {
        background: linear-gradient(90deg, #ff007a, #2563eb) !important;
        color: white !important; border-radius: 50px !important; height: 60px; width: 100%; font-size: 22px; font-weight: 900;
    }
    
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; }

    .stTextArea>div>div>textarea { background-color: #ffffff !important; color: #0f172a !important; border: 2px solid #e2e8f0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. CREATOR BIO & v40 SUBJECT LOCKING logic
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def get_v40_visual_prompt(urdu_text, style):
    """Restoring the precise subject locking from Version 40."""
    try:
        instr = f"Act as a Film Director. Extract only the primary visual subject from Urdu: '{urdu_text}'. Describe it in detail in English for a 3D animation. Ensure accuracy of objects/animals/emotions. No humans unless mentioned. Output only the English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} cinematic animation style, {desc}, highly detailed masterpiece, 8k, vibrant lighting"
    except: return urdu_text

# ==========================================
# 3. RESTORED v40 MOVIE ENGINE (With File fix)
# ==========================================
def create_v40_masterpiece_restored(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        # Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 2: Multi-Scene Generation (The v40 logic)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} کی پہچان ہو رہی ہے (v40 Logic Enabled)...")
            refined_p = get_v40_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            img_obj = Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
            img_obj.save(img_path, "JPEG")
            
            # THE ZOOM-OUT FIX (1.4x to 1.0x) - As requested
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.4 - 0.4 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Final Render
        status.info("⚙️ ویڈیو رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V43_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Electric AI Chat", "🎬 Pro Master Studio", "🎨 Image Studio"])

with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if any(k in p.lower() for k in ["kisne", "creator", "essa"]) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Professional Movie Production (v40 Stable Engine)")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=200, key="movie_script_v43")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Awaaz:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["3D Cartoon", "Realistic", "Cinematic"])

    if st.button("🚀 Generate Final Master Video"):
        if m_script:
            with st.spinner("⚡ ES AI is rendering your masterpiece..."):
                video_res = create_v40_masterpiece_restored(m_script, mv, mr, ms)
                if "mp4" in video_res and os.path.exists(video_res):
                    with open(video_res, 'rb') as f:
                        video_bytes = f.read()
                    st.video(video_bytes)
                    st.download_button("Download Video ⬇️", video_bytes, file_name=video_res)
                    st.success("✅ شاہکار تیار ہے!")
                else: st.error(video_res)

with tab_image:
    st.info("Image Studio features are temporarily optimized to ensure Video Engine stability.")
    p_img = st.text_input("Enter Image Prompt:")
    if st.button("Generate Image"):
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_img)}?nologo=true"
        st.image(img_url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v43.0 | v40 Engine Restored | Muhammad Essa Awan</p>", unsafe_allow_html=True)
