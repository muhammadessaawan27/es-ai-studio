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
from PIL import Image, ImageDraw, ImageFont

# Senior Engineer Fix for Image and MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
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
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 12px; height: 50px; font-weight: bold; border: none; }
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

# ==========================================
# 2. PROMPT & GENDER LOGIC
# ==========================================
def get_smart_prompt(scene_text):
    # Detect if story is about a male or female to fix the image bug
    gender_bonus = ""
    if any(k in scene_text for k in ["احمد", "لڑکا", "آدمی", "boy", "man", "king", "badshah"]):
        gender_bonus = "Focus on male character, young boy, no women, no girls, "
    elif any(k in scene_text for k in ["لڑکی", "عورت", "girl", "woman", "queen"]):
        gender_bonus = "Focus on female character, "
        
    return f"Professional 3D cinematic animation style, {gender_bonus} {scene_text[:80]}, high quality, 8k, realistic lighting, masterpiece, no text"

# ==========================================
# 3. ADVANCED MOVIE ENGINE (SUBTITLES + ZOOM OUT)
# ==========================================
def create_pro_movie_with_subs(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Voice & Fail-Safe BGM
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def run_v(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(run_v())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Multi-Scene Generation
        words = story.split()
        num_scenes = 4
        chunk = max(1, len(words) // num_scenes)
        clips = []

        for i in range(num_scenes):
            st_idx, end_idx = i*chunk, (i+1)*chunk if i != 3 else len(words)
            scene_text = " ".join(words[st_idx:end_idx])
            
            # Smart Prompting to fix Gender Accuracy
            prompt = get_smart_prompt(scene_text)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(requests.get(img_url).content)
            
            # Step 4: Add Subtitles on Image
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            # Drawing a shadow box for text
            draw.rectangle([0, h-100, w, h], fill=(0,0,0,150))
            # Text placement (Simplified for Cloud Servers)
            draw.text((w/2, h-50), scene_text[-40:], fill="white", anchor="ms") # Show last 40 chars
            img.save(img_path)

            # Step 5: Cinematic ZOOM OUT Animation (Fixed Direction)
            scene_dur = voice_audio.duration / num_scenes
            clip = ImageClip(img_path).set_duration(scene_dur).set_fps(24)
            # Starting big (1.1) and going small (1.0) = Zoom Out
            clip = clip.resize(lambda t: 1.15 - 0.05 * t).set_position('center')
            clips.append(clip)

        # Step 6: Final Merge
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        final_video = final_video.resize(newsize=(w, h))
        
        out_name = f"ES_Movie_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24)
        return out_name
    except Exception as e:
        return f"Error: {e}"

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
    
    col1, col2 = st.columns([1, 4])
    with col1: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='recorder')
    with col2: up_img = st.file_uploader("➕ Upload Image", type=["jpg", "png"])

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        res = ESSA_BIO if any(k in prompt.lower() for k in ["kisne banaya", "creator", "essa"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai&cache=true").text
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voice Studio")
    vt = st.text_area("Yahan likhein:")
    vl, vg = st.columns(2)
    with vl: lang = st.selectbox("Language:", ["Urdu", "English"])
    with vg: gender = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        vc = "ur-PK-UzmaNeural" if gender == "Female" else "ur-PK-AsadNeural"
        async def sv(): await edge_tts.Communicate(vt, vc).save("temp.mp3")
        asyncio.run(sv()); st.audio("temp.mp3")

with tabs[2]:
    st.header("🎬 Pro Movie Studio v15.0")
    m_script = st.text_area("Movie Script:", height=150, placeholder="Example: Ahmad ne jungle mein ek khazana dhoonda...")
    mv_col, mr_col = st.columns(2)
    with mv_col: m_voice = st.selectbox("Voice Selection:", ["Male", "Female"], index=0)
    with mr_col: m_ratio = st.selectbox("Video Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    if st.button("Generate Cinematic Movie 🚀"):
        if m_script:
            with st.spinner("AI سب ٹائٹلز اور موشن ویڈیو تیار کر رہا ہے..."):
                video = create_pro_movie_with_subs(m_script, m_voice, m_ratio)
                if "mp4" in video:
                    st.video(video)
                    st.success("مبارک ہو! ویڈیو سب ٹائٹلز اور زوم آؤٹ کے ساتھ تیار ہے۔")
                    with open(video, "rb") as f: st.download_button("Download HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v15.0 | Subtitles & Gender Detection Active</p>", unsafe_allow_html=True)
