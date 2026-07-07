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

# Senior Engineer Fix: Persistent Session for stability
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & UI
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
# 2. VISUAL DIRECTOR (ROBUST PROMPT)
# ==========================================
def get_pro_visual_prompt(urdu_text, style_choice):
    try:
        refiner = f"Describe this Urdu scene in detailed English for AI image generation, focus on objects/animals/emotions: '{urdu_text}'. Cinematic, 8k, no text."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(refiner)}?model=openai&cache=true"
        res = session.get(url, timeout=30)
        return f"{style_choice} style, {res.text if res.status_code == 200 else urdu_text}, masterpiece, ultra-detailed"
    except:
        return f"{style_choice} style, {urdu_text}, cinematic 8k"

# ==========================================
# 3. HIGH-STABILITY MOVIE ENGINE (RETRY LOGIC)
# ==========================================
def create_ultimate_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Secure Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Format
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            prompt = get_pro_visual_prompt(scene, style)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            
            # --- SENIOR ENGINEER RETRY LOGIC ---
            success = False
            for attempt in range(3): # Try 3 times
                try:
                    with session.get(img_url, timeout=120, stream=True) as r: # Massive 120s timeout
                        if r.status_code == 200:
                            with open(img_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                            # PIL Cleanup to avoid avcodec errors
                            Image.open(img_path).convert("RGB").save(img_path, "JPEG")
                            success = True
                            break
                except:
                    time.sleep(2) # Wait 2s before retrying
                    continue
            
            if success:
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                clip = clip.resize(lambda t: 1.15 - 0.08 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        if not clips: raise ValueError("Server was too slow even after retries.")

        # Final Render
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_Final_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
        
        return out_name
    except Exception as e:
        return f"Technical Update Needed: {str(e)}"

# ==========================================
# 4. DASHBOARD
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>ULTIMATE MULTI-MODAL STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 AI Agent Chat", "🎙️ Voice Studio", "🎬 Pro Movie Studio"])

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
        res = ESSA_BIO if any(k in prompt.lower() for k in ["kisne banaya", "creator", "essa"]) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model=openai", timeout=30).text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Voiceover Generator")
    vt = st.text_area("Yahan likhein:")
    vl, vg = st.columns(2)
    with vl: lang = st.selectbox("Language:", ["Urdu", "English"])
    with vg: gender = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        vc = "ur-PK-UzmaNeural" if gender == "Female" else "ur-PK-AsadNeural"
        async def sv(): await edge_tts.Communicate(vt, vc).save("es_v.mp3")
        asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.header("🎬 Pro Cinematic Studio v22.0")
    m_script = st.text_area("Movie Script:", height=150, placeholder="Example: Ek bahadur larka...")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Final Master Movie"):
        if m_script:
            with st.spinner("AI سرور سے رابطہ کر رہا ہے اور ڈیٹا ویریفائی کر رہا ہے۔۔۔"):
                video = create_ultimate_movie(m_script, mv, mr, ms)
                if "mp4" in video:
                    st.video(video)
                    with open(video, "rb") as f: st.download_button("Download Full HD", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v22.0 | Advanced Timeout & Retry Engine | Muhammad Essa Awan</p>", unsafe_allow_html=True)
