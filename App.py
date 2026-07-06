import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import time
import re

# ==========================================
# CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

# Premium Metallic CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 80px; 
        font-weight: 900;
        margin-bottom: 0px;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 50px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 5px 15px rgba(0, 212, 255, 0.4); }
    .status-box { padding: 10px; border-radius: 10px; background-color: #16213e; border: 1px solid #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# CONSTANTS & IDENTITY
# ==========================================
SYSTEM_PROMPT = "You are ES AI created by Muhammad Essa Awan. Answer professionally, naturally, and intelligently in the user's language (Urdu, Hindi, or English)."

ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی وہ الحمد للہ اللہ کے فضل سے ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور سلسلۂ نقشبندیہ اویسیہ کے ایک کارکن ہیں۔
اس وقت وہ سلسلۂ عالیہ کے موجودہ حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

# Expanded Creator Detection Keywords
IDENTITY_KEYWORDS = [
    r"who (made|created|designed|developed) you", r"your (creator|owner|founder|maker|boss)",
    r"tumhe (kisne|kis ne) (banaya|design kiya|banaya hai)", r"apka (malik|creator|owner) kaun hai",
    r"essa awan", r"muhammad essa", r"creator kon hai", r"tume kisne banaya", r"who is essa"
]

# ==========================================
# CORE AI ENGINE (RETRY LOGIC & STABILITY)
# ==========================================
def get_ai_response(user_query, chat_history):
    # 1. Identity Check (Regex based)
    for pattern in IDENTITY_KEYWORDS:
        if re.search(pattern, user_query.lower()):
            return ESSA_BIO

    # 2. Prepare Context (Last 5 messages for speed and accuracy)
    context = ""
    for msg in chat_history[-5:]:
        context += f"{msg['role']}: {msg['content']}\n"
    
    full_prompt = f"System: {SYSTEM_PROMPT}\nContext:\n{context}User: {user_query}\nAssistant:"
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    # 3. API Request with Retry Logic
    url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&cache=true"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=90) # Increased timeout
            response.raise_for_status() # Check for HTTP errors
            
            if response.text:
                return response.text
            else:
                raise ValueError("Empty Response")
                
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                time.sleep(2) # Wait before retry
                continue
            else:
                return "معذرت، اس وقت سرور سے رابطہ نہیں ہو پا رہا۔ براہ کرم تھوڑی دیر بعد دوبارہ کوشش کریں یا اپنا انٹرنیٹ چیک کریں۔"

# ==========================================
# UI LAYOUT
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00d4ff; letter-spacing: 5px; font-weight: bold;'>ADVANCED MULTI-MODAL AGENT</p>", unsafe_allow_html=True)

tabs = st.tabs(["💬 ES Smart Chat", "🎙️ ES Voice Studio", "🎬 ES Movie Studio"])

# --- TAB 1: CHAT ---
with tabs[0]:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # User Input
    if prompt := st.chat_input("مجھ سے کوئی بھی سوال پوچھیں..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ES AI سوچ رہا ہے..."):
                response = get_ai_response(prompt, st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- TAB 2: VOICE STUDIO ---
with tabs[1]:
    st.header("🎙️ Professional Voiceover Generator")
    v_text = st.text_area("وہ متن لکھیں جسے آپ آواز میں بدلنا چاہتے ہیں:", height=150)
    col1, col2 = st.columns(2)
    with col1:
        v_lang = st.selectbox("زبان منتخب کریں:", ["Urdu", "English", "Hindi"], key="v_lang")
    with col2:
        v_gen = st.selectbox("آواز کی صنف (Gender):", ["Female", "Male"], key="v_gen")

    if st.button("Generate Audio 🚀"):
        if v_text:
            # Voice Mapping
            voice_db = {
                "Urdu": {"Female": "ur-PK-UzmaNeural", "Male": "ur-PK-AsadNeural"},
                "English": {"Female": "en-US-JennyNeural", "Male": "en-US-GuyNeural"},
                "Hindi": {"Female": "hi-IN-SwaraNeural", "Male": "hi-IN-MadhurNeural"}
            }
            selected_v = voice_db[v_lang][v_gen]
            
            async def generate_voice():
                communicate = edge_tts.Communicate(v_text, selected_v)
                await communicate.save("es_ai_voice.mp3")

            with st.spinner("آواز تیار کی جا رہی ہے..."):
                asyncio.run(generate_voice())
                st.audio("es_ai_voice.mp3")
                with open("es_ai_voice.mp3", "rb") as file:
                    st.download_button("Download MP3 ⬇️", file, file_name="es_ai_voice.mp3")
        else:
            st.warning("براہ کرم پہلے کچھ متن لکھیں۔")

# --- TAB 3: MOVIE STUDIO ---
with tabs[2]:
    st.header("🎬 Pro Cinematic Movie Studio")
    st.info("اپنی مووی کا اسکرپٹ یہاں لکھیں اور اسے گوگل کولاب (Movie Engine) کے ذریعے رینڈر کریں۔")
    m_script = st.text_area("مووی اسکرپٹ / کہانی:", height=200, placeholder="ایک خوبصورت جنگل کی کہانی...")
    m_ratio = st.selectbox("ویڈیو کا سائز (Ratio):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Square (1:1)"])
    
    if st.button("Save Script for Rendering"):
        if m_script:
            st.success("اسکرپٹ محفوظ ہو گیا ہے! اب ویڈیو بنانے کے لیے اپنا 'ES AI Movie Engine' (Google Colab) چلائیں۔")
        else:
            st.warning("پہلے کہانی لکھیں۔")

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>© 2024 ES AI Studio | Powered by Muhammad Essa Awan</p>", unsafe_allow_html=True)
