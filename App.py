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

tab1, tab2, tab3 = st.tabs(["💬 ES Smart Chat (Brain)", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- ADVANCED AI BRAIN (For detailed Info) ---
def get_detailed_info(query):
    try:
        # Ye API ab GPT-4 ki tarah lambe aur maloomati jawab degi
        response = requests.get(f"https://hercai.onrender.com/v3/hercai?question={query}", timeout=10)
        data = response.json()
        return data['reply']
    except:
        return "Bhai Essa, main is waqt internet se maloomat nikaal raha hoon. Please thori der baad dobara poochein ya apna sawal wazeh karein."

with tab1:
    st.header("💬 Intelligent Assistant")
    st.write("Aap mujhse kitabon, science, ya kisi bhi topic par maloomat le sakte hain.")
    
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]): st.write(chat["content"])

    user_msg = st.chat_input("Bhai Essa, koi bhi sawal poochein...")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"): st.write(user_msg)
        
        with st.spinner("Main research kar raha hoon..."):
            answer = get_detailed_info(user_msg)
            with st.chat_message("assistant"): st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

with tab2:
    st.header("🎙️ Voiceover Generator")
    v_text = st.text_area("Yahan wo likhein jo AI se bulwana hai:")
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
            await edge_tts.Communicate(v_text, v_code).save("es_voice.mp3")
        asyncio.run(speak())
        st.audio("es_voice.mp3")

with tab3:
    st.header("🎬 Pro Movie Studio")
    st.write("Movie Dashboard Active Hai! Script likhein aur Colab chalayein.")
    st.text_area("Movie Script:", height=150)
    st.button("Generate Pro Movie")
