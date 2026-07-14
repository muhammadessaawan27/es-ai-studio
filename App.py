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
# 1. DATABASE & ENTERPRISE ARCHITECTURE
# ==========================================
DB_FILE = "sglowina_enterprise_titan_final.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT, joined_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS wallets (user_id TEXT PRIMARY KEY, credits INTEGER, plan TEXT, updated_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS system_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan TEXT, trx_id TEXT, proof_blob BLOB, status TEXT, date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, timestamp TEXT)''')
        
        # MASTER ADMIN (Muhammad Essa Awan & Saba Wahid)
        admin_pass = bcrypt.hashpw("admin786".encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", ("ADMIN_001", "admin@sglowina.ai", admin_pass, "admin", "active", "2024-01-01"))
        c.execute("INSERT OR IGNORE INTO wallets VALUES (?,?,?,?)", ("ADMIN_001", 999999, "Founder", str(datetime.now())))
        
        defaults = [('easypaisa_no', '03086834020'), ('jazzcash_no', '03086834020'), ('account_holder', 'Saba Wahid')]
        for k, v in defaults: c.execute("INSERT OR IGNORE INTO system_settings VALUES (?,?)", (k, v))
        conn.commit()

init_enterprise_db()

# ==========================================
# 2. RESTORED UI & LOGO (FIXED CSS)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan OS", layout="wide", page_icon="🎬")

def apply_restored_ui():
    """Point Fix: Removed #MainMenu and Header hiding rules to restore Three Dots & Settings"""
    st.markdown("""
        <style>
        /* Only hide the default footer, leave everything else visible */
        footer {display: none !important;}
        
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        /* RESTORED: Electric Executive Header */
        .executive-header {
            text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9;
            background: #0f172a; border-radius: 0 0 40px 40px; color: #fff;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        }

        /* RESTORED: Circular Rotating Logo */
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
        .circular-s {
            width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 50px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 25px rgba(0, 212, 255, 0.4), inset 0 0 15px #ff007a;
            animation: spinGlow 8s infinite linear;
        }
        @keyframes spinGlow { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

        .stButton>button { background: #000000 !important; color: white !important; border-radius: 10px !important; height: 50px; width: 100%; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY & BIO
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.
"""

# ==========================================
# 4. v40 INDUSTRIAL MOVIE ENGINE (LOCKED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        import moviepy.video.fx.all as vfx
        u_id = f"v1_{str(uuid.uuid4())[:6]}"
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        asyncio.run(edge_tts.Communicate(story, v_code).save(f"a_{u_id}.mp3"))
        audio = AudioFileClip(f"a_{u_id}.mp3")
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280)}
        w, h = res_map.get(ratio, (1280, 720))
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(s + ' 3d cinematic ' + style)}?width={w}&height={h}&seed={seed}&nologo=true"
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(requests.get(url).content)
            with Image.open(img_p) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.1 - 0.1 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_TITAN_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. MAIN SaaS LOGIC
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

apply_restored_ui()

if not st.session_state.user:
    # --- LOGIN SCREEN ---
    st.markdown('<div class="executive-header"><h1 style="font-family:Orbitron;">ES FOUNDER & CEOs</h1><p>SGLOWINA AI ENTERPRISE TITAN ACCESS</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        e = st.text_input("Enterprise ID")
        p = st.text_input("Security Key", type="password")
        if st.button("Enter Dashboard 🚀"):
            conn = get_db_connection()
            u = conn.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone()
            if u and bcrypt.checkpw(p.encode(), u[2].encode()):
                wallet = conn.execute("SELECT credits, plan FROM wallets WHERE user_id=?", (u[0],)).fetchone()
                st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": wallet[0]}
                st.rerun()
            else: st.error("Access Denied.")
            conn.close()
else:
    u = st.session_state.user
    apply_restored_ui()
    
    # Sidebar
    st.sidebar.markdown(f"<div class='circular-logo'>ES</div>", unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 {u['email']}\n\n💰 Credits: {u['credits']}")
    
    menu = st.sidebar.radio("SGLOWINA COMMAND:", ["🏠 Dashboard", "🎥 Video Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Branded Header
    st.markdown('<div class="executive-header"><h1>ES Founder & CEOs</h1><p>SGLOWINA AI OFFICIAL STUDIO</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-logo">ES</div></div>', unsafe_allow_html=True)

    # --- ROUTING ---
    if menu == "🎥 Video Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
        m_s = st.text_area("Story Script")
        if st.button("Generate Masterpiece"):
            if m_s and u['credits'] >= 10:
                res = create_v40_titan_movie(m_s, "Male", "YouTube (16:9)", "Realistic", u['id'], 786)
                if "mp4" in res: st.video(res)
            else: st.warning("Check script or credits.")

    elif menu == "🎨 Image Studio":
        st.write("### 🎨 Industrial HD Visual Studio")
        i_p = st.text_area("Image Details")
        if st.button("Generate HD Visuals 🚀"):
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(i_p)}?nologo=true"
            st.image(url)

    elif menu == "💬 Chat":
        if p := st.chat_input("Hukum..."):
            res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

st.markdown("<p style='text-align:center; padding:10px; border-top:1px solid #eee; margin-top:50px;'>ES Founder & CEOs</p>", unsafe_allow_html=True)
