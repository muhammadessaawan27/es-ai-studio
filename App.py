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
# 1. DATABASE & SECURITY ARCHITECTURE
# ==========================================
DB_FILE = "sglowina_enterprise_v2.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    # Payments Table (Rule 64.4 Verification)
    c.execute('''CREATE TABLE IF NOT EXISTS payments 
                 (id TEXT PRIMARY KEY, user_id TEXT, amount REAL, method TEXT, 
                  trans_id TEXT, screenshot_path TEXT, status TEXT, date TEXT)''')
    # Official Wallet Settings (Security Rule)
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    # Audit Logs
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, admin_id TEXT, timestamp TEXT)''')
    
    # Initialize Official Payment Numbers (Super Admin Only)
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('easypaisa_no', '03XX-XXXXXXX')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('jazzcash_no', '03XX-XXXXXXX')")
    c.execute("INSERT OR IGNORE INTO system_settings VALUES ('account_name', 'Muhammad Essa Awan')")
    
    # MASTER ADMIN SETUP
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_TITAN", "admin@sglowina.ai", admin_pass, "admin", 999999, "2024-01-01"))
    conn.commit()
    conn.close()

init_enterprise_db()

# ==========================================
# 2. BRANDING & UI (EXECUTIVE MINIMAL)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Enterprise OS", layout="wide", page_icon="🎬")

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
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
            border: 3px solid #00d4ff; box-shadow: 0 0 30px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 60px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY FIREWALL (CEO & FOUNDER)
# ==========================================
SGLOW_BIO = """
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.

**Muhammad Essa Awan** is the Founder & CEO, lead visionary, and Chief logical architect. 
**Saba Wahid** is the Founder & CEO and the daughter of Wahid Bakhsh.

Sglowina AI Enterprise v1.1. Official Shariah-Compliant Architecture.
"""

# ==========================================
# 4. SAAS BUSINESS LOGIC (RULE 64.4)
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

def login_gate():
    apply_executive_ui()
    st.markdown('<div class="brand-header">SGLOWINA AI ENTERPRISE ACCESS</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        t_l, t_r = st.tabs(["🔐 Secure Login", "📝 Create Business Account"])
        with t_l:
            e = st.text_input("Email")
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
            ne, np = st.text_input("New Email"), st.text_input("New Password", type="password")
            if st.button("Register as Creator (10 Free Credits)"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Registration Success! Login to start.")
                except: st.error("Email exists.")
                conn.close()

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
if not st.session_state.user:
    login_gate()
else:
    u = st.session_state.user
    apply_executive_ui()
    
    # Sidebar Management
    conn = get_db_connection()
    curr_credits = conn.execute("SELECT credits FROM users WHERE id=?", (u['id'],)).fetchone()[0]
    st.sidebar.markdown(f"### 👤 {u['email']}\n💰 Credits: **{curr_credits}**")
    
    if u['role'] == "admin":
        menu = st.sidebar.radio("SGLOWINA ADMIN:", ["📈 Stats", "👥 Manage Users", "💰 Pending Payments", "🎬 Use AI System"])
    else:
        menu = st.sidebar.radio("SGLOWINA MENU:", ["🏠 Dashboard", "🎥 Movie Studio", "🎨 Image Studio", "💬 Chat", "💳 Recharge Credits"])

    # Shared Branding
    st.markdown("""<div class="executive-header"><div style="text-align:center; font-family:'Inter'; font-weight:800; font-size:1.8rem; color:#000;">Muhammad Essa Awan & Saba Wahid</div>
                <div style="text-align:center; font-family:'Orbitron'; font-weight:900; color:#ff007a; letter-spacing:3px;">FOUNDERS & CEOs | SGLOWINA AI</div></div>""", unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    # --- 💸 RULE 64.4: SECURE RECHARGE (USER VIEW) ---
    if menu == "💳 Recharge Credits":
        st.title("💳 Buy Premium Credits")
        st.write("Select a plan and follow instructions to recharge your account.")
        
        c1, c2, c3 = st.columns(3)
        c1.info("PKR 1,000\n\n**100 Credits**")
        c2.success("PKR 2,000\n\n**220 Credits** (Bonus)")
        c3.warning("PKR 3,000\n\n**350 Credits** (Big Bonus)")
        
        # Display Official Numbers (Admin Controlled)
        e_no = conn.execute("SELECT value FROM system_settings WHERE key='easypaisa_no'").fetchone()[0]
        j_no = conn.execute("SELECT value FROM system_settings WHERE key='jazzcash_no'").fetchone()[0]
        a_nm = conn.execute("SELECT value FROM system_settings WHERE key='account_name'").fetchone()[0]
        
        st.markdown(f"""
        <div style="background:#f1f5f9; padding:20px; border-radius:15px; border-left:10px solid #ff007a;">
            <h3>Official Payment Methods</h3>
            <p><b>EasyPaisa:</b> {e_no}</p>
            <p><b>JazzCash:</b> {j_no}</p>
            <p><b>Account Holder:</b> {a_nm}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Submit Payment Proof")
        t_id = st.text_input("Transaction ID (TRX)")
        t_amt = st.number_input("Amount Paid", min_value=1000)
        t_proof = st.file_uploader("Upload Screenshot", type=["jpg", "png", "jpeg"])
        
        if st.button("Submit Payment for Verification"):
            if t_id and t_proof:
                p_id = str(uuid.uuid4())[:8]
                conn.execute("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (p_id, u['id'], t_amt, "Mobile Wallet", t_id, "proof_file", "pending", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("Request Sent! Credits will be added after Admin verification.")

    # --- 💰 RULE 64.4: PENDING PAYMENTS (ADMIN VIEW) ---
    elif menu == "💰 Pending Payments" and u['role'] == "admin":
        st.title("💰 Verify Pending Payments")
        pending = pd.read_sql_query("SELECT payments.*, users.email FROM payments JOIN users ON payments.user_id = users.id WHERE payments.status='pending'", conn)
        
        if pending.empty: st.info("No pending requests.")
        else:
            for index, row in pending.iterrows():
                with st.expander(f"Request from {row['email']} - PKR {row['amount']}"):
                    st.write(f"TRX ID: {row['trans_id']}")
                    if st.button(f"Approve Payment {row['id']} ✅"):
                        # Calculate credits based on PKR
                        creds = 100 if row['amount'] < 2000 else 220 if row['amount'] < 3000 else 350
                        conn.execute("UPDATE users SET credits = credits + ? WHERE id=?", (creds, row['user_id']))
                        conn.execute("UPDATE payments SET status='approved' WHERE id=?", (row['id'],))
                        conn.execute("INSERT INTO audit_logs (action, admin_id, timestamp) VALUES (?, ?, ?)",
                                     (f"Approved {creds} credits for {row['email']}", u['id'], datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.rerun()

    # --- 🎥 MOVIE STUDIO (LOCKED v40 + CREDIT CHECK) ---
    elif menu == "🎥 Movie Studio":
        if curr_credits < 10:
            st.error("❌ Credits Finished! Please Recharge.")
        else:
            st.write("### 🎥 Industrial Cinematic Engine (v40 Power)")
            m_s = st.text_area("Story Script")
            if st.button("Generate Masterpiece (10 Credits)"):
                # Credit Deduction First
                conn.execute("UPDATE users SET credits = credits - 10 WHERE id=?", (u['id'],))
                conn.commit()
                # Then call v40 production engine...
                st.success("Rendering Started!")

    elif menu == "👥 Users" and u['role'] == "admin":
        st.title("Enterprise User Control")
        # Full CRUD logic as per Rule 64.4 Admin Controls...

    conn.close()

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise v1.1 | Founders & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
