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
# 1. INDUSTRIAL INFRASTRUCTURE (RULE 61)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_final.db"
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except Exception:
    pass

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, trans_id TEXT, status TEXT, date TEXT)''')
    
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_MASTER", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('holder_name', 'Saba Wahid')")
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. WHITE-LABEL UI SECURITY (RULE 64.5)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Enterprise OS", layout="wide", page_icon="🎬")

def apply_executive_branding():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;} footer {display: none !important;} 
        header {visibility: hidden;} .stDeployButton {display:none !important;}
        
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
        .logo-container { display: flex; flex-direction: column; align-items: center; padding: 25px 0; }
        .circular-s {
            width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 25px #00d4ff, inset 0 0 15px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        .stTextArea>div>div>textarea, .stTextInput>div>div>input { background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 10px !important; color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED BIO)
# ==========================================
SGL_BIO = """
**Sglowina AI is proudly developed by the Sglowina Team.**

**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.

**Muhammad Essa Awan** is the Founder & CEO, a professional Mechanical Engineer, and lead logical architect. 
**Saba Wahid** is the Founder & CEO and the daughter of Wahid Bakhsh.

Official Version 1.0 Premium Release.
"""

# ==========================================
# 4. ADVANCED AGENT & MOVIE ENGINE (v40 LOCKED)
# ==========================================
def create_v40_titan_movie(story, voice, ratio, style, seed):
    u_id = f"v1_prod_{str(uuid.uuid4())[:6]}"
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        import moviepy.video.fx.all as vfx
        v_code = "ur-PK-UzmaNeural" if "Female" in voice else "ur-PK-AsadNeural"
        audio_f = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_f))
        audio = AudioFileClip(audio_f)
        
        res_map = {
            "YouTube (16:9)": (1280, 720), "TikTok (9:16)": (720, 1280), 
            "Instagram (1:1)": (1024, 1024), "Ultra-Wide (21:9)": (2560, 1080)
        }
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        for i, s in enumerate(sentences):
            # Enforcing Shariah Policy and Golden Rules 1-11
            prompt = f"Professional 3D cinematic scene of {s}, {style} style, 8k, high detail, masterpiece. No humans unless asked."
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&negative=deformed,blurry"
            img_p = f"i_{u_id}_{i}.jpg"
            with open(img_p, "wb") as f: f.write(requests.get(url).content)
            with Image.open(img_p) as im: im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
            clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
            # Zoom Out Fix: 1.25 -> 1.0
            clip = clip.resize(lambda t: 1.25 - 0.25 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out_name = f"ES_TITAN_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. SaaS MAIN EXECUTION
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

apply_executive_branding()

if not st.session_state.user:
    st.markdown('<div class="executive-header"><div style="font-size:1.8rem; font-weight:800;">Muhammad Essa Awan & Saba Wahid</div><div style="font-size:1rem; letter-spacing:4px;">ES FOUNDER & CEOs | SGLOWINA AI</div></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Secure Login", "📝 New Registration"])
        with t_l:
            e = st.text_input("Business Email")
            p = st.text_input("Password", type="password")
            if st.button("Access Titan OS 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied!")
        with t_r:
            ne, np = st.text_input("Creator Email"), st.text_input("Create Password", type="password")
            if st.button("Register as Creator"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account Ready!")
                except: st.error("Email exists.")
                conn.close()
else:
    u = st.session_state.user
    conn = get_db_connection()
    db_u = conn.execute("SELECT credits, role FROM users WHERE id=?", (u['id'],)).fetchone()
    credits = 999999 if db_u[1] == "admin" else db_u[0]

    # Sidebar: Unified & Clean
    st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    menu = st.sidebar.radio("SGLOWINA TITAN:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "👥 Users" if u['role']=="admin" else "💳 Recharge"])
    
    if st.sidebar.button("Logout 🚪"):
        st.session_state.user = None
        st.rerun()

    # Executive Branding
    st.markdown('<div class="executive-header"><div style="text-align:center; font-family:\'Inter\'; font-weight:800; font-size:1.8rem; color:#fff;">Muhammad Essa Awan & Saba Wahid</div><div style="text-align:center; font-family:\'Orbitron\'; font-weight:900; color:#ff007a; letter-spacing:3px;">ES FOUNDER & CEOs | SGLOWINA AI</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    # PAGE LOGIC
    if menu == "🎨 Image Studio":
        st.write("### 🎨 Industrial HD Image Studio")
        i_p = st.text_area("Describe Image(s) - One per line:")
        c1, c2, c3 = st.columns(3)
        with c1: i_s = st.selectbox("Style", ["Realistic", "3D Pixar", "Anime", "Logo", "Sketch"])
        with c2: i_r = st.selectbox("Resolution", ["Square (1:1)", "YouTube HD (16:9)", "TikTok (9:16)", "Ultra-Wide (21:9)"])
        with c3: i_q = st.slider("Quantity", 1, 10, 1)
        char_seed = st.number_input("Consistency Lock ID:", value=786)
        if st.button("Generate HD Visuals 🚀"):
            if i_p and credits >= i_q:
                prompts = [line.strip() for line in i_p.split('\n') if line.strip()]
                w, h = (1024, 1024) if "1:1" in i_r else (1280, 720) if "16:9" in i_r else (720, 1280) if "9:16" in i_r else (2560, 1080)
                for p_item in prompts:
                    for q in range(i_q):
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_item + ' ' + i_s)}?width={w}&height={h}&seed={char_seed+q}&nologo=true"
                        st.image(url, caption=f"Titan Output: {p_item[:30]}...")

    elif menu == "🎥 Movie Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
        if credits < 10: st.error("Low Credits!")
        else:
            m_s = st.text_area("Production Script")
            cv1, cv2, cv3 = st.columns(3)
            with cv1: v = st.selectbox("Voice", ["Male (Asad)", "Female (Uzma)"])
            with cv2: r = st.selectbox("Ratio", ["YouTube (16:9)", "TikTok (9:16)"])
            with cv3: s = st.selectbox("Style", ["Realistic", "Cinematic", "3D Cartoon"])
            c_seed = st.number_input("Face Lock ID:", value=786)
            if st.button("Render Titan Movie"):
                res = create_v40_titan_movie(m_s, v, r, s, u['id'], c_seed)
                if "mp4" in res:
                    st.video(res)
                    if u['role'] != "admin": conn.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (u['id'],)); conn.commit()

    elif menu == "👥 Users" and u['role'] == "admin":
        st.title("User Management System")
        users_df = pd.read_sql_query("SELECT id, email, role, credits, joined_at FROM users", conn)
        st.dataframe(users_df, use_container_width=True)
        target = st.text_input("Enter Email to add Credits")
        val = st.number_input("Amount", min_value=0)
        if st.button("Update User"):
            conn.execute("UPDATE users SET credits = credits + ? WHERE email=?", (val, target))
            conn.commit(); st.success("User Updated!")

    elif menu == "💳 Recharge":
        ep = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key='easypaisa'").fetchone()[0]
        st.info(f"Official EasyPaisa: {ep} (Saba Wahid)")

    elif menu == "💬 Chat":
        if p := st.chat_input("Hukum..."):
            res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text.replace("ChatGPT", "Sglowina AI")
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)
    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Version 1.0 | ES Founder & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
