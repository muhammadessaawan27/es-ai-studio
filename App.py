import sys
# MUST BE FIRST THING: Globally patch PIL.Image for Pillow 10+ compatibility with MoviePy
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS if hasattr(PIL.Image, 'Resampling') else 1
    sys.modules['PIL.Image'] = PIL.Image
except:
    pass

import streamlit as st
import asyncio
import requests
import urllib.parse
import os
import time
import re
import uuid
import random
from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import json
import concurrent.futures

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"
TRANSITION_SFX_FILE = "transition_whoosh.mp3"

# Download professional clean transition whoosh sound effect on startup
def download_transition_sfx():
    if os.path.exists(TRANSITION_SFX_FILE) and os.path.getsize(TRANSITION_SFX_FILE) > 5000:
        return
    try:
        res = requests.get("https://www.soundjay.com/mechanical/sounds/whoosh-1.mp3", timeout=12)
        if res.status_code == 200:
            with open(TRANSITION_SFX_FILE, "wb") as f: f.write(res.content)
    except: pass

download_transition_sfx()

# Global Session State Registration to permanently prevent NameErrors
if "gen_mode" not in st.session_state:
    st.session_state.gen_mode = "Cinematic Photo Zoom & Pan (100% Free & Unlimited)"
if "pollinations_key" not in st.session_state:
    st.session_state.pollinations_key = ""

# Expanded Urdu to English Dictionary
UR_EN_DICT = {
    "درخت": "trees", "جنگل": "forest", "baag": "garden", "باغات": "gardens",
    "پرندے": "birds", "پرندہ": "bird", "بارش": "rain", "طوفان": "storm",
    "بادل": "clouds", "ہوا": "wind", "آگ": "fire", "پانی": "water",
    "لڑکا": "boy", "لڑکی": "girl", "عورت": "woman", "مرد": "man",
    "بادشاہ": "king", "ملکہ": "queen", "محل": "palace", "تخت": "throne",
    "شیر": "lion", "تلوار": "sword", "جنگ": "war", "قبر": "grave",
    "خوفناک": "scary", "جن": "ghost", "اندھیرا": "dark", "موت": "death",
    "خوبصورت": "beautiful", "جادو": "magic", "جادوئی": "magical",
    "مسجد": "mosque", "نماز": "prayer", "دعا": "pray", "نور": "holy light",
    "چوزہ": "cute fluffy yellow chick", "چوزے": "cute fluffy yellow chicks",
    "بلی": "cute cat", "بندر": "funny monkey", "طوطا": "colorful parrot",
    "خرگوش": "fluffy cartoon rabbit", "بالٹی": "bucket", "سر": "head", "چوہا": "cute mouse",
    "سپر ہیرو": "superhero", "ہنستے": "laughing", "لوٹ پوٹ": "hilariously rolling and laughing"
}

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
    MOVIEPY_ERROR = ""
except Exception as e:
    MOVIEPY_AVAILABLE = False
    MOVIEPY_ERROR = str(e)
    class AudioFileClip:
        def __init__(self, *args, **kwargs): raise NameError("MoviePy missing")
    class ImageClip:
        def __init__(self, *args, **kwargs): raise NameError("MoviePy missing")
    class VideoFileClip:
        def __init__(self, *args, **kwargs): raise NameError("MoviePy missing")
    def concatenate_videoclips(*args, **kwargs): raise NameError("MoviePy missing")
    def CompositeAudioClip(*args, **kwargs): raise NameError("MoviePy missing")
    def CompositeVideoClip(*args, **kwargs): raise NameError("MoviePy missing")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Page Config
st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V1.0", layout="wide", page_icon="🎬")

if not MOVIEPY_AVAILABLE:
    st.sidebar.error("⚠️ MoviePy library is missing! Video generation will not work. Please add 'moviepy' to requirements.txt.")
if not EDGE_TTS_AVAILABLE:
    st.sidebar.error("⚠️ edge-tts library is missing! Voice synthesis will not work. Please add 'edge-tts' to requirements.txt.")

if "enable_watermark" not in st.session_state: st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)
custom_watermark_file = st.sidebar.file_uploader("Upload Custom Watermark Logo (Premium Only):", type=["png", "jpg", "jpeg"])

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=1)
active_renderers = 0
render_lock = threading.Lock()

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

def hash_password(password):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(password, hashed):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

# Multi-Provider Robust Public Image Uploader
def get_public_url(uploaded_file):
    if not uploaded_file:
        return None
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name
    file_type = uploaded_file.type

    # Provider 1: tmpfiles.org
    try:
        url = "https://tmpfiles.org/api/v1/upload"
        files = {'file': (file_name, file_bytes, file_type)}
        res = requests.post(url, files=files, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                return data["data"]["url"].replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
    except: pass

    # Provider 2: envs.sh
    try:
        url = "https://envs.sh"
        files = {'file': (file_name, file_bytes, file_type)}
        res = requests.post(url, files=files, timeout=10)
        if res.status_code == 200:
            return res.text.strip()
    except: pass

    # Provider 3: file.io
    try:
        url = "https://file.io"
        files = {'file': (file_name, file_bytes, file_type)}
        res = requests.post(url, files=files, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return data["link"]
    except: pass

    return None

# Advanced Multimodal Vision AI Image Analyzer
def describe_reference_image(image_url):
    if not image_url:
        return ""
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the person's gender, ethnicity, facial features, hair, apparel, and style in 15 words or less. Example: 'A beautiful young Pakistani Muslim girl wearing a clean red headscarf, brown eyes.'"},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "model": "openai",
            "jsonMode": False
        }
        res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                desc = data["choices"][0]["message"]["content"].strip()
                desc = re.sub(r'^(description|this is|image shows|the photo shows)\s*:\s*', '', desc, flags=re.IGNORECASE)
                return desc
    except: pass
    return ""

def get_db_connection():
    pg_url = os.environ.get("DATABASE_URL")
    if pg_url:
        try:
            import psycopg2
            return psycopg2.connect(pg_url)
        except: pass
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try: conn.execute("PRAGMA journal_mode=WAL;")
    except: pass
    return conn

def backup_db_to_json():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        users = [dict(row) for row in cursor.execute("SELECT * FROM users").fetchall()]
        payments = [dict(row) for row in cursor.execute("SELECT * FROM local_payments").fetchall()]
        config = [dict(row) for row in cursor.execute("SELECT * FROM system_config").fetchall()]
        conn.close()
        backup_data = {"users": users, "payments": payments, "config": config}
        with open(DB_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
    except: pass

def restore_db_from_json():
    if not os.path.exists(DB_BACKUP_FILE): return
    try:
        with open(DB_BACKUP_FILE, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        conn = get_db_connection()
        cursor = conn.cursor()
        for user in backup_data.get("users", []):
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, username, email, password_hash, plan, credits, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.get("id"), user["username"], user["email"], user["password_hash"], user["plan"], user["credits"], user["role"], user["status"], user["created_at"]))
        for pay in backup_data.get("payments", []):
            cursor.execute("""
                INSERT OR IGNORE INTO local_payments (id, username, method, trx_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pay["id"], pay["username"], pay["method"], pay["trx_id"], pay["amount"], pay["status"], pay["created_at"]))
        for cfg in backup_data.get("config", []):
            cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (cfg["key"], cfg["value"]))
        conn.commit()
        conn.close()
    except: pass

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    is_sqlite = "sqlite" in str(type(conn))
    serial_primary = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    placeholder = "?" if is_sqlite else "%s"
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id {serial_primary},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'Free',
            credits INTEGER DEFAULT 50,
            role TEXT DEFAULT 'User',
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, user_id INTEGER, project_name TEXT,
            type TEXT, file_path TEXT, prompt TEXT, created_at TEXT, is_favorite INTEGER DEFAULT 0
        )
    """)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS credits_history (id {serial_primary}, user_id INTEGER, action TEXT, credits_used INTEGER, balance_after INTEGER, date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS local_payments (id TEXT PRIMARY KEY, username TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, credits INTEGER, uses_left INTEGER)")
    
    cursor.execute(f"SELECT COUNT(*) FROM coupons WHERE code = {placeholder}", ('ESSASABA',))
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"INSERT INTO coupons (code, credits, uses_left) VALUES ({placeholder}, 100, 1000)", ('ESSASABA',))
    
    h_admin = hash_password("786")
    for adm in ["essasaba", "essa_awan"]:
        cursor.execute(f"SELECT COUNT(*) FROM users WHERE LOWER(username) = {placeholder}", (adm,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 5000, {placeholder}, {placeholder})",
                           (adm, f"{adm}@sglowina.ai", h_admin, "Enterprise", "Admin", "2026-07-21"))
    
    h_saba = hash_password("1234")
    cursor.execute(f"SELECT COUNT(*) FROM users WHERE LOWER(username) = {placeholder}", ("saba_wahid",))
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 5000, {placeholder}, {placeholder})",
                       ("saba_wahid", "saba@sglowina.ai", h_saba, "Enterprise", "Admin", "2026-07-21"))
                       
    conn.commit()
    conn.close()

init_db_v21()
restore_db_from_json()

def register_saas_user(username, email, password):
    username = username.strip().lower()
    email = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        h = hash_password(password)
        cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, 'Free', 50, 'User', {placeholder})",
                       (username, email, h, time.strftime("%Y-%m-%d")))
        conn.commit()
        backup_db_to_json()
        return True, "User registered successfully!"
    except: return False, "Username or Email already exists."
    finally: conn.close()

def authenticate_user(username, password):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"SELECT password_hash FROM users WHERE LOWER(username) = LOWER({placeholder})", (username,))
        row = cursor.fetchone()
        if row:
            hashed = row[0] if not isinstance(row, dict) and not hasattr(row, 'keys') else row['password_hash']
            return verify_password(password.strip(), hashed)
        return False
    except: return False
    finally: conn.close()

