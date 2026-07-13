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
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ==========================================
# 1. CORE SYSTEM ARCHITECTURE (RULE 61)
# ==========================================
DB_FILE = "sglowina_titan_master.db"
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id TEXT PRIMARY KEY, user_id TEXT, type TEXT, prompt TEXT, result_url TEXT, timestamp TEXT)''')
    
    # MASTER ADMIN SETUP (Muhammad Essa Awan & Saba Wahid)
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_MASTER", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. ADVANCED AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglowinaTitanOS:
    @staticmethod
    def visual_director_agent(urdu_text, style_choice, mode="image"):
        """Enforces Golden Rules 1-11 and Islamic Policy for all visual generation"""
        # Step 1: Detect Islamic Content
        islamic_keywords = ["allah", "islam", "muslim", "quran", "hadith", "masjid", "salah", "namaz", "qabr", "kafan", "janazah", "prophet", "nabi", "rasul", "sahabah"]
        is_islamic = any(word in urdu_text.lower() for word in islamic_keywords) or any(k in urdu_text for k in ["اللہ", "نبی", "صحابہ", "قبر", "کفن"])
        
        # Step 5: Face Protection (Noorani Light)
        revered_keywords = ["نبی", "رسول", "صحابی", "ولی اللہ", "امام", "پیمبر", "Prophet", "Sahaba", "Wali Allah"]
        is_revered = any(k in urdu_text for k in revered_keywords)
        
        face_protection = ""
        if is_revered:
            face_protection = "STRICTLY NO FACE. NO FACIAL FEATURES. SHOW BRIGHT WHITE DIVINE NOOR (LIGHT) INSTEAD OF FACE. Back view only. Extremely respectful."

        # Step 2, 4, 6 & Rule 1-11: Content and Cultural Accuracy
        policy_instr = ""
        if is_islamic:
            policy_instr = "Requirement: Authentic Muslim cultural appearance, traditional modest clothing (robes, turbans, hijabs), historical architecture. Strictly no modern western elements."

        director_instr = (
            f"Act as Sglowina Production Agent. Context: '{urdu_text}'. {face_protection} {policy_instr} "
            f"Style: {style_choice}. Rule: Follow Golden Rule 1-11: Detect subjects, animals, and objects accurately. "
            "Symmetrical faces, 8k, highly detailed, realistic 3D animation."
        )
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
            res = session.get(url, timeout=30)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 3. EXECUTIVE UI & BRANDING
# ==========================================
def apply_executive_branding():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        .executive-header {
            text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;
        }
        .main-names { font-size: 1.5rem; font-weight: 800; color: #000000; letter-spacing: 1px; }
        .role-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 4px; text-transform: uppercase; }

        .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
        .circular-s {
            width: 90px; height: 90px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 35px; color: #ffffff;
            border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 4. IDENTITY FIREWALL (LOCKED OFFICIAL BIO)
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.

**Muhammad Essa Awan** is the Founder & CEO. He is a professional Mechanical Engineer, Fabricator, and the lead visionary who architected this industrial intelligence platform.

**Saba Wahid** is the Founder & CEO of Sglowina AI. She is the daughter of Wahid Bakhsh and the spouse of Muhammad Essa Awan (Mrs. Saba Wahid).

This is the official Version 1.0 Premium SaaS Release.
"""

# ==========================================
# 5. TITAN MOVIE ENGINE (v40 LOGIC - LOCKED)
# ==========================================
def fetch_img(url): return session.get(url, timeout=60).content

def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
    status = st.empty()
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
            status.info(f"🎨 Rendering Scene {i+1}/{len(sentences)} (Policy Enforced)...")
            # Step 7: Final Quality Check & Prompt Refinement via OS Agent
            refined = SglowinaTitanOS.visual_director_agent(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true&negative={urllib.parse.quote(STRICT_ISLAMIC_NEGATIVE)}"
            
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # v40 Locked Zoom-In: 1.0 to 1.15
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"Sglowina_Titan_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 6. MAIN APPLICATION EXECUTION
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

apply_executive_branding()

if not st.session_state.user:
    st.markdown('<div class="brand-header">SGLOWINA AI - SECURE ENTERPRISE ACCESS</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab_log, tab_reg = st.tabs(["🔐 Login", "📝 Register"])
        with tab_log:
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Enter Titan Dashboard 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied!")
        with tab_reg:
            ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
            if st.button("Create Sglovina Account"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account Ready! Please Login.")
                except: st.error("Email exists.")
                conn.close()
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{u['credits']}**")
    page = st.sidebar.radio("SGLOWINA TITAN COMMAND:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Pro Image Studio", "💬 Smart Chat", "👥 Manage Users" if u['role']=="admin" else "💳 Recharge"])
    
    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Executive Branding Header (Muhammad Essa Awan & Saba Wahid)
    st.markdown("""<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
                <div class="role-tag">Founders & CEOs | SGLOWINA AI OFFICIAL STUDIO</div></div>""", unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    if page == "🎥 Movie Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
        if u['credits'] < 10: st.warning("Please recharge credits.")
        else:
            m_s = st.text_area("Enter Full Story Script:")
            col1, col2, col3 = st.columns(3)
            with col1: v = st.selectbox("Voice:", ["Male (Asad)", "Female (Uzma)"])
            with col2: r = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
            with col3: s = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
            seed = st.number_input("Character Identity Lock:", value=786)
            if st.button("Generate Titan Movie (10 Credits)"):
                res = create_v40_titan_movie(m_s, v, r, s, u['id'], seed)
                if "mp4" in res:
                    st.video(res)
                    conn = get_db_connection()
                    conn.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (u['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Video Rendered! Credits Deducted.")

    elif page == "🎨 Pro Image Studio":
        st.write("### 🎨 Industrial HD Visual Studio (Multi-Prompt)")
        p_i = st.text_area("Describe Image(s) - One per line:")
        ci1, ci2, ci3 = st.columns(3)
        with ci1: style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design"])
        with ci2: size = st.selectbox("Size:", ["Square (1:1)", "YouTube HD"])
        with ci3: count = st.slider("Quantity:", 1, 10, 1)
        if st.button("Generate Images (1 Credit/Img)"):
            # Multi-Prompt logic with 62-rule director enforcement...
            st.info("Agent is identifying subjects and enforcing policy...")

    elif page == "💬 Smart Chat":
        st.write("### 💬 Sglowina Intelligence Dashboard")
        if p := st.chat_input("Hukum..."):
            if any(k in p.lower() for k in ["kisne", "who", "saba", "essa"]): res = SGL_BIO
            else:
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text.replace("ChatGPT", "Sglowina AI")
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise v1.0 | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
