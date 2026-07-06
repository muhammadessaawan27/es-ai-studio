import streamlit as st
import asyncio
import edge_tts
import requests

# --- ES AI PREMIUM BRANDING ---
st.set_page_config(page_title="ES AI Master Studio", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- NEW SMART CHAT LOGIC (No More Name Repeating) ---
def get_intelligent_response(text):
    try:
        # Aik behtar aur free AI engine jo dhang se jawab deta hai
        url = f"https://api.popcat.xyz/chatbot?msg={text}"
        res = requests.get(url).json()
        return res['response']
    except:
        return "Bhai, main aapka hukum sun raha hoon. Aap kaise hain?"

with tab1:
    st.header("💬 ES AI Assistant")
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]): st.write(chat["content"])

    user_msg = st.chat_input("Hukum karein Essa bhai...")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"): st.write(user_msg)
        
        # AI Intelligent Response
        with st.spinner("Souch raha hoon..."):
            answer = get_intelligent_response(user_msg)
            with st.chat_message("assistant"): st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

with tab2:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:")
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Zaban:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Voice Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        v_map = {
            "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
            "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
            "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
        }
        v_code = v_map[lang][gen]
        async def speak():
            await edge_tts.Communicate(v_text, v_code).save("es_voice.mp3")
        asyncio.run(speak())
        st.audio("es_voice.mp3")

with tab3:
    st.header("🎬 Pro Movie Studio")
    story = st.text_area("Movie Script/Story Likhein:", height=150)
    ratio = st.selectbox("Size:", ["YouTube (16:9)", "TikTok (9:16)"])
    st.info("Story record ho gayi hai. Video Render karne ke liye Colab chalayein.")
