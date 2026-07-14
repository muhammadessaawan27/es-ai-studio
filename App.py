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
# 1. CORE SYSTEM ARCHITECTURE (RULE 61)
# ==========================================
DB_FILE = "sglowina_titan_production_v1.db"
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

class DatabaseManager:
    @staticmethod
    def get_connection():
        # Using context manager for safe closure
        return sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)

    @staticmethod
    def init_db():
        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT, joined_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS wallets (user_id TEXT PRIMARY KEY, credits INTEGER, plan TEXT, updated_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan TEXT, trx_id TEXT, proof_blob BLOB, status TEXT, timestamp TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS system_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, timestamp TEXT)''')
            
            # Super Admin
            admin_pass = bcrypt.hashpw("admin786".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", ("ADMIN_001", "admin@sglowina.ai", admin_pass, "admin", "active", "2024-07-14"))
            c.execute("INSERT OR IGNORE INTO wallets VALUES (?,?,?,?)", ("ADMIN_001", 999999, "Founder", str(datetime.now())))
            
            # Standardized Database Keys (Correction #3)
            defaults = [('easypaisa_no', '03086834020'), ('jazzcash_no', '03086834020'), ('account_holder', 'Saba Wahid')]
            for k, v in defaults:
                c.execute("INSERT OR IGNORE INTO system_settings VALUES (?,?)", (k, v))
            conn.commit()

DatabaseManager.init_db()

# ==========================================
# 2. ADVANCED AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglowinaTitanOS:
    @staticmethod
    def visual_director_agent(urdu_text, style_choice):
        shariah_keywords = ["نبی", "رسول", "صحابی", "ولی اللہ", "اللہ", "قبر", "کفن", "prophet", "sahaba"]
        is_holy = any(k in urdu_text.lower() for k in shariah_keywords)
        protection = "STRICTLY NO FACE. NO FACIAL FEATURES. SHOW BRIGHT NOOR LIGHT." if is_holy else ""
        director_instr = f"Act as High-End Director. Scene: '{urdu_text}'. {protection} Style: {style_choice}. 8k cinematic."
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(director_instr)}?model=openai&cache=true"
            res = session.get(url, timeout=40)
            return res.text if res.status_code == 200 else urdu_text
        except: return urdu_text

# ==========================================
# 3. WHITE-LABEL EXECUTIVE UI (RULE 64.5)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan OS", layout="wide", page_icon="🎬")

def apply_white_label_css():
    st.markdown("""
        <style>
        header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        .stDeployButton {display:none;} [data-testid="stSidebarNav"] {visibility: visible !important;}
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        .executive-header { text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9; background: #0f172a; border-radius: 0 0 40px 40px; color: #fff; }
        .circular-logo { width: 80px; height: 80px; background: #0f172a; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Orbitron', sans-serif; font-size: 35px; color: white; border: 3px solid #00d4ff; animation: spin 8s infinite linear; margin: auto; }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 4. TITAN MOVIE ENGINE (v40 - PRODUCTION READY)
# ==========================================
def fetch_img_content(url):
    try:
        r = session.get(url, timeout=60)
        return r.content if r.status_code == 200 else None
    except: return None

def create_v40_titan_movie(story, voice, ratio, style, user_id, seed):
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
    
    u_id = f"v1_{str(uuid.uuid4())[:6]}"
    temp_files = []
    try:
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"{u_id}_a.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        temp_files.append(audio_f)
        
        audio = AudioFileClip(audio_f)
        # Standardized Ratios (Correction #2)
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map.get(ratio, (1280, 720))
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)

        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(SglowinaTitanOS.visual_director_agent(s, style))}?width={w}&height={h}&seed={seed}&nologo=true" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img_content, img_urls)):
                if img_data:
                    img_p = f"{u_id}_i_{i}.jpg"
                    with Image.open(io.BytesIO(img_data)) as im:
                        im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                    temp_files.append(img_p)
                    clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                    clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                    clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_MOVIE_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        audio.close(); final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"
    finally:
        # Step 6: Proper Cleanup
        for f in temp_files:
            if os.path.exists(f): os.remove(f)

# ==========================================
# 5. SAAS CONTROLLER
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

def login_system():
    apply_white_label_css()
    st.markdown('<div class="executive-header"><h1 style="font-family:Orbitron;">ES FOUNDER & CEOs</h1><p>SGLOWINA AI ENTERPRISE ACCESS</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        tab_l, tab_r = st.tabs(["🔐 Login", "📝 Enterprise Signup"])
        with tab_l:
            e = st.text_input("Enterprise ID")
            p = st.text_input("Security Key", type="password")
            if st.button("Access Titan OS 🚀"):
                with DatabaseManager.get_connection() as conn:
                    u = conn.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone()
                    if u and bcrypt.checkpw(p.encode(), u[2].encode()):
                        wallet = conn.execute("SELECT credits, plan FROM wallets WHERE user_id=?", (u[0],)).fetchone()
                        st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": wallet[0], "plan": wallet[1]}
                        conn.execute("INSERT INTO audit_logs (user_id, action, timestamp) VALUES (?,?,?)", (u[0], "AUTH_LOGIN", str(datetime.now())))
                        st.rerun()
                    else: st.error("Access Denied.")
        with tab_r:
            st.info("Registration requires Admin Approval.")

# ==========================================
# 6. MAIN APP FLOW
# ==========================================
if not st.session_state.user:
    login_system()
else:
    u = st.session_state.user
    apply_white_label_css()
    
    # Sidebar Live Sync
    with DatabaseManager.get_connection() as conn:
        db_wallet = conn.execute("SELECT credits FROM wallets WHERE user_id=?", (u['id'],)).fetchone()
        current_credits = db_wallet[0] if db_wallet else 0
    
    st.sidebar.markdown(f"<div class='circular-logo'>ES</div>", unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 {u['email']}\n\n💰 Credits: **{'Unlimited' if u['role']=='admin' else current_credits}**")
    
    if u['role'] == "admin":
        menu = st.sidebar.radio("COMMAND:", ["📈 Stats", "💰 Payments", "👥 Users", "🎬 Use AI"])
    else:
        menu = st.sidebar.radio("MENU:", ["🏠 Dashboard", "🎥 Video Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge", "📖 About"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    st.markdown('<div class="executive-header"><h1>ES Founder & CEOs</h1><p>SGLOWINA AI OFFICIAL STUDIO</p></div>', unsafe_allow_html=True)

    # --- VIDEO STUDIO (ATOMIC CREDIT DEDUCTION) ---
    if menu == "🎥 Video Studio" or (u['role']=="admin" and menu=="🎬 Use AI"):
        st.write("### 🎥 Industrial Production Cluster")
        m_s = st.text_area("Production Script")
        ratio = st.selectbox("Format", ["YouTube (16:9)", "TikTok/Reels (9:16)"]) # Correction #2
        if st.button("Generate Masterpiece (10 Credits)"):
            if m_s and (current_credits >= 10 or u['role']=="admin"):
                with st.spinner("Processing Production Job..."):
                    # Render Video (Correction #1 - Proper function call)
                    res_file = create_v40_titan_movie(m_s, "Male", ratio, "Realistic", u['id'], 786)
                    if "mp4" in res_file:
                        st.video(res_file)
                        # Atomic Success Transaction (Correction #4)
                        if u['role'] != 'admin':
                            with DatabaseManager.get_connection() as conn:
                                conn.execute("UPDATE wallets SET credits = credits - 10 WHERE user_id=?", (u['id'],))
                                conn.execute("INSERT INTO audit_logs (user_id, action, timestamp) VALUES (?,?,?)", (u['id'], "VIDEO_GEN_SUCCESS", str(datetime.now())))
                            st.rerun() # Refresh Sidebar
                    else: st.error(res_file)

    # --- RECHARGE MODULE (STANDARDIZED KEYS) ---
    elif menu == "💳 Recharge":
        st.title("💳 Purchase Credits")
        with DatabaseManager.get_connection() as conn:
            # Correction #3: Unified keys
            ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa_no'").fetchone()[0]
            jc = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='jazzcash_no'").fetchone()[0]
            name = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='account_holder'").fetchone()[0]
        
        st.info(f"**EasyPaisa/JazzCash:** {ep} | **Holder:** {name}")
        st.code(ep, language="text") # Point #7: Copy Button
        # Payment submission logic...

    # --- ABOUT ---
    elif menu == "📖 About":
        st.title("Founder Biography")
        st.write("Muhammad Essa Awan & Saba Wahid")
        st.write("Specialists in Mechanical Engineering and Enterprise AI Architecture.")

st.markdown("<p style='text-align: center; border-top: 1px solid #eee; padding-top: 10px; margin-top:50px; font-weight:bold;'>ES Founder & CEOs</p>", unsafe_allow_html=True)
