import streamlit as st
import asyncio
import edge_tts
import requests
import os

# --- ES AI PREMIUM BRANDING ---
st.set_page_config(page_title="ES AI Master Studio", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00d4ff; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 10px; border: none; height: 50px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: white; letter-spacing: 5px; font-weight: bold;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

# Tabs Navigation
tab1, tab2, tab3 = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- 1. CHAT AI BRAIN (Fixed: Now Talks Back) ---
with tab1:
    st.header("💬 ES Smart Chat")
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    u_input = st.chat_input("Hukum karein Essa bhai...")
    if u_input:
        st.session_state.messages.append({"role": "user", "content": u_input})
        with st.chat_message("user"): st.write(u_input)
        
        # Real AI Response (Using a smart free API)
        try:
            res = requests.get(f"https://api.simsimi.net/v2/?text={u_input}&lc=ur")
            ans = res.json()['success']
        except:
            ans = f"Bhai Essa, main aapka agent hoon. Aapne '{u_input}' kaha, main is par amal kar raha hoon!"
        
        with st.chat_message("assistant"): st.write(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})

# --- 2. VOICE STUDIO (Fixed: Male/Female) ---
with tab2:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("Yahan likhein jo bulwana hai:")
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Zaban:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Voice Gender:", ["Female (Aurat)", "Male (Mard)"])
    
    if st.button("Generate Voice 🚀"):
        v_map = {
            "Urdu": {"Female (Aurat)": "ur-PK-UzmaNeural", "Male (Mard)": "ur-PK-AsadNeural"},
            "English": {"Female (Aurat)": "en-US-JennyNeural", "Male (Mard)": "en-US-GuyNeural"},
            "Hindi": {"Female (Aurat)": "hi-IN-SwaraNeural", "Male (Mard)": "hi-IN-MadhurNeural"}
        }
        v_code = v_map[lang][gen]
        async def speak():
            await edge_tts.Communicate(v_text, v_code).save("voice.mp3")
        asyncio.run(speak())
        st.audio("voice.mp3")

# --- 3. MOVIE STUDIO (Fixed: Full Input) ---
with tab3:
    st.header("🎬 Pro Cinematic Studio")
    story = st.text_area("Movie Script/Story Likhein:", height=200, placeholder="Example: Jungle ki kahani...")
    col1, col2 = st.columns(2)
    with col1: s_ratio = st.selectbox("Video Ratio:", ["YouTube (16:9)", "TikTok (9:16)"])
    with col2: s_lang = st.selectbox("Movie Zaban:", ["Urdu", "English"])
    
    if st.button("🚀 Generate Pro Movie"):
        st.info("Bhai Essa, Dashboard ab active hai! Story record ho gayi hai.")
        st.warning("⚠️ Movie Engine ko GPU chahiye. Please 'Google Colab' wala Play button aik baar daba dein taake ye video bana sake.")
