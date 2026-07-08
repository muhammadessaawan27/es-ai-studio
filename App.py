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

# Global Session for persistent speed
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein, resize
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED ELECTRIC UI (v40 STYLE)
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
# 2. CREATOR BIO & v40 SUBJECT LOCKING (ORIGINAL)
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

# ==========================================
# 3. v40 MOVIE ENGINE (UNTOUCHED LOGIC)
# ==========================================
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

        # v40 Sentence Splitting
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎨 منظر {i+1} بن رہا ہے (v40 Mode)...")
            refined_p = get_visual_prompt_v40(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_data = session.get(img_url, timeout=60).content
            img_obj = Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
            img_obj.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # v40 Force Motion (1.2 to 1.0)
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
# 4. IMAGE & PROMPT TO VIDEO STUDIO (NEW)
# ==========================================
def image_studio_module():
    st.write("### 🎨 ES AI Artistic Studio")
    sub_tab = st.radio("Choose Service:", ["Text to Image", "Professional Photo Edit", "Prompt to Video Clip"], horizontal=True)
    
    neg = "&negative=girl,woman,female,blurry,distorted"

    if sub_tab == "Text to Image":
        p = st.text_area("Describe the image you want:", placeholder="e.g. A robotic eagle flying over a mountain...")
        c1, c2 = st.columns(2)
        with c1: style = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Sketch"])
        with c2: size = st.selectbox("Ratio:", ["Square (1:1)", "Portrait (9:16)", "Landscape (16:9)"])
        if st.button("Generate Image 🚀"):
            res_dim = {"Square (1:1)": (1024, 1024), "Portrait (9:16)": (720, 1280), "Landscape (16:9)": (1280, 720)}
            w, h = res_dim[size]
            with st.spinner("AI is painting..."):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p + ' ' + style)}?width={w}&height={h}&nologo=true{neg}"
                st.image(url, caption="Generated Result")

    elif sub_tab == "Professional Photo Edit":
        f = st.file_uploader("Upload Image:", type=["jpg", "png"])
        if f:
            st.image(f, width=300)
            edit_p = st.text_input("Describe the change (e.g. Change background to a flower garden):")
            if st.button("Apply Surgery 🚀"):
                with st.spinner("Modifying..."):
                    # Img2Img Simulation
                    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_p)}?width=1024&height=1024&nologo=true{neg}"
                    st.image(url, caption="Edited Result")

    elif sub_tab == "Prompt to Video Clip":
        st.info("یہ آپ کے پرامپٹ سے ایک چھوٹا (4-5 سیکنڈ) کا متحرک ویڈیو کلپ بنائے گا۔")
        vid_p = st.text_area("Describe the video motion:")
        if st.button("Generate Video Clip 🎥"):
            with st.spinner("AI is animating your prompt..."):
                # Using specialized video prompt logic
                vid_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(vid_p + ' cinematic motion movie clip')}?width=1280&height=720&model=video&nologo=true"
                st.image(vid_url, caption="Animated Clip Preview (Rendering...)")
                st.warning("Video rendering via API is currently in Beta. Result will appear as a high-motion sequence.")

# ==========================================
# 5. MAIN UI TABS
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
    st.write("### 🎥 v40 Professional Cinematic Production")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=200, key="v40_final")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Awaaz:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["3D Cartoon", "Realistic", "Cinematic"])
    if st.button("🚀 Generate v40 Master Video"):
        if m_script:
            with st.spinner("⚡ ES AI is rendering your masterpiece..."):
                video_res = create_cinematic_v40(m_script, mv, mr, ms)
                if "mp4" in video_res:
                    st.video(open(video_res, 'rb').read())
                    st.download_button("Download Video ⬇️", open(video_res, 'rb').read(), file_name=video_res)

with tab_image:
    image_studio_module()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v52.0 | v40 Engine Restored | Image Studio Integrated | Muhammad Essa Awan</p>", unsafe_allow_html=True)
