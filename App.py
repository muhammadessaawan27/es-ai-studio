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

# ==========================================
# 1. ENTERPRISE CORE SYSTEM (RULE 61 & 64.4)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_final_v1.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Rule 61: Modular Independent Tables
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, method TEXT, 
                  trans_id TEXT, status TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    
    # MASTER ADMIN SETUP (Muhammad Essa Awan & Saba Wahid)
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (id, email, password, role, status, credits, joined_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_001", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    # OFFICIAL PAYMENT SETTINGS (MANDATORY FIX)
    c.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", ('easypaisa', '03086834020'))
    c.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", ('jazzcash', '03086834020'))
    c.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", ('holder_name', 'Saba Wahid'))
    
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. ADVANCED AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglovinaTitanOS:
    @staticmethod
    def visual_director_agent(urdu_text, style_choice):
        """Enforces Islamic Policy & Golden Rules 1-11"""
        holy_list = ["نبی", "رسول", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah", "قبر", "کفن"]
        is_holy = any(k in urdu_text for k in holy_list)
        protection = "STRICTLY NO FACE. NO FACIAL FEATURES. SHOW BRIGHT WHITE NOOR LIGHT." if is_holy else ""
        director_instr = (f"Act as High-End Film Director. Scene: '{urdu_text}'. {protection} "
                         f"Style: {style_choice}. 8k, cinematic, epic composition. Rule: Match characters accurately.")
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
            res = requests.get(url, timeout=25)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 3. EXECUTIVE UI & BRANDING (Version 1.0 Locked)
# ==========================================
st.set_page_config(page_title="Sglovina AI - Official Titan OS", layout="wide", page_icon="🎬")

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
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
        .circular-s {
            width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 50px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 25px #00d4ff, inset 0 0 15px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

apply_executive_ui()

# ==========================================
# 4. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGL_BIO = """
Sglowina AI is developed by the Sglowina Team.
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.
Muhammad Essa Awan is the lead visionary and logic architect. Saba Wahid is the Co-Founder & CEO.
This is the official Version 1.0 Premium Release.
"""

# ==========================================
# 5. SaaS AUTHENTICATION (RULE 64.3 ACCESS)
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

def login_gate():
    st.markdown('<div class="brand-header">ES FOUNDER & CEOs | SGLOWINA AI</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Secure Login", "📝 Register Account"])
        with t_l:
            e = st.text_input("Business Email")
            p = st.text_input("Security Password", type="password")
            if st.button("Enter Titan OS 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied!")
        with t_r:
            ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
            if st.button("Register Creator"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account Ready! Login now.")
                except: st.error("Email exists.")
                conn.close()

# ==========================================
# 6. MOVIE ENGINE (v40 LOCKED)
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
            refined = SglovinaTitanOS.visual_director_agent(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative=deformed,blurry"
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(session.get(url).content)
            with Image.open(img_p) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglovina_Final_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 7. MAIN SYSTEM EXECUTION
# ==========================================
if not st.session_state.user:
    login_gate()
else:
    u = st.session_state.user
    apply_executive_ui()
    conn = get_db_connection()
    db_u = conn.execute("SELECT credits, role FROM users WHERE id=?", (u['id'],)).fetchone()
    credits = 999999 if db_u[1] == "admin" else db_u[0]

    # Sidebar: Clean & Working
    st.sidebar.markdown(f"### 👤 {u['email']}")
    st.sidebar.markdown(f"💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    
    if u['role'] == "admin":
        menu = st.sidebar.radio("SGLOWINA COMMAND:", ["📈 Stats", "👥 Users", "💰 Payments", "🎬 Admin Studio", "💬 Chat"])
    else:
        menu = st.sidebar.radio("SGLOWINA MENU:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Shared Branding Header
    st.markdown('<div class="brand-header">ES FOUNDER & CEOs | SGLOWINA AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    # --- TABS LOGIC ---
    if menu == "🎨 Image Studio":
        st.write("### 🎨 Industrial HD Image Studio")
        img_p = st.text_area("Describe Image (One per line for batch generation):")
        c_s, c_r, c_q = st.columns(3)
        with c_s: style = st.selectbox("Style:", ["Realistic", "3D Pixar", "Anime", "Logo"])
        with c_r: ratio = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD (16:9)", "TikTok (9:16)"])
        with c_q: qty = st.slider("Quantity:", 1, 10, 1)
        seed = st.number_input("Character Lock ID:", value=786)
        if st.button("Generate Industrial Visuals 🚀"):
            if img_p and credits >= qty:
                st.info("Sglowina Agent is painting your visuals...")
                # (Image rendering logic here using user seed...)

    elif menu == "🎥 Movie Studio" or menu == "🎬 Admin Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
        if u['role'] != "admin" and credits < 10: st.error("Low Credits! Recharge now.")
        else:
            m_s = st.text_area("Enter Production Script:")
            v = st.selectbox("Narrator:", ["Male (Asad)", "Female (Uzma)"])
            r = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
            s = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
            seed = st.number_input("Face Lock ID:", value=786)
            if st.button("Generate Official Titan Movie"):
                res = create_v40_titan_movie(m_s, v, r, s, u['id'], seed)
                if "mp4" in res:
                    st.video(res)
                    if u['role'] != "admin": conn.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (u['id'],)); conn.commit()

    elif menu == "💳 Recharge":
        ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa'").fetchone()[0]
        nm = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='holder_name'").fetchone()[0]
        st.markdown(f"""<div style="background:#f1f5f9; padding:20px; border-radius:15px; border:2px solid #ff007a;">
            <h3>Official Payment Details</h3>
            <p><b>EasyPaisa / JazzCash:</b> {ep}<br><b>Account Name:</b> {nm}</p></div>""", unsafe_allow_html=True)
        st.subheader("Submit Payment Proof")
        trx = st.text_input("Transaction ID")
        if st.button("Request Credits"): st.success("Sent for Approval!")

    elif menu == "💬 Chat":
        st.write("### 💬 Sglowina Intelligence")
        if p := st.chat_input("Hukum..."):
            if is_id_call(p): res = SGL_BIO
            else: res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text.replace("ChatGPT", "Sglowina AI")
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Version 1.0 | ES Founder & CEOs</p>", unsafe_allow_html=True)
