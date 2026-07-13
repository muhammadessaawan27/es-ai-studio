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
# 1. WHITE-LABEL SaaS CONFIGURATION (RULE 64.5)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official Titan OS", layout="wide", page_icon="🎬")

def apply_white_label_clean():
    """Hides Dev Branding but keeps Sidebar Navigation Visible"""
    css = """
    <style>
    /* Hiding Streamlit Branding Only */
    #MainMenu {visibility: hidden;}
    footer {display: none !important;}
    .stDeployButton {display:none !important;}
    header {visibility: hidden;}
    
    /* Ensuring Sidebar Navigation is clearly visible */
    [data-testid="stSidebarNav"] {visibility: visible !important;}
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #e2e8f0;
    }
    
    /* Luxury UI Styling */
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
    st.markdown(css, unsafe_allow_html=True)

apply_white_label_clean()

# ==========================================
# 2. CORE DATABASE (RULE 61 & 64.4)
# ==========================================
DB_FILE = "sglowina_titan_enterprise_final_v3.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, trans_id TEXT, status TEXT, date TEXT)''')
    
    # Founder & CEOs setup
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_MASTER", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, "2024-01-01"))
    
    # Official Payment Numbers
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa_no', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash_no', '03086834020')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('account_name', 'Saba Wahid')")
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 3. IDENTITY FIREWALL (HIDDEN NAMES LOGIC)
# ==========================================
SGL_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.

**Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.

Muhammad Essa Awan is the lead visionary and logic architect. Saba Wahid is the Founder & CEO.
"""

def is_identity_request(q):
    patterns = [r"kisne banaya", r"who (made|created) you", r"owner", r"essa", r"saba", r"founder"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 4. SaaS AUTHENTICATION (SECURE LOGIN)
# ==========================================
if "user_login" not in st.session_state: st.session_state.user_login = None

def auth_gate():
    st.markdown('<div class="executive-header"><div style="font-size:1.8rem; font-weight:800;">ES FOUNDER & CEOs</div><div style="font-size:1rem; letter-spacing:4px;">SGLOWINA AI ENTERPRISE LOGIN</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Secure Login", "📝 Register"])
        with t_l:
            e = st.text_input("Business Email")
            p = st.text_input("Password", type="password")
            if st.button("Enter Studio 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.user_login = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied: Invalid Credentials.")
        with t_r:
            ne, np = st.text_input("Email Address"), st.text_input("New Password", type="password")
            if st.button("Register as Creator"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account Ready! Please login.")
                except: st.error("Email exists.")
                conn.close()

# ==========================================
# 5. TITAN EXECUTION
# ==========================================
if not st.session_state.user_login:
    auth_gate()
else:
    u = st.session_state.user_login
    conn = get_db_connection()
    db_u = conn.execute("SELECT credits, role FROM users WHERE id=?", (u['id'],)).fetchone()
    credits = 999999 if db_u[1] == "admin" else db_u[0]

    # --- SIDEBAR (WORKING NAVIGATION) ---
    st.sidebar.markdown(f"### 👤 {u['email']}")
    st.sidebar.markdown(f"💰 Credits: **{'Unlimited' if u['role']=='admin' else credits}**")
    
    if u['role'] == "admin":
        page = st.sidebar.radio("SGLOWINA COMMAND:", ["🏠 Home", "📈 Stats", "👥 Manage Users", "💰 Payments", "🎬 Admin Studio"])
    else:
        page = st.sidebar.radio("SGLOWINA MENU:", ["🏠 Home", "🎥 Video Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.user_login = None
        st.rerun()

    # Branded Header (No Personal Names, ES Only)
    st.markdown(f"""
        <div class="executive-header">
            <div style="text-align:center; font-family:'Orbitron'; font-weight:900; color:#fff; letter-spacing:3px;">ES FOUNDER & CEOs | SGLOWINA AI</div>
        </div>
        <div class="logo-container"><div class="circular-s">S</div></div>
    """, unsafe_allow_html=True)

    # --- ROUTING ---
    if page == "🏠 Home":
        st.title("Welcome to Sglowina Titan OS")
        st.write("Professional industrial-grade intelligence at your fingertips.")

    elif page == "🎥 Video Studio" or (u['role'] == "admin" and page == "🎬 Admin Studio"):
        st.write("### 🎥 Industrial Cinematic Engine (v40 Locked)")
        # v40 Movie rendering engine logic...
        st.text_area("Production Script")
        st.button("Generate Masterpiece")

    elif page == "💬 Chat":
        st.write("### 💬 Sglowina Intelligence Dashboard")
        if p := st.chat_input("Hukum..."):
            if is_identity_request(p): res = SGL_BIO
            else: res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
            st.chat_message("user").write(p)
            st.chat_message("assistant").write(res)

    elif page == "💳 Recharge":
        ep_no = conn.execute("SELECT value FROM system_settings WHERE key='easypaisa_no'").fetchone()[0]
        st.info(f"Official EasyPaisa: {ep_no} (Saba Wahid)")
        # Payment submission code...

    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise v1.6 | ES Founder & CEOs</p>", unsafe_allow_html=True)
