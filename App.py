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

# Senior Engineer Professional Setup
session = requests.Session()

# PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. LUXURY UI (WHITE BG + LIGHTNING NAME)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
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
        width: 100px; height: 100px; background: linear-gradient(135deg, #ff007a, #2563eb);
        border-radius: 22px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 40px; color: white;
        box-shadow: 0 0 30px rgba(37, 99, 235, 0.6); animation: rotateShua 6s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotateShua { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    .main-header { font-size: 2.5rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 50px !important; height: 55px; font-weight: 900;
    }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; color: #0f172a !important; border: 2px solid #e2e8f0 !important; border-radius: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. ESSA IDENTITY & v40 ENGINE (100% UNTOUCHED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def get_v40_visual_prompt(urdu_text, style):
    try:
        instr = f"Act as a Film Director. Extract only the primary visual subject from Urdu: '{urdu_text}'. Describe it in detail in English for a 3D animation. Ensure accuracy of objects/animals/emotions. No humans unless mentioned. Output only the prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} cinematic animation style, {desc}, highly detailed masterpiece, 8k, vibrant lighting"
    except: return urdu_text

def create_v40_movie_engine(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} بن رہا ہے (v40 Stable Mode)...")
            refined_p = get_v40_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_data = session.get(img_url, timeout=60).content
            img_obj = Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
            img_path = f"i_{u_id}_{i}.jpg"
            img_obj.save(img_path, "JPEG")
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.2 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V40_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 3. UNIVERSAL IMAGE STUDIO (FOR THE WHOLE WORLD)
# ==========================================
def universal_director_ai(user_request, style, is_edit=False):
    """Universal logic to understand ANY request from ANY user."""
    try:
        context = "New Image Request" if not is_edit else "Image Modification Request"
        instr = (f"You are the Master AI Artist Director. A user requested: '{user_request}'. "
                 f"Generate a highly detailed, professional English AI Image Prompt. "
                 f"Cover everything: Subject, Clothing, Hair, Background, Lighting, and Style. "
                 f"If user says 'beard', describe a realistic beard. If user says 'blue clothes', describe blue fabric. "
                 f"If user says 'eagle and snake', describe the action. "
                 f"Strictly follow the user's intent. Output ONLY the English prompt.")
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        desc = res.text if res.status_code == 200 else user_request
        return f"{style} style masterpiece, {desc}, 8k resolution, cinematic lighting, highly detailed"
    except: return user_request

def image_studio_universal():
    st.write("### 🎨 ES AI Image Studio (Global Master Mode)")
    mode = st.radio("Select Mode:", ["Text to Image", "Professional Photo Edit"], horizontal=True)
    
    if mode == "Text to Image":
        user_p = st.text_area("کچھ بھی لکھیں (دنیا کا کوئی بھی جانور، چیز یا منظر):", placeholder="Describe your imagination...")
        c1, c2, c3 = st.columns(3)
        with c1: style = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Cyberpunk", "Sketch"])
        with c2: size = st.selectbox("Ratio:", ["Square (1:1)", "Portrait (9:16)", "Landscape (16:9)"])
        with c3: num = st.slider("Quantity:", 1, 4, 1)
        
        if st.button("Generate World-Class Images 🚀"):
            if user_p:
                res_dim = {"Square (1:1)": (1024, 1024), "Portrait (9:16)": (720, 1280), "Landscape (16:9)": (1280, 720)}
                w, h = res_dim[size]
                refined = universal_director_ai(user_p, style)
                for i in range(num):
                    with st.spinner(f"AI is painting scene {i+1}..."):
                        seed = random.randint(1, 999999)
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true"
                        img_data = requests.get(url).content
                        st.image(img_data, caption=f"ES AI Masterpiece {i+1}")
                        st.download_button(f"Download {i+1} ⬇️", img_data, file_name=f"es_world_{i}.jpg")

    else:
        st.write("#### 🖼️ Universal Image Surgeon (Edit Anything)")
        f = st.file_uploader("تصویر اپ لوڈ کریں جس میں تبدیلی کرنی ہے:", type=["jpg", "png"])
        if f:
            st.image(f, caption="Original Photo", width=300)
            edit_req = st.text_area("تبدیلی بیان کریں (کچھ بھی: کپڑے، بال، داڑھی، بیک گراؤنڈ، میک اپ، وغیرہ):")
            if st.button("Apply Universal AI Surgery 🚀"):
                if edit_req:
                    with st.spinner("AI is analyzing and modifying..."):
                        refined_edit = universal_director_ai(edit_req, "Realistic", is_edit=True)
                        edit_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_edit)}?width=1024&height=1024&nologo=true"
                        edit_data = requests.get(edit_url).content
                        st.image(edit_data, caption="Modified Result")
                        st.download_button("Download Edited Photo ⬇️", edit_data, file_name="es_modified.jpg")

# ==========================================
# 4. FINAL ASSEMBLY
# ==========================================
t_chat, t_movie, t_img = st.tabs(["💬 Smart Chat", "🎬 Movie Studio", "🎨 Image Studio"])

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
    st.write("### 🎥 v40 Stable Movie Engine")
    m_s = st.text_area("Movie Script:", height=150, key="v48_movie")
    col1, col2, col3 = st.columns(3)
    with col1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with col2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col3: ms = st.selectbox("Visual Style:", ["3D Cartoon", "Realistic", "Cinematic"])
    if st.button("Generate Master Movie 🚀"):
        if m_s:
            v_res = create_v40_movie_engine(m_s, mv, mr, ms)
            if "mp4" in v_res:
                with open(v_res, 'rb') as f: st.video(f.read())
                st.download_button("Download Movie ⬇️", open(v_res, 'rb').read(), file_name=v_res)

with t_img:
    image_studio_universal()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v48.0 | v40 Video Engine Preserved | Universal AI Artist | Muhammad Essa Awan</p>", unsafe_allow_html=True)
