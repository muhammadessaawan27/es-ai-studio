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

# Senior Engineer Stability Configuration
session = requests.Session()

# PIL Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED DESIGN (WHITE BG + LIGHTNING NAME)
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
# 2. ESSA IDENTITY & v40 ENGINE (100% ORIGINAL - PROTECTED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def get_v40_visual_prompt(urdu_text, style):
    try:
        instr = f"Extract core subject from Urdu: '{urdu_text}'. Detailed English 3D animation prompt. Accurate animals/objects. No humans unless mentioned. Output ONLY prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} cinematic animation, {desc}, masterpiece, 8k"
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
            status.info(f"🎨 منظر {i+1} بن رہا ہے (v40 Locked Engine)...")
            refined_p = get_v40_visual_prompt(scene, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_data = session.get(url, timeout=60).content
            img_path = f"i_{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(img_data)
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24).resize(newsize=(w, h))
            clip = clip.resize(lambda t: 1.2 - 0.2 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V40_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 3. PROFESSIONAL IMAGE SURGEON (IDENTITY GUARD)
# ==========================================
def get_surgeon_prompt(user_req, subject_desc, style):
    try:
        instr = (f"IDENTITY GUARD: User wants to modify their photo. "
                 f"Subject Description (MUST RETAIN): {subject_desc}. "
                 f"Modification requested: {user_req}. "
                 f"Description: Combine subject and modification into a 100-word English prompt. "
                 "DO NOT CHANGE GENDER. Keep face identity. High quality 8k.")
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
        return f"{style} masterpiece, {res.text if res.status_code == 200 else user_req}, 8k"
    except: return user_req

def image_studio_pro_v57():
    st.write("### 🎨 ES AI Professional Image Surgeon & Studio")
    mode = st.radio("Choose Service:", ["Text to Image", "Professional Photo Edit"], horizontal=True)
    
    # Professional Aspect Ratios
    size_map = {
        "Profile Picture (1:1)": (1024, 1024),
        "YouTube Banner (21:9)": (2560, 1080),
        "YouTube Thumbnail (16:9)": (1280, 720),
        "TikTok/Insta Story (9:16)": (720, 1280),
        "Facebook Cover (approx)": (1200, 444)
    }

    if mode == "Text to Image":
        p = st.text_area("تصویر بیان کریں (مثلاً: اڑتا ہوا باز اور سانپ):")
        c1, c2, c3 = st.columns(3)
        with c1: style = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Oil Painting"], key="t_s")
        with c2: size = st.selectbox("Format/Ratio:", list(size_map.keys()), key="t_r")
        with c3: num = st.slider("Quantity:", 1, 4, 1)
        if st.button("Generate Masterpiece 🚀"):
            w, h = size_map[size]
            refined = get_v40_visual_prompt(p, style)
            for i in range(num):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,female"
                st.image(url, caption=f"Result {i+1}")
    else:
        st.write("#### 🖼️ Identity-Safe Photo Surgeon")
        f = st.file_uploader("اپنی تصویر اپ لوڈ کریں:", type=["jpg", "png", "jpeg"])
        if f:
            st.image(f, width=300, caption="Original Photo")
            subj = st.text_input("تصویر میں موجود بندے کا حلیہ بتائیں (مثلاً: داڑھی والا مرد، کالی قمیض):", placeholder="Identity Guard کے لیے ضروری ہے")
            edit_req = st.text_area("تبدیلی بتائیں (مثلاً: بیک گراؤنڈ بدل دو، رنگ گورا کر دو):")
            size_edit = st.selectbox("تبدیلی کے بعد سائز کیا ہو؟", list(size_map.keys()), key="e_r")
            if st.button("Apply Professional Surgery 🚀"):
                if subj and edit_req:
                    with st.spinner("AI سرجری کر رہا ہے..."):
                        w, h = size_map[size_edit]
                        refined_edit = get_surgeon_prompt(edit_req, subj, "Realistic")
                        # Identity Enforced URL
                        edit_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_edit)}?width={w}&height={h}&nologo=true&negative={'girl,female' if 'مرد' in subj or 'man' in subj.lower() else ''}"
                        st.image(edit_url, caption="Modified Result")
                        st.download_button("Download Edited Photo ⬇️", requests.get(edit_url).content, file_name="es_modified.jpg")
                else: st.warning("حلیہ اور تبدیلی دونوں لکھنا لازمی ہے!")

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
    m_s = st.text_area("Movie Script:", height=150)
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
    image_studio_pro_v57()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v57.0 | v40 Engine | Identity Guard | Social Media Sizes | Muhammad Essa Awan</p>", unsafe_allow_html=True)
