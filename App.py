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
# 1. WHITE-LABEL ENGINE (RULE 64.5 - FIXED)
# ==========================================
st.set_page_config(
    page_title="Sglowina AI - Official Titan OS", 
    layout="wide", 
    page_icon="🎬"
)

def apply_clean_branding():
    """Hides Third-Party Branding while keeping UI Functional"""
    hide_streamlit_style = """
    <style>
    /* Rule 64.5: Hiding ONLY Development Branding */
    #MainMenu {visibility: hidden;} /* Top right hamburger */
    footer {display: none !important;} /* "Made with Streamlit" */
    .stDeployButton {display:none !important;} /* Deploy button */
    header {visibility: hidden;} /* Header decorations */
    
    /* RESTORING SIDEBAR VISIBILITY */
    [data-testid="stSidebarNav"] {visibility: visible !important;}
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #e2e8f0;
    }
    
    /* LUXURY UI THEME */
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
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

apply_clean_branding()

# ==========================================
# 2. CORE DATABASE (RULE 61 INDEPENDENCE)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_final.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, trans_id TEXT, status TEXT, date TEXT)''')
    
    # FOUNDER & CEOs SETUP
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_001", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa', '03XX-XXXXXXX')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash', '03XX-XXXXXXX')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('holder_name', 'Muhammad Essa Awan')")
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. IDENTITY FIREWALL (LOCKED)
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.

Muhammad Essa Awan is the lead visionary, Mechanical Engineer, and architect. 
Saba Wahid is the Founder & CEO and the daughter of Wahid Bakhsh.
"""

# ==========================================
# 4. SaaS AUTHENTICATION (SECURE LOGIN)
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

def login_signup_gate():
    st.markdown('<div class="executive-header"><div style="font-size:1.8rem; font-weight:800;">Muhammad Essa Awan & Saba Wahid</div><div style="font-size:1rem; letter-spacing:4px;">SGLOWINA AI ENTERPRISE LOGIN</div></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Secure Login", "📝 Register"])
        with t_l:
            email = st.text_input("Business Email")
            pwd = st.text_input("Password", type="password")
            if st.button("Enter Dashboard 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hashlib.sha256(pwd.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.authenticated_user = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied: Invalid Credentials.")
        with t_r:
            ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
            if st.button("Create Enterprise ID"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Success! Please login.")
                except: st.error("Email exists.")
                conn.close()

# ==========================================
# 5. MAIN SYSTEM EXECUTION
# ==========================================
if not st.session_state.authenticated_user:
    login_signup_gate()
else:
    u = st.session_state.authenticated_user
    conn = get_db_connection()
    db_u = conn.execute("SELECT credits, role FROM users WHERE id=?", (u['id'],)).fetchone()
    credits = 999999 if db_u[1] == "admin" else db_u[0]

    # --- SIDEBAR (RE-ENABLED & WORKING) ---
    st.sidebar.markdown(f"### 👤 {u['email']}")
    st.sidebar.markdown(f"💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    
    if u['role'] == "admin":
        page = st.sidebar.radio("SGLOWINA COMMAND:", ["📈 Stats", "👥 Users", "💰 Payments", "⚙️ Settings", "🎬 AI Studio"])
    else:
        page = st.sidebar.radio("SGLOWINA MENU:", ["🏠 Dashboard", "🎥 Video Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.authenticated_user = None
        st.rerun()

    # White-Label Header (NO Streamlit Branding)
    st.markdown(f"""
        <div class="executive-header">
            <div style="font-family:'Inter'; font-weight:800; font-size:1.8rem; color:#fff; text-align:center;">Muhammad Essa Awan & Saba Wahid</div>
            <div style="text-align:center; font-family:'Orbitron'; font-weight:900; color:#ff007a; letter-spacing:3px;">ES FOUNDER & CEOs | SGLOWINA AI</div>
        </div>
        <div class="logo-container"><div class="circular-s">S</div></div>
    """, unsafe_allow_html=True)

    # --- PAGE LOGIC ---
    if page == "🎥 Video Studio":
        st.write("### 🎥 Industrial Cinematic Engine (v40 Locked)")
        # v40 Logic here...

    elif page == "💬 Chat":
        st.write("### 💬 Sglowina Intelligence Dashboard")
        if p := st.chat_input("Hukum..."):
            if any(k in p.lower() for k in ["founder", "creator", "owner", "kisne banaya"]): res = SGL_BIO
            else:
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

    elif page == "⚙️ Settings" and u['role'] == "admin":
        st.title("⚙️ Enterprise Configuration")
        # Admin payment number settings here...

    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise v1.3 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
