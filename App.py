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

tab1, tab2, tab3 = st.tabs(["💬 ES Chat (LLM Brain)", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- ASLI AI ENGINE (NO FAKE RESPONSES) ---
def get_real_ai_brain(question):
    try:
        # Ye aik real AI engine hai jo detailed maloomat deta hai
        url = f"https://hercai.onrender.com/v3/hercai?question={question}"
        res = requests.get(url, timeout=15)
        data = res.json()
        return data['reply']
    except Exception as e:
        return f"Error: AI Engine se rabta nahi ho saka. (Technical Detail: {str(e)})"

with tab1:
    st.header("💬 Advanced AI Assistant")
    st.info("Aap mujhse dunya ki koi bhi maloomat le sakte hain (Kitabein, Science, History).")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    msg = st.chat_input("Yahan apna sawal likhein...")
    if msg:
        st.session_state.messages.append({"role": "user", "content": msg})
        with st.chat_message("user"): st.write(msg)
        
        with st.spinner("AI Souch raha hai..."):
            # Ab sirf asli AI ka jawab aayega
            final_reply = get_real_ai_brain(msg)
            with st.chat_message("assistant"): st.write(final_reply)
            st.session_state.messages.append({"role": "assistant", "content": final_reply})

with tab2:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:")
    v_lang = st.selectbox("Zaban:", ["Urdu", "English", "Hindi"])
    v_gen = st.radio("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        v_map = {
            "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
            "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
            "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
        }
        v_code = v_map[v_lang][v_gen]
        async def speak():
            await edge_tts.Communicate(v_text, v_code).save("es_voice.mp3")
        asyncio.run(speak())
        st.audio("es_voice.mp3")

with tab3:
    st.header("🎬 Pro Movie Studio")
    st.write("Movie Dashboard set hai. Script likhein aur Colab ka button dabayein.")
    st.text_area("Movie Script:", height=100)
    st.button("Render Movie")
