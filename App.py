import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import logging
import json
import hashlib
import re
import traceback
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# CONFIGURATION
# ==========================================
APP_NAME = "ES AI"
APP_VERSION = "3.0"
CREATOR = "Muhammad Essa Awan"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("es_ai.log"), logging.StreamHandler()]
)

st.set_page_config(page_title=f"{APP_NAME} Master Studio", layout="wide")

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "cache" not in st.session_state: st.session_state.cache = {}
if "ai_status" not in st.session_state: st.session_state.ai_status = "ONLINE"
if "total_questions" not in st.session_state: st.session_state.total_questions = 0
if "total_answers" not in st.session_state: st.session_state.total_answers = 0
if "greeted" not in st.session_state:
    st.info("السلام علیکم، میں ES AI ہوں۔ میں آپ کی کس طرح مدد کر سکتا ہوں؟")
    st.session_state.greeted = True

# ==========================================
# CORE UTILITIES
# ==========================================
def create_session():
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = create_session()

def save_chat_to_file():
    try:
        with open("conversation.txt", "w", encoding="utf-8") as f:
            for msg in st.session_state.messages:
                f.write(f"{msg['role']} : {msg['content']}\n")
    except Exception as e:
        logging.error(f"Failed to save chat: {e}")

# ==========================================
# AI ENGINE
# ==========================================
def ask_ai(question, temp=0.7):
    key = hashlib.md5(question.encode("utf-8")).hexdigest()
    if key in st.session_state.cache: return st.session_state.cache[key]
    
    try:
        history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages[-20:]])
        full_prompt = f"Previous Conversation:\n{history}\n\nCurrent User:\n{question}"
        
        url = f"https://text.pollinations.ai/{urllib.parse.quote(full_prompt)}?model=openai&temperature={temp}&system=You+are+{APP_NAME}+created+by+{CREATOR}."
        response = SESSION.get(url, timeout=90)
        response.raise_for_status()
        answer = response.text.strip() or "سرور نے خالی جواب دیا۔"
        
        st.session_state.cache[key] = answer
        return answer
    except Exception as e:
        logging.error(f"AI Engine Error: {e}")
        return "AI Engine میں عارضی مسئلہ آیا ہے۔ براہ کرم دوبارہ کوشش کریں۔"

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header(f"⚙ {APP_NAME} Settings")
    memory_limit = st.slider("Conversation Memory", 10, 100, 20)
    ai_temp = st.slider("AI Creativity", 0.0, 1.0, 0.7)
    show_logs = st.checkbox("Show Logs")
    
    st.markdown("---")
    st.subheader("ES AI Info")
    st.write(f"Status : {st.session_state.ai_status}")
    st.write(f"Questions : {st.session_state.total_questions}")
    st.write(f"Answers : {st.session_state.total_answers}")
    st.write(f"Date : {datetime.now().strftime('%d-%m-%Y')}")
    
    if st.button("Clear AI Cache"): st.session_state.cache = {}; st.success("Cache Cleared")
    if st.button("Reset Memory"): st.session_state.messages = []; st.rerun()

# ==========================================
# MAIN UI
# ==========================================
tab1, tab2, tab3 = st.tabs(["💬 Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

with tab1:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("مجھ سے کوئی بھی سوال پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.total_questions += 1
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                answer = ask_ai(prompt, ai_temp)
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.total_answers += 1
                save_chat_to_file()

with tab2:
    st.header("Professional Voice Studio")
    v_text = st.text_area("Write Text", height=150)
    c1, c2 = st.columns(2)
    lang = c1.selectbox("Language", ["Urdu", "English", "Hindi"])
    gen = c2.selectbox("Gender", ["Female", "Male"])
    
    if st.button("Generate Voice"):
        if v_text.strip():
            with st.spinner("Generating..."):
                try:
                    voices = {
                        "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                        "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                        "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
                    }
                    voice = voices[lang][gen]
                    asyncio.run(edge_tts.Communicate(v_text, voice).save("es_voice.mp3"))
                    st.audio("es_voice.mp3")
                    with open("es_voice.mp3", "rb") as f:
                        st.download_button("Download MP3", f, "es_ai_voice.mp3")
                except Exception as e:
                    st.error(f"Voice Error: {e}")

with tab3:
    st.header("🎬 Movie Studio")
    script = st.text_area("Movie Script", height=200, placeholder="اپنی فلم کی مکمل سکرپٹ یہاں لکھیں...")
    if st.button("Prepare Render"):
        if script.strip():
            st.success("Movie Project Saved")
            st.code(script)

# ==========================================
# CLEANUP & FOOTER
# ==========================================
if len(st.session_state.messages) > memory_limit:
    st.session_state.messages = st.session_state.messages[-memory_limit:]

st.markdown("---")
st.markdown(f"<center><b>{APP_NAME} MASTER STUDIO</b><br>Created By {CREATOR}<br>Professional Edition</center>", unsafe_allow_html=True)
