import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. PREMIUM BRANDING & UI
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
        font-size: 20px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Creator Bio
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# ==========================================
# 2. ADVANCED ENGINES
# ==========================================

def get_smart_chat(query):
    if any(k in query.lower() for k in ["kisne banaya", "who made you", "creator", "essa"]): return ESSA_BIO
    encoded = urllib.parse.quote(query)
    try:
        r = requests.get(f"https://text.pollinations.ai/{encoded}?model=openai&cache=true", timeout=30)
        return r.text if r.status_code == 200 else "AI Engine is thinking..."
    except: return "Connection slow, please try again."

def create_pro_video(story, ratio):
    try:
        # Step 1: Human-like Voice
        async def generate_v():
            await edge_tts.Communicate(story, "ur-PK-UzmaNeural").save("v.mp3")
        asyncio.run(generate_v())
        audio = AudioFileClip("v.mp3")
        dur = audio.duration

        # Step 2: Dimensions Logic (FIXED RATIO BUG)
        res_map = {
            "YouTube (16:9)": (1280, 720),
            "TikTok/Reels (9:16)": (720, 1280),
            "Instagram (1:1)": (720, 720)
        }
        w, h = res_map[ratio]

        # Step 3: Multi-Scene Cinematic Engine
        words = story.split()
        num_scenes = 3 if len(words) > 20 else 1
        chunk = max(1, len(words) // num_scenes)
        
        clips = []
        for i in range(num_scenes):
            scene_text = " ".join(words[i*chunk : (i+1)*chunk])
            # Force "Animated/Disney" Style to avoid real humans unless needed
            prompt = f"3D Disney Pixar style animation, highly detailed cinematic, {scene_text[:100]}, cute characters, vibrant colors, 8k, no text, no tea cups"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&nologo=true"
            
            # Download Image
            img_data = requests.get(img_url).content
            with open(f"s_{i}.jpg", "wb") as f: f.write(img_data)
            
            # Step 4: Motion Effect (Simulated 3D Movement)
            clip = ImageClip(f"s_{i}.jpg").set_duration(dur/num_scenes).set_fps(24)
            clip = clip.resize(lambda t: 1 + 0.05 * t).set_position('center') # Dynamic Zoom
            clips.append(clip)

        # Merge
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        final_video = final_video.resize(newsize=(w, h)) # FORCE RESIZE
        
        out_file = "es_pro_video.mp4"
        final_video.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k")
        return out_file
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    prompt = st.chat_input("Poochein...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            res = get_smart_chat(prompt)
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voice Studio")
    v_text = st.text_area("Yahan likhein:")
    if st.button("Generate Audio 🚀", key="v_btn"):
        if v_text:
            async def sv(): await edge_tts.Communicate(v_text, "ur-PK-UzmaNeural").save("test_v.mp3")
            asyncio.run(sv())
            st.audio("test_v.mp3")

with tabs[2]:
    st.header("🎬 Pro Movie Studio (Fixed Ratios)")
    m_script = st.text_area("Apni Kahani Likhein:", height=150, placeholder="Example: Jungle mein sher aur hathi dost ban gaye...")
    m_ratio = st.selectbox("Size Select Karein:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    
    if st.button("Generate Professional Video 🚀"):
        if m_script:
            with st.spinner("مناظر اور کارٹون تیار ہو رہے ہیں..."):
                video_file = create_pro_video(m_script, m_ratio)
                if "mp4" in video_file:
                    st.video(video_file)
                    with open(video_file, "rb") as f:
                        st.download_button("Download HD Video ⬇️", f, file_name=f"es_ai_{m_ratio.split()[0]}.mp4")
                else: st.error(video_file)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v5.0 | Premium Motion Graphics Enabled</p>", unsafe_allow_html=True)
