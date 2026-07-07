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

# Senior Engineer Fix for PIL
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
except Exception as e:
    st.error(f"Engine Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & UI
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 12px; height: 50px; font-weight: bold; border: none; transition: 0.3s;}
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

ESSA_BIO = "مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔ وہ ایک مکینیکل انجینئر اور فیبرکیٹر ہیں۔"

# ==========================================
# 2. THE VISUAL DIRECTOR (GOLDEN RULES)
# ==========================================
def generate_visual_prompt(scene_text):
    """
    Implementation of Character Recognition & Visual Generation Rules.
    This function analyzes text to create accurate image prompts.
    """
    # Detect Character Attributes (Rule 1, 2)
    subject = "a cinematic 3D Pixar style scene"
    if any(k in scene_text for k in ["بچہ", "لڑکا", "احمد", "boy", "kid"]):
        subject = "a cute 3D animated young boy"
    elif any(k in scene_text for k in ["بچی", "لڑکی", "girl"]):
        subject = "a cute 3D animated little girl"
    elif any(k in scene_text for k in ["بوڑھا", "بزرگ", "old man"]):
        subject = "a 3D animated kind old man with white beard"
    elif any(k in scene_text for k in ["عورت", "woman"]):
        subject = "a 3D animated woman"

    # Detect Animals (Rule 3)
    animals = ""
    animal_list = {"شیر": "lion", "ہاتھی": "elephant", "چوہا": "mouse", "بلی": "cat", "کتا": "dog", "پرندہ": "bird", "بندر": "monkey"}
    for k, v in animal_list.items():
        if k in scene_text: animals += f", a realistic 3D {v}"

    # Detect Emotions (Rule 6)
    emotion = ", neutral expression"
    if any(k in scene_text for k in ["رو رہا", "اداس", "sad", "crying"]): emotion = ", crying emotional face, teary eyes"
    elif any(k in scene_text for k in ["ہنس رہا", "خوش", "happy", "laughing"]): emotion = ", joyful laughing face, big smile"
    elif any(k in scene_text for k in ["غصہ", "angry"]): emotion = ", angry aggressive face"
    elif any(k in scene_text for k in ["ڈرا", "خوف", "scared"]): emotion = ", terrified scared eyes"

    # Detect Actions (Rule 7)
    action = ""
    if any(k in scene_text for k in ["دوڑ", "بھاگ", "running"]): action = ", running fast"
    elif any(k in scene_text for k in ["بیٹھا", "sitting"]): action = ", sitting peacefully"
    elif any(k in scene_text for k in ["کھا", "eating"]): action = ", eating food"
    elif any(k in scene_text for k in ["پڑھ", "reading"]): action = ", reading a book"

    # Detect Objects (Rule 4, 5)
    objects = ""
    obj_list = {"بٹوہ": "wallet", "کتاب": "book", "گاڑی": "car", "سائیکل": "bicycle", "درخت": "lush trees", "پھول": "flowers", "گھر": "house"}
    for k, v in obj_list.items():
        if k in scene_text: objects += f", including a {v}"

    # Golden Rule Assembly
    final_prompt = f"{subject}{animals}{action}{emotion}{objects}, cinematic lighting, vibrant 3D animation style, highly detailed, 8k, masterpiece, no humans unless specified, accurate characters"
    return final_prompt

# ==========================================
# 3. MOVIE ENGINE (SCENE SYNC + ZOOM OUT)
# ==========================================
def create_masterpiece_movie(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Professional Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def run_v(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(run_v())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Scene Splitting
        words = story.split()
        num_scenes = 4 if len(words) > 10 else 1
        chunk = max(1, len(words) // num_scenes)
        clips = []

        for i in range(num_scenes):
            st_idx, end_idx = i*chunk, (i+1)*chunk if i != (num_scenes-1) else len(words)
            scene_text = " ".join(words[st_idx:end_idx])
            
            # Applying Golden Rules via generate_visual_prompt
            refined_prompt = generate_visual_prompt(scene_text)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(requests.get(img_url).content)
            
            # Step 4: Add Subtitles & 3D Zoom Out
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, h-80, w, h], fill=(0,0,0,140))
            draw.text((w/2, h-40), scene_text[-50:], fill="white", anchor="ms") # Simple Subtitle
            img.save(img_path)

            clip = ImageClip(img_path).set_duration(voice_audio.duration/num_scenes).set_fps(24)
            # ZOOM OUT Animation (1.1 to 1.0)
            clip = clip.resize(lambda t: 1.12 - 0.04 * t).set_position('center')
            clips.append(clip)

        # Step 5: Final Render
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        final_video = final_video.resize(newsize=(w, h))
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24)
        return out_name
    except Exception as e:
        return f"Technical Error: {e}"

# ==========================================
# 4. MAIN UI
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold; letter-spacing: 5px;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    prompt = st.chat_input("Hukum karein Essa bhai...")
    if prompt:
        res = ESSA_BIO if "essa" in prompt.lower() else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai&cache=true").text
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"): st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

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
    st.header("🎬 Master Cinematic Studio v16.0")
    st.info("آپ کے تمام 'Golden Rules' اب اس انجن میں شامل کر دیے گئے ہیں۔")
    m_script = st.text_area("Movie Script:", height=150, placeholder="مثال: احمد باغ میں بیٹھا رو رہا تھا، اس کا بٹوہ گم ہو گیا تھا۔")
    mv_col, mr_col = st.columns(2)
    with mv_col: m_voice = st.selectbox("Voice:", ["Male", "Female"])
    with mr_col: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    if st.button("Generate Master Movie 🚀"):
        if m_script:
            with st.spinner("قوانین کے مطابق مناظر تیار ہو رہے ہیں..."):
                video = masterpiece_movie = create_masterpiece_movie(m_script, m_voice, m_ratio)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v16.0 | Golden Rules Engine Active</p>", unsafe_allow_html=True)
