import streamlit as st
import asyncio
import edge_tts
import requests
import json

# --- ES AI PREMIUM UI ---
st.set_page_config(page_title="ES AI Master Studio", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; background: linear-gradient(90deg, #00d4ff, #ff007a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 80px; font-weight: 900; }
    .stButton>button { background: linear-gradient(45deg, #00d4ff, #ff007a); color: white; border-radius: 10px; border: none; height: 50px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>PROFESSIONAL AI AGENT SYSTEM</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Real AI Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

# --- ASLI AI ENGINE (NO HARDCODED REPLIES) ---
def get_ai_result(user_query):
    try:
        # Ye ek powerful API hai jo real GPT-4 results deti hai
        url = "https://api.paxsenix.biz/ai/gpt4"
        params = {"q": user_query}
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('reply', "AI ne koi jawab nahi diya.")
        else:
            return f"Technical Error: Server ne {response.status_code} code diya."
    except Exception as e:
        return f"Connection Error: {str(e)}"

# --- TAB 1: ASLI CHAT ---
with tab1:
    st.header("💬 Asli AI Chat Center")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    user_input = st.chat_input("Koi bhi maloomat poochein (Science, History, Books)...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.write(user_input)
        
        with st.spinner("AI Brain processing..."):
            # Yahan koi hardcoded message nahi hai
            ai_response = get_ai_result(user_input)
            with st.chat_message("assistant"): st.write(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

# --- TAB 2: VOICE STUDIO ---
with tab2:
    st.header("🎙️ Voice Generator")
    v_text = st.text_area("Likhein jo bulwana hai:")
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Zaban:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        v_map = {
            "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
            "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
            "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
        }
        v_code = v_map[lang][gen]
        async def speak():
            await edge_tts.Communicate(v_text, v_code).save("voice.mp3")
        asyncio.run(speak())
        st.audio("voice.mp3")

# --- TAB 3: MOVIE STUDIO ---
with tab3:
    st.header("🎬 Pro Movie Studio")
    st.info("Script yahan likhein aur Rendering ke liye Google Colab chalayein.")
    st.text_area("Script Data:", height=150)
    st.button("Request Video Render")
