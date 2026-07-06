import streamlit as st
import asyncio
import edge_tts
import requests

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
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>MUHAMMAD ESSA'S OFFICIAL INTELLIGENCE</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

# --- CREATOR'S IDENTITY ---
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# --- REAL AI BRAIN (NO HARDCODED FALLBACKS) ---
def get_intelligent_response(query):
    query_lower = query.lower()
    
    # Creator info check
    creator_keywords = ["kisne banaya", "who made you", "owner", "creator", "founder", "banane wala", "aapka malik"]
    if any(word in query_lower for word in creator_keywords):
        return ESSA_BIO

    # Direct Request to a powerful AI Engine
    try:
        # Using a highly stable and smart endpoint
        url = f"https://text.pollinations.ai/{query}?model=openai&system=You are ES AI, a highly advanced agent created by Muhammad Essa Awan. Provide professional, detailed, and human-like answers."
        response = requests.get(url, timeout=30)
        return response.text
    except Exception as e:
        return f"Technical Update Required: {str(e)}"

# --- TAB 1: CHAT ---
with tab1:
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]): st.write(chat["content"])

    user_input = st.chat_input("مجھ سے کوئی بھی سوال پوچھیں...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.write(user_input)
        
        with st.spinner("AI Brain Working..."):
            reply = get_intelligent_response(user_input)
            with st.chat_message("assistant"): st.write(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

# --- TAB 2: VOICE STUDIO ---
with tab2:
    v_text = st.text_area("Yahan likhein jo AI se bulwana hai:", height=150)
    c1, c2 = st.columns(2)
    with c1: lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2: gen = st.selectbox("Gender:", ["Female", "Male"])
    
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

# --- TAB 3: MOVIE STUDIO ---
with tab3:
    st.info("Bhai Essa, Script لکھیں اور ویڈیو بنانے کے لیے گوگل کولاب استعمال کریں۔")
    st.text_area("Script Details:", height=150)
    st.button("Request Video Render")
