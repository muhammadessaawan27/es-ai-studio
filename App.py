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

# Senior Engineer Fix for Image processing
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
except Exception as e:
    st.error(f"System Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. DESIGN & IDENTITY
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
        font-size: clamp(40px, 8vw, 80px); font-weight: 900;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.01); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
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
    patterns = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns) if q else False

# ==========================================
# 2. FAIL-SAFE BGM LOGIC
# ==========================================
def get_bgm_url(story_text):
    t = story_text.lower()
    if any(k in t for k in ["jungle", "sher", "wild", "forest"]):
        return "https://www.chosic.com/wp-content/uploads/2021/07/The-Wild-Animals.mp3"
    elif any(k in t for k in ["king", "badshah", "history", "qila", "warrior"]):
        return "https://www.chosic.com/wp-content/uploads/2020/06/Epic-Adventure.mp3"
    else:
        return "https://www.chosic.com/wp-content/uploads/2021/04/Inspiring-Story.mp3"

# ==========================================
# 3. ADVANCED MOVIE ENGINE (FAIL-SAFE)
# ==========================================
def create_master_movie(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Voice Generation (Must Work)
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def run_v(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(run_v())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: Fail-Safe BGM Logic
        final_audio_track = voice_audio
        try:
            bgm_url = get_bgm_url(story)
            bgm_path = f"{u_id}_bgm.mp3"
            r = requests.get(bgm_url, timeout=10)
            if r.status_code == 200:
                with open(bgm_path, "wb") as f: f.write(r.content)
                bgm_audio = AudioFileClip(bgm_path).volumex(0.12).set_duration(voice_audio.duration)
                final_audio_track = CompositeAudioClip([voice_audio, bgm_audio])
        except Exception as e:
            # If BGM fails, we just log it and continue with voice only
            print(f"BGM Load Warning: {e}")

        # Step 3: Scene Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 4: Multi-Scene Generation
        words = story.split()
        num_scenes = 4
        chunk = max(1, len(words) // num_scenes)
        clips = []

        for i in range(num_scenes):
            st_idx, end_idx = i*chunk, (i+1)*chunk if i != 3 else len(words)
            scene_text = " ".join(words[st_idx:end_idx])
            prompt = f"Professional 3D cinematic animation style, {scene_text[:85]}, high quality, 8k, realistic lighting, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            img_data = requests.get(img_url).content
            with open(img_path, "wb") as f: f.write(img_data)
            
            # Zoom-Out Animation (Professional Look)
            clip = ImageClip(img_path).set_duration(voice_audio.duration/num_scenes).set_fps(24)
            clip = clip.resize(lambda t: 1.1 - 0.05 * t).set_position('center')
            clips.append(clip)

        # Step 5: Final Render
        final_video = concatenate_videoclips(clips, method="compose").set_audio(final_audio_track)
        final_video = final_video.resize(newsize=(w, h))
        
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, threads=4)
        return out_name
    except Exception as e:
        return f"Technical Error: {str(e)}"

# ==========================================
# 4. UI DASHBOARD
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold; letter-spacing: 5px;'>MUHAMMAD ESSA'S OFFICIAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Chat & Vision", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("---")
    c1, c2 = st.columns([1, 4])
    with c1: mic_recorder(start_prompt="🎙️ Speak", stop_prompt="🛑 Stop", key='recorder')
    with c2: up_img = st.file_uploader("➕ Upload Image", type=["jpg", "png"])

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        if is_creator_query(prompt):
            res = ESSA_BIO
        else:
            encoded_q = urllib.parse.quote(prompt)
            try:
                r = requests.get(f"https://text.pollinations.ai/{encoded_q}?model=openai&cache=true", timeout=30)
                res = r.text if r.status_code == 200 else "AI سرور مصروف ہے۔"
            except: res = "Connection Error."
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voice Studio")
    vt = st.text_area("Yahan likhein:")
    vl, vg = st.columns(2)
    with vl: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with vg: gender = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀", key="v_btn"):
        if vt:
            vc = "ur-PK-UzmaNeural" if gender == "Female" else "ur-PK-AsadNeural"
            async def run_v(): await edge_tts.Communicate(vt, vc).save("temp.mp3")
            asyncio.run(run_v()); st.audio("temp.mp3")

with tabs[2]:
    st.header("🎬 Pro Cinematic Movie Studio")
    m_script = st.text_area("Movie Script:", height=150, placeholder="Example: Ek bahadur larka...")
    m_vc, m_rs = st.columns(2)
    with m_vc: m_voice = st.selectbox("Voice Selection:", ["Male", "Female"], index=0)
    with m_rs: m_ratio = st.selectbox("Video Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    if st.button("Generate Master Movie 🚀"):
        if m_script:
            with st.spinner("مناظر، آواز اور موسیقی تیار ہو رہی ہے..."):
                video = create_master_movie(m_script, m_voice, m_ratio)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download Movie ⬇️", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio v14.0 | Fail-Safe Engine Enabled</p>", unsafe_allow_html=True)
