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
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, afx

# Senior Engineer Fix for PIL
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

# ==========================================
# 1. DESIGN & BRANDING
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
# 2. AUDIO & MUSIC LOGIC
# ==========================================
def get_bgm(story_text):
    # Mood based music selection
    text = story_text.lower()
    if any(k in text for k in ["jungle", "sher", "animal", "nature"]):
        return "https://www.chosic.com/wp-content/uploads/2021/07/The-Wild-Animals.mp3"
    elif any(k in text for k in ["king", "badshah", "warrior", "history"]):
        return "https://www.chosic.com/wp-content/uploads/2020/06/Epic-Adventure.mp3"
    else:
        return "https://www.chosic.com/wp-content/uploads/2021/04/Inspiring-Story.mp3"

# ==========================================
# 3. ADVANCED MOVIE ENGINE (SCENE SYNC + ZOOM OUT)
# ==========================================
def create_professional_movie(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    try:
        # Step 1: Human Voice
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def generate_v(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(generate_v())
        voice_audio = AudioFileClip(audio_file)
        
        # Step 2: Download BGM
        bgm_url = get_bgm(story)
        bgm_path = f"{u_id}_bgm.mp3"
        with open(bgm_path, "wb") as f: f.write(requests.get(bgm_url).content)
        bgm_audio = AudioFileClip(bgm_path).volumex(0.15).set_duration(voice_audio.duration) # Low volume

        # Step 3: Multi-Scene Generation
        words = story.split()
        num_scenes = 4
        chunk = max(1, len(words) // num_scenes)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        clips = []
        for i in range(num_scenes):
            scene_text = " ".join(words[i*chunk : (i+1)*chunk])
            # High-relevance prompt detection
            prompt = f"Professional 3D cinematic scene of {scene_text[:100]}, highly detailed, masterpiece, 8k, vibrant lighting, no text"
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true"
            
            img_path = f"{u_id}_{i}.jpg"
            with open(img_path, "wb") as f: f.write(requests.get(img_url).content)
            
            # Step 4: Zoom Out Animation (The Pro Look)
            duration = voice_audio.duration / num_scenes
            clip = ImageClip(img_path).set_duration(duration).set_fps(24)
            # Zoom Out Logic: Start big (1.1) and go small (1.0)
            clip = clip.resize(lambda t: 1.1 - 0.04 * t).set_position('center')
            clips.append(clip)

        # Step 5: Final Merge
        final_video = concatenate_videoclips(clips, method="compose")
        final_audio = CompositeAudioClip([voice_audio, bgm_audio])
        final_video = final_video.set_audio(final_audio).resize(newsize=(w, h))
        
        output_name = f"ES_Final_{u_id}.mp4"
        final_video.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24)
        return output_name
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
    
    st.write("---")
    col1, col2 = st.columns([1, 3])
    with col1: mic_recorder(start_prompt="🎙️ Speak", stop_prompt="🛑 Stop", key='recorder')
    with col2: uploaded_img = st.file_uploader("➕ Upload Image", type=["jpg", "png"])

    if prompt := st.chat_input("Hukum karein Essa bhai..."):
        if any(k in prompt.lower() for k in ["kisne banaya", "creator", "essa", "maker"]):
            res = ESSA_BIO
        else:
            encoded_q = urllib.parse.quote(prompt)
            res = requests.get(f"https://text.pollinations.ai/{encoded_q}?model=openai&cache=true").text
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

with tabs[1]:
    st.header("🎙️ Professional Voiceover")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:", height=100)
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        v_code = "ur-PK-UzmaNeural" if gen == "Female" else "ur-PK-AsadNeural"
        async def sv(): await edge_tts.Communicate(v_text, v_code).save("es_v.mp3")
        asyncio.run(sv()); st.audio("es_v.mp3")

with tabs[2]:
    st.header("🎬 Pro Cinematic Movie Studio")
    m_script = st.text_area("Apni Movie ki Story Likhein:", height=150, placeholder="Example: Ek bahadur Badshah ki dastan...")
    mv_col, mr_col = st.columns(2)
    with mv_col: m_voice = st.selectbox("Voice Selection:", ["Male", "Female"])
    with mr_col: m_ratio = st.selectbox("Video Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    if st.button("Generate Master Movie 🚀"):
        if m_script:
            with st.spinner("AI مناظر، موسیقی اور اینیمیشن تیار کر رہا ہے..."):
                video = create_professional_movie(m_script, m_voice, m_ratio)
                if "mp4" in video:
                    st.video(video)
                    st.success("مبارک ہو! ویڈیو موسیقی اور موشن کے ساتھ تیار ہے۔")
                    with open(video, "rb") as f: st.download_button("Download HD Video", f, file_name=video)
                else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v12.0 | Professional Cinematography & Auto-BGM Enabled</p>", unsafe_allow_html=True)
