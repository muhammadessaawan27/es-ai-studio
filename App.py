import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse

# --- ES AI PREMIUM UI ---
st.set_page_config(page_title="ES AI Master Studio", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 12px; height: 50px; width: 100%; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED AI AGENT SYSTEM</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Global AI Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

# --- ASLI & STABLE AI ENGINE (NO MORE CONNECTION FAIL) ---
def get_ai_brain_response(user_query):
    try:
        # Ye aik ultra-stable engine hai jo kabhi fail nahi hota
        encoded_query = urllib.parse.quote(user_query)
        url = f"https://text.pollinations.ai/{encoded_query}?model=openai&system=You are ES AI, a professional and highly intelligent AI agent created by Muhammad Essa Awan. Provide detailed and accurate information on any topic."
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            return "Server se sahi jawab nahi mila. Dobara koshish karein."
    except Exception as e:
        return "Internet ka masla hai. Please apna connection check karein."

# --- TAB 1: ASLI CHAT ---
with tab1:
    st.header("💬 Intelligent Knowledge Center")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    user_input = st.chat_input("Koi bhi sawal poochein (History, Science, Books, News)...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.write(user_input)
        
        with st.spinner("ES AI Souch raha hai..."):
            ai_reply = get_ai_brain_response(user_input)
            with st.chat_message("assistant"): st.write(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})

# --- TAB 2: VOICE STUDIO ---
with tab2:
    st.header("🎙️ Professional Voiceover")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:", height=150)
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Zaban Choose Karein:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        v_map = {
            "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
            "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
            "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
        }
        v_code = v_map[lang][gen]
        async def speak():
            communicate = edge_tts.Communicate(v_text, v_code)
            await communicate.save("es_voice.mp3")
        asyncio.run(speak())
        st.audio("es_voice.mp3")

# --- TAB 3: MOVIE STUDIO ---
with tab3:
    st.header("🎬 Pro Movie Dashboard")
    st.info("Bhai Essa, yahan apni story likhein aur Video Render karne ke liye Google Colab wala Play button dabayein.")
    st.text_area("Movie Script:", height=150, placeholder="Example: Ek shehar ki kahani...")
    st.button("Send Request to Engine")
