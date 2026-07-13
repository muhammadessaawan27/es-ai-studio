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
# 1. ENTERPRISE CORE SYSTEM (RULE 61)
# ==========================================
DB_FILE = "sglovina_titan_enterprise.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, status TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id TEXT PRIMARY KEY, user_id TEXT, type TEXT, prompt TEXT, result_url TEXT, timestamp TEXT)''')
    
    # MASTER ADMIN SETUP (Muhammad Essa Awan & Saba Wahid)
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_TITAN", "admin@sglovina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. ADVANCED AI AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglovinaTitanAgent:
    def __init__(self, user_email):
        self.user_email = user_email

    def creative_director(self, urdu_text, style):
        # Step 1, 5, 6: Enforcement of Islamic Policy & Subject Locking
        holy_list = ["نبی", "رسول", "صحابی", "ولی اللہ", "Prophet", "Sahaba", "Wali Allah", "قبر", "کفن"]
        is_holy = any(k in urdu_text for k in holy_list)
        
        policy = ""
        if is_holy:
            policy = "STRICTLY NO FACE. Show bright white Noor light. Modest historical Islamic clothing. Accurate Shariah visuals."
        
        try:
            instr = f"Director: '{urdu_text}'. {policy}. Style: {style}. Professional 3D cinematic. Output English prompt."
            url = f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true"
            res = session.get(url, timeout=25)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 3. EXECUTIVE UI & BRANDING (Muhammad Essa Awan Primary)
# ==========================================
st.set_page_config(page_title="Sglovina AI - Official V1.0 Titan", layout="wide", page_icon="🎬")

def apply_executive_ui():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #0f172a; font-family: 'Inter', sans-serif; }
        
        .brand-header {
            font-family: 'Orbitron', sans-serif; font-size: clamp(1rem, 5vw, 2.2rem); font-weight: 900;
            text-align: center; letter-spacing: 5px; color: #fff;
            background: #0f172a; padding: 20px; border-radius: 0 0 40px 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3); animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 15px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        }
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
        .circular-s {
            width: 110px; height: 110px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: #ffffff;
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
# 4. IDENTITY FIREWALL (CEO & FOUNDER - Muhammad Essa Awan First)
# ==========================================
SGLOWINA_BIO = """
Sglovina AI is proudly developed by the Sglowina Team.

**Founders & CEOs:** Muhammad Essa Awan & Saba Wahid.

**Muhammad Essa Awan** is the Founder & CEO. He is a professional Mechanical Engineer, Fabricator, and the lead visionary who architected this industrial intelligence platform.

**Saba Wahid** is the Founder & CEO of Sglovina AI. She is the spouse of Muhammad Essa Awan (Mrs. Saba Wahid) and the daughter of Wahid Bakhsh.

This is the official Version 1.0 Premium SaaS Release.
"""

def is_identity_request(q):
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in [r"kisne banaya", r"who made you", r"owner", r"saba", r"essa", r"founder", r"ceo"])

# ==========================================
# 5. SAAS AUTHENTICATION
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None

def login_signup():
    st.markdown('<div class="brand-header">SGLOWINA AI - TITAN ENTERPRISE</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Login", "📝 Create Account"])
        with t_l:
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Enter Studio 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Email یا پاس ورڈ غلط ہے۔")
        with t_r:
            ne = st.text_input("New Email")
            np = st.text_input("New Password", type="password")
            if st.button("Register Account"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account Ban Gaya! Ab Login karein.")
                except: st.error("Ye Email pehle se موجود ہے۔")
                conn.close()

# ==========================================
# 6. TITAN MOVIE ENGINE (v40 LOGIC - LOCKED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, user_id):
    agent = SglovinaTitanAgent(user_id)
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
            refined = agent.creative_director(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={random.randint(1,99999)}&nologo=true&negative=girl,female,deformed"
            img_data = session.get(url, timeout=60).content
            img_p = f"i_{u_id}_{i}.jpg"
            with Image.open(io.BytesIO(img_data)) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
        final = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglovina_Final_{u_id}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out
    except Exception as e: return f"Error: {e}"

# ==========================================
# 7. MAIN DASHBOARD EXECUTION
# ==========================================
if not st.session_state.user:
    login_signup()
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 👤 {u['email']}")
    st.sidebar.markdown(f"💰 Credits: **{u['credits']}**")
    
    if u['role'] == "admin":
        menu = st.sidebar.radio("SGLOWINA COMMAND:", ["📈 Statistics", "👥 Manage Users", "💳 Payments", "🎬 Use AI"])
    else:
        menu = st.sidebar.radio("SGLOWINA MENU:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Smart Chat"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # --- BRANDING (Muhammad Essa Awan First, Founders & CEOs) ---
    st.markdown('<div class="brand-header">SGLOWINA AI OFFICIAL STUDIO</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="logo-container">
            <div class="circular-s">S</div>
            <div style="text-align:center; font-family:'Inter'; font-weight:800; font-size:1.8rem; color:#000;">Muhammad Essa Awan & Saba Wahid</div>
            <div style="text-align:center; font-family:'Orbitron'; font-weight:900; color:#ff007a; letter-spacing:3px;">FOUNDERS & CEOs | SGLOWINA AI</div>
        </div>
        """, unsafe_allow_html=True)

    if menu == "🎥 Movie Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
        if u['credits'] < 10: st.warning("Please recharge credits.")
        else:
            m_s = st.text_area("Enter Script:")
            v = st.selectbox("Voice:", ["Male (Asad)", "Female (Uzma)"])
            r = st.selectbox("Ratio:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
            s = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
            if st.button("Generate Official Titan Movie"):
                res = create_v40_titan_movie(m_s, v, r, s, u['id'])
                if "mp4" in res:
                    st.video(res)
                    conn = get_db_connection()
                    conn.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (u['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Movie Rendered Successfully! 10 Credits Deducted.")

    elif menu == "💬 Smart Chat":
        st.write("### 💬 Sglowina Intelligence Dashboard")
        if "msgs" not in st.session_state: st.session_state.msgs = []
        for msg in st.session_state.msgs:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        if p := st.chat_input("Hukum karein Admin..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            with st.chat_message("user"): st.write(p)
            if is_identity_request(p): res = SGLOWINA_BIO
            else:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true&system=You+are+Sglowina+AI"
                res = session.get(url).text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            with st.chat_message("assistant"):
                st.write(res); st.session_state.msgs.append({"role": "assistant", "content": res})

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold; color: #000;'>Sglowina AI Version 1.0 | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
