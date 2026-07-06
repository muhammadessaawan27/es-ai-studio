import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import time
import re

# ==========================================
# 1. CORE CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

# Premium Metallic UI Design (Preserved exactly as requested)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 80px; font-weight: 900;
        margin-bottom: 0px;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 55px; width: 100%; 
        font-size: 20px; font-weight: bold; border: none;
        box-shadow: 0px 4px 15px rgba(0, 212, 255, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. IDENTITY & SYSTEM PROMPTS
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔

محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔

وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔

وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔

اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔

انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# Identity Detection Logic
def check_identity(query):
    patterns = [
        r"kisne banaya", r"who made you", r"owner", r"creator", r"founder", 
        r"banane wala", r"essa awan", r"muhammad essa", r"tera baap", r"kon ho tum"
    ]
    return any(re.search(p, query.lower()) for p in patterns)

# ==========================================
# 3. ADVANCED AI ENGINE (ROBUST & SILENT)
# ==========================================
def get_es_ai_response(user_query, history):
    if check_identity(user_query):
        return ESSA_BIO

    # Context Construction
    chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
    system_instr = "You are ES AI, a professional intelligence created by Muhammad Essa Awan. Answer in detail and strictly follow the user's language."
    full_prompt = f"System: {system_instr}\nHistory: {chat_context}\nUser: {user_query}\nAssistant:"
    
    encoded_query = urllib.parse.quote(full_prompt)
    
    # Provider List (Multi-Engine for Stability)
    urls = [
        f"https://text.pollinations.ai/{encoded_query}?model=openai&cache=true",
        f"https://hercai.onrender.com/v3/hercai?question={encoded_query}"
    ]

    for url in urls:
        for _ in range(2): # Silent 2-time retry per URL
            try:
                response = requests.get(url, timeout=45)
                if response.status_code == 200:
                    res_json = response.json() if "hercai" in url else None
                    text = res_json.get('reply') if res_json else response.text
                    if text and len(text.strip()) > 1:
                        return text.strip()
            except:
                time.sleep(1)
                continue
    
    return "System is updating. Please try a different query."

# ==========================================
# 4. USER INTERFACE (TABS & FEATURES)
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>MUHAMMAD ESSA AWAN'S OFFICIAL AGENT</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Intelligent Chat", "🎙️ Voice Studio", "🎬 Movie Studio"])

# --- TAB 1: CHAT SYSTEM ---
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    if prompt := st.chat_input("مجھ سے کوئی بھی معلومات پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                response = get_es_ai_response(prompt, st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- TAB 2: VOICE STUDIO ---
with tab2:
    st.header("🎙️ Voice Studio")
    v_text = st.text_area("جو کہلوانا ہے یہاں لکھیں:", height=150)
    c1, c2 = st.columns(2)
    with c1:
        v_lang = st.selectbox("Language:", ["Urdu", "English", "Hindi"])
    with c2:
        v_gen = st.selectbox("Gender:", ["Female", "Male"])
    
    if st.button("Generate Voice 🚀"):
        if v_text.strip():
            v_map = {
                "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
            }
            v_code = v_map[v_lang][v_gen]
            
            async def generate_voice():
                await edge_tts.Communicate(v_text, v_code).save("es_voice.mp3")

            with st.spinner("Creating..."):
                try:
                    asyncio.run(generate_voice())
                    st.audio("es_voice.mp3")
                    with open("es_voice.mp3", "rb") as f:
                        st.download_button("Download ⬇️", f, file_name="es_ai_voice.mp3")
                except Exception as e:
                    st.error("Error creating audio.")
        else:
            st.warning("Please enter some text.")

# --- TAB 3: MOVIE STUDIO ---
with tab3:
    st.header("🎬 Pro Movie Studio")
    st.info("Bhai Essa, یہاں اپنی مووی کا اسکرپٹ لکھیں اور ویڈیو رینڈر کرنے کے لیے گوگل کولاب استعمال کریں۔")
    m_script = st.text_area("Script Details:", height=200, placeholder="Write your story here...")
    m_ratio = st.selectbox("Video Ratio:", ["YouTube (16:9)", "TikTok (9:16)"])
    
    if st.button("Save Script"):
        if m_script.strip():
            st.success(f"Script saved! Use Movie Engine to render {m_ratio} video.")
        else:
            st.warning("Script cannot be empty.")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #555;'>ES AI Studio | Powered by Muhammad Essa Awan</p>", unsafe_allow_html=True)
