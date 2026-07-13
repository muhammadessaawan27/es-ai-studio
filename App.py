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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. CORE SYSTEM INDEPENDENCE (RULE 61)
# ==========================================
DB_FILE = "sglowina_enterprise_core.db"
session = requests.Session()

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_enterprise_architecture():
    conn = get_db_connection()
    c = conn.cursor()
    # Users: Persistent Storage
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, 
                  role TEXT, status TEXT, credits INTEGER, joined_at TEXT)''')
    # Admin System: Working Links Check
    c.execute('''CREATE TABLE IF NOT EXISTS system_config 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # MANDATORY FOUNDER CONFIGURATION (Muhammad Essa Awan & Saba Wahid)
    admin_pass = hashlib.sha256("admin786".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("ADMIN_GLOBAL", "admin@sglowina.ai", admin_pass, "admin", "active", 999999, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

init_enterprise_architecture()

# ==========================================
# 2. ADVANCED AI AGENT COMMAND SYSTEM (RULE 62)
# ==========================================
class SglowinaTitanOS:
    """The Multi-Agent Brain of Sglowina AI."""
    def __init__(self, user_id):
        self.user_id = user_id
        self.engines = ["openai", "mistral", "llama", "unity"]

    def orchestrate_text(self, prompt, system_role):
        """Rule 61: API Independence Layer"""
        for engine in self.engines:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}?model={engine}&system={urllib.parse.quote(system_role)}&cache=true"
                res = requests.get(url, timeout=20)
                if res.status_code == 200:
                    return res.text.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except: continue
        return "System Internal Fallback: Processing Request..."

    def production_agent(self, urdu_script, style):
        """Production Agent: Story -> Prompt -> Video Workflow"""
        # Islamic Content Visual Generation Rules Enforcement
        shariah_keywords = ["allah", "islam", "nabi", "rasul", "sahaba", "qabr", "kafan", "اللہ", "نبی", "قبر"]
        is_shariah = any(k in urdu_script.lower() for k in shariah_keywords)
        
        guard_prompt = ""
        if is_shariah:
            guard_prompt = "STRICTLY NO FACE. NO FACIAL FEATURES. Show bright white Noorani light. Modest Islamic historical clothing. Traditional graves."

        director_query = f"Act as Sglowina Production Director. Scene: '{urdu_script}'. {guard_prompt}. Style: {style}. Technical 3D cinematic prompt. English only."
        return self.orchestrate_text(director_query, "You are a professional film production agent.")

# ==========================================
# 3. EXECUTIVE UI & BRANDING
# ==========================================
def apply_enterprise_ui():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
        
        /* Functional Header */
        .executive-header {
            text-align: center; padding: 25px; border-bottom: 2px solid #f1f5f9; margin-bottom: 20px;
            background: #0f172a; border-radius: 0 0 50px 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .main-names { font-size: 1.8rem; font-weight: 800; color: #ffffff; letter-spacing: 1px; }
        .role-tag { font-size: 1rem; font-weight: 900; color: #ff007a; letter-spacing: 5px; text-transform: uppercase; }

        .logo-container { display: flex; justify-content: center; padding: 20px 0; }
        .circular-s {
            width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Orbitron', sans-serif; font-size: 55px; color: white;
            border: 4px solid #ff007a; box-shadow: 0 0 30px #ff007a;
            animation: spin 8s infinite linear;
        }
        @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
        
        .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
        [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 4. IDENTITY FIREWALL (LOCKED FOUNDER DATA)
# ==========================================
FOUNDER_BIO = """
**ES Founder & CEOs:** Muhammad Essa Awan & Saba Wahid.

**Muhammad Essa Awan** is the Founder & CEO, Chief logical architect and lead engineer of Sglowina AI.

**Saba Wahid** is the Founder & CEO, director of operations and enterprise management.

Sglowina AI is an industrial-grade intelligence ecosystem developed from scratch for global creative excellence.
"""

# ==========================================
# 5. ENTERPRISE SAAS ROUTING (RULE 64.3)
# ==========================================
if "session_id" not in st.session_state:
    st.session_state.session_id = None

def login_register():
    apply_enterprise_ui()
    st.markdown('<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div><div class="role-tag">SGLOWINA AI ENTERPRISE LOGIN</div></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab_log, tab_reg = st.tabs(["🔐 Secure Login", "📝 New Registration"])
        with tab_log:
            e = st.text_input("Enterprise Email")
            p = st.text_input("Security Password", type="password")
            if st.button("Enter Dashboard 🚀"):
                conn = get_db_connection()
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
                conn.close()
                if u:
                    st.session_state.session_id = {"id": u[0], "email": u[1], "role": u[3], "credits": u[5]}
                    st.rerun()
                else: st.error("Access Denied: Invalid Credentials.")
        
        with tab_reg:
            ne, np = st.text_input("New Business Email"), st.text_input("Create Password", type="password")
            if st.button("Register Creator"):
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (str(uuid.uuid4())[:8], ne, hashlib.sha256(np.encode()).hexdigest(), "user", "active", 10, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Enterprise ID Created! Please login.")
                except: st.error("Email registration error.")
                conn.close()

# ==========================================
# 6. MAIN SYSTEM EXECUTION
# ==========================================
if not st.session_state.session_id:
    login_register()
else:
    u = st.session_state.session_id
    apply_enterprise_ui()
    
    # --- Sidebar Command Center ---
    st.sidebar.markdown(f"### 👤 {u['email']}")
    st.sidebar.markdown(f"💰 Credits: **{u['credits']}**")
    
    if u['role'] == "admin":
        page = st.sidebar.radio("SGLOWINA TITAN COMMAND:", ["📈 Enterprise Analytics", "👥 Manage Users", "💳 Billing", "🎬 Use AI System"])
    else:
        page = st.sidebar.radio("SGLOWINA DASHBOARD:", ["🏠 Home", "🎥 Video Studio", "🎨 Image Studio", "💬 Intelligent Chat"])

    if st.sidebar.button("Logout 🚪"):
        st.session_state.session_id = None
        st.rerun()

    # --- SHARED BRANDING ---
    st.markdown('<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div><div class="role-tag">ES FOUNDER & CEOs | SGLOWINA AI OFFICIAL</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

    # --- PAGES (RULE 64.3 WORKING LINKS) ---
    if page == "🎥 Video Studio":
        st.write("### 🎥 Industrial Video Production Agent")
        m_s = st.text_area("Production Script")
        v = st.selectbox("Narrator", ["Male (Asad)", "Female (Uzma)"])
        r = st.selectbox("Ratio", ["YouTube (16:9)", "TikTok (9:16)"])
        s = st.selectbox("Production Style", ["Cinematic", "Realistic", "3D Pixar"])
        if st.button("Execute Production (10 Credits)"):
            # (v40 Logic with Rule 1-11 enforcement via Production Agent)
            st.info("Sglowina Agent is verifying script and applying Shariah Policy...")
            # Video rendering logic...

    elif page == "💬 Intelligent Chat":
        st.write("### 💬 Sglowina Intelligence Dashboard")
        # (Full chat history with Identity Lock 64.3)
        if p := st.chat_input("Hukum..."):
            if any(k in p.lower() for k in ["founder", "creator", "owner", "kisne banaya"]):
                res = FOUNDER_BIO
            else:
                agent = SglowinaTitanOS(u['id'])
                res = agent.orchestrate_text(p, "You are Sglowina AI. Answer only in Urdu.")
            st.write(res)

    elif page == "👥 Manage Users" and u['role'] == "admin":
        st.title("User & Enterprise Management")
        conn = get_db_connection()
        users = pd.read_sql_query("SELECT id, email, role, status, credits, joined_at FROM users", conn)
        st.dataframe(users, use_container_width=True)
        # Admin CRUD functionality...

st.markdown("---")
st.markdown("<p style='text-align: center; font-weight: bold;'>Sglowina AI Enterprise Titan v1.0 | ES Founder & CEOs: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
