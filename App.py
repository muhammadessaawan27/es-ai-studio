import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import random
import sqlite3
import hashlib
import pandas as pd
from PIL import Image
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. WHITE-LABEL & UI SECURITY (RULE 64.5)
# ==========================================
st.set_page_config(
    page_title="Sglowina AI - Official Titan OS", 
    layout="wide", 
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

def apply_executive_ui():
    """Hides GitHub, Fork, and Streamlit branding completely"""
    st.markdown("""
        <style>
        /* Hiding GitHub, Fork, and Source buttons */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {display: none !important;}
        .stDeployButton {display:none !important;}
        
        /* White-Label Theme */
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        .executive-header {
            text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9;
            background: #0f172a; border-radius: 0 0 50px 50px; color: #fff;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        }
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
        .circular-s {
            width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 30px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        .stTextArea>div>div>textarea, .stTextInput>div>div>input { background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 10px !important; color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & IDENTITY (RULE 61)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_master.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_TITAN", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('holder_name', 'Saba Wahid')")
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 3. IDENTITY FIREWALL (CEO & FOUNDER)
# ==========================================
SGL_OFFICIAL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the Founder & CEO, lead visionary, and Chief logical architect. 
Saba Wahid is the Founder & CEO and the daughter of Wahid Bakhsh.
Official Version 1.0 Release.
"""

def is_identity_request(q):
    patterns = [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. v40 INDUSTRIAL MOVIE ENGINE (LOCKED)
# ==========================================
def fetch_img(url): return session.get(url, timeout=60).content

def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    u_id = f"v1_{str(uuid.uuid4())[:6]}"
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        import moviepy.video.fx.all as vfx
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(s + ' ' + style)}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,deformed"
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_MASTER_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. UI ROUTING & AUTH
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

def main():
    apply_executive_ui()
    
    if not st.session_state.user:
        # --- LOGIN / SIGNUP ---
        st.markdown('<div class="executive-header"><div style="font-size:1.8rem; font-weight:800;">ES FOUNDER & CEOs</div><div style="font-size:1rem; letter-spacing:4px;">SGLOWINA AI ENTERPRISE LOGIN</div></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            tab_l, tab_r = st.tabs(["🔐 Login", "📝 Create Account"])
            with tab_l:
                e = st.text_input("Business Email")
                p = st.text_input("Password", type="password")
                if st.button("Enter Titan OS 🚀"):
                    conn = get_db_connection()
                    u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                    conn.close()
                    if u:
                        st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                        st.rerun()
                    else: st.error("Access Denied!")
            with tab_r:
                ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
                if st.button("Register Creator"):
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                     (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success("Account Created! Login Now.")
                    except: st.error("Email registration error.")
                    conn.close()
    else:
        # --- DASHBOARD ---
        u = st.session_state.user
        conn = get_db_connection()
        db_u = conn.execute("SELECT credits FROM users WHERE id=?", (u['id'],)).fetchone()
        
        st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{'Unlimited' if u['role']=='admin' else db_u[0]}**")
        menu = st.sidebar.radio("SGLOWINA COMMAND:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Smart Chat", "⚙️ Admin" if u['role']=="admin" else "💳 Recharge"])

        if st.sidebar.button("Logout 🚪"):
            st.session_state.user = None
            st.rerun()

        # Branding
        st.markdown("""<div class="executive-header"><div style="font-family:'Orbitron'; font-weight:900; color:#fff; letter-spacing:3px;">ES FOUNDER & CEOs | SGLOWINA AI</div></div>""", unsafe_allow_html=True)
        st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

        if menu == "🎨 Image Studio":
            st.write("### 🎨 Industrial HD Visual Studio")
            i_p = st.text_area("Describe Image(s) - One per line:")
            c1, c2, c3 = st.columns(3)
            with c1: i_s = st.selectbox("Style:", ["Realistic", "3D Pixar", "Anime", "Logo"])
            with c2: i_r = st.selectbox("Size:", ["Square (1:1)", "YouTube HD (16:9)", "TikTok (9:16)"])
            with c3: i_q = st.slider("Quantity:", 1, 10, 1)
            char_seed = st.number_input("Face Lock ID:", value=786)
            if st.button("Generate Masterpieces 🚀"):
                if i_p:
                    prompts = [line.strip() for line in i_p.split('\n') if line.strip()]
                    w, h = (1024, 1024) if "1:1" in i_r else (1280, 720) if "16:9" in i_r else (720, 1280)
                    for p_item in prompts:
                        for q in range(i_q):
                            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_item + ' ' + i_s)}?width={w}&height={h}&seed={char_seed+q}&nologo=true"
                            st.image(url)

        elif menu == "🎥 Movie Studio":
            st.write("### 🎥 Titan Video Engine")
            m_script = st.text_area("Production Script:")
            if st.button("Render Official Movie"):
                # v40 logic call...
                st.success("Rendering Started!")

        elif menu == "💬 Smart Chat":
            st.write("### 💬 Sglowina Intelligence")
            if p := st.chat_input("Hukum..."):
                if is_identity_request(p): res = SGL_OFFICIAL_BIO
                else: res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
                st.chat_message("user").write(p)
                st.chat_message("assistant").write(res)

        conn.close()

if __name__ == "__main__":
    main()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Version 1.0 | ES Founder & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
