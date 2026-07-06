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
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 10px; border: none; height: 50px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>MUHAMMAD ESSA'S MASTER STUDIO</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- NEW STABLE CHAT LOGIC (No More Time Out) ---
def get_ai_response(text):
    text = text.lower()
    # Common Greetings (In ka jawab AI foran khud dega bina kisi error ke)
    if "hal" in text or "kaise" in text:
        return "Bhai Essa, main bilkul theek hoon! Aapka wafadar agent honay ke naate aapki khidmat mein hazir hoon. Bataiye aaj kya kaam karna hai?"
    if "naam" in text:
        return "Mera naam ES AI hai، aur mujhe Muhammad Essa Awan ne banaya hai."
    
    try:
        # Agar koi mushkil sawal ho toh AI server se poochega
        url = f"https://api.popcat.xyz/chatbot?msg={text}"
        res = requests.get(url, timeout=5) # 5 second ka time limit
        return res.json()['response']
    except:
        # Agar server busy ho toh ye wala pyara jawab aayega
        return "Bhai Essa, main aapki baat samajh raha hoon. Main is waqt aapke agle hukum ka intezar kar raha hoon!"

with tab1:
    st.header("💬 ES AI Assistant")
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]): st.write(chat["content"])

    user_msg = st.chat_input("Hukum karein Essa bhai...")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"): st.write(user_msg)
        
        # AI Response
        answer = get_ai_response(user_msg)
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
    st.write("Movie Dashboard Active Hai! Script likhein aur Colab chalayein.")
    st.text_area("Script:", height=100)
    st.button("Generate Pro Movie")
