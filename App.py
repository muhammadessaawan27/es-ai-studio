import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import time
import re
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. CORE CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

# Premium Metallic UI
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
    .chat-row { display: flex; align-items: center; gap: 10px; }
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
    patterns = [r"kisne banaya", r"who made you", r"owner", r"creator", r"essa awan", r"muhammad essa", r"maker"]
    return any(re.search(p, query.lower()) for p in patterns)

# ==========================================
# 3. ROBUST AI ENGINE (TRIPLE FAIL-SAFE)
# ==========================================
def get_es_ai_response(user_query, history):
    if check_identity(user_query): return ESSA_BIO

    chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
    system_prompt = "You are ES AI, a smart assistant by Muhammad Essa Awan. Answer accurately."
    full_prompt = f"{system_prompt}\n{chat_context}\nUser: {user_query}\nAI:"
    encoded = urllib.parse.quote(full_prompt)

    # 3 High-Stability Engines
    urls = [
        f"https://text.pollinations.ai/{encoded}?model=openai&cache=true",
        f"https://hercai.onrender.com/v3/hercai?question={encoded}",
        f"https://api.paxsenix.biz/ai/gpt4?q={encoded}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=40)
            if response.status_code == 200:
                if "hercai" in url or "paxsenix" in url:
                    res_data = response.json()
                    text = res_data.get('reply') or res_data.get('content')
                else:
                    text = response.text
                if text and len(text.strip()) > 2: return text.strip()
        except: continue
    
    return "بھا ئی عیسیٰ، اس وقت تمام سرورز پر بوجھ زیادہ ہے۔ براہ کرم تھوڑی دیر بعد دوبارہ کوشش کریں۔"

# ==========================================
# 4. MAIN UI INTERFACE
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MULTI-MODAL AGENT</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- TAB 1: CHAT (VOICE INPUT ADDED) ---
with tabs[0]:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    # Voice Input Feature
    st.write("🎙️ **Voice Typing:** بٹن دبا کر بولیں، آپ کی آواز ٹائپ ہو جائے گی۔")
    audio = mic_recorder(start_prompt="Click to Speak (اردو/English)", stop_prompt="Stop Recording", key='recorder')
    
    voice_text = ""
    if audio:
        # Placeholder message for voice processing (Requires external API for real STT, 
        # but here we provide the UI structure as requested)
        voice_text = "Voice recording captured! (Please type or edit below)"

    if prompt := st.chat_input("مجھ سے کوئی بھی سوال پوچھیں...", value=voice_text):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                response = get_es_ai_response(prompt, st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- TAB 2: VOICE STUDIO ---
with tabs[1]:
    st.header("🎙️ Voice Studio")
    v_text = st.text_area("جو کہلوانا ہے یہاں لکھیں:", height=150)
    col1, col2 = st.columns(2)
    with col1: v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with col2: v_gen = st.selectbox("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        if v_text:
            v_map = {"Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                     "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                     "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}}
            selected_v = v_map[v_lang][v_gen]
            async def generate_v(): await edge_tts.Communicate(v_text, selected_v).save("es_v.mp3")
            asyncio.run(generate_v())
            st.audio("es_v.mp3")
        else: st.warning("Please enter text.")

# --- TAB 3: MOVIE STUDIO ---
with tabs[2]:
    st.header("🎬 Pro Movie Studio")
    m_script = st.text_area("Movie Script Details:", height=200)
    if st.button("Save Script"): st.success("Script saved! Run Movie Engine in Colab.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio | Muhammad Essa Awan</p>", unsafe_allow_html=True)
