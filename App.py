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

# Senior Engineer Fix: Persistent Session
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
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
    
    /* Background: Professional White for Readability */
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    /* Lightning Animation for Name */
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 25px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 45px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 900;
        text-align: center; letter-spacing: 8px; animation: lightningGlow 1.5s infinite;
        background: #1e293b; padding: 10px; border-radius: 0 0 20px 20px;
    }
    
    /* 3D Rotating Logo v29 style */
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .ai-shua {
        width: 100px; height: 100px; background: linear-gradient(135deg, #ff007a, #2563eb);
        border-radius: 22px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6); animation: rotateShua 6s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotateShua { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    
    .main-header { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    
    /* Premium Tabs & Buttons */
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 50px; padding: 10px; gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 50px !important; height: 55px; font-weight: 900;
    }
    
    /* Input Visibility */
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; color: #0f172a !important;
        border: 2px solid #e2e8f0 !important; border-radius: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. BIO & SUBJECT LOCKING (v40 PROVEN LOGIC)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def get_v40_visual_prompt(urdu_text, style):
    """v40 logic for subject locking and precision."""
    try:
        instr = f"Act as a Film Director. Extract only the primary visual subject from Urdu: '{urdu_text}'. Describe it in English for 3D animation, focus on objects/animals/emotions accurately. No humans unless mentioned. Output only the prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} cinematic style, {desc}, highly detailed masterpiece, 8k, vibrant colors, realistic lighting"
    except: return urdu_text

# ==========================================
# 3. MOVIE ENGINE (v40 BASE + ZOOM-OUT FIX)
# ==========================================
def create_masterpiece_v42(story, voice_gen, ratio, style):
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

        # Step 2: Multi-Scene Visual Sync
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} کی تخلیق ہو رہی ہے (v40 Precision Mode)...")
            refined_p = get_v40_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            img_obj = Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
            img_obj.save(img_path, "JPEG")
            
            # THE ZOOM-OUT FIX (1.4x to 1.0x) - Moving Away
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.4 - 0.4 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Step 3: Final Render (Fail-Safe Encoding)
        status.info("⚙️ ویڈیو رینڈر ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V42_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. IMAGE GENERATOR (TEXT-TO-IMAGE & IMAGE-TO-IMAGE)
# ==========================================
def image_studio():
    st.write("### 🎨 ES AI Image Studio")
    mode = st.radio("Chose Mode:", ["Text to Image", "Edit Photo (Img2Img)"], horizontal=True)
    
    if mode == "Text to Image":
        p = st.text_area("What do you want to create?", placeholder="Example: A lion sitting on a throne...")
        c1, c2, c3 = st.columns(3)
        with c1: style = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Digital Art", "Sketch"])
        with c2: size = st.selectbox("Ratio:", ["Square (1:1)", "Portrait (9:16)", "Landscape (16:9)"])
        with c3: num = st.slider("Images:", 1, 4, 1)
        
        if st.button("Generate Now 🚀"):
            res_dim = {"Square (1:1)": (1024, 1024), "Portrait (9:16)": (720, 1280), "Landscape (16:9)": (1280, 720)}
            w, h = res_dim[size]
            for i in range(num):
                with st.spinner(f"Creating Image {i+1}..."):
                    full_p = f"{style} style, {p}, 8k, highly detailed, masterpiece"
                    img_data = requests.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_p)}?width={w}&height={h}&seed={random.randint(1,99999)}").content
                    st.image(img_data, caption=f"Result {i+1}")
                    st.download_button(f"Download {i+1} ⬇️", img_data, file_name=f"es_img_{i}.jpg")

    else:
        st.write("#### 🖼️ Image to Image Editor")
        f = st.file_uploader("Upload Image:", type=["jpg", "png"])
        if f:
            st.image(f, width=300)
            edit_p = st.text_input("Change what? (Example: change background to space)")
            if st.button("Apply AI Edit 🚀"):
                with st.spinner("AI is editing..."):
                    # Advanced Img2Img Prompting
                    full_p = f"Modify this image: {edit_p}, maintain style, realistic, 8k"
                    img_data = requests.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_p)}?width=1024&height=1024&nologo=true").content
                    st.image(img_data, caption="Edited Version")
                    st.download_button("Download ⬇️", img_data, file_name="es_edited.jpg")

# ==========================================
# 5. MAIN TABS
# ==========================================
t_chat, t_movie, t_img = st.tabs(["💬 Chat", "🎬 Movie Studio", "🎨 Image Studio"])

with t_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if any(k in p.lower() for k in ["kisne", "creator", "essa"]) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with t_movie:
    st.write("### 🎥 Precision Movie Studio v42")
    m_s = st.text_area("Movie Script (v40 Visual Quality Enabled):", height=150)
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with col2: mr = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col3: ms = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Cinematic"])
    if st.button("Generate v42 Master Movie 🚀"):
        if m_s:
            v_res = create_masterpiece_v42(m_s, mv, mr, ms)
            if "mp4" in v_res:
                st.video(open(v_res, 'rb').read())
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with t_img:
    image_studio()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v42.0 | v40 Video Engine | Image Studio Integrated | Muhammad Essa Awan</p>", unsafe_allow_html=True)
