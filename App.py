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
import bcrypt
import pandas as pd
from PIL import Image
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. CORE DATABASE ARCHITECTURE (FIXED)
# ==========================================
# Changed DB name to v6 to force a fresh start and fix column mismatch errors
DB_FILE = "sglowina_enterprise_titan_v6.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        # Table Users
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT, joined_at TEXT)''')
        # Table Wallets
        c.execute('''CREATE TABLE IF NOT EXISTS wallets 
                     (user_id TEXT PRIMARY KEY, credits INTEGER, plan TEXT, updated_at TEXT)''')
        # Table Settings
        c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                     (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
        # Table Payments
        c.execute('''CREATE TABLE IF NOT EXISTS payments 
                     (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan TEXT, trx_id TEXT, status TEXT, date TEXT)''')
        
        # MASTER ADMIN (Muhammad Essa Awan & Saba Wahid)
        admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
                  ("ADMIN_MASTER", "admin@sglowina.ai", admin_pass, "admin", "active", "2024-01-01"))
        c.execute("INSERT OR IGNORE INTO wallets (user_id, credits, plan, updated_at) VALUES (?, ?, ?, ?)", 
                  ("ADMIN_MASTER", 999999, "Founder", str(datetime.now())))
        
        # Default Business Settings (Managed via Admin)
        defaults = [('easypaisa_no', '03086834020'), ('jazzcash_no', '03086834020'), ('account_holder', 'Saba Wahid')]
        for k, v in defaults:
            c.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?,?)", (k, v))
        conn.commit()

init_enterprise_db()

# ==========================================
# 2. WHITE-LABEL UI & ELECTRIC LOGO (LOCKED)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan OS", layout="wide", page_icon="🎬")

def apply_titan_ui():
    st.markdown("""
        <style>
        /* White-Label: Hiding Streamlit Branding Only */
        #MainMenu {visibility: hidden;} footer {display: none !important;}
        .stDeployButton {display:none !important;} header {visibility: hidden;}
        [data-testid="stSidebarNav"] {visibility: visible !important;}

        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        /* Executive Header */
        .brand-header {
            text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9;
            background: #0f172a; border-radius: 0 0 40px 40px; color: #fff;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        }

        /* 3D Rotating Logo */
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
        .circular-s {
            width: 110px; height: 110px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 30px #ff007a;
            animation: spinGlow 10s infinite linear;
        }
        @keyframes spinGlow { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        .stTextArea>div>div>textarea, .stTextInput>div>div>input { background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 10px !important; color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGL_OFFICIAL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the Founder & CEO, Chief Mechanical Engineer, and lead visionary behind the platform's core architecture.
Saba Wahid is the Founder & CEO and the director of enterprise operations.
"""

def is_identity_request(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"])

# ==========================================
# 4. TITAN MOVIE ENGINE (v40 LOGIC - LOCKED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        import moviepy.video.fx.all as vfx
        u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
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
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(s + ' 3d cinematic ' + style)}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,deformed"
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(requests.get(url).content)
            with Image.open(img_p) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24).resize(newsize=(w, h))
            clip = clip.resize(lambda t: 1.1 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_MASTER_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. SaaS ROUTING & AUTHENTICATION
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

def main():
    apply_titan_ui()
    
    if not st.session_state.user:
        # --- LOGIN / SIGNUP ---
        st.markdown('<div class="brand-header">ES FOUNDER & CEOs | SGLOWINA AI</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1.5,1])
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            tab_l, tab_r = st.tabs(["🔐 Secure Login", "📝 New Account"])
            with tab_l:
                e = st.text_input("Enterprise ID")
                p = st.text_input("Security Key", type="password")
                if st.button("Enter Titan OS 🚀"):
                    conn = get_db_connection()
                    u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                    conn.close()
                    if u:
                        w = get_db_connection().execute("SELECT credits, plan FROM wallets WHERE user_id=?", (u[0],)).fetchone()
                        st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": w[0], "plan": w[1]}
                        st.rerun()
                    else: st.error("Access Denied!")
            with tab_r:
                ne, np = st.text_input("Work Email"), st.text_input("New Security Key", type="password")
                if st.button("Initialize Enterprise ID"):
                    conn = get_db_connection()
                    try:
                        u_id = str(uuid.uuid4())[:8]
                        h_p = hashlib.sha256(np.encode()).hexdigest()
                        with conn:
                            conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (u_id, ne, h_p, "user", "active", str(datetime.now())))
                            conn.execute("INSERT INTO wallets VALUES (?,?,?,?)", (u_id, 10, "Starter", str(datetime.now())))
                        st.success("Enterprise ID Created!")
                    except: st.error("Email exists.")
                    conn.close()
    else:
        # --- DASHBOARD ---
        u = st.session_state.user
        conn = get_db_connection()
        db_u = conn.execute("SELECT credits FROM wallets WHERE user_id=?", (u['id'],)).fetchone()
        
        st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{'Unlimited' if u['role']=='admin' else db_u[0]}**")
        menu = st.sidebar.radio("SGLOWINA COMMAND:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge"])

        if st.sidebar.button("Logout 🚪"):
            st.session_state.user = None
            st.rerun()

        # Branding Header
        st.markdown('<div class="brand-header"><h1>ES Founder & CEOs</h1></div>', unsafe_allow_html=True)
        st.markdown('<div class="logo-container"><div class="circular-s">S</div><div class="brand-name">Sglowina AI</div></div>', unsafe_allow_html=True)

        if menu == "🎨 Image Studio":
            st.write("### 🎨 Industrial HD Visual Studio")
            p_i = st.text_area("Describe Image(s) - One per line:")
            c1, c2, c3 = st.columns(3)
            with c1: i_s = st.selectbox("Style:", ["Realistic", "3D Pixar", "Anime", "Logo"])
            with c2: i_r = st.selectbox("Size:", ["Square (1:1)", "YouTube HD (16:9)", "TikTok (9:16)"])
            with c3: i_q = st.slider("Quantity:", 1, 10, 1)
            char_id = st.number_input("Consistency Seed:", value=786)
            if st.button("Generate HD Visuals 🚀"):
                if p_i:
                    prompts = [line.strip() for line in p_i.split('\n') if line.strip()]
                    w, h = (1024, 1024) if "1:1" in i_r else (1280, 720) if "16:9" in i_r else (720, 1280)
                    for p_item in prompts:
                        for q in range(i_q):
                            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_item + ' ' + i_s)}?width={w}&height={h}&seed={char_id+q}&nologo=true"
                            st.image(url)

        elif menu == "🎥 Movie Studio":
            st.write("### 🎥 Titan Video Engine (v40 Power)")
            m_s = st.text_area("Production Script:")
            if st.button("Render Official Movie"):
                res = create_v40_titan_movie(m_s, "Male", "YouTube (16:9)", "Realistic", u['id'], 786)
                if "mp4" in res: st.video(res)

        elif menu == "💬 Chat":
            if p := st.chat_input("Hukum..."):
                if is_identity_request(p): res = SGL_OFFICIAL_BIO
                else: res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
                st.chat_message("user").write(p)
                st.chat_message("assistant").write(res)

        elif menu == "💳 Recharge":
            ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa_no'").fetchone()[0]
            st.info(f"Official EasyPaisa: {ep} (Saba Wahid)")

        conn.close()

if __name__ == "__main__":
    main()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise Titan v1.0 | ES Founder & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
