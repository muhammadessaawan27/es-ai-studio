import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import random  # Senior Engineer Fix: Added missing library
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from streamlit_mic_recorder import mic_recorder

# Senior Engineer Fix: Patch for Image attribute error
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# ==========================================
# 1. PREMIUM BRANDING & DESIGN
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
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 20px; font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
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

def check_identity(query):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa awan", r"muhammad essa", r"maker", r"owner"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns) if query else False

# ==========================================
# 2. ADVANCED CHAT ENGINE (NO LIMITS)
# ==========================================
def get_ai_response(query):
    if check_identity(query): return ESSA_BIO
    encoded = urllib.parse.quote(query)
    system_instr = urllib.parse.quote("You are ES AI created by Muhammad Essa Awan. Answer professionally.")
    url = f"https://text.pollinations.ai/{encoded}?model=openai&cache=true&system={system_instr}"
    try:
        r = requests.get(url, timeout=30)
        return r.text if r.status_code == 200 else "سرور مصروف ہے، دوبارہ کوشش کریں۔"
    except: return "کنکشن کا مسئلہ ہے، انٹرنیٹ چیک کریں۔"

# ==========================================
# 3. MULTI-SCENE CINEMATIC VIDEO ENGINE
# ==========================================
def create_cinematic_movie(story, voice_gen, ratio):
    try:
        # Unique User ID
        u_id = str(uuid.uuid4())[:8]
        
        # Step 1: Voice Generation
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_voice.mp3"
        async def gv():
            await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        audio = AudioFileClip(audio_file)
        full_duration = audio.duration

        # Step 2: Split story into 4 Scenes
        words = story.split()
        num_scenes = 4
        chunk = max(1, len(words) // num_scenes)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        clips = []
        for i in range(num_scenes):
            start_idx = i * chunk
            end_idx = (i + 1) * chunk if i != 3 else len(words)
            scene_text = " ".join(words[start_idx : end_idx])
            
            # High-Quality Cinematic Prompt
            prompt = f"Cinematic 3D animation, {scene_text[:80]}, high detail, 8k, realistic lighting, masterpiece, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}"
            
            img_path = f"{u_id}_img_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(requests.get(img_url).content)
            
            # Step 3: Scene Motion (Slow Zoom)
            scene_duration = full_duration / num_scenes
            clip = ImageClip(img_path).set_duration(scene_duration).set_fps(24)
            clip = clip.resize(lambda t: 1 + 0.04 * t).set_position('center')
            clips.append(clip)

        # Step 4: Combine Everything
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        final_video = final_video.resize(newsize=(w, h))
        
        output_name = f"ES_AI_Movie_{u_id}.mp4"
        final_video.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24)
        
        return output_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; font-weight: bold; letter-spacing: 3px;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Cinematic Movie Studio"])

with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    mic_recorder(start_prompt="Record Message", stop_prompt="Stop", key='recorder')
    prompt = st.chat_input("Hukum karein Essa bhai...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("ES AI Souch raha hai..."):
                res = get_ai_response(prompt)
                st.write(res)
                st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("Voiceover Studio (M/F)")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:", height=100)
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Awaaz:", ["Female", "Male"])
    if st.button("Generate Audio 🚀", key="tab2_btn"):
        if v_text:
            v_code = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
            async def sv(): await edge_tts.Communicate(v_text, v_code).save("v_out.mp3")
            asyncio.run(sv())
            st.audio("v_out.mp3")

with tabs[2]:
    st.header("Cinematic Movie Studio (Multi-Scene)")
    m_script = st.text_area("Apni Movie ki Story Likhein:", height=150)
    col_v, col_r = st.columns(2)
    with col_v: m_voice = st.selectbox("Voice Selection:", ["Female", "Male"], key="mv_gen")
    with col_r: m_ratio = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr_sel")

    if st.button("Generate Master Movie 🚀", key="mv_btn"):
        if m_script:
            with st.spinner("AI مناظر تیار کر رہا ہے۔۔۔ اس میں تھوڑا وقت لگ سکتا ہے۔"):
                video_file = create_cinematic_movie(m_script, m_voice, m_ratio)
                if "mp4" in video_file:
                    st.video(video_file)
                    with open(video_file, "rb") as f:
                        st.download_button("Download HD Video ⬇️", f, file_name=video_file)
                    st.success("مبارک ہو! ملٹی سین مووی تیار ہے۔")
                else: st.error(video_file)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio v9.1 | Fixed Undefined Random Error</p>", unsafe_allow_html=True)
