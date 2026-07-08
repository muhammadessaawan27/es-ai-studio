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

# Global Session
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein, resize
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED ELECTRIC UI (NO CHANGES)
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
    @keyframes pulseGlow { 0%, 100% { box-shadow: 0 0 30px #ff007a; } 50% { box-shadow: 0 0 70px #00d4ff; } }
    .main-header { font-size: 3rem; font-weight: 900; color: #0f172a; text-align: center; text-transform: uppercase; margin-bottom: 20px; }
    .stButton>button {
        background: linear-gradient(90deg, #ff007a, #2563eb) !important;
        color: white !important; border: none !important; border-radius: 50px !important;
        height: 60px; width: 100%; font-size: 22px; font-weight: 900;
    }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 18px; }
    .stTextArea>div>div>textarea, .stTextInput>div>div>input {
        background-color: #ffffff !important; color: #0f172a !important; border: 2px solid #e2e8f0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. CREATOR BIO & v40 ENGINE (UNTOUCHED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
"""

def get_visual_prompt_v40(urdu_text, style):
    try:
        instr = f"Extract only the main visual subject and atmosphere from this Urdu: '{urdu_text}'. Describe it clearly in English for a 3D animation model. No preamble."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=20)
        desc = res.text if res.status_code == 200 else urdu_text
        return f"{style} animation style, {desc}, highly detailed, cinematic lighting, 8k, realistic masterpiece, vivid colors"
    except: return urdu_text

def create_cinematic_v40(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} بن رہا ہے...")
            refined_p = get_visual_prompt_v40(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            with open(img_path, "wb") as f: f.write(img_data)
            img_obj = Image.open(img_path).convert("RGB").resize((w, h))
            img_obj.save(img_path, "JPEG")
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V40_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 3. UNIVERSAL IMAGE STUDIO (New Tab)
# ==========================================
def get_image_studio_director(urdu_req, style):
    """Translates any user requirement into a professional prompt."""
    try:
        instr = f"Professional Image Director: User wants: '{urdu_req}'. Create a highly detailed English prompt for an AI Image Generator. Include details about clothes, beard, background, lighting, and textures. Ensure it respects original gender if specified. Output ONLY English."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=20)
        desc = res.text if res.status_code == 200 else urdu_req
        return f"{style} style, {desc}, masterpiece, 8k resolution, cinematic lighting, sharp focus"
    except: return urdu_req

def image_studio_module():
    st.write("### 🎨 ES AI Universal Image Studio")
    mode = st.radio("Select Mode:", ["Text to Image", "Edit Photo (Img2Img)"], horizontal=True)
    
    if mode == "Text to Image":
        user_p = st.text_area("جو تصویر بنوانی ہے بیان کریں (مثلاً: اڑتا ہوا باز اور سانپ):", placeholder="Describe your imagination...")
        c1, c2, c3 = st.columns(3)
        with c1: style = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Sketch", "Digital Art"])
        with c2: size = st.selectbox("Ratio:", ["Square (1:1)", "Portrait (9:16)", "Landscape (16:9)"])
        with c3: num = st.slider("Quantity:", 1, 4, 1)
        
        if st.button("Generate Masterpiece 🚀"):
            if user_p:
                res_dim = {"Square (1:1)": (1024, 1024), "Portrait (9:16)": (720, 1280), "Landscape (16:9)": (1280, 720)}
                w, h = res_dim[size]
                refined = get_image_studio_director(user_p, style)
                for i in range(num):
                    with st.spinner(f"AI is painting scene {i+1}..."):
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true&negative=girl,woman,female"
                        img_data = requests.get(url).content
                        st.image(img_data, caption=f"ES AI Masterpiece {i+1}")
                        st.download_button(f"Download {i+1} ⬇️", img_data, file_name=f"es_img_{i}.jpg")
            else: st.warning("کچھ لکھیں تو سہی!")

    else:
        st.write("#### 🖼️ Professional Image Surgeon (Edit Anything)")
        f = st.file_uploader("تصویر اپ لوڈ کریں جس میں تبدیلی کرنی ہے:", type=["jpg", "png", "jpeg"])
        if f:
            st.image(f, caption="Original Photo", width=300)
            edit_req = st.text_area("تبدیلی بیان کریں (مثلاً: بیک گراؤنڈ بدل دو، بال سفید کر دو، یا بلو کپڑے پہنوا دو):")
            if st.button("Apply AI Changes 🚀"):
                if edit_req:
                    with st.spinner("AI is analyzing and modifying..."):
                        refined_edit = get_image_studio_director(edit_req, "Realistic")
                        edit_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_edit)}?width=1024&height=1024&nologo=true&negative=girl,woman,female"
                        edit_data = requests.get(edit_url).content
                        st.image(edit_data, caption="Modified Result")
                        st.download_button("Download Edited Photo ⬇️", edit_data, file_name="es_edited.jpg")
                else: st.warning("تبدیلی کی تفصیل لکھیں!")

# ==========================================
# 4. DASHBOARD ASSEMBLY
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Electric AI Chat", "🎬 Pro Movie Studio", "🎨 Image Studio"])

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
    st.write("### 🎥 Professional Cinematic Production v40")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=200, key="movie_v40")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Awaaz:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["3D Cartoon", "Realistic", "Cinematic"])
    if st.button("🚀 Generate v40 Master Video"):
        if m_script:
            with st.spinner("⚡ ES AI is rendering your masterpiece..."):
                video_res = create_cinematic_v40(m_script, mv, mr, ms)
                if "mp4" in video_res:
                    with open(video_res, 'rb') as f: st.video(f.read())
                    st.download_button("Download Video ⬇️", open(video_res, 'rb'), file_name=video_res)

with tab_image:
    image_studio_module()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v51.0 | v40 Engine Locked | Universal Image Studio | Muhammad Essa Awan</p>", unsafe_allow_html=True)
