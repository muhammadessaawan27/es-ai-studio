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
# 1. DATABASE ARCHITECTURE (RULE 61 & 64.3)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_final.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Enterprise User Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    # Payment & Settings Table
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, trans_id TEXT, status TEXT, date TEXT)''')
    
    # MANDATORY FOUNDER SETUP (Rule 64.3 Admin Access)
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_001", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    # Default Secure Payment Details
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('holder_name', 'Saba Wahid')")
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. ADVANCED AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglowinaTitanOS:
    @staticmethod
    def visual_director_agent(urdu_text, style_choice):
        """Creative Agent: Enforces Islamic Policy & All 62 Rules"""
        holy_list = ["نبی", "رسول", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah", "قبر", "کفن"]
        is_holy = any(k in urdu_text for k in holy_list)
        protection = "STRICTLY NO FACE. NO FACIAL FEATURES. SHOW NOOR (LIGHT). Modest Islamic clothing." if is_holy else ""
        director_instr = (f"Act as High-End Director. Scene: '{urdu_text}'. {protection} "
                         f"Style: {style_choice}. 8k, cinematic, accurate subject matching.")
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
            res = requests.get(url, timeout=25)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 3. EXECUTIVE UI & BRANDING
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan OS", layout="wide", page_icon="🎬")

def apply_executive_ui():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        .brand-header {
            text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9;
            background: #0f172a; border-radius: 0 0 50px 50px; color: #fff;
            animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; box-shadow: 0 0 20px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; box-shadow: 0 0 20px #00d4ff; }
        }
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
        .circular-s {
            width: 110px; height: 110px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 50px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 25px #00d4ff, inset 0 0 15px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        .stTextArea>div>div>textarea, .stTextInput>div>div>input { background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 10px !important; color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 4. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the Founder & CEO, lead visionary and engineer. Saba Wahid is the Founder & CEO.
This is the official Version 1.0 Premium Release.
"""

# ==========================================
# 5. TITAN MOVIE ENGINE (v40 LOCKED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        import moviepy.video.fx.all as vfx
        u_id = f"v1_prod_{str(uuid.uuid4())[:6]}"
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
            refined = SglowinaTitanOS.visual_director_agent(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative=deformed,blurry"
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(requests.get(url).content)
            with Image.open(img_p) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_FINAL_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 6. MAIN SYSTEM ROUTING
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

apply_executive_ui()

if not st.session_state.user:
    # --- SECURE LOGIN GATE ---
    st.markdown('<div class="brand-header">ES FOUNDER & CEOs | SGLOWINA AI</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["🔐 Secure Login", "📝 Create Account"])
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
                except: st.error("Email exists.")
                conn.close()
else:
    u = st.session_state.user
    conn = get_db_connection()
    db_u = conn.execute("SELECT credits, role FROM users WHERE id=?", (u['id'],)).fetchone()
    credits = 999999 if db_u[1] == "admin" else db_u[0]

    # --- SIDEBAR (RESTORED & WORKING) ---
    st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    menu = st.sidebar.radio("SGLOWINA COMMAND:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "👥 Users" if u['role']=="admin" else "💳 Recharge"])
    
    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Executive Branding Header
    st.markdown("""<div class="executive-header"><div style="text-align:center; font-family:'Inter'; font-weight:800; font-size:1.8rem; color:#fff;">Muhammad Essa Awan & Saba Wahid</div>
                <div style="text-align:center; font-family:'Orbitron'; font-weight:900; color:#ff007a; letter-spacing:3px;">FOUNDERS & CEOs | SGLOWINA AI</div></div>""", unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    # --- PAGE LOGIC ---
    if menu == "🎨 Image Studio":
        st.write("### 🎨 Industrial HD Visual Studio")
        i_p = st.text_area("Describe Image(s) - One per line:")
        c1, c2, c3 = st.columns(3)
        with c1: i_s = st.selectbox("Art Style", ["Realistic", "3D Pixar", "Anime", "Logo"])
        with c2: i_r = st.selectbox("Resolution", ["Square (1:1)", "YouTube HD (16:9)", "TikTok (9:16)"])
        with c3: i_q = st.slider("Quantity", 1, 10, 1)
        char_seed = st.number_input("Face Lock ID:", value=786)
        if st.button("Generate HD Visuals 🚀"):
            if i_p and credits >= i_q:
                prompts = [line.strip() for line in i_p.split('\n') if line.strip()]
                w, h = (1024, 1024) if "1:1" in i_r else (1280, 720) if "16:9" in i_r else (720, 1280)
                for p_item in prompts:
                    for q in range(i_q):
                        refined = SglowinaTitanOS.visual_director_agent(p_item, i_s)
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={char_seed+q}&nologo=true"
                        st.image(url, caption=f"Titan Output: {p_item[:30]}...")

    elif menu == "🎥 Movie Studio":
        st.write("### 🎥 Titan Video Production Engine")
        m_s = st.text_area("Full Production Script")
        if st.button("Generate Official Titan Movie"):
            res = create_v40_titan_movie(m_s, "Male", "YouTube (16:9)", "Realistic", u['id'], 786)
            if "mp4" in res: st.video(res)

    elif menu == "👥 Users" and u['role'] == "admin":
        st.title("User Management System")
        users_df = pd.read_sql_query("SELECT id, email, role, credits, joined_at FROM users", conn)
        st.dataframe(users_df, use_container_width=True)

    elif menu == "💳 Recharge":
        ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa'").fetchone()[0]
        st.success(f"Official EasyPaisa: {ep} (Saba Wahid)")

    elif menu == "💬 Chat":
        if p := st.chat_input("Hukum..."):
            res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text.replace("ChatGPT", "Sglowina AI")
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise Titan v1.0 | ES Founder & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