def get_user_data(username):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"SELECT * FROM users WHERE LOWER(username) = LOWER({placeholder})", (username,))
        row = cursor.fetchone()
        if row:
            if not isinstance(row, dict) and hasattr(row, '_fields'):
                return dict(row)
            elif isinstance(row, dict):
                return row
            else:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
        return None
    except: return None
    finally: conn.close()

def deduct_user_credits(username, amount):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"UPDATE users SET credits = MAX(0, credits - {placeholder}) WHERE LOWER(username) = LOWER({placeholder})", (amount, username))
        conn.commit()
        backup_db_to_json()
    except: pass
    finally: conn.close()

def log_credit_usage(user_id, action, used, balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"INSERT INTO credits_history (user_id, action, credits_used, balance_after, date) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
                       (user_id, action, used, balance, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except: pass
    finally: conn.close()

# Real-time Web Search Engine
def search_web_ddg(query):
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text, re.DOTALL)
            if snippets:
                clean_snippets = []
                for s in snippets[:3]:
                    clean_s = re.sub(r'<[^>]*>', '', s).strip()
                    clean_snippets.append(clean_s)
                return "\n".join(clean_snippets)
    except: pass
    return ""

def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    motion, lighting, color_grading, composition = "Zoom Out (v40 Default)", "Volumetric Light", "Hollywood Cinematic", "Cinematic Wide Shot"
    
    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action", "bhaag", "بھاگ", "دوڑ", "تیز"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["scary", "ghost", "dark", "grave", "death", "haunted", "scared", "قبر", "خوف", "جن", "بھوت", "تاریک", "ڈرا", "موت"]):
        motion = "Dolly In"
        lighting, color_grading = "Dark Cinematic, Shadows", "Horror Green"
    elif any(k in text for k in ["fight", "battle", "sword", "war", "تلوار", "جنگ", "لڑائی"]):
        motion = "Handheld Camera"
    elif any(k in text for k in ["walk", "stroll", "چلنا", "گھوم", "سیر"]):
        motion = "Follow Shot"
    elif any(k in text for k in ["think", "silent", "quiet", "meditate", "سوچ", "خاموش"]):
        motion = "Ken Burns Effect"
        
    if any(k in text for k in ["pray", "prayer", "mosque", "peace", "holy", "divine", "مسجد", "دعا", "نماز", "پاک", "نور"]):
        lighting, color_grading = "Golden Hour", "Warm"
    elif any(k in text for k in ["night", "midnight", "moon", "رات", "چاند", "اندھیرا"]):
        lighting, color_grading = "Moonlight", "Cold Blue"
        
    return {"motion": motion, "lighting": lighting, "color_grading": color_grading, "composition": composition}

# Fast POST Request on Unified Endpoint
def generate_text_pollinations(prompt, system_prompt=""):
    models = ["openai-fast", "openai", "mistral"]
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    for model in models:
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": random.choice(user_agents)
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "model": model,
                "jsonMode": False
            }
            res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    text_out = data["choices"][0]["message"]["content"]
                    if len(text_out.strip()) > 5:
                        return text_out.strip()
        except: pass
        
    try:
        headers = {"User-Agent": random.choice(user_agents)}
        clean_p = urllib.parse.quote(prompt[:250])
        clean_sys = urllib.parse.quote(system_prompt[:250])
        res = requests.get(f"https://gen.pollinations.ai/text/{clean_p}?model=openai-fast&system={clean_sys}", headers=headers, timeout=12)
        if res.status_code == 200 and len(res.text.strip()) > 5:
            return res.text.strip()
    except: pass
    
    return ""

