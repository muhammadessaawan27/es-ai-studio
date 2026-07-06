import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. CORE CONFIGURATION & BRANDING
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
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. IDENTITY DATA
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def check_identity(query):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"creator", r"essa awan", r"muhammad essa"]
    return any(re.search(p, query.lower(), re.IGNORECASE) for p in patterns) if query else False

# ==========================================
# 3. ROBUST AI CHAT ENGINE
# ==========================================
def get_ai_response(query, history):
    if check_identity(query): return ESSA_BIO
    
    encoded = urllib.parse.quote(query)
    # Silent Retry Logic with multiple fallback engines
    urls = [
        f"https://text.pollinations.ai/{encoded}?model=openai&cache=true",
        f"https://hercai.onrender.com/v3/hercai?question={encoded}"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                return r.json().get('reply') if 'hercai' in url else r.text
        except: continue
    return "معذرت، ابھی سرور جواب نہیں دے رہا۔ براہ کرم دوبارہ کوشش کریں۔"

# ==========================================
# 4. UI INTERFACE (TABS)
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MASTER STUDIO</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 Smart Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

# --- TAB 1: CHAT ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    st.write("🎙️ **Voice Typing:**")
    audio_rec = mic_recorder(start_prompt="Click to Speak", stop_prompt="Stop", key='recorder')
    
    prompt = st.chat_input("مجھ سے کچھ بھی پوچھیں...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Souch raha hoon..."):
                res = get_ai_response(prompt, st.session_state.messages)
                st.write(res)
                st.session_state.messages.append({"role": "assistant", "content": res})

# --- TAB 2: VOICE ---
with tabs[1]:
    st.header("🎙️ Voice Studio")
    v_text = st.text_area("متن لکھیں:", height=100)
    c1, c2 = st.columns(2)
    with c1: v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: v_gen = st.selectbox("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        if v_text:
            v_map = {"Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                     "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                     "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}}
            v_code = v_map[v_lang][v_gen]
            async def sv(): await edge_tts.Communicate(v_text, v_code).save("temp_v.mp3")
            asyncio.run(sv())
            st.audio("temp_v.mp3")
            with open("temp_v.mp3", "rb") as f: st.download_button("Download Audio", f, file_name="voice.mp3")

# --- TAB 3: MOVIE STUDIO (THE FIX) ---
with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    st.info("Bhai Essa, یہاں کہانی لکھیں، میں اسی ویب سائٹ پر ویڈیو بناؤں گا۔")
    m_script = st.text_area("Movie Script:", height=150, placeholder="ایک جنگل کی کہانی...")
    m_ratio = st.selectbox("Video Size:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    
    if st.button("Generate Video Now 🚀"):
        if m_script:
            with st.spinner("ویڈیو تیار ہو رہی ہے... اس میں 1 منٹ لگ سکتا ہے۔"):
                try:
                    # 1. Generate Voice
                    async def gv(): await edge_tts.Communicate(m_script, "ur-PK-UzmaNeural").save("m_audio.mp3")
                    asyncio.run(gv())
                    audio = AudioFileClip("m_audio.mp3")
                    
                    # 2. Generate 2 Images for Slideshow
                    img_urls = [
                        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_script[:50])}?width=1280&height=720&nologo=true",
                        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(m_script[50:100])}?width=1280&height=720&nologo=true"
                    ]
                    
                    clips = []
                    for i, url in enumerate(img_urls):
                        img_data = requests.get(url).content
                        with open(f"img_{i}.jpg", "wb") as f: f.write(img_data)
                        clip = ImageClip(f"img_{i}.jpg").set_duration(audio.duration/2).set_fps(24)
                        clips.append(clip)
                    
                    # 3. Create Video
                    final_vid = concatenate_videoclips(clips, method="compose").set_audio(audio)
                    # Resize according to ratio
                    if m_ratio == "TikTok/Reels (9:16)": final_vid = final_vid.resize(height=1280, width=720)
                    elif m_ratio == "Instagram (1:1)": final_vid = final_vid.resize(height=720, width=720)
                    else: final_vid = final_vid.resize(height=720, width=1280)
                    
                    final_vid.write_videofile("es_movie.mp4", codec="libx264", audio_codec="aac")
                    
                    st.video("es_movie.mp4")
                    with open("es_movie.mp4", "rb") as f:
                        st.download_button("Download Movie ⬇️", f, file_name="es_ai_movie.mp4")
                    st.success("مبارک ہو! ویڈیو بن گئی ہے۔")
                except Exception as e:
                    st.error(f"ویڈیو بنانے میں مسئلہ ہوا: {str(e)}")
        else:
            st.warning("پہلے کہانی لکھیں۔")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio | Muhammad Essa Awan</p>", unsafe_allow_html=True)
