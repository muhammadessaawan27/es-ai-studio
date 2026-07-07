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
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & PREMIUM DESIGN
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
        color: white; border-radius: 12px; height: 50px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.01); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# Creator Biography
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# ==========================================
# 2. THE VISUAL DIRECTOR (GOLDEN RULES + STYLES)
# ==========================================
def generate_visual_prompt(scene_text, style_choice, custom_style=""):
    """
    Combines Style Selection with 11 Character Recognition Rules.
    """
    # Define Styles (Requirement 1-8)
    style_prompts = {
        "Realistic": "high-end photorealistic photography, real life, 8k resolution, highly detailed skin textures, natural lighting",
        "Cinematic": "professional movie scene, anamorphic lens, dramatic lighting, cinematic color grading, masterpiece, 8k",
        "3D Cartoon": "3D Disney Pixar animation style, adorable features, smooth surfaces, vibrant cinematic colors",
        "Anime": "modern high-quality anime style, hand-drawn aesthetic, vibrant colors, Makoto Shinkai style, expressive eyes",
        "Illustration / Digital Art": "vibrant digital art, concept illustration, artistic brush strokes, detailed painting",
        "Sketch": "detailed pencil sketch, charcoal drawing, hand-drawn on textured paper, black and white artistic",
        "Kids Cartoon": "simple flat 2D cartoon style, bright primary colors, friendly characters, thick outlines, storybook style",
        "Custom": custom_style
    }
    
    active_style = style_prompts.get(style_choice, style_prompts["Realistic"])

    # Character Logic (Rule 1-2)
    subject = "a cinematic scene"
    if any(k in scene_text for k in ["بچہ", "لڑکا", "احمد", "boy", "kid"]):
        subject = "a young boy character"
    elif any(k in scene_text for k in ["بچی", "لڑکی", "girl"]):
        subject = "a little girl character"
    elif any(k in scene_text for k in ["بوڑھا", "بزرگ", "old man"]):
        subject = "a kind old man with white beard"
    elif any(k in scene_text for k in ["عورت", "woman"]):
        subject = "a woman character"

    # Animals (Rule 3)
    animals = ""
    animal_list = {"شیر": "lion", "ہاتھی": "elephant", "چوہا": "mouse", "بلی": "cat", "کتا": "dog", "پرندہ": "bird", "بندر": "monkey"}
    for k, v in animal_list.items():
        if k in scene_text: animals += f", a {v}"

    # Emotions (Rule 6)
    emotion = ""
    if any(k in scene_text for k in ["رو رہا", "اداس", "sad", "crying"]): emotion = ", crying emotional face"
    elif any(k in scene_text for k in ["ہنس رہا", "خوش", "happy", "laughing"]): emotion = ", joyful smiling face"
    elif any(k in scene_text for k in ["غصہ", "angry"]): emotion = ", angry aggressive face"

    # Actions & Objects (Rule 4, 5, 7)
    action_obj = ""
    if any(k in scene_text for k in ["دوڑ", "running"]): action_obj += ", running"
    elif any(k in scene_text for k in ["بیٹھا", "sitting"]): action_obj += ", sitting"
    
    obj_list = {"بٹوہ": "wallet", "کتاب": "book", "درخت": "lush trees", "گھر": "house"}
    for k, v in obj_list.items():
        if k in scene_text: action_obj += f", featuring a {v}"

    # Assembly (Golden Rule)
    final_prompt = f"{active_style}, {subject}{animals}{emotion}{action_obj}, highly detailed, {active_style}, no text, no blur, masterpiece"
    return final_prompt

# ==========================================
# 3. MOVIE ENGINE (SCENE SYNC + ZOOM OUT)
# ==========================================
def create_masterpiece_movie(story, voice_gen, ratio, style_choice, custom_style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Voice
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
        num_scenes = 4 if len(words) > 10 else 1
        chunk = max(1, len(words) // num_scenes)
        clips = []

        for i in range(num_scenes):
            st_idx, end_idx = i*chunk, (i+1)*chunk if i != 3 else len(words)
            scene_text = " ".join(words[st_idx:end_idx])
            
            # Apply Style + Golden Rules
            refined_prompt = generate_visual_prompt(scene_text, style_choice, custom_style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            img_data = requests.get(img_url).content
            with open(img_path, "wb") as f: f.write(img_data)
            
            # Subtitles & Zoom Out
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, h-80, w, h], fill=(0,0,0,140))
            draw.text((w/2, h-40), scene_text[-50:], fill="white", anchor="ms") 
            img.save(img_path)

            clip = ImageClip(img_path).set_duration(voice_audio.duration/num_scenes).set_fps(24)
            # Professional ZOOM OUT (1.12 to 1.0)
            clip = clip.resize(lambda t: 1.12 - 0.04 * t).set_position('center')
            clips.append(clip)

        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        final_video = final_video.resize(newsize=(w, h))
        out_name = f"ES_AI_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24)
        return out_name
    except Exception as e:
        return f"Technical Error: {e}"

# ==========================================
# 4. MAIN UI DASHBOARD
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold; letter-spacing: 5px;'>MUHAMMAD ESSA'S OFFICIAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Chat & Vision", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    col1, col2 = st.columns([1, 4])
    with col1: mic_recorder(start_prompt="🎙️ Speak", stop_prompt="🛑 Stop", key='recorder')
    with col2: up_img = st.file_uploader("➕ Upload Image", type=["jpg", "png"])

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        if any(k in prompt.lower() for k in ["kisne banaya", "creator", "essa"]):
            res = ESSA_BIO
        else:
            encoded_q = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded_q}?model=openai&cache=true"
            try:
                r = requests.get(url, timeout=30)
                res = r.text if r.status_code == 200 else "AI سرور مصروف ہے۔"
            except: res = "Connection Error."
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voice Studio")
    vt = st.text_area("Yahan wo likhein jo AI se bulwana hai:")
    vl, vg = st.columns(2)
    with vl: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with vg: gender = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀", key="v_btn"):
        if vt:
            vc = "ur-PK-UzmaNeural" if gender == "Female" else "ur-PK-AsadNeural"
            async def run_v(): await edge_tts.Communicate(vt, vc).save("temp.mp3")
            asyncio.run(run_v()); st.audio("temp.mp3")

with tabs[2]:
    st.header("🎬 Pro Movie Studio v17.0")
    m_script = st.text_area("Movie Script:", height=150, placeholder="Example: Jungle mein sher aur hathi dost ban gaye...")
    
    col_v, col_r, col_s = st.columns(3)
    with col_v: m_voice = st.selectbox("Voice:", ["Male", "Female"])
    with col_r: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col_s: m_style = st.selectbox("Visual Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Illustration / Digital Art", "Sketch", "Kids Cartoon", "Custom"])

    custom_style_txt = ""
    if m_style == "Custom":
        custom_style_txt = st.text_input("Enter your custom style description:")

    if st.button("Generate Master Movie 🚀"):
        if m_script:
            with st.spinner(f"AI {m_style} اسٹائل میں مووی تیار کر رہا ہے..."):
                video = create_masterpiece_movie(m_script, m_voice, m_ratio, m_style, custom_style_txt)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio v17.0 | Advanced Style Selector Active</p>", unsafe_allow_html=True)