# Official Google Translate API integration
def translate_ur_to_en_enhanced(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            result = res.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if len(translated_text.strip()) > 3:
                return translated_text.strip()
    except: pass
    
    try:
        url = f"https://translate.google.com/translate_a/single?client=at&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            result = res.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if len(translated_text.strip()) > 3:
                return translated_text.strip()
    except: pass
    
    try:
        instruction = (
            "You are an expert visual prompt translator. Translate the Urdu scene into clean visual English. "
            "Translate animal subjects explicitly. No human descriptors if subject is an animal."
        )
        res_text = generate_text_pollinations(f"Urdu: {text}", instruction)
        if res_text: return res_text
    except: pass
    
    words = re.findall(r'[\u0600-\u06FF]+', text)
    translated_words = [UR_EN_DICT[w] for w in words if w in UR_EN_DICT]
    if translated_words:
        return f"Cinematic scene depicting {', '.join(translated_words)}, highly detailed"
    return "Beautiful scene scenery, highly detailed"

# SaaS-Ready Dynamic Story & Product Promo Explainer Engine
def generate_local_fallback_script(topic, genre, style):
    topic = topic.strip()
    topic_ur = topic
    
    is_urdu = any(ord(c) > 127 for c in topic)
    if not is_urdu:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ur&dt=t&q={urllib.parse.quote(topic)}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                topic_ur = "".join([sentence[0] for sentence in res.json()[0] if sentence[0]])
        except: pass

    topic_ur_clean = topic_ur.replace("کہانی", "").replace("کی کہانی", "").replace("کا راز", "").strip()
    topic_lower = topic.lower()
    
    # Marketing and Product Keywords
    promo_keywords = ["lipstick", "cream", "product", "shampoo", "soap", "beauty", "cosmetic", "sale", "brand", "business", "پروڈکٹ", "خوبصورتی", "لپسٹک", "کریم", "شیمپو", "صابن", "برانڈ", "تشہیر", "مارکیٹنگ", "پروموشن", "بزنس", "دکان", "خریدیں", "خرید"]
    horror_keywords = ["کوٹھی", "قبر", "جن", "بھوت", "ڈراونا", "تاریک", "خوف", "راز", "موت", "grave", "ghost", "horror", "scary", "dark", "secret", "haunted"]
    hero_keywords = ["ٹارزن", "سپر ہیرو", "بہادر", "شیر", "جنگل", "بندر", "خرگوش", "چوزہ", "tarzan", "hero", "superhero", "lion", "jungle", "adventure", "chick", "rabbit"]
    islamic_keywords = ["مسجد", "نماز", "اسلامی", "تاریخ", "دعا", "نور", "الله", "mosque", "islamic", "historical", "faith", "spiritual"]
    
    if any(k in topic_lower or k in topic_ur for k in promo_keywords) or "business" in genre.lower() or "promo" in genre.lower() or "advertisement" in genre.lower():
        scenes_ur = [
            f"کیا آپ اپنے لائف اسٹائل کو مزید خوبصورت اور پرکشش بنانا چاہتے ہیں؟ پیش ہے {topic_ur_clean} جو آپ کی زندگی میں لائے گا ایک نیا نکھار۔",
            f"یہ شاندار {topic_ur_clean} خاص طور پر جدید تقاضوں اور اعلیٰ ترین معیار کو مدنظر رکھ کر تیار کیا گیا ہے۔",
            f"اس کا بے مثال استعمال نہ صرف آپ کی خوبصورتی اور اعتماد میں اضافہ کرتا ہے بلکہ آپ کو دیتا ہے ایک پرفیکٹ اور لگژری احساس۔",
            f"ہر بار جب آپ {topic_ur_clean} استعمال کرتے ہیں، تو لوگ آپ کی طرف متوجہ ہوئے بغیر نہیں رہ سکتے۔",
            f"معیار پر کوئی سمجھوتہ نہیں، یہی وجہ ہے کہ سمجھدار اور خوبصورت لوگ صرف {topic_ur_clean} پر ہی بھروسہ کرتے ہیں۔",
            f"آج ہی {topic_ur_clean} حاصل کریں اور اپنے حسن اور شخصیت کو چار چاند لگائیں، کیونکہ آپ اس کے حقدار ہیں۔"
        ]
    elif any(k in topic_lower or k in topic_ur for k in horror_keywords) or "horror" in genre.lower() or "suspense" in genre.lower():
        scenes_ur = [
            f"سرد چاندنی رات میں، دور دراز جنگل کے سائے میں {topic_ur_clean} کا ایک ہولناک راز چھپا ہوا تھا۔",
            f"لوگ دور کھڑے ہو کر {topic_ur_clean} کی طرف دیکھتے اور خوف سے کانپنے لگتے تھے۔",
            f"ایک رات، ایک نڈر مسافر نے ہمت باندھی اور {topic_ur_clean} کے اس پراسرار سائے کی طرف قدم بڑھائے۔",
            f"جیسے ہی وہ آگے بڑھا، تیز گرج چمک اور ٹھنڈی ہوا نے اس کا راستہ روکنے کی کوشش کی۔",
            f"دروازہ کھولتے ہی اس کے سامنے {topic_ur_clean} کا وہ صدیوں پرانا راز آشکار ہو گیا جس نے سب کے رونگٹے کھڑے کر دیے۔",
            f"اس پُراسرار واقعے کے بعد پورے علاقے پر ایک خوفناک خاموشی چھا گئی جو ہمیشہ یاد رہے گی۔"
        ]
    elif any(k in topic_lower or k in topic_ur for k in hero_keywords) or "story" in genre.lower() or "moral" in genre.lower():
        scenes_ur = [
            f"ایک قدیم اور پُراسرار سرزمین پر {topic_ur_clean} کی بہادری اور عزم کے قصے گونج رہے تھے۔",
            f"ہر ایک کی زبان پر {topic_ur_clean} کی بے پناہ طاقت اور حیرت انگیز کارناموں کا تذکرہ تھا۔",
            f"ایک دن صبح سویرے، {topic_ur_clean} ایک نئے اور پُرخطر مہم جوئی پر روانہ ہوا جس کی راہ میں شدید امتحانات تھے۔",
            f"راستے میں اس کا سامنا گہرے جنگلات, بلند پہاڑوں اور نہایت خطرناک چیلنجز سے ہوا۔",
            f"اپنی سچی ہمت اور طاقت کا بھرپور مظاہرہ کرتے ہوئے {topic_ur_clean} نے تمام رکاوٹوں کو جڑ سے اکھاڑ پھینکا۔",
            f"اس شاندار کامیابی کے بعد پوری سرزمین پر {topic_ur_clean} کی فتح کے شادیانے بجنے لگے۔"
        ]
    elif any(k in topic_lower or k in topic_ur for k in islamic_keywords) or "islamic" in genre.lower():
        scenes_ur = [
            f"تاریخ کے اوراق میں {topic_ur_clean} کی عظمت اور ایمان کی سچی داستانیں روشن ہیں۔",
            f"جب ہم {topic_ur_clean} کے اس پاکیزہ سفر کا مطالعہ کرتے ہیں، تو روح ایمان سے تازہ ہو جاتی ہے۔",
            f"ایک پاکیزہ صبح، لوگ {topic_ur_clean} کے فیض اور برکت کی تلاش میں جمع ہوئے۔",
            f"دلوں میں سچی عقیدت اور اللہ پر بھرپور یقین لیے سب نے امن اور سلامتی کا راستہ اختیار کیا۔",
            f"آسمان سے نازل ہونے والے خوبصورت سفید نور کی برکت سے سب کی دعائیں مستجاب ہوئیں۔",
            f"آخر میں یہ واضح ہوتا ہے کہ {topic_ur_clean} کا یہ پاکیزہ پیغام ہمارے ایمان کی مضبوطی کا باعث ہے۔"
        ]
    else:
        scenes_ur = [
            f"آئیے آج ہم {topic_ur_clean} کے نہایت ہی اہم اور عملی پہلوؤں پر تفصیلی روشنی ڈالتے ہیں۔",
            f"جب ہم {topic_ur_clean} کے اس وسیع موضوع کی گہرائی کا مطالعہ کرتے ہیں، تو ہمیں حیرت انگیز حقائق معلوم ہوتے ہیں۔",
            f"موجودہ دور کی تیز رفتار ٹیکنالوجی میں {topic_ur_clean} ہمارے علم اور عمل کے لیے ایک سنگِ میل ثابت ہو رہا ہے۔",
            f"اس معلوماتی سفر میں ہمیں {topic_ur_clean} کے عملی طریقوں اور چیلنجز کو بھی سمجھنا گا۔",
            f"بہترین حکمت عملی اور سائنسی تحقیق کی مدد سے ہم {topic_ur_clean} کے میدان میں غیر معمولی کامیابی پا سکتے ہیں۔",
            f"یہ ثابت ہوتا ہے کہ {topic_ur_clean} کا یہ جدید تصور ہماری ترقی اور فکری بلندی کے لیے بنیادی حیثیت رکھتا ہے۔"
        ]
        
    return " ۔ ".join(scenes_ur)

# Highly Intelligent Speech Sanitizer
def sanitize_speech_text(text):
    text = re.sub(r'\[.*?\]|\(.*?\)|（.*?）|【.*?】|［.*?］|\{.*?\}', '', text)
    cleaned_lines = []
    for line in text.split("\n"):
        line_strip = line.strip()
        if not line_strip:
            continue
            
        if re.match(r'^[\d\.\-\s]+$', line_strip):
            continue
            
        if re.match(r'^(scene|scene\s*\d+|منظر\s*\d+|part\s*\d+|حصہ\s*\d+|promo|trailer|intro|outro|60\s*second|60\s*سیکنڈ)\b', line_strip, re.IGNORECASE):
            continue
            
        speak_match = re.search(r'(voiceover|narration|dialogue|audio|speaks|voice|آواز|مکالمہ|کہانی|بولیں|بولتا ہے)\s*:\s*(.*)', line_strip, re.IGNORECASE)
        if speak_match:
            spoken_part = speak_match.group(2).strip()
            if spoken_part:
                cleaned_lines.append(spoken_part)
            continue
            
        if re.match(r'^(visual|prompt|background|image|video|camera|setting|scene|منظر|تصویر|پرامپٹ|پس\s*منظر)\s*:\s*', line_strip, re.IGNORECASE):
            continue
            
        cleaned_lines.append(line_strip)
        
    return " ".join(cleaned_lines).strip()

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined_text = (scene_text_en + " " + scene_text_ur).lower()
    spiritual_keywords = [
        "prophet", "sahaba", "saint", "angel", "god", "allah", "messenger", "nooh", "musa", "isa", "ibrahim", "yousuf", "muhammad", 
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "کفن", "غوث", "قطب", "امام", "پیمغبر",
        "grave", "shroud", "hell", "heaven", "paradise", "pious", "aulia", "angels", "holy dome", "mosque"
    ]
    if any(k in combined_text for k in spiritual_keywords):
        return True, (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from the heavens, "
            "sacred light beam, peaceful glowing background. "
            "STRICTLY NO human faces, NO visible bodies, NO portraits, NO human figures. Pure sacred light."
        )
    return False, scene_text_en

def is_human_character_present(scene):
    scene_l = scene.lower()
    human_indicators = [
        "man", "male", "boy", "he", "him", "adventurer", "maseeha", "mushaf", "مرد", "لڑکا", "احمد", "علی", "بادشاہ", "essa", "awan", "bhai",
        "larki", "woman", "female", "girl", "she", "her", "عائشہ", "ayisha", "عورت", "لڑکی", "زارا", "سارہ", "saba", "baji", "behn"
    ]
    return any(k in scene_l for k in human_indicators)

def analyze_consistent_subject(story_text, style):
    story_l = story_text.lower()
    style_theme = "cartoon" if style == "3D Cartoon" else "photorealistic"
    if any(k in story_l for k in ["چوزہ", "chick", "چوزے"]):
        return f"a cute fluffy yellow {style_theme} chick wearing an upside-down metallic bucket on its head as superhero helmet"
    if any(k in story_l for k in ["چوہا", "mouse", "rat"]):
        return f"a cute tiny {style_theme} brown mouse wearing superhero attire"
    if any(k in story_l for k in ["بندر", "monkey"]):
        return f"a funny goofy {style_theme} brown monkey"
    return ""

def clean_animal_prompt_of_humans(prompt, urdu_text, style):
    prompt_lower = prompt.lower()
    urdu_lower = urdu_text.lower()
    
    has_human_urdu = any(k in urdu_lower for k in ["لڑکا", "لڑکی", "عورت", "مرد", "انسان", "بچہ", "بچے", "لوگ", "شہزادہ", "بادشاہ", "ملکہ"])
    has_animal_urdu = any(k in urdu_lower for k in ["چوزہ", "چوزے", "بلی", "بندر", "طوطا", "خرگوش", "چوہا", "جانور", "حیوان", "شیر", "چیتا", "ہاتھی", "بھیڑیا"])
    
    if style in ["Realistic HD", "Cinematic Hollywood", "Corporate Business", "Rustic Village Life", "Islamic Historical"]:
        realism_booster = "photographic award-winning shot of a real live animal, realistic textures, natural lighting, strictly no CGI, no 3D cartoon render, "
    else:
        realism_booster = ""

    style_prefix = "3D cartoon Pixar style"
    if style == "Realistic HD":
        style_prefix = "highly realistic professional wildlife photography of a"
    elif style == "Cinematic Hollywood":
        style_prefix = "cinematic Hollywood movie scene of a"
    elif style == "Bollywood Dramatic":
        style_prefix = "dramatic Bollywood film shot of a"
    elif style == "Lollywood Classic":
        style_prefix = "authentic Lollywood film shot of a"
    elif style == "Islamic Historical":
        style_prefix = "grand Islamic historical film shot of a"
    elif style == "Corporate Business":
        style_prefix = "professional corporate business setup of a"
    elif style == "Educational Explainer":
        style_prefix = "clean educational explainer illustration of a"
    elif style == "Anime Art":
        style_prefix = "high-quality Japanese anime illustration of a"
    elif style == "Rustic Village Life":
        style_prefix = "rustic traditional village scene of a"
    elif style == "Dark Gothic / Mystery":
        style_prefix = "dark gothic suspenseful scene of a"
    
    if has_animal_urdu and not has_human_urdu:
        human_words = ["boy", "girl", "child", "infant", "toddler", "kid", "human", "person", "man", "woman", "he", "she", "male", "female", "glasses", "mustache", "beard"]
        cleaned_prompt = prompt
        for word in human_words:
            cleaned_prompt = re.sub(r'\b' + word + r'\b', '', cleaned_prompt, flags=re.IGNORECASE)
        
        if "چوزہ" in urdu_lower or "chick" in urdu_lower:
            cleaned_prompt = f"A beautiful wide-angle landscape shot of a {realism_booster}{style_prefix} fluffy yellow chick wearing a metal bucket on head, walking along a scenic detailed forest path, sharp focus, no background blur, no bokeh, beautiful trees, " + cleaned_prompt
        elif "بلی" in urdu_lower:
            cleaned_prompt = f"A beautiful wide-angle shot of a {realism_booster}{style_prefix} cute cat sitting in a lush detailed forest, sharp focus, no background blur, " + cleaned_prompt
        elif any(k in urdu_lower for k in ["شیر", "چیتا", "ہاتھی", "بھیڑیا", "حیوان", "جانور", "lion", "cheetah", "elephant", "wolf"]):
            cleaned_prompt = f"A majestic wide-angle {realism_booster}{style_prefix} group shot of a friendly lion, a cheetah, a small cute elephant, and a wolf walking side-by-side along a highly-detailed scenic forest trail, vibrant colors, sharp focus, no background blur, no bokeh, " + cleaned_prompt
        elif "بندر" in urdu_lower or "طوطا" in urdu_lower or "خرگوش" in urdu_lower:
            cleaned_prompt = f"A beautiful wide-angle scenic {realism_booster}{style_prefix} group shot of cute animals including a funny monkey, a colorful parrot, and a fluffy rabbit laughing and playing together in a detailed green forest pasture, sharp focus, no background blur, no bokeh, " + cleaned_prompt
            
        cleaned_prompt = re.sub(r',\s*,', ',', cleaned_prompt)
        cleaned_prompt = re.sub(r'\s+', ' ', cleaned_prompt).strip()
        return cleaned_prompt
        
    return prompt

def generate_enhanced_cinematic_prompt(urdu_scene, style, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url, attire_desc="", consistent_char_desc=""):
    try:
        scene_lower = urdu_scene.lower()
        gender_booster = ""
        
        style_boosters = {
            "Realistic HD": "ultra photorealistic, award-winning photography style, 8k resolution, highly detailed, sharp focus, natural real skin textures, strictly no 3D render, no CGI, no drawing",
            "Sglowina News Studio (نیوز رپورٹ)": "photorealistic professional news studio setup, high-tech broadcasting television background, crisp studio lighting, clear realistic news anchor reporter, real-life capture",
            "Cinematic Movie Trailer (پرومو ٹریلر)": "intense high-budget epic movie trailer shot, dramatic action cinematography, high contrast movie frame, dark shadows, highly suspenseful atmosphere, extremely detailed",
            "3D Cartoon": "3D cartoon animation style, Pixar style, Disney animation style, vibrant colors, stylized cute characters, playful environment, no realism",
            "Cinematic Hollywood": "cinematic Hollywood movie style, dramatic atmospheric lighting, anamorphic lens, high-fidelity movie frame, rich realistic textures, professional cinematography, strictly no CGI",
            "Bollywood Dramatic": "highly dramatic Bollywood movie style, rich colors, emotional dynamic lighting, vibrant clothing, cinematic film frame",
            "Lollywood Classic": "authentic classic Lollywood film style, rich Pakistani traditional atmosphere, warm vibrant colors, dramatic scene composition",
            "Islamic Historical": "grand Islamic historical movie style, ancient arabian architecture, majestic sands, rich Middle Eastern textures, golden hour volumetric lighting",
            "Corporate Business": "professional corporate business setup, clean modern office environment, photorealistic business professionals, modern corporate videography, clean lighting",
            "Educational Explainer": "clean educational explainer graphic style, clear high-contrast vector illustrations, professional instructional design, beautiful stylized diagrams, clean white background",
            "Anime Art": "beautiful anime illustration, high-quality Japanese anime art style, detailed background",
            "Logo Design": "minimalist professional vector logo design, flat colors, icon style",
            "Rustic Village Life": "rustic traditional old village life, raw earthy tones, authentic rural setting, natural rustic lighting",
            "Dark Gothic / Mystery": "moody dark gothic mystery, eerie misty atmosphere, shadows, dramatic cinematic suspense look"
        }
        style_tag = style_boosters.get(style, "cinematic film style, highly detailed")
        
        # Beauty booster for commercial and product promo genres (PREVENTS DIRT AND BLEMISHES)
        beauty_booster = ""
        is_cosmetic = any(k in urdu_scene.lower() or k in style.lower() for k in ["lipstick", "cream", "shampoo", "soap", "beauty", "cosmetic", "makeup", "لپسٹک", "کریم", "صابن", "خوبصورتی"])
        if is_cosmetic:
            beauty_booster = (
                "flawless smooth glowing skin, professional commercial makeup, airbrushed high-end beauty advertising portrait, "
                "elegant lips, perfect single lip shape, high-fashion aesthetic, zero skin blemishes, no wrinkles, no freckles, "
                "no spots, hyper-clean facial skin, single anatomically correct mouth, professional studio lighting, preventing overlapping lips or duplicate mouths"
            )

        if character_heritage == "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)":
            if any(k in scene_lower for k in ["larki", "woman", "female", "girl", "عورت", "لڑکی", "زارا", "سارہ"]):
                gender_booster = f"beautiful elegant Eastern woman, realistic facial features, wearing traditional modest cotton Shalwar Kameez {attire_desc or 'with clean dupatta elegantly draped over head as hijab'}, modest posture"
            elif any(k in scene_lower for k in ["man", "male", "boy", "مرد", "لڑکا", "احمد", "علی", "بادشاہ"]):
                gender_booster = f"handsome majestic Eastern man, realistic facial structure, wearing traditional modest cotton Shalwar Kameez {attire_desc or 'with high collar, short neat beard'}, strictly modest"
        elif character_heritage == "Ancient Arabian":
            gender_booster = f"wearing ancient traditional Arabian flowing robes {attire_desc}, desert turban, historic Middle Eastern facial features"
        elif character_heritage == "Western / Modern":
            gender_booster = f"modern stylish contemporary Western clothing {attire_desc}, jeans and jacket"
        elif character_heritage == "Far Eastern":
            gender_booster = f"traditional East Asian oriental attire {attire_desc}"

        instruction = (
            "You are an expert visual prompt writer. Translate and expand the Urdu scene into a detailed English prompt for Flux AI. \n"
            "RULES:\n"
            f"1. Strictly enforce the visual style: '{style_tag}'. If realistic, do NOT include sketch, cgi, or 3d terms.\n"
            "2. Keep character consistent: if consistent character description is provided, keep that exact character active in the frame.\n"
            "3. NEGATIVE PROMPT: If story is about animals, STRICTLY NO human characters, NO human faces, NO human boys or girls, NO human kids. Focus purely on the cute animal."
        )
        prompt_input = f"Urdu Scene: {urdu_scene}\nStyle: {style_tag}\n"
        if consistent_char_desc:
            prompt_input += f"Consistent Subject Memory (Main Character): {consistent_char_desc}\n"
        if gender_booster: prompt_input += f"Attire/Gender Tags: {gender_booster}\n"
        if beauty_booster: prompt_input += f"Beauty Enhancement Guidelines: {beauty_booster}\n"
        
        formatted_instruction = instruction.replace("{raw_male_url}", raw_male_url or "None").replace("{raw_female_url}", raw_female_url or "None")
        refined_p = generate_text_pollinations(prompt_input, formatted_instruction)
        if refined_p:
            refined_p = re.sub(r'^(prompt:|visual prompt:|cinematic prompt:)\s*', '', refined_p, flags=re.IGNORECASE).strip()
            return f"{refined_p}, visual style: {style_tag}"
    except: pass
    
    translated_p = translate_ur_to_en_enhanced(urdu_scene)
    return f"Highly detailed {style}, {translated_p}"

def apply_color_lut_harmony(img_path, style_preset):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.15)
            im = ImageEnhance.Contrast(im).enhance(1.05)
            if style_preset == "3D Cartoon":
                im = ImageEnhance.Color(im).enhance(1.10)
            elif style_preset == "Dark Gothic / Mystery":
                im = ImageEnhance.Color(im).enhance(0.75)
            im.save(img_path, "PNG")
    except: pass

