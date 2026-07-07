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

# Senior Engineer Optimization: Handling File I/O and Video Backends
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Backend Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM BRANDING & UI (Muhammad Essa Awan)
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
        margin-bottom: 0px;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 55px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none; transition: 0.2s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 5px 20px rgba(0, 212, 255, 0.5); }
    </style>
    """, unsafe_allow_html=True)

ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns) if q else False

# ==========================================
# 2. UNIVERSAL VISUAL DIRECTOR (GPT-4 LEVEL)
# ==========================================
def get_verified_visual_prompt(urdu_text, style_choice):
    try:
        refiner_prompt = f"Professional prompt for AI Image: Convert this Urdu to a detailed English prompt describing animals, buildings, and emotions accurately: '{urdu_text}'. No text, 8k resolution."
        encoded_refiner = urllib.parse.quote(refiner_prompt)
        director_res = requests.get(f"https://text.pollinations.ai/{encoded_refiner}?model=openai&cache=true", timeout=15)
        visual_description = director_res.text if director_res.status_code == 200 else urdu_text
        return f"{style_choice} style, {visual_description}, highly detailed, cinematic lighting, 8k, realistic masterpiece"
    except:
        return f"{style_choice} style, {urdu_text}, cinematic"

# ==========================================
# 3. BULLETPROOF MOVIE ENGINE (FIXING AVCODEC ERRORS)
# ==========================================
def create_bulletproof_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Secure Voice Generation
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        
        # Verify Audio File
        if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 100:
            raise ValueError("Audio Generation Failed or File Empty")
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            prompt = get_verified_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            # Secure Image Download with PIL Cleanup (Fixes avcodec invalid data error)
            img_res = requests.get(img_url, timeout=20)
            if img_res.status_code == 200:
                with open(img_path, "wb") as f: f.write(img_res.content)
                
                # RE-SAVING WITH PIL: This strips bad headers and ensures 100% valid data for MoviePy
                temp_pil = Image.open(img_path).convert("RGB")
                temp_pil.save(img_path, "JPEG", quality=95)
                
                # Step 4: Cinematic Zoom OUT (No Black Borders)
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h)) 
                clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))
            else:
                continue

        if not clips: raise ValueError("Could not generate any valid visual scenes.")

        # Step 5: Final Rendering
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Ready_{u_id}.mp4"
        # Using ultra-safe encoding settings
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4)
        
        # Immediate cleanup of raw clips to save server memory
        for i in range(len(sentences)):
            p = f"{u_id}_{i}.jpg"
            if os.path.exists(p): os.remove(p)
            
        return out_name
    except Exception as e:
        return f"System Maintenance Error: {str(e)}"

# ==========================================
# 4. MAIN UI INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- CHAT TAB ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    col_a, col_b = st.columns([1, 5])
    with col_a: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='mic')
    with col_b: st.file_uploader("➕ Upload Image/Error", type=["jpg", "png"], key="up")

    if prompt := st.chat_input("Ask ES AI anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        # Identity Logic
        if is_creator_query(prompt):
            res = ESSA_BIO
        else:
            try:
                res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai&cache=true", timeout=20).text
            except: res = "Server connection lost. Please refresh."
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

# --- VOICE TAB ---
with tabs[1]:
    st.header("🎙️ Professional Voice Studio")
    vt = st.text_area("Write text to convert to voice:")
    v_c1, v_c2 = st.columns(2)
    with v_c1: v_gender = st.selectbox("Select Gender:", ["Female", "Male"])
    with v_c2: st.selectbox("Language:", ["Urdu", "English"], key="v_lang")
    if st.button("Generate Pro Audio 🚀"):
        if vt:
            v_file = "es_talk.mp3"
            v_code = "ur-PK-UzmaNeural" if v_gender == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(vt, v_code).save(v_file)
            asyncio.run(sv()); st.audio(v_file)

# --- MOVIE TAB (Fixed Logic) ---
with tabs[2]:
    st.header("🎬 Universal Cinematic Studio v21.0")
    st.info("This engine automatically verifies each image to prevent 'avcodec' errors.")
    m_script = st.text_area("Story Script:", height=150, placeholder="Example: A lion is walking in a dark forest...")
    
    m_c1, m_c2, m_c3 = st.columns(3)
    with m_c1: m_voice = st.selectbox("Voice Selection:", ["Male", "Female"])
    with m_c2: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with m_c3: m_style = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Launch Universal Rendering"):
        if m_script:
            with st.spinner("Verifying data and rendering video..."):
                video = create_bulletproof_movie(m_script, m_voice, m_ratio, m_style)
                if "mp4" in video:
                    st.video(video)
                    st.success("Masterpiece Delivered!")
                    with open(video, "rb") as f: st.download_button("Download Full HD", f, file_name=video)
                else: st.error(f"Render Failed: {video}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v21.0 | Bulletproof Rendering Engine | Muhammad Essa Awan</p>", unsafe_allow_html=True)
