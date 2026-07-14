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
# 1. ENTERPRISE ARCHITECTURE SETUP (RULE 61)
# ==========================================
DB_FILE = "sglowina_enterprise_production_v1.db"
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

class DatabaseManager:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)

    @staticmethod
    def init_db():
        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            # Full Schema Implementation
            c.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT, joined_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS wallets (user_id TEXT PRIMARY KEY, credits INTEGER, plan TEXT, updated_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS system_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan TEXT, trx_id TEXT, status TEXT, timestamp TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, timestamp TEXT)''')
            
            # Super Admin Setup (Muhammad Essa Awan & Saba Wahid)
            admin_pass = bcrypt.hashpw("admin786".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", ("ADMIN_TITAN", "admin@sglowina.ai", admin_pass, "admin", "active", "2024-01-01"))
            c.execute("INSERT OR IGNORE INTO wallets VALUES (?,?,?,?)", ("ADMIN_TITAN", 999999, "Founder", str(datetime.now())))
            
            # Global Business Settings
            defaults = [('easypaisa_no', '03086834020'), ('jazzcash_no', '03086834020'), ('account_holder', 'Saba Wahid')]
            for k, v in defaults: c.execute("INSERT OR IGNORE INTO system_settings VALUES (?,?)", (k, v))
            conn.commit()

DatabaseManager.init_db()

# ==========================================
# 2. WHITE-LABEL & ANIMATED BRANDING (RULE 64.5)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Enterprise Titan OS", layout="wide", page_icon="🎬")

def apply_production_ui():
    st.markdown("""
        <style>
        header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        .stDeployButton {display:none;} [data-testid="stSidebarNav"] {visibility: visible !important;}
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        .executive-header {
            text-align: center; padding: 20px; border-bottom: 2px solid #f1f5f9;
            background: #0f172a; border-radius: 0 0 40px 40px; color: #fff;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1); animation: electricGlow 2s infinite;
        }
        @keyframes electricGlow {
            0%, 100% { border-bottom: 4px solid #ff007a; text-shadow: 0 0 10px #ff007a; }
            50% { border-bottom: 4px solid #00d4ff; text-shadow: 0 0 20px #00d4ff; }
        }
        .circular-logo {
            width: 90px; height: 90px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 38px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 25px rgba(0, 212, 255, 0.4), inset 0 0 15px #ff007a;
            animation: spinGlow 8s infinite linear; margin: 20px auto;
        }
        @keyframes spinGlow { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 10px !important; height: 50px; width: 100%; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. ADVANCED TITAN AGENT SYSTEM (RULE 62)
# ==========================================
class SglowinaTitanOS:
    @staticmethod
    def visual_orchestrator(urdu_text, style):
        """Rule 62: Production Agent with Shariah Guard"""
        holy = ["نبی", "رسول", "صحابی", "اللہ", "قبر", "کفن", "prophet", "sahaba"]
        is_holy = any(k in urdu_text.lower() for k in holy)
        protection = "STRICTLY NO FACE. SHOW NOOR LIGHT." if is_holy else ""
        director_instr = f"Director: '{urdu_text}'. {protection} Style: {style}. 8k Cinematic 3D."
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
            res = session.get(url, timeout=30)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 4. v40 MOVIE ENGINE (MEMORY OPTIMIZED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
    
    u_id = f"job_{str(uuid.uuid4())[:6]}"
    temp_files = []
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"{u_id}_a.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        temp_files.append(audio_f)
        
        audio_clip = AudioFileClip(audio_f)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map.get(ratio, (1280, 720))
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio_clip.duration / len(sentences)

        for i, s in enumerate(sentences):
            refined = SglowinaTitanOS.visual_orchestrator(s, style)
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined)}?width={w}&height={h}&seed={seed}&nologo=true"
            img_res = session.get(url, timeout=45)
            if img_res.status_code == 200:
                img_p = f"{u_id}_i_{i}.jpg"
                with Image.open(io.BytesIO(img_res.content)) as im:
                    im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                temp_files.append(img_p)
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        if not clips: raise ValueError("Image cluster failed to respond.")
        
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
        out_name = f"ES_FINAL_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # Proper Object Closure (Point #7)
        audio_clip.close(); final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"
    finally:
        # Proper Cleanup (Point #6)
        for f in temp_files:
            if os.path.exists(f): os.remove(f)

# ==========================================
# 5. SaaS ROUTING & MODULES
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

apply_production_ui()

if not st.session_state.user:
    st.markdown('<div class="executive-header"><h1 style="font-family:Orbitron;">ES FOUNDER & CEOs</h1><p>SGLOWINA AI ENTERPRISE ACCESS</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        e = st.text_input("Enterprise ID")
        p = st.text_input("Security Key", type="password")
        if st.button("Enter Dashboard 🚀"):
            with DatabaseManager.get_connection() as conn:
                u = conn.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone()
                if u and bcrypt.checkpw(p.encode(), u[2].encode()):
                    w = conn.execute("SELECT credits, plan FROM wallets WHERE user_id=?", (u[0],)).fetchone()
                    st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": w[0], "plan": w[1]}
                    conn.execute("INSERT INTO audit_logs (user_id, action, timestamp) VALUES (?,?,?)", (u[0], "LOGIN", str(datetime.now())))
                    st.rerun()
                else: st.error("Access Denied.")

else:
    u = st.session_state.user
    # Sidebar Live Sync
    with DatabaseManager.get_connection() as conn:
        credits = conn.execute("SELECT credits FROM wallets WHERE user_id=?", (u['id'],)).fetchone()[0]
    
    st.sidebar.markdown(f"### 🛡️ {u['role'].upper()} SESSION")
    st.sidebar.markdown(f"💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    
    if u['role'] == "admin":
        menu = st.sidebar.radio("SGLOWINA ADMIN:", ["🏠 Dashboard", "📈 Statistics", "👥 User List", "💰 Manage Payments", "⚙️ System Settings", "🎬 Use AI Studio", "📖 About"])
    else:
        menu = st.sidebar.radio("TITAN MENU:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge Wallet", "📖 About"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Logo & Header
    st.markdown('<div class="executive-header"><h1>ES Founder & CEOs</h1><p>SGLOWINA AI OFFICIAL STUDIO</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="circular-logo">ES</div>', unsafe_allow_html=True)

    # --- 🎥 MOVIE STUDIO (FIXED) ---
    if menu == "🎥 Movie Studio" or (u['role']=="admin" and menu=="🎬 Use AI Studio"):
        st.write("### 🎥 Industrial Cinematic Production")
        m_s = st.text_area("Story Script")
        if st.button("Generate Masterpiece (10 Credits)"):
            if m_s and (credits >= 10 or u['role']=="admin"):
                with st.spinner("Agent is rendering production job..."):
                    res = create_v40_titan_movie(m_s, "Male", "YouTube (16:9)", "Realistic", u['id'], 786)
                    if "mp4" in res:
                        st.video(res)
                        if u['role'] != 'admin':
                            with DatabaseManager.get_connection() as conn:
                                conn.execute("UPDATE wallets SET credits = credits - 10 WHERE user_id=?", (u['id'],))
                                conn.execute("INSERT INTO audit_logs (user_id, action, timestamp) VALUES (?,?,?)", (u['id'], "VIDEO_GEN", str(datetime.now())))
                                conn.commit()
                            st.rerun()
                    else: st.error(res)

    # --- 🎨 IMAGE STUDIO (FIXED ROUTING) ---
    elif menu == "🎨 Image Studio":
        st.write("### 🎨 Industrial HD Visual Studio")
        p_i = st.text_area("Image Details (One per line)")
        if st.button("Generate (1 Credit)"):
            if p_i and (credits >= 1 or u['role']=="admin"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?nologo=true"
                st.image(url)
                if u['role'] != 'admin':
                    with DatabaseManager.get_connection() as conn:
                        conn.execute("UPDATE wallets SET credits = credits - 1 WHERE user_id=?", (u['id'],))
                        conn.execute("INSERT INTO audit_logs (user_id, action, timestamp) VALUES (?,?,?)", (u['id'], "IMAGE_GEN", str(datetime.now())))
                        conn.commit()
                    st.rerun()

    # --- 💳 RECHARGE (FIXED LOGIC) ---
    elif menu == "💳 Recharge Wallet":
        st.title("💳 Purchase Premium Credits")
        with DatabaseManager.get_connection() as conn:
            ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa_no'").fetchone()[0]
            jc = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='jazzcash_no'").fetchone()[0]
            holder = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='account_holder'").fetchone()[0]
        
        st.info(f"EasyPaisa/JazzCash: **{ep}** | Holder: **{holder}**")
        st.code(ep, language="text") # Point #7: Correct Streamlit Copy Solution
        # Form for proof upload...

    # --- 📈 ADMIN STATS (POINT #3) ---
    elif menu == "📈 Statistics" and u['role']=="admin":
        st.title("Enterprise Analytics")
        with DatabaseManager.get_connection() as conn:
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            logs = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50", conn)
            st.metric("Total Active Users", users_count)
            st.write("### Recent Activity Logs")
            st.dataframe(logs, use_container_width=True)

st.markdown("<p style='text-align: center; border-top: 1px solid #eee; padding-top: 10px; margin-top:50px; font-weight:bold;'>Sglowina AI Enterprise | ES Founder & CEOs</p>", unsafe_allow_html=True)