def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    if any(k in text for k in ["rain", "storm", "thunder", "clouds", "بارش", "طوفان"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "battle", "clash", "تلوار", "جنگ"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3"
    elif any(k in text for k in ["forest", "jungle", "birds", "nature", "درخت", "جنگل", "باغات", "باغ", "پرندے"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/forest-wind-1.mp3"
        
    if sfx_url:
        sfx_filename = f"sfx_{u_id}_{idx}.mp3"
        try:
            res = session.get(sfx_url, timeout=10)
            if res.status_code == 200:
                with open(sfx_filename, "wb") as f: f.write(res.content)
                return sfx_filename
        except: pass
    return None

def apply_blurred_background_padding(img_path, target_w, target_h):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            resizer = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
            bg = im.resize((target_w, target_h), resizer).filter(ImageFilter.GaussianBlur(radius=22))
            im_ratio = im.width / im.height
            target_ratio = target_w / target_h
            if im_ratio > target_ratio:
                new_w, new_h = target_w, int(target_w / im_ratio)
            else:
                new_w, new_h = int(target_h * im_ratio), target_h
            fg = im.resize((new_w, new_h), resizer)
            bg.paste(fg, ((target_w - new_w) // 2, (target_h - new_h) // 2))
            bg.save(img_path, "PNG")
    except: pass

# Beautiful Soft Blue Cinematic Gradient Generator
def generate_cinematic_gradient_placeholder(img_path, w, h, scene_text="Sglowina AI"):
    try:
        im = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(im)
        for y in range(h):
            r = int(20 + (10 * (y / h)))
            g = int(35 + (15 * (y / h)))
            b = int(70 - (20 * (y / h)))
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        im.save(img_path, "PNG")
    except:
        try: Image.new("RGB", (w, h), color=(30, 58, 138)).save(img_path, "PNG")
        except: pass

def is_valid_image(img_path):
    if not os.path.exists(img_path) or os.path.getsize(img_path) < 1000:
        return False
    try:
        with Image.open(img_path) as im:
            im.load()
        return True
    except:
        return False

def ensure_image_exists(img_path, w, h, scene_text="Sglowina AI"):
    if not is_valid_image(img_path):
        try:
            if os.path.exists(img_path): os.remove(img_path)
        except: pass
        generate_cinematic_gradient_placeholder(img_path, w, h, scene_text)

def apply_custom_watermark(img_path, watermark_bytes):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            with Image.open(io.BytesIO(watermark_bytes)) as wm:
                wm = wm.convert("RGBA")
                wm_w = int(im.width * 0.15)
                wm_ratio = wm.height / wm.width
                wm_h = int(wm_w * wm_ratio)
                wm = wm.resize((wm_w, wm_h))
                im.paste(wm, (im.width - wm_w - 30, im.height - wm_h - 30), wm)
            im.convert("RGB").save(img_path, "PNG")
    except: pass

# Parallel Downloader utilizing ThreadPool and injecting reference images correctly
def parallel_download_flux_images(urls, paths, prompts, w, h, style="Realistic HD", api_key=""):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    def download_single_image(index):
        url, path, prompt_text = urls[index], paths[index], prompts[index]
        success = False
        
        t_session = requests.Session()
        headers = {"User-Agent": random.choice(user_agents)}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        t_session.headers.update(headers)
        
        active_url = url
        if api_key and "key=" not in active_url:
            active_url += f"&key={api_key}"
            
        try:
            res = t_session.get(active_url, timeout=12)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(path, "wb") as f: f.write(res.content)
                if is_valid_image(path):
                    success = True
        except: pass
        
        if not success:
            generate_cinematic_gradient_placeholder(path, w, h, prompt_text)

    max_workers = min(4, len(urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(download_single_image, range(len(urls)))

# Background Music Gallery Theme Caching Engine
def get_cached_bg_music(theme):
    theme_urls = {
        "Hollywood Dramatic (فلمی اور ڈرامہ)": "https://www.soundjay.com/free-music/sounds/heart-of-the-sea-01.mp3",
        "News Explainer (معلوماتی اور خبریں)": "https://www.soundjay.com/free-music/sounds/around-the-lake-01.mp3",
        "Horror Suspense (خوفناک اور پراسرار)": "https://www.soundjay.com/free-music/sounds/after-the-rain-01.mp3",
        "Cartoon & Kids Story (کارٹون کہانی)": "https://www.soundjay.com/free-music/sounds/bright-and-breezy-01.mp3",
        "Business & Tech (کارپوریٹ اور بزنس)": "https://www.soundjay.com/free-music/sounds/ambient-tech-01.mp3",
        "AI Space Ambient (خلائی اور جدید)": "https://www.soundjay.com/free-music/sounds/sky-gazer-01.mp3"
    }
    url = theme_urls.get(theme, "https://www.soundjay.com/free-music/sounds/heart-of-the-sea-01.mp3")
    fn = f"bg_{hashlib.md5(theme.encode()).hexdigest()[:8]}.mp3"
    cf = os.path.join(AUDIO_CACHE_DIR, fn)
    if os.path.exists(cf) and os.path.getsize(cf) > 100000:
        return cf
    try:
        res = session.get(url, timeout=20, verify=False)
        if res.status_code == 200:
            with open(cf, "wb") as f: f.write(res.content)
            return cf
    except: pass
    return None

def download_video_safely(url, dest_path, progress_status, api_key=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        with session.get(url, stream=True, headers=headers, timeout=120) as r:
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                return True
    except Exception as e:
        progress_status.warning(f"Video download timeout ({e}). Falling back to Cinematic Zoom...")
    return False

# Seamlessly loop a VideoFileClip if it is shorter than target narration duration
def loop_video_clip_safely(clip, target_duration):
    if clip.duration is None:
        return clip.set_duration(target_duration)
    if clip.duration >= target_duration:
        return clip.subclip(0, target_duration)
    try:
        from moviepy.editor import concatenate_videoclips
        loops_needed = int(np.ceil(target_duration / clip.duration))
        repeated_clips = [clip] * loops_needed
        looped = concatenate_videoclips(repeated_clips, method="compose")
        return looped.subclip(0, target_duration)
    except:
        return clip.set_duration(target_duration)

def apply_camera_motion_v40(img_path, motion, duration, w, h, video_pace="Standard Narrated Story (عام کہانی)"):
    if not MOVIEPY_AVAILABLE: return None
    ensure_image_exists(img_path, w, h, "Visualizing scene...")
    
    scale_factor = 1.15 if "Trailer" in video_pace else 1.05
    cw, ch = int(w * scale_factor), int(h * scale_factor)
    cw, ch = make_even(cw), make_even(ch)
    
    temp_img_path = img_path.replace(".png", "_resized.png")
    try:
        with Image.open(img_path) as im:
            resizer = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
            resized_im = im.resize((cw, ch), resizer)
            resized_im.save(temp_img_path, "PNG")
    except Exception as e:
        temp_img_path = img_path

    try:
        clip = ImageClip(temp_img_path).set_duration(duration).set_fps(24)
        
        motions_map = {
            "Zoom Out (v40 Default)": lambda: clip.set_position('center'),
            "Zoom In": lambda: clip.set_position('center'),
            "Pan Left": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center')),
            "Pan Right": lambda: clip.set_position(lambda t: (int((w - cw) * (1 - t / duration)), 'center')),
            "Pan Up": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))),
            "Pan Down": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration)))),
            "Dolly In": lambda: clip.set_position('center'),
            "Dolly Out": lambda: clip.set_position('center'),
            "Ken Burns Effect": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center')),
            "Tracking Shot": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), int((h - ch)/2 + (2 * np.sin(2 * np.pi * t * 1.5))))),
            "Follow Shot": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), int((h - ch)/2 + (2 * np.sin(2 * np.pi * t * 1.5))))),
            "Handheld Camera": lambda: clip.set_position(lambda t: (int((w - cw)/2 + (2 * np.sin(2 * np.pi * t * 2.0))), int((h - ch)/2 + (2 * np.cos(2 * np.pi * t * 1.7))))).rotate(lambda t: 0.5 * np.sin(2 * np.pi * t * 1.0)),
        }
        
        active_motion = motion if motion != "AI Hollywood Director (Auto)" else "Zoom Out (v40 Default)"
        animated_clip = motions_map.get(active_motion, motions_map["Zoom Out (v40 Default)"])()
        
        return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
    except Exception as ex:
        st.warning(f"Motion error '{motion}': {ex}. Falling back to static frame.")
        
    try:
        static_temp = img_path.replace(".png", "_static.png")
        generate_cinematic_gradient_placeholder(static_temp, w, h, "Sglowina Fallback")
        return ImageClip(static_temp).set_duration(duration)
    except:
        # Avoid black screens globally by rendering a beautiful soft gradient clip
        fb_img = f"temp_err_fb_{uuid.uuid4().hex[:6]}.png"
        generate_cinematic_gradient_placeholder(fb_img, w, h, "Sglowina AI")
        return ImageClip(fb_img).set_duration(duration)

