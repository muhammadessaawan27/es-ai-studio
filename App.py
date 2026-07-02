import streamlit as st
import asyncio
import edge_tts

# --- ES AI BRANDING ---
st.set_page_config(page_title="ES AI Master Studio", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00d4ff; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 70px; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: white; letter-spacing: 5px;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# Functions
async def generate_voice(text, v_code):
    communicate = edge_tts.Communicate(text, v_code)
    await communicate.save("voice.mp3")
    return "voice.mp3"

# TAB 1: Chat
with tab1:
    st.header("💬 Chat with ES AI")
    msg = st.chat_input("Hukum karein Essa bhai...")
    if msg:
        st.chat_message("user").write(msg)
        st.chat_message("assistant").write(f"Bhai Muhammad Essa, main aapka agent hoon. Aapne poocha: {msg}")

# TAB 2: Voice
with tab2:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("Likhein jo AI se bulwana hai:")
    v_gen = st.radio("Gender:", ["Female", "Male"])
    if st.button("Generate Voice 🚀"):
        v_code = "ur-PK-UzmaNeural" if v_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = asyncio.run(generate_voice(v_text, v_code))
        st.audio(audio_file)

# TAB 3: Studio
with tab3:
    st.header("🎬 Pro Movie Studio")
    st.write("Bhai, aapka Link ab active ho raha hai! Movie engine hum isi dashboard mein jorhenge.")
