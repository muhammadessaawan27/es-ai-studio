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
from datetime import datetime
from PIL import Image
import pandas as pd

# ==========================================
# 1. DATABASE & SECURITY SETUP
# ==========================================
DB_FILE = "es_ai_saas.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                 role TEXT, status TEXT, credits INTEGER, plan TEXT, joined_at TEXT)''')
    # Payments Table
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, 
                 plan TEXT, status TEXT, timestamp TEXT)''')
    # History Table
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT, 
                 prompt TEXT, result_url TEXT, timestamp TEXT)''')
    
    # Create Admin if not exists (Password: admin123)
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (email, password, role, status, credits, plan, joined_at) VALUES (?,?,?,?,?,?,?)",
              ("admin@esai.com", admin_hash, "admin", "active", 999999, "Lifetime", datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

init_db()

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 2. SAAS UI & BRANDING
# ==========================================
st.set_page_config(page_title="ES AI Master SaaS", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 900;
        text-align: center; letter-spacing: 5px; color: #fff;
        background: #1e293b; padding: 10px; border-radius: 0 0 20px 20px;
        animation: glow 1.5s infinite;
    }
    @keyframes glow { 0%, 100% { text-shadow: 0 0 10px #2563eb; } 50% { text-shadow: 0 0 20px #ff007a; } }
    .saas-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #2563eb; }
    .stButton>button { background: linear-gradient(90deg, #2563EB, #7C3AED) !important; color: white !important; border-radius: 10px !important; height: 45px; width: 100%; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTICATION SYSTEM
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def login_user(email, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=? AND status='active'", (email, hash_pass(password)))
    user = c.fetchone()
    conn.close()
    return user

def register_user(email, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, role, status, credits, plan, joined_at) VALUES (?,?,?,?,?,?,?)",
                  (email, hash_pass(password), "user", "active", 10, "Free", datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

# ==========================================
# 4. CORE AI ENGINES (Preserved v40)
# ==========================================
session = requests.Session()

def get_v40_visual_prompt(urdu_text):
    instr = f"Director: Extract primary subject from Urdu: '{urdu_text}'. Describe in English for 3D animation. Accurate animals/objects. No humans unless mentioned."
    res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai", timeout=25)
    return res.text if res.status_code == 200 else urdu_text

# (create_v40_movie_engine and image_studio_pro_module logic here, wrapped with credit checks)

# ==========================================
# 5. NAVIGATION & PAGES
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>ES AI MASTER STUDIO</h1>", unsafe_allow_html=True)
    
    auth_tab1, auth_tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    with auth_tab1:
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Login 🚀"):
            user = login_user(email, pwd)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else: st.error("Ghalat Email ya Password! Ya account block hai.")
    with auth_tab2:
        new_email = st.text_input("New Email")
        new_pwd = st.text_input("New Password", type="password")
        if st.button("Register Now"):
            if register_user(new_email, new_pwd): st.success("Account ban gaya! Ab Login karein.")
            else: st.error("Email pehle se maujood hai.")

else:
    # --- LOGGED IN AREA ---
    user_data = st.session_state.user
    role = user_data[3]
    
    st.sidebar.markdown(f"### 👤 {user_data[1]}")
    st.sidebar.markdown(f"**Plan:** {user_data[6]} | **Credits:** {user_data[5]}")
    
    if role == "admin":
        menu = st.sidebar.radio("Admin Menu:", ["📈 Dashboard", "👥 Manage Users", "💰 Payments", "🎬 Use AI"])
    else:
        menu = st.sidebar.radio("User Menu:", ["🏠 My Dashboard", "🎬 Movie Studio", "🎨 Image Studio", "💬 Chat", "💳 Upgrade"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if role == "admin" and menu == "📈 Dashboard":
        st.title("Admin Control Center")
        conn = get_db_connection()
        total_u = pd.read_sql("SELECT COUNT(*) FROM users", conn).iloc[0,0]
        total_p = pd.read_sql("SELECT SUM(amount) FROM payments WHERE status='approved'", conn).iloc[0,0] or 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Users", total_u)
        col2.metric("Revenue", f"PKR {total_p}")
        col3.metric("Active Sessions", "Global")
        conn.close()

    elif role == "admin" and menu == "👥 Manage Users":
        st.title("User Management")
        conn = get_db_connection()
        df = pd.read_sql("SELECT id, email, role, status, credits, plan, joined_at FROM users", conn)
        st.dataframe(df, use_container_width=True)
        
        target_email = st.text_input("User Email to Manage")
        action = st.selectbox("Action", ["Add Credits", "Reduce Credits", "Block User", "Active User", "Delete User"])
        val = st.number_input("Value (if applicable)", min_value=0)
        
        if st.button("Apply Action"):
            c = conn.cursor()
            if action == "Add Credits": c.execute("UPDATE users SET credits = credits + ? WHERE email=?", (val, target_email))
            elif action == "Block User": c.execute("UPDATE users SET status = 'blocked' WHERE email=?", (target_email,))
            elif action == "Delete User": c.execute("DELETE FROM users WHERE email=?", (target_email,))
            conn.commit()
            st.success("Hukum par amal ho gaya!")
        conn.close()

    # --- USER DASHBOARD ---
    elif menu == "🏠 My Dashboard":
        st.title(f"Welcome back, Essa Bhai!")
        st.markdown(f"""
        <div class="saas-card">
            <h3>Your Account Status</h3>
            <p><b>Current Plan:</b> {user_data[6]}</p>
            <p><b>Available Credits:</b> {user_data[5]}</p>
            <p><b>Account Level:</b> {user_data[3]}</p>
        </div>
        """, unsafe_allow_html=True)
        
    # --- MOVIE STUDIO (WITH CREDIT CHECK) ---
    elif menu == "🎬 Movie Studio":
        st.header("🎬 Pro Movie Studio")
        if user_data[5] < 10:
            st.warning("Bhai, Credits khatam hain! Please recharge karein.")
        else:
            m_s = st.text_area("Story Script")
            if st.button("Generate Movie (Cost: 10 Credits)"):
                # Deduct credits
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (user_data[0],))
                conn.commit()
                conn.close()
                st.success("Credits deducted. Starting v40 Engine...")
                # Call v40 Movie Engine here...

    # --- UPGRADE PLAN ---
    elif menu == "💳 Upgrade":
        st.title("Choose Your Plan")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown("### Basic\n**100 Credits**\nPKR 1000/mo")
            if st.button("Buy Basic"): st.info("Pay 1000 to EasyPaisa: 03xx-xxxxxxx and send screenshot in Chat.")
        with p2:
            st.markdown("### Pro\n**500 Credits**\nPKR 3000/mo")
            if st.button("Buy Pro"): st.info("Contact Admin.")
        with p3:
            st.markdown("### Premium\n**2000 Credits**\nPKR 10000/mo")
            if st.button("Buy Premium"): st.info("Contact Admin.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v60.0 | SaaS Production Edition | Muhammad Essa Awan</p>", unsafe_allow_html=True)