def apply_clip_transition(clip, transition, duration):
    try:
        fade_dur = min(0.3, duration / 3.0)
        if transition in ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Film Dissolve (Muted)"]:
            return clip.fadein(fade_dur).fadeout(fade_dur)
    except: pass
    return clip

def fetch_img_failover(prompt, w, h, seed, ref_url=None):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        if ref_url:
            url += f"&image={urllib.parse.quote(ref_url)}"
        res = session.get(url, timeout=30)
        if res.status_code == 200: return res.content
    except: pass
    return None

def save_audio_safe(text, voice, rate, pitch, filename):
    try:
        async def amain():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(filename)
        asyncio.run(amain())
        return True
    except Exception as e:
        st.error(f"Voice synthesis error: {e}")
        return False

# Urdu Font Finder to safely load beautiful Nastaliq rendering
def get_urdu_font(font_size):
    font_paths = [
        "Jameel Noori Nastaleeq.ttf", 
        "NotoNastaliqUrdu-Regular.ttf", 
        "arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, font_size)
            except: pass
    try: return ImageFont.load_default()
    except: return None

# Secure subtitle burning function to overlay text elegantly
def burn_subtitles_to_image(img_path, scene_text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            draw = ImageDraw.Draw(im)
            w, h = im.size
            font_size = max(18, int(h * 0.045))
            font = get_urdu_font(font_size)
            
            bar_h = int(font_size * 2.2)
            bar_y = h - bar_h - 20
            
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            draw_overlay.rectangle([20, bar_y, w - 20, h - 20], fill=(0, 0, 0, 180))
            
            im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(im)
            
            text_w = draw.textlength(scene_text, font=font) if hasattr(draw, 'textlength') else (len(scene_text) * (font_size // 2))
            text_x = max(30, (w - text_w) // 2)
            text_y = bar_y + (bar_h - font_size) // 2
            
            draw.text((text_x, text_y), scene_text, fill=(255, 255, 255), font=font)
            im.save(img_path, "PNG")
    except: pass

def apply_canva_typography(img_path, text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            draw = ImageDraw.Draw(im)
            w, h = im.size
            font_size = int(h * 0.04) if h * 0.04 > 16 else 16
            try: font = get_urdu_font(font_size)
            except: font = None
            overlay = Image.new('RGBA', im.size, (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            box_h = int(font_size * 2.5)
            box_y = h - box_h - 25
            draw_overlay.rounded_rectangle([30, box_y, w - 30, h - 25], radius=12, fill=(15, 23, 42, 200))
            im = Image.alpha_composite(im.convert('RGBA'), overlay).convert('RGB')
            ImageDraw.Draw(im).text((50, box_y + (box_h - font_size) // 2), text, fill=(255, 255, 255), font=font)
            im.save(img_path, "PNG")
    except: pass

# ==========================================
# 4. SINGLE CLICK DIRECT MOVIE GENERATION
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", video_model="wan-fast", custom_wm_bytes=None, enable_sub=False, bg_music_theme="Hollywood Dramatic (فلمی اور ڈرامہ)", video_pace="Standard Narrated Story (عام کہانی)"):
    if not MOVIEPY_AVAILABLE:
        st.error(f"MoviePy is not available on this server. Error: {MOVIEPY_ERROR}.")
        return "Error"
    u_id = str(uuid.uuid4())[:8]
    global active_renderers
    with render_lock:
        active_renderers += 1
        my_pos = active_renderers
    status = st.empty()
    if my_pos > 2:
        status.info(f"⏳ Waiting in Queue... Your Position: #{my_pos - 2}.")
        
    with render_semaphore:
        with render_lock: active_renderers -= 1
        progress_bar = st.progress(0.0)
        
        user_db = get_user_data(st.session_state.logged_in_user)
        if not user_db:
            st.error("Authentication Error. Please login again.")
            return "Error"
        
        user_id = user_db["id"]
        user_credits = user_db["credits"]
        user_type = user_db["plan"]
        
        if user_credits < 15:
            st.error("Deduction failed: Sglowina requires at least 15 credits to generate video.")
            return "Error"
        
        active_watermark = True if user_type == "Free" else enable_watermark
        raw_male_url = get_public_url(uploaded_male_img) if uploaded_male_img else None
        raw_female_url = get_public_url(uploaded_female_img) if uploaded_female_img else None
        
        # Analyze uploaded files dynamically to generate strict visual guidelines
        male_desc = ""
        female_desc = ""
        if raw_male_url:
            with st.spinner("Analyzing Male Reference Image..."):
                male_desc = describe_reference_image(raw_male_url)
        if raw_female_url:
            with st.spinner("Analyzing Female Reference Image..."):
                female_desc = describe_reference_image(raw_female_url)

        active_api_key = pollinations_key.strip()
        if not active_api_key:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            row = cursor.fetchone()
            if row and row['value'].strip(): active_api_key = row['value'].strip()
            conn.close()
            
        try:
            progress_bar.progress(0.05)
            
            raw_sentences = [s.strip() for s in re.split(r'[۔\n.!|?()؛;]', story) if len(s.strip()) > 3]
            sentences = []
            current_segment = ""
            for s in raw_sentences:
                if not current_segment: current_segment = s
                else:
                    if len(current_segment) < 25 or len(s) < 20: current_segment += " " + s
                    else:
                        sentences.append(current_segment)
                        current_segment = s
            if current_segment: sentences.append(current_segment)
            if not sentences: sentences = [story]
            
            total_scenes = len(sentences)
            clips = [None] * total_scenes
            generated_prompts = [None] * total_scenes
            img_paths = [None] * total_scenes
            flux_prompt_urls = [None] * total_scenes
            temporary_audio_tracks = [None] * total_scenes
            generated_images = []
            has_bg_music = False
            cached_bg_path = None
            
            status.info(f"🎙️ Voiceovers: Generating speech audio for {total_scenes} scene(s)...")
            
            story_lower_all = story.lower()
            female_keywords = ["larki", "woman", "female", "girl", "she", "her", "عائشہ", "ayisha", "عورت", "لڑکی", "زارا", "سارہ", "saba", "baji", "behn"]
            male_keywords = ["man", "male", "boy", "he", "him", "adventurer", "maseeha", "mushaf", "مرد", "لڑکا", "احمد", "علی", "بادشاہ", "essa", "awan", "bhai"]
            
            story_has_female = any(k in story_lower_all for k in female_keywords)
            story_has_male = any(k in story_lower_all for k in male_keywords)
            primary_gender = "female" if (story_has_female and not story_has_male) else ("male" if (story_has_male and not story_has_female) else None)
            
            attire_tag = "wearing clean bright red and green cotton clothing" if primary_gender == "female" else "wearing elegant white historical cotton dress"
            
            consistent_char_desc = analyze_consistent_subject(story, style)
            
            for idx, scene in enumerate(sentences):
                status.info(f"🎙️ Voiceovers: Compiling speech for Scene {idx + 1} of {total_scenes}...")
                
                # Dynamic Voice Selector BUG FIX: Respect the user's selected dropdown voice strictly!
                v_code_scene = voice_gen
                
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                clean_narration_text = sanitize_speech_text(scene)
                if len(clean_narration_text) < 2:
                    clean_narration_text = "اگلا منظر۔"
                    
                if not save_audio_safe(clean_narration_text, v_code_scene, rate, pitch, sub_audio_path):
                    raise Exception("Voice generation failed.")
                temporary_audio_tracks[idx] = sub_audio_path
                
            progress_bar.progress(0.12)
            if enable_bg_music:
                cached_bg_path = get_cached_bg_music(bg_music_theme)
                if cached_bg_path and os.path.exists(cached_bg_path): has_bg_music = True
                
            progress_bar.progress(0.18)
            res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
            w, h = res_map.get(ratio, (1280, 720))
            w, h = make_even(w), make_even(h)
            
            for i, scene in enumerate(sentences):
                status.info(f"🎨 Visuals: Formatting high-quality prompt for Scene {i + 1} of {total_scenes}...")
                english_scene = translate_ur_to_en_enhanced(scene)
                is_spiritual = False
                if enable_islamic_filter:
                    is_spiritual, safe_scene_en = apply_islamic_safety_filter(english_scene, scene)
                    if is_spiritual: english_scene = safe_scene_en
                
                dir_settings = analyze_scene_for_director(scene)
                if camera_motion != "AI Hollywood Director (Auto)": dir_settings["motion"] = camera_motion
                
                local_human = is_human_character_present(scene)
                character_present = local_human or (primary_gender is not None)
                
                # Dynamic Reference Image Assignment based on scene context
                ref_url = None
                char_visual_reference = ""
                if is_human_character_present(scene) or primary_gender:
                    if "larki" in scene.lower() or "girl" in scene.lower() or "woman" in scene.lower() or primary_gender == "female":
                        ref_url = raw_female_url
                        char_visual_reference = female_desc
                    else:
                        ref_url = raw_male_url
                        char_visual_reference = male_desc
                if not ref_url:
                    ref_url = raw_female_url or raw_male_url
                    char_visual_reference = female_desc or male_desc

                active_heritage = character_heritage
                if character_heritage == "Automatic" or not character_heritage:
                    active_heritage = "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)" if (any(k in scene.lower() for k in female_keywords + male_keywords) or primary_gender) else "Western / Modern"
                
                refined_p = generate_enhanced_cinematic_prompt(scene, style, active_heritage, enable_islamic_filter, raw_male_url, raw_female_url, attire_tag if character_present else "", char_visual_reference or consistent_char_desc)
                refined_p = clean_animal_prompt_of_humans(refined_p, scene, style)
                
                if "Trailer" in video_pace:
                    refined_p = "epic high-budget movie trailer shot, intense dramatic shadows, high contrast action framing, highly suspenseful cinematic masterpiece, " + refined_p
                
                if not is_spiritual and character_present:
                    refined_p += " [Avoid cross-gender blending, anatomically correct]"
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}, {dir_settings['composition']}"
                generated_prompts[i] = refined_p
                
                if "Real AI Video" in gen_mode and active_api_key:
                    status.info(f"🎥 Rendering Video Scene {i+1}/{total_scenes} via {video_model}...")
                    aspect_ratio_param = "16:9" if "16:9" in ratio else "9:16"
                    motion_prompt = f"high motion, realistic physics movement, wind blowing, {refined_p}"
                    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt[:400])}?model={video_model}&aspectRatio={aspect_ratio_param}&key={active_api_key}&duration=4"
                    if ref_url: 
                        vid_url += f"&image={urllib.parse.quote(ref_url)}"
                    
                    vid_path = f"v_{u_id}_{i}.mp4"
                    if download_video_safely(vid_url, vid_path, status, active_api_key):
                        try:
                            scene_voice_clip = AudioFileClip(temporary_audio_tracks[i])
                            dur_scene = scene_voice_clip.duration
                            
                            # Video looping fix to prevent black screen when voice is longer than video clip
                            raw_vid_clip = VideoFileClip(vid_path).resize((w, h))
                            clip = loop_video_clip_safely(raw_vid_clip, dur_scene)
                            
                            sfx_file = download_scene_sfx(scene, u_id, i)
                            if sfx_file and os.path.exists(sfx_file):
                                sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                                clip = clip.set_audio(CompositeAudioClip([scene_voice_clip.volumex(1.2), sfx_audio]))
                                generated_images.append(sfx_file)
                            else:
                                clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                            
                            clips[i] = apply_clip_transition(clip, transition_style, dur_scene)
                            generated_images.append(vid_path)
                            continue
                        except Exception as e:
                            st.warning(f"Video clip loading failed: {e}. Switching to photo fallback...")
                
                # Flux Image Generation with direct reference image injection
                flux_prompt_urls[i] = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p[:400])}?width={w}&height={h}&seed={seed + i * 17}&nologo=true&model=flux"
                if ref_url:
                    flux_prompt_urls[i] += f"&image={urllib.parse.quote(ref_url)}"
                img_paths[i] = f"i_{u_id}_{i}.png"
                
            progress_bar.progress(0.25)
            indices_needing_images = [idx for idx, c in enumerate(clips) if c is None]
            if indices_needing_images:
                status.info("🎨 Visuals: Actively generating custom AI scenes with Flux AI...")
                parallel_download_flux_images(
                    [flux_prompt_urls[idx] for idx in indices_needing_images],
                    [img_paths[idx] for idx in indices_needing_images],
                    [generated_prompts[idx] for idx in indices_needing_images], w, h, style, active_api_key
                )
                for idx in indices_needing_images:
                    if img_paths[idx]: generated_images.append(img_paths[idx])
            
            progress_bar.progress(0.45)
            
            for i in range(total_scenes):
                if clips[i] is not None: continue
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                scene = sentences[i]
                
                status.info(f"🎞️ Video: Applying camera motion and compiling Scene {i + 1} of {total_scenes}...")
                ensure_image_exists(img_path, w, h, scene)
                apply_color_lut_harmony(img_path, style)
                if enable_sub:
                    burn_subtitles_to_image(img_path, scene)
                if custom_wm_bytes is not None:
                    apply_custom_watermark(img_path, custom_wm_bytes)
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                
                dir_settings = analyze_scene_for_director(scene)
                active_motion = camera_motion if camera_motion != "AI Hollywood Director (Auto)" else dir_settings["motion"]
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h, video_pace)
                if clip is None:
                    try: clip = ImageClip(img_path).set_duration(dur_scene).resize((w, h))
                    except:
                        # Avoid black screens on motion fallback failures
                        fb_name = f"fallback_{u_id}_{i}.png"
                        generate_cinematic_gradient_placeholder(fb_name, w, h, "Sglowina Fallback")
                        clip = ImageClip(fb_name).set_duration(dur_scene)
                
                if os.path.exists(TRANSITION_SFX_FILE):
                    try:
                        t_sfx = AudioFileClip(TRANSITION_SFX_FILE).volumex(0.12).set_duration(1.0)
                        sfx_file = download_scene_sfx(scene, u_id, i)
                        if sfx_file and os.path.exists(sfx_file):
                            sfx_audio = AudioFileClip(sfx_file).volumex(0.10).set_duration(dur_scene)
                            clip = clip.set_audio(CompositeAudioClip([scene_voice_clip.volumex(1.4), sfx_audio, t_sfx.set_start(0)]))
                            generated_images.append(sfx_file)
                        else:
                            clip = clip.set_audio(CompositeAudioClip([scene_voice_clip.volumex(1.4), t_sfx.set_start(0)]))
                    except:
                        clip = clip.set_audio(scene_voice_clip.volumex(1.4))
                else:
                    clip = clip.set_audio(scene_voice_clip.volumex(1.4))
                    
                clips[i] = apply_clip_transition(clip, transition_style, dur_scene)
                
            progress_bar.progress(0.70)
            status.info("🎵 Audio Mixer: Ducking background music and mixing elements...")
            valid_clips = [c for c in clips if c is not None]
            if not valid_clips: raise Exception("No valid scenes were generated.")
            
            final_video = concatenate_videoclips(valid_clips, method="compose")
            if has_bg_music and cached_bg_path:
                try:
                    bg_track = AudioFileClip(cached_bg_path).volumex(0.03).set_duration(final_video.duration)
                    final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                except Exception as e: st.warning(f"Background music error: {e}")
                
            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            status.info("🎬 Rendering: Stitching elements into final master video (Ultrafast compression active)...")
            write_kwargs = {"codec": "libx264", "audio_codec": "aac", "fps": 24, "preset": "ultrafast", "threads": 4, "ffmpeg_params": ["-pix_fmt", "yuv420p"]}
            try: final_video.write_videofile(out_name, logger=None, **write_kwargs)
            except: final_video.write_videofile(out_name, verbose=False, **write_kwargs)
            
            final_video.close()
            for sub_voice in temporary_audio_tracks:
                try: os.remove(sub_voice)
                except: pass
            for file_p in generated_images:
                try:
                    if file_p != cached_bg_path: 
                        os.remove(file_p)
                        if file_p.endswith(".png"):
                            for suffix in ["_resized.png", "_static.png"]:
                                temp_f = file_p.replace(".png", suffix)
                                if os.path.exists(temp_f): os.remove(temp_f)
                except: pass
                
            progress_bar.progress(1.0)
            status.success("🚀 Video Generated Successfully!")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
            cursor.execute(f"INSERT INTO projects (id, user_id, project_name, type, file_path, prompt, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})", 
                           (u_id, user_id, f"Video Project {u_id}", "Video", out_name, " | ".join([p for p in generated_prompts if p]), time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            backup_db_to_json()
            conn.close()
            
            deduct_user_credits(st.session_state.logged_in_user, 15)
            log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
            return out_name
        except Exception as e:
            for sub_voice in temporary_audio_tracks:
                try: os.remove(sub_voice)
                except: pass
            for file_p in generated_images:
                try:
                    if file_p != cached_bg_path: 
                        os.remove(file_p)
                        if file_p.endswith(".png"):
                            for suffix in ["_resized.png", "_static.png"]:
                                temp_f = file_p.replace(".png", suffix)
                                if os.path.exists(temp_f): os.remove(temp_f)
                except: pass
            progress_bar.empty()
            return f"Error Details: {e}"
        finally: gc.collect()

# ==========================================
# 5. UI SYSTEM STYLE (Streamlit Theme Sync)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght=900&family=Inter:wght=400;500;700;900&display=swap');
    
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    
    .glow-title { 
        font-size: 1.2rem !important; font-weight: 300 !important; font-family: 'Inter', sans-serif;
        color: #1e3a8a !important; letter-spacing: 2px; margin: 0 !important;
    }
    
    .dashboard-header {
        display: flex; justify-content: center; align-items: center; gap: 15px;
        margin-top: 15px; margin-bottom: 20px;
    }
    
    .circular-s {
        width: 50px !important; height: 50px !important; background: #ffffff !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        border: 2px solid #2563eb !important;
        animation: rotateSpins 10s infinite linear;
    }
    
    .metallic-s {
        font-family: 'Orbitron', sans-serif; font-size: 28px !important; font-weight: 900;
        color: #2563eb !important;
    }
    
    @keyframes rotateSpins {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .stButton>button, .stFormSubmitButton>button { 
        background: linear-gradient(90deg, #2563eb, #1d4ed8) !important; color: white !important; 
        border-radius: 12px !important; height: 55px !important; width: 100% !important; 
        font-size: 20px !important; font-weight: bold !important; border: 1px solid #3b82f6 !important;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2) !important;
    }
    textarea, input, select, .stTextArea textarea, .stTextInput input {
        background-color: #ffffff !important; color: #0f172a !important; 
        border: 2px solid #cbd5e1 !important; border-radius: 10px !important;
    }
    label, [data-testid="stWidgetLabel"] p { color: #1e3a8a !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="dashboard-header">
        <div class="circular-s"><span class="metallic-s">S</span></div>
        <h1 class="glow-title">Sglowina AI | ایس گلووینا</h1>
    </div>
""", unsafe_allow_html=True)

tab_auth, tab_chat, tab_movie, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In", "💬 Electric AI Chat", "🎬 Pro Movie Studio", "🎨 Pro Image Studio", "👤 Enterprise Center"
])

# Sign-In Form
with tab_auth:
    st.write("### 🔑 Sglowina Secure Authentication")
    auth_mode = st.radio("Choose Action", ["Sign In", "Create New Account"])
    with st.form("auth_form"):
        u_name = st.text_input("Username")
        u_email = st.text_input("Email (only for registration)") if auth_mode != "Sign In" else ""
        p_word = st.text_input("Password", type="password")
        btn_submit = st.form_submit_button("Submit 🚀")
        if btn_submit:
            if auth_mode == "Sign In":
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    u_data = get_user_data(u_name)
                    if u_data and u_data['role'] == 'Admin':
                        st.success("Welcome back, Muhammad Essa Awan and Saba Wahid to Sglowina AI! 🟢")
                    else:
                        st.success("Welcome to Sglowina AI! 🟢")
                    time.sleep(2)
                    st.rerun()
                else: st.error("Invalid credentials.")
            else:
                success, msg = register_saas_user(u_name, u_email, p_word)
                if success: st.success(msg)
                else: st.error(msg)

# Chat Bot
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        web_snippets = ""
        p_lower = p.lower()
        if any(k in p_lower for k in ["search", "live", "latest", "who is", "what is", "current", "news", "گوگل", "سرچ", "اج کل"]):
            web_snippets = search_web_ddg(p)
            
        system_prompt = "You are Sglowina AI, an advanced real-time assistant developed by Sglowina Team. "
        if web_snippets:
            system_prompt += f"\n[Live Web Search Context]:\n{web_snippets}\nUse this real-time context to accurately formulate your response."
            
        res = generate_text_pollinations(p, system_prompt)
        translated_res = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
        
        with st.chat_message("assistant"):
            st.write(translated_res)
            st.info("📋 Click the Copy icon in the top right of the box below to copy the full response:")
            st.code(translated_res, language="")
            st.session_state.msgs.append({"role": "assistant", "content": translated_res})

# Pro Movie Studio
with tab_movie:
    st.write("### 🎥 Movie Studio")
    
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"], key="gen_mode_select")
    st.session_state.gen_mode = gen_mode
    pollinations_key = st.text_input("Enter Pollinations API Key (if using video mode):", type="password", key="pollinations_key_input") if "Real AI Video" in st.session_state.gen_mode else ""
    st.session_state.pollinations_key = pollinations_key
    
    st.write("#### 📝 Sglowina AI Script Writer (Optional)")
    with st.expander("Write a story automatically with Sglowina AI"):
        script_genre = st.selectbox("Story Genre:", ["Product Promo & Advertisement (مصنوعات کی تشہیر)", "Moral Animal Story", "Islamic Historical Story", "Business Explainer Script", "Hollywood Action Plot", "Fun Educational Kid Story"])
        script_topic = st.text_input("Enter Topic/Theme:", placeholder="e.g. A luxury lipstick with smooth cherry red finish")
        if st.button("Generate Script with AI ✨"):
            if script_topic.strip():
                with st.spinner("AI is crafting your story..."):
                    story_prompt = f"Write a scenic, detailed {script_genre} in Urdu language, with clear, separate sentences divided by periods. Topic: {script_topic}. Keep it engaging for a cinematic video narration."
                    
                    system_msg = "You are a professional creative Urdu storyteller."
                    if script_genre in ["Business Explainer Script", "Product Promo & Advertisement (مصنوعات کی تشہیر)"]:
                        system_msg = (
                            "You are an expert marketing copywriter and commercial ad director. "
                            "Write a highly persuasive, captivating, and luxury commercial promo script in Urdu. "
                            "Focus heavily on praising the brand/product benefits, luxury feel, premium quality, and emotional appeal. "
                            "Do NOT write a generic fiction story; write an attractive advertisement script."
                        )
                    
                    ai_story = generate_text_pollinations(story_prompt, system_msg)
                    
                    if not ai_story or len(ai_story.strip()) < 10:
                        st.info("💡 Sglowina Local Explainer Engine is compiling a custom cinematic script for you...")
                        ai_story = generate_local_fallback_script(script_topic, script_genre, "Realistic HD")
                        
                    st.session_state.movie_script_val = ai_story.strip()
                    st.success("Story Generated! It has been copied to the Script Box below.")
                    st.rerun()
            else:
                st.error("Please enter a topic first.")

    if "movie_script_val" not in st.session_state:
        st.session_state.movie_script_val = ""
    m_script = st.text_area("Enter Movie Script (Urdu/English):", key="movie_script_val", height=150)
    enable_islamic_filter = st.checkbox("Enable Islamic Safety Filter 🛡️", value=True)
    
    col_up1, col_up2 = st.columns(2)
    with col_up1: uploaded_male_img = st.file_uploader("Upload Male Reference Image:", type=["jpg", "png", "jpeg"])
    with col_up2: uploaded_female_img = st.file_uploader("Upload Female Reference Image:", type=["jpg", "png", "jpeg"])

    col_main_s1, col_main_s2 = st.columns(2)
    with col_main_s1:
        bg_music_theme = st.selectbox("Select Background Music Theme:", [
            "Hollywood Dramatic (فلمی اور ڈرامہ)",
            "News Explainer (معلوماتی اور خبریں)",
            "Horror Suspense (خوفناک اور پراسرار)",
            "Cartoon & Kids Story (کارٹون کہانی)",
            "Business & Tech (کارپوریٹ اور بزنس)",
            "AI Space Ambient (خلائی اور جدید)"
        ])
    with col_main_s2:
        video_pace = st.selectbox("Select Video Output Mode & Pace:", [
            "Standard Narrated Story (عام کہانی)",
            "Fast-Paced Cinematic Trailer (ٹریلر اور پرومو)"
        ])

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9 = st.columns(9)
    with mc1: mv = st.selectbox("Voice:", ["Urdu India Male (Salman)", "Urdu India Female (Gul)", "Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Sglowina News Studio (نیوز رپورٹ)", "Cinematic Movie Trailer (پرومو ٹریلر)", "3D Cartoon", "Cinematic Hollywood", "Bollywood Dramatic", "Lollywood Classic", "Islamic Historical", "Corporate Business", "Educational Explainer", "Anime Art", "Logo Design", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Pan Up", "Pan Down", "Dolly In", "Dolly Out", "Orbit Camera", "Crane Shot", "Drone Shot", "Tracking Shot", "Follow Shot", "Handheld Camera", "Shoulder Camera", "Cinematic Reveal", "Whip Pan", "Tilt Up", "Tilt Down", "Roll Camera", "Parallax Motion", "Ken Burns Effect", "Rack Focus", "Motion Blur"])
    with mc7: transition_style = st.selectbox("Transition Effect:", ["Cross Dissolve (Fade)", "Instant Cut"])
    with mc8: video_model = st.selectbox("AI Video Model:", ["wan-fast", "seedance", "veo"])
    with mc9: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map[mv_pitch]
        
        wm_bytes = custom_watermark_file.getvalue() if custom_watermark_file else None
        
        voice_map = {
            "Urdu Male (Asad)": "ur-PK-AsadNeural",
            "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
            "Urdu India Male (Salman)": "ur-IN-SalmanNeural",
            "Urdu India Female (Gul)": "ur-IN-GulNeural",
            "English US Male (Guy)": "en-US-GuyNeural",
            "English US Female (Jenny)": "en-US-JennyNeural",
            "Arabic Egypt Male (Shakir)": "ar-EG-ShakirNeural",
            "Persian Male (Farid)": "fa-IR-FaridNeural"
        }
        active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
        
        active_gen_mode = st.session_state.gen_mode
        active_key = st.session_state.pollinations_key
        
        with st.spinner("🎬 Generating Sglowina Masterpiece..."):
            v_res = create_cinematic_v40(
                m_script, active_voice, rate_val, pitch_val, mr, ms, sd, camera_motion, transition_style,
                enable_watermark, enable_bg_music, uploaded_male_img, uploaded_female_img,
                enable_islamic_filter, "Automatic", active_gen_mode, active_key, video_model,
                custom_wm_bytes=wm_bytes, enable_sub=False, bg_music_theme=bg_music_theme, video_pace=video_pace
            )
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res):
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: st.error(v_res)

# Pro Image Studio
with tab_image:
    st.write("### 🎨 Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    char_desc_img = st.text_input("Consistent Character Description:", placeholder="e.g. A young girl with blue eyes")
    
    uploaded_ref_img = st.file_uploader("Upload Reference Image (for character consistency):", type=["jpg", "png", "jpeg"], key="visual_studio_ref")
    
    canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="e.g. Studio Title")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["3D Cartoon", "Realistic HD", "Cinematic Film", "Anime Art", "Logo Design"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 5, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        if u_db and u_db['credits'] >= 2 * count:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim.get(i_size, (1024, 1024))
            
            raw_ref_url = get_public_url(uploaded_ref_img) if uploaded_ref_img else None
            ref_desc = ""
            if raw_ref_url:
                with st.spinner("Analyzing Reference Image..."):
                    ref_desc = describe_reference_image(raw_ref_url)
            
            final_p = p_i
            if ref_desc:
                final_p = f"Subject matches this description: {ref_desc}. {p_i}"
            elif char_desc_img.strip():
                final_p = f"Character is {char_desc_img.strip()}. {p_i}"
                
            img_data = fetch_img_failover(f"{final_p}, visual style: {i_style}", w, h, random.randint(1,999999), ref_url=raw_ref_url)
            if img_data:
                img_path = "temp_canvas_image.jpg"
                with open(img_path, "wb") as f_temp: f_temp.write(img_data)
                if canva_overlay_text.strip(): apply_canva_typography(img_path, canva_overlay_text.strip())
                st.image(img_path, caption="Generated Visual")
                try: os.remove(img_path)
                except: pass
                deduct_user_credits(st.session_state.logged_in_user, 2)
            else: st.error("Image generation failed.")
        else: st.error("Insufficient credits.")

# Enterprise tab
with tab_enterprise:
    st.write("### 👤 Enterprise Center")
    ent_tab_user, ent_tab_history, ent_tab_billing, ent_tab_admin = st.tabs(["👤 Profile", "Saved Projects", "💳 Billing Packages", "🔒 Admin Control Panel"])
    u_db = get_user_data(st.session_state.logged_in_user)
    
    with ent_tab_user:
        if u_db:
            st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Balance: **{u_db['credits']}** 🪙")
            st.write("Joined Sglowina Cloud:")
            st.code(u_db['created_at'])
        else: st.warning("Please sign in first.")
        
    with ent_tab_history:
        if u_db:
            conn = get_db_connection()
            rows = conn.execute("SELECT * FROM projects WHERE user_id = ?", (u_db['id'],)).fetchall()
            conn.close()
            if not rows: st.write("No saved projects found.")
            for r in rows:
                st.write(f"🎬 **{r['project_name']}** (Created: {r['created_at']})")
                st.code(r['prompt'])
                st.markdown("---")
        else: st.warning("Please sign in.")
        
    with ent_tab_billing:
        st.success("#### 🏆 Sglowina Premium Monthly Plan")
        st.write("💰 **Price:** 1000 PKR / Month | 🪙 **Credits:** 450 Credits")
        st.write(" Redeem Sglowina Promo Coupon:")
        with st.form("coupon_form"):
            coupon_code = st.text_input("Enter Coupon Code:")
            if st.form_submit_button("Redeem 🎁") and u_db:
                conn = get_db_connection()
                cursor = conn.cursor()
                placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
                cursor.execute(f"SELECT * FROM coupons WHERE UPPER(code) = UPPER({placeholder})", (coupon_code.strip(),))
                c_row = cursor.fetchone()
                if c_row and c_row['uses_left'] > 0:
                    cursor.execute(f"UPDATE users SET credits = credits + {placeholder} WHERE id = {placeholder}", (c_row['credits'], u_db['id']))
                    cursor.execute(f"UPDATE coupons SET uses_left = uses_left - 1 WHERE code = {placeholder}", (c_row['code'],))
                    conn.commit()
                    st.success("Credits added successfully!")
                    st.rerun()
                else: st.error("Invalid or expired coupon.")
                conn.close()

        st.markdown("---")
        st.write("### 📱 Pakistani Local Payment (EasyPaisa/JazzCash)")
        st.info("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")
        if u_db:
            with st.form("payment_form"):
                p_method = st.selectbox("Method:", ["EasyPaisa", "JazzCash"])
                p_trx = st.text_input("Transaction ID (TrxID):")
                p_amt = st.number_input("Amount Sent:", value=1000.0)
                if st.form_submit_button("Submit Proof 🚀"):
                    conn = get_db_connection()
                    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
                    try:
                        conn.execute(f"INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'Pending', {placeholder})",
                                     (str(uuid.uuid4())[:8], u_db['username'], p_method, p_trx.strip(), p_amt, time.strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success("Payment submitted successfully for verification!")
                    except sqlite3.IntegrityError: st.error("This TrxID already exists.")
                    finally: conn.close()
                    
    with ent_tab_admin:
        if u_db and u_db['role'] == 'Admin':
            st.success("Admin authorized.")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            m_key = cursor.fetchone()
            current_key = m_key['value'] if m_key else ""
            
            with st.form("admin_key_form"):
                new_key = st.text_input("Set Master API Key:", value=current_key, type="password")
                if st.form_submit_button("Save Master Key"):
                    cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('master_pollinations_key', ?)", (new_key.strip(),))
                    conn.commit()
                    st.success("Key updated!")
            
            st.write("### Pending Payment Requests")
            pending_reqs = cursor.execute("SELECT * FROM local_payments WHERE status = 'Pending'").fetchall()
            for r in pending_reqs:
                st.write(f"👤 User: `{r['username']}` | Trx: `{r['trx_id']}` | Amount: {r['amount']} PKR")
                if st.button(f"Approve {r['trx_id']}", key=f"app_{r['id']}"):
                    cursor.execute("UPDATE local_payments SET status = 'Approved' WHERE id = ?", (r['id'],))
                    cursor.execute("UPDATE users SET credits = credits + 450, plan = 'Premium' WHERE username = ?", (r['username'],))
                    conn.commit()
                    st.success("Approved!")
                    st.rerun()
            conn.close()
        else: st.error("Admin access denied.")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 20px; color: #475569;'>Sglowina AI Version 1.0 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
