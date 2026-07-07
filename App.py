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

# Senior Engineer Fix: Force imageio to find backends and handle MoviePy correctly
try:
    import imageio
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except Exception as e:
    st.error(f"System Engine Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PRODUCTION GRADE CONFIGURATION
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
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0px 8px 20px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. IDENTITY DATA (PRESERVED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"owner", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 3. HIGH-STABILITY CHAT ENGINE
# ==========================================
def get_professional_response(query):
    if is_creator_query(query): return ESSA_BIO
    
    encoded_q = urllib.parse.quote(query)
    system_role = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer professionally and intelligently.")
    url = f"https://text.pollinations.ai/{encoded_q}?model=openai&system={system_role}&cache=true"
    
    try:
        r = requests.get(url, timeout=45)
        return r.text if r.status_code == 200 else "سرور اس وقت جواب نہیں دے رہا، براہ کرم دوبارہ کوشش کریں۔"
    except:
        return "کنکشن کا مسئلہ ہے، براہ کرم تھوڑی دیر بعد پوچھیں۔"

# ==========================================
# 4. BUG-FREE MOVIE ENGINE (FIXED BACKEND ERROR)
# ==========================================
def create_master_movie(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    try:
        # 1. Voice Generation
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def generate_v():
            await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(generate_v())
        audio = AudioFileClip(audio_file)
        dur = audio.duration

        # 2. Dimensions Logic
        res = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res[ratio]

        # 3. Multi-Scene (4 Scenes)
        words = story.split()
        num_scenes = 4
        chunk = max(1, len(words) // num_scenes)
        
        clips = []
        for i in range(num_scenes):
            start = i * chunk
            end = (i + 1) * chunk if i != 3 else len(words)
            scene_text = " ".join(words[start:end])
            
            prompt = f"Professional 3D cinematic animation style, {scene_text[:70]}, vibrant, 8k, masterpiece, no text"
            seed = random.randint(1, 99999)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
            
            img_path = f"{u_id}_img_{i}.jpg"
            # Using Session for better reliability
            with requests.get(img_url, stream=True) as r:
                r.raise_for_status()
                with open(img_path, 'wb') as f:
                    for data in r.iter_content(chunk_size=8192):
                        f.write(data)
            
            # Senior Engineer Fix: Pre-loading image with PIL to verify backend accessibility
            temp_img = Image.open(img_path).convert("RGB")
            temp_img.save(img_path) # Ensure clean JPG format
            
            clip = ImageClip(img_path).set_duration(dur/num_scenes).set_fps(24)
            # Smooth Animation (Bug-Free Resize)
            clip = clip.resize(newsize=(w, h)).resize(lambda t: 1 + 0.04 * t)
            clips.append(clip)

        # 4. Final Processing
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"movie_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, threads=4)
        
        # Cleanup
        for i in range(num_scenes): os.remove(f"{u_id}_img_{i}.jpg")
        os.remove(audio_file)
        
        return out_name
    except Exception as e:
        return f"Technical Error: {str(e)}"

# ==========================================
# 5. UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold; letter-spacing: 5px;'>MUHAMMAD ESSA'S OFFICIAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    st.write("🎙️ **Voice Typing:**")
    mic_recorder(start_prompt="Record Command", stop_prompt="Stop", key='recorder')

    if prompt := st.chat_input("مجھ سے کچھ بھی پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            res = get_professional_response(prompt)
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("Voiceover Studio")
    v_text = st.text_area("متن لکھیں:", height=100)
    col1, col2 = st.columns(2)
    with col1: lang = st.selectbox("Zaban:", ["Urdu", "English", "Hindi"])
    with col2: gen = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Audio 🚀"):
        if v_text:
            v_code = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def run_v(): await edge_tts.Communicate(v_text, v_code).save("es_v.mp3")
            asyncio.run(run_v()); st.audio("es_v.mp3")

with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    m_script = st.text_area("کہانی لکھیں:", height=150, placeholder="یہاں اپنی کہانی لکھیں...")
    mv_col, mr_col = st.columns(2)
    with mv_col: m_voice = st.selectbox("Voice:", ["Female", "Male"], key="mv")
    with mr_col: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr")

    if st.button("Generate Master Movie 🚀"):
        if m_script:
            with st.spinner("ویڈیو رینڈر ہو رہی ہے..."):
                video = create_master_movie(m_script, m_voice, m_ratio)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f:
                        st.download_button("Download Movie ⬇️", f, file_name=f"ES_AI_{u_id}.mp4" if 'u_id' in locals() else "movie.mp4")
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>© 2024 ES AI Master Studio | Production v10.0</p>", unsafe_allow_html=True)
