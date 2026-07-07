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

# Senior Engineer Speed & Quality Optimization
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"System Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & UI (Muhammad Essa Master Studio)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 12px; height: 55px; font-weight: bold; border: none; transition: 0.2s;}
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

# ==========================================
# 2. THE AI VISUAL DIRECTOR (UNIVERSAL RECOGNITION)
# ==========================================
def get_universal_visual_prompt(urdu_text, style_choice):
    """
    This function uses a secret AI call to translate and enhance the visual 
    description of ANY object, animal or building mentioned in Urdu.
    """
    try:
        # Secret background AI call to translate and describe the scene
        # It detects animals, buildings, and concepts automatically
        refiner_prompt = f"Convert this Urdu description into a highly detailed English visual prompt for AI image generation. Identify all animals, buildings, characters, and emotions: '{urdu_text}'. Output only the English prompt."
        encoded_refiner = urllib.parse.quote(refiner_prompt)
        
        director_res = requests.get(f"https://text.pollinations.ai/{encoded_refiner}?model=openai&cache=true", timeout=15)
        visual_description = director_res.text if director_res.status_code == 200 else urdu_text
        
        # Adding Style and Quality
        final_prompt = f"{style_choice} style, {visual_description}, cinematic lighting, masterpiece, 8k, highly detailed textures, vibrant colors, no text, no distorted faces"
        return final_prompt
    except:
        return f"{style_choice} style, {urdu_text}, masterpiece, 8k"

# ==========================================
# 3. HIGH-SPEED PRO MOVIE ENGINE
# ==========================================
def create_universal_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Human Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: Ratio Settings
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Processing
        sentences = re.split(r'[۔.!]', story)
        sentences = [s.strip() for s in sentences if len(s) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            # Universal Recognition Logic
            prompt = get_universal_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,1000000)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            img_data = requests.get(img_url).content
            with open(img_path, "wb") as f: f.write(img_data)
            
            # Step 4: ZOOM OUT Animation (1.15 to 1.0) - No black borders
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            clip = clip.resize(newsize=(w, h)) # Auto Fill
            clip = clip.resize(lambda t: 1.15 - 0.07 * (t/dur_per)).set_position('center')
            clips.append(fadein(clip, 0.4))

        # Final Render with high-speed settings
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Universal_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. MAIN UI INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>THE FUTURE OF AI CINEMATOGRAPHY</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

# --- CHAT TAB ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    col_a, col_b = st.columns([1, 4])
    with col_a: mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key='mic')
    with col_b: st.file_uploader("➕", type=["jpg", "png"], key="up")

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        # Creator Identity Guard
        if any(k in prompt.lower() for k in ["kisne banaya", "creator", "essa", "maker"]):
            res = ESSA_BIO
        else:
            res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai&cache=true").text
            
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

# --- MOVIE STUDIO TAB ---
with tabs[2]:
    st.header("🎬 Pro Universal Movie Studio v20.0")
    st.info("اب اے آئی ہر لفظ کو پہچانے گا، چاہے وہ کوئی بھی جانور ہو یا دنیا کی کوئی بھی عمارت۔")
    m_script = st.text_area("Movie Script:", height=150, placeholder="یہاں اپنی کہانی لکھیں (مثال: ایفل ٹاور کے پاس ایک عقاب اڑ رہا تھا...)")
    
    c1, c2, c3 = st.columns(3)
    with c1: m_voice = st.selectbox("Voice:", ["Male", "Female"])
    with c2: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: m_style = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Universal Master Movie"):
        if m_script:
            with st.spinner("اے آئی ڈائریکٹر منظر کو سمجھ رہا ہے اور ویڈیو رینڈر کر رہا ہے..."):
                video = create_universal_movie(m_script, m_voice, m_ratio, m_style)
                if "mp4" in video:
                    st.video(video)
                    st.success("مبارک ہو! آپ کا شاہکار تیار ہے۔")
                    with open(video, "rb") as f: st.download_button("Download Full HD", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v20.0 | High-Speed Global Vision Engine | Muhammad Essa Awan</p>", unsafe_allow_html=True)
