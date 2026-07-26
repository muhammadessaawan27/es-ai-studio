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

# ==========================================
# PIL COMPATIBILITY MONKEYPATCH (Failsafe for Pillow >= 10)
# ==========================================
if not hasattr(Image, 'ANTIALIAS'):
    try:
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    except AttributeError:
        Image.ANTIALIAS = Image.LANCZOS

# ==========================================
# 1. BROWSER SESSION STABILITY HEADERS & CACHE DIRECTORIES
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"

# ==========================================
# 2. MOVIEPY CINEMATIC IMPORTS WITH SAFE FALLBACK
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
    MOVIEPY_ERROR = ""
except Exception as e:
    MOVIEPY_AVAILABLE = False
    MOVIEPY_ERROR = str(e)
    
    class AudioFileClip:
        def __init__(self, *args, **kwargs):
            raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")
    class ImageClip:
        def __init__(self, *args, **kwargs):
            raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")
    class VideoFileClip:
        def __init__(self, *args, **kwargs):
            raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")
    def concatenate_videoclips(*args, **kwargs):
        raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")
    def CompositeAudioClip(*args, **kwargs):
        raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")
    def CompositeVideoClip(*args, **kwargs):
        raise NameError("MoviePy library is missing on this server. Please add 'moviepy' to your requirements.txt.")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# ==========================================
# 3. STREAMLIT CONFIGURATION & GLOBAL STATES
# ==========================================
st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V2.1", layout="wide", page_icon="🎬")

if not MOVIEPY_AVAILABLE:
    st.sidebar.error("⚠️ MoviePy library is missing! Video generation will not work. Please add 'moviepy' to requirements.txt.")
if not EDGE_TTS_AVAILABLE:
    st.sidebar.error("⚠️ edge-tts library is missing! Voice synthesis will not work. Please add 'edge-tts' to requirements.txt.")

SGLOWINA_BIO = (
    "Sglowina AI is a SaaS Enterprise platform designed and developed by Muhammad Essa Awan and Saba Wahid. "
    "It is built to empower creators with highly advanced AI-driven video synthesis, image styling, "
    "and intelligent automated director tools."
)

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []

st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=1)  # Core encoding process safety lock
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

def get_public_url(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        url = "https://tmpfiles.org/api/v1/upload"
        files = {'file': (uploaded_file.name, file_bytes, uploaded_file.type)}
        res = requests.post(url, files=files, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                temp_url = data["data"]["url"]
                raw_url = temp_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                return raw_url
    except Exception:
        pass
    return None

# ==========================================
# 4. DATABASE BACKUP AND RESTORE ENGINE (SaaS Cloud Failsafe)
# ==========================================
def get_db_connection():
    pg_url = os.environ.get("DATABASE_URL")
    if pg_url:
        try:
            import psycopg2
            conn = psycopg2.connect(pg_url)
            return conn
        except Exception:
            pass
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def backup_db_to_json():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        users = [dict(row) for row in cursor.execute("SELECT * FROM users").fetchall()]
        payments = [dict(row) for row in cursor.execute("SELECT * FROM local_payments").fetchall()]
        config = [dict(row) for row in cursor.execute("SELECT * FROM system_config").fetchall()]
        conn.close()
        
        backup_data = {
            "users": users,
            "payments": payments,
            "config": config
        }
        with open(DB_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
    except Exception:
        pass

def restore_db_from_json():
    if not os.path.exists(DB_BACKUP_FILE):
        return
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
            cursor.execute("""
                INSERT OR REPLACE INTO system_config (key, value)
                VALUES (?, ?)
            """, (cfg["key"], cfg["value"]))
            
        conn.commit()
        conn.close()
    except Exception:
        pass

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    is_sqlite = not hasattr(conn, "closed")
    serial_primary = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    
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
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            project_name TEXT,
            type TEXT,
            file_path TEXT,
            prompt TEXT,
            created_at TEXT,
            is_favorite INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS credits_history (
            id {serial_primary},
            user_id INTEGER,
            action TEXT,
            credits_used INTEGER,
            balance_after INTEGER,
            date TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_payments (
            id TEXT PRIMARY KEY,
            username TEXT,
            method TEXT,
            trx_id TEXT UNIQUE,
            amount REAL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            credits INTEGER,
            uses_left INTEGER
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM coupons WHERE code = 'ESSASABA'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO coupons (code, credits, uses_left) VALUES ('ESSASABA', 100, 1000)")
    
    h_admin = hash_password("786")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'essasaba'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("essasaba", "essasaba@sglowina.ai", h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = 'essasaba'", (h_admin,))

    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'essa_awan'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("essa_awan", "essa@sglowina.ai", h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = 'essa_awan'", (h_admin,))
                       
    h_saba = hash_password("1234")
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'saba_wahid'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("saba_wahid", "saba@sglowina.ai", h_saba, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = 'saba_wahid'", (h_saba,))
                       
    conn.commit()
    conn.close()

init_db_v21()
restore_db_from_json()

# ==========================================
# 5. ENTERPRISE AUTHENTICATION HELPERS
# ==========================================
def register_saas_user(username, email, password):
    username = username.strip().lower()
    email = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        h = hash_password(password)
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (username, email, h, 'Free', 50, 'User', time.strftime("%Y-%m-%d")))
        conn.commit()
        backup_db_to_json()
        return True, "User registered successfully!"
    except Exception:
        return False, "Username or Email already exists."
    finally:
        conn.close()

def authenticate_user(username, password):
    username = username.strip().lower()
    password = password.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return verify_password(password, row['password_hash'])
    return False

def get_user_data(username):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def deduct_user_credits(username, amount):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE LOWER(username) = LOWER(?)", (amount, username))
    conn.commit()
    backup_db_to_json()
    conn.close()

def log_credit_usage(user_id, action, used, balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO credits_history (user_id, action, credits_used, balance_after, date) VALUES (?, ?, ?, ?, ?)",
                   (user_id, action, used, balance, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# AI Hollywood Director Mode Intelligent Scene & Speaker Analyzer
def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    
    motion = "Zoom Out (v40 Default)"
    lighting = "Volumetric Light"
    color_grading = "Hollywood Cinematic"
    composition = "Cinematic Wide Shot" # Default to wide shot to capture forests, magic, ruins, and birds
    
    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action", "bhaag"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["scary", "ghost", "dark", "grave", "death", "haunted", "scared"]):
        motion = "Dolly In"
        lighting = "Dark Cinematic, Shadows"
        color_grading = "Horror Green"
    elif any(k in text for k in ["fight", "battle", "sword", "war"]):
        motion = "Handheld Camera"
    elif any(k in text for k in ["walk", "stroll"]):
        motion = "Follow Shot"
    elif any(k in text for k in ["think", "silent", "quiet", "meditate"]):
        motion = "Ken Burns Effect"
        
    if any(k in text for k in ["pray", "prayer", "mosque", "peace", "holy", "divine"]):
        lighting = "Golden Hour"
        color_grading = "Warm"
    elif any(k in text for k in ["night", "midnight", "moon"]):
        lighting = "Moonlight"
        color_grading = "Cold Blue"
        
    return {
        "motion": motion,
        "lighting": lighting,
        "color_grading": color_grading,
        "composition": composition
    }

def translate_ur_to_en_enhanced(text):
    try:
        instruction = (
            "You are an expert Hollywood cinematic prompt writer. Translate the following Urdu story scene into highly descriptive English visual instructions. \n"
            "CRITICAL RULES: \n"
            "1. Explicitly identify the main subjects (e.g., 'a single male', 'a single female', 'a lion', 'only a peaceful landscape with no humans'). \n"
            "2. Do NOT blend genders. If the subject is a man, do NOT include feminine descriptions. If the subject is a woman, do NOT include masculine features. \n"
            "3. Never add animals unless they are explicitly mentioned in the text. \n"
            "4. Ensure anatomical perfection. No extra hands, no overlapping bodies, no weird deformities. \n"
            "5. Output ONLY the English translation and detailed visual descriptions, with no conversational filler or prefixes."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' Urdu text: ' + text)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return text

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined_text = (scene_text_en + " " + scene_text_ur).lower()
    
    spiritual_keywords = [
        "prophet", "sahaba", "saint", "angel", "god", "allah", "messenger", "nooh", "musa", "isa", "ibrahim", "yousuf", "muhammad", 
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "کفن", "غوث", "قطب", "امام", "پیمغبر",
        "grave", "shroud", "hell", "heaven", "paradise", "pious", "aulia", "angels", "holy dome", "mosque"
    ]
    
    if any(k in combined_text for k in spiritual_keywords):
        safe_prompt = (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from the heavens, "
            "sacred light beam, peaceful glowing ancient background, majestic natural mountains and glowing golden sand, "
            "awe-inspiring holy atmosphere, highly detailed cosmic sky. "
            "STRICTLY NO human faces, NO visible bodies, NO portraits, NO human figures, NO blasphemous shapes. "
            "Pure sacred light, beautiful symbolic representation."
        )
        return True, safe_prompt
    return False, scene_text_en

# Pure story-driven prompt mastermind containing no external independent variables
def generate_enhanced_cinematic_prompt(urdu_scene, style, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        scene_lower = urdu_scene.lower()
        gender_booster = ""
        
        style_boosters = {
            "Realistic HD": "ultra photorealistic, 8k resolution, highly detailed, sharp focus, natural skin textures, professional studio lighting, shot on 35mm lens",
            "Cinematic Film": "cinematic movie style, dramatic Hollywood cinematic lighting, Arri Alexa LF camera, deep shadows, cinematic color grade, depth of field",
            "3D Cartoon": "3D cartoon animation style, Pixar and Disney style, smooth 3D renders, stylized charming characters, vibrant colorful environment, claymation textures, adorable animated movie aesthetic, beautiful 3D digital art",
            "Anime Art": "beautiful anime illustration, high-quality Japanese anime art style, clean lines, vibrant cel shading, detailed background, Makoto Shinkai or Kyoto Animation aesthetic",
            "Logo Design": "minimalist professional vector logo design, clean graphic art, solid flat colors, high contrast, elegant emblem, icon style",
            "Historical Epic": "grand historical epic movie style, majestic ancient atmosphere, rich cultural heritage textures, cinematic golden hour lighting, dramatic historical film frame",
            "Rustic Village Life": "rustic traditional old village life aesthetic, raw earthy tones, authentic rural setting, natural rustic lighting, historical simplicity",
            "Dark Gothic / Mystery": "moody dark gothic mystery aesthetic, eerie misty atmosphere, shadows and contrast, dramatic cinematic suspense look, dark fantasy style"
        }
        style_tag = style_boosters.get(style, "cinematic film style, highly detailed")
        
        # SENSE ORIENTED CULTURAL STYLING
        if character_heritage == "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)":
            if any(k in scene_lower for k in ["صبا", "saba", "woman", "female", "girl", "larki"]):
                gender_booster = (
                    "beautiful elegant Eastern Pakistani Punjabi Pathan woman, realistic South Asian sharp facial features, "
                    "wearing traditional modest cotton Shalwar Kameez with a clean modest Dupatta elegantly draped over her head as a hijab, "
                    "strictly no western look, modest posture"
                )
            elif any(k in scene_lower for k in ["عیسی", "essa", "awan", "احمد", "ahmad", "man", "male", "boy"]):
                gender_booster = (
                    "handsome majestic Eastern Pakistani Punjabi Pathan man, highly realistic South Asian facial structure, "
                    "wearing a traditional modest cotton Shalwar Kameez with high collar, neat short Islamic beard, "
                    "strictly no western look"
                )
        elif character_heritage == "Ancient Arabian":
            gender_booster = "wearing ancient traditional Arabian flowing historical robes, classic desert turban, historic Middle Eastern facial features"
        elif character_heritage == "Western / Modern":
            gender_booster = "modern stylish contemporary Western clothing, jeans and jacket"
        elif character_heritage == "Far Eastern":
            gender_booster = "traditional East Asian oriental attire"

        instruction = (
            "You are an expert Hollywood visual artist and prompt engineer. "
            "Analyze the Urdu scene and write a highly detailed visual English image prompt matching the specified style. \n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. STRICT VISUAL ALIGNMENT: You must depict EXACTLY what is written in the Urdu scene sentence. "
            "If it describes birds, trees, majestic gardens, magic, forests, or ancient ruins, focus intensely on showing those beautiful environmental elements. "
            "If no human is explicitly mentioned, do NOT generate any human characters. "
            "If a boy is mentioned, show only a boy. If a girl is mentioned, show only a girl. Never show opposite genders unless they both appear in the text.\n"
            "2. VISUAL SCALE: Always show characters as smaller figures integrated into a wider cinematic shot (medium-full or wide-angle shot) so the rich scenery, landscapes, weather, and animals are fully visible. Never show giant face close-ups.\n"
            "3. STYLE: Strict visual conformity with the 'VISUAL STYLE TAGS'. If style is '3D Cartoon', make it Pixar-like. If 'Anime Art', Japanese hand-drawn style. If 'Cinematic Film', realistic live-action film style.\n"
            "4. ISLAMIC FILTER: If the Urdu scene mentions Prophets/Auliya, heaven, hell, or Islamic sacred elements, strictly avoid any human faces or bodies. Instead, depict gorgeous volumetric golden/white spiritual rays of light in cosmic landscapes, ancient mystical ruins, or majestic desert paths.\n"
            "5. CHARACTER REFS: If reference URLs are provided, align the facial details to them: Male {raw_male_url}, Female {raw_female_url}.\n"
            "6. Output ONLY the final English prompt with absolutely no extra text or conversation."
        )
        
        prompt_input = f"Urdu Scene: {urdu_scene}\n"
        prompt_input += f"VISUAL STYLE TAGS: {style_tag}\n"
        if gender_booster:
            prompt_input += f"FORCE GENDER AND ATTIRE STYLING TAGS: {gender_booster}\n"
        if raw_male_url:
            prompt_input += f"Male reference image URL: {raw_male_url}\n"
        if raw_female_url:
            prompt_input += f"Female reference image URL: {raw_female_url}\n"
        if enable_islamic_filter:
            prompt_input += "Islamic Safety Filter: Active\n"
        else:
            prompt_input += "Islamic Safety Filter: Inactive\n"

        formatted_instruction = instruction.replace("{raw_male_url}", raw_male_url or "None").replace("{raw_female_url}", raw_female_url or "None")

        url = f"https://text.pollinations.ai/{urllib.parse.quote(formatted_instruction + ' ' + prompt_input)}?model=openai"
        res = session.get(url, timeout=20)
        if res.status_code == 200:
            refined_p = res.text.strip()
            refined_p = re.sub(r'^(prompt:|visual prompt:|cinematic prompt:)\s*', '', refined_p, flags=re.IGNORECASE)
            refined_p = f"{refined_p}, visual style: {style_tag}"
            return refined_p
    except Exception:
        pass
    return f"Cinematic film scene: {urdu_scene}, style: {style_tag}, highly detailed, 8k"

def apply_color_lut_harmony(img_path, style_preset):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            if style_preset in ["Realistic HD", "Cinematic Film"]:
                r, g, b = im.split()
                r = r.point(lambda i: int(i * 1.05))
                b = b.point(lambda i: int(i * 0.95))
                im = Image.merge("RGB", (r, g, b))
            elif style_preset == "Dark Gothic / Mystery":
                im = ImageEnhance.Color(im).enhance(0.7)
                r, g, b = im.split()
                b = b.point(lambda i: int(i * 1.10))
                im = Image.merge("RGB", (r, g, b))
            elif style_preset == "Historical Epic":
                r, g, b = im.split()
                r = r.point(lambda i: int(i * 1.08))
                g = g.point(lambda i: int(i * 1.02))
                b = b.point(lambda i: int(i * 0.90))
                im = Image.merge("RGB", (r, g, b))
            
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "JPEG")
    except Exception:
        pass

def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    
    if any(k in text for k in ["rain", "storm", "thunder", "clouds", "بارش", "طوفان"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "battle", "clash", "تلوار", "جنگ"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3"
    elif any(k in text for k in ["forest", "jungle", "birds", "nature", "درخت", "جنگل", "باغات", "باغ", "پرندے", "پرندہ"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/forest-wind-1.mp3"
    elif any(k in text for k in ["fire", "burn", "flame", "آگ"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/fire-1.mp3"
    elif any(k in text for k in ["wind", "breeze", "ہوا"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/wind-howl-01.mp3"
        
    if sfx_url:
        sfx_filename = f"sfx_{u_id}_{idx}.mp3"
        try:
            res = session.get(sfx_url, timeout=10)
            if res.status_code == 200:
                with open(sfx_filename, "wb") as f:
                    f.write(res.content)
                return sfx_filename
        except Exception:
            pass
    return None

def apply_blurred_background_padding(img_path, target_w, target_h):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            bg = im.resize((target_w, target_h)).filter(ImageFilter.GaussianBlur(radius=22))
            im_ratio = im.width / im.height
            target_ratio = target_w / target_h
            if im_ratio > target_ratio:
                new_w = target_w
                new_h = int(target_w / im_ratio)
            else:
                new_h = target_h
                new_w = int(target_h * im_ratio)
            fg = im.resize((new_w, new_h))
            px = (target_w - new_w) // 2
            py = (target_h - new_h) // 2
            bg.paste(fg, (px, py))
            bg.save(img_path, "JPEG")
    except Exception:
        pass

# ==========================================
# FAILOVER IMAGE EMERGENCY RECOVERY SYSTEM (Strictly No Text Overlay & No Pitch Black)
# ==========================================
def ensure_image_exists(img_path, w, h, scene_text="Sglowina AI"):
    if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
        try:
            base = Image.new("RGB", (w, h), color=(10, 15, 30))
            draw = ImageDraw.Draw(base)
            
            for _ in range(8):
                cx = random.randint(0, w)
                cy = random.randint(0, h)
                r = random.randint(150, 350)
                
                color_choices = [
                    (random.randint(15, 45), random.randint(30, 90), random.randint(60, 140)), 
                    (random.randint(40, 90), random.randint(20, 50), random.randint(15, 45)), 
                    (random.randint(25, 65), random.randint(15, 45), random.randint(50, 110))
                ]
                color = random.choice(color_choices)
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
                
            base = base.filter(ImageFilter.GaussianBlur(radius=40))
            base.save(img_path, "JPEG")
        except Exception:
            try:
                im = Image.new("RGB", (w, h), color=(15, 23, 42))
                im.save(img_path, "JPEG")
            except:
                pass

# Parallel image downloader using ThreadPoolExecutor for 5x Speed boost
def parallel_download_flux_images(urls, paths, sentences, w, h):
    def download_single(i):
        url = urls[i]
        path = paths[i]
        scene_text = sentences[i]
        
        for attempt in range(3):
            try:
                res = session.get(url, timeout=30)
                if res.status_code == 200 and len(res.content) > 2000:
                    with open(path, "wb") as f:
                        f.write(res.content)
                    return True
            except Exception:
                pass
            time.sleep(1)
            
        try:
            simple_prompt = urllib.parse.quote(f"cinematic beautiful scene: {scene_text[:60]}")
            fallback_url = f"https://image.pollinations.ai/prompt/{simple_prompt}?width={w}&height={h}&nologo=true"
            res = session.get(fallback_url, timeout=15)
            if res.status_code == 200 and len(res.content) > 2000:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception:
            pass
            
        ensure_image_exists(path, w, h, scene_text)
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(download_single, range(len(urls))))

# ==========================================
# 6. LOCAL AUDIO CACHE AND BANDWIDTH SAVER (Failsafe CDN Audio Sync)
# ==========================================
def get_cached_bg_music(is_horror, is_epic):
    if is_horror:
        cache_file = os.path.join(AUDIO_CACHE_DIR, "bg_horror.mp3")
        url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
    elif is_epic:
        cache_file = os.path.join(AUDIO_CACHE_DIR, "bg_epic.mp3")
        url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
    else:
        cache_file = os.path.join(AUDIO_CACHE_DIR, "bg_standard.mp3")
        url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
        
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100000:
        return cache_file
        
    try:
        res = session.get(url, timeout=15, verify=False)
        if res.status_code == 200:
            with open(cache_file, "wb") as f:
                f.write(res.content)
            return cache_file
    except Exception:
        pass
    return None

# Non-blocking Stream Video Downloader
def download_video_safely(url, dest_path, progress_status):
    try:
        with session.get(url, stream=True, timeout=45) as r:
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                return True
    except Exception:
        progress_status.warning("Video stream connection dropped. Falling back to Cinematic Zoom...")
    return False

# Motion control logic safely wrapped to prevent MoviePy engine crash
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    if not MOVIEPY_AVAILABLE:
        return None
    
    ensure_image_exists(img_path, w, h, "Visualizing scene...")
    
    try:
        scale_factor = 1.30
        
        if motion in ["Whip Pan", "Tracking Shot"]:
            try:
                with Image.open(img_path) as im_blur:
                    im_blur = im_blur.filter(ImageFilter.GaussianBlur(radius=1))
                    im_blur.save(img_path, "JPEG")
            except Exception:
                pass

        base_clip = ImageClip(img_path).set_duration(duration).set_fps(24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = base_clip.resize((cw, ch))
        
        animated_clip = None
        
        if motion == "Zoom In":
            animated_clip = clip.resize(lambda t: 1.0 + 0.15 * (t / duration)).set_position('center')
        elif motion == "Zoom Out (v40 Default)":
            animated_clip = clip.resize(lambda t: 1.15 - 0.15 * (t / duration)).set_position('center')
        elif motion == "Pan Left":
            animated_clip = clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center'))
        elif motion == "Pan Right":
            animated_clip = clip.set_position(lambda t: (int((w - cw) * (1 - t / duration)), 'center'))
        elif motion == "Pan Up":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (t / duration))))
        elif motion == "Pan Down":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration))))
        elif motion == "Dolly In" or motion == "Push In":
            animated_clip = clip.resize(lambda t: 1.0 + 0.25 * (t / duration)).set_position('center')
        elif motion == "Dolly Out" or motion == "Pull Out":
            animated_clip = clip.resize(lambda t: 1.25 - 0.25 * (t / duration)).set_position('center')
        elif motion == "Orbit Camera" or motion == "Arc Shot":
            animated_clip = clip.rotate(lambda t: -3 + 6 * (t / duration)).resize(lambda t: 1.1 + 0.1 * (t / duration)).set_position('center')
        elif motion == "Crane Shot":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))).rotate(lambda t: -2 * (t / duration))
        elif motion == "Drone Shot":
            animated_clip = clip.resize(lambda t: 1.30 - 0.30 * (t / duration)).rotate(lambda t: 5 * (t / duration)).set_position('center')
        elif motion == "Tracking Shot" or motion == "Follow Shot":
            animated_clip = clip.set_position(lambda t: (
                int((w - cw) * (t / duration)),
                int((h - ch)/2 + (5 * np.sin(2 * np.pi * t * 1.5)))
            ))
        elif motion == "Handheld Camera" or motion == "Shoulder Camera":
            animated_clip = clip.set_position(lambda t: (
                int((w - cw)/2 + (8 * np.sin(2 * np.pi * t * 2.0))),
                int((h - ch)/2 + (6 * np.cos(2 * np.pi * t * 1.7)))
            )).rotate(lambda t: 1.5 * np.sin(2 * np.pi * t * 1.0))
        elif motion == "Cinematic Reveal":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration))))
        elif motion == "Whip Pan":
            animated_clip = clip.set_position(lambda t: (int((w - cw) * ((t / duration) ** 3)), 'center'))
        elif motion == "Tilt Up":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (t / duration))))
        elif motion == "Tilt Down":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration))))
        elif motion == "Roll Camera":
            animated_clip = clip.rotate(lambda t: 8 * (t / duration)).set_position('center')
        elif motion == "Parallax Motion" or motion == "Ken Burns Effect":
            animated_clip = clip.resize(lambda t: 1.05 + 0.15 * (t / duration)).set_position(lambda t: (int((w - cw) * (t / duration)), 'center'))
        elif motion == "Rack Focus" or motion == "Motion Blur":
            animated_clip = clip.resize(lambda t: 1.10 - 0.10 * (t / duration)).set_position('center')
        else:
            animated_clip = clip.set_position('center')

        final_clip = CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
        return final_clip
    except Exception as ex:
        st.warning(f"Error applying camera motion '{motion}': {ex}. Falling back to default centering.")
    try:
        return ImageClip(img_path).set_duration(duration).resize((w, h))
    except Exception:
        return ImageClip(np.zeros((h, w, 3), dtype=np.uint8)).set_duration(duration)

# Safe transitions renderer
def apply_clip_transition(clip, transition, duration):
    try:
        if transition == "Cross Dissolve (Fade)":
            return clip.fadein(0.5).fadeout(0.5)
        elif transition == "Flash Transition (White Glow)":
            return clip.fadein(0.3).fadeout(0.3)
        elif transition == "Film Dissolve (Muted)":
            return clip.fadein(0.4).fadeout(0.4)
        elif transition == "Instant Cut":
            return clip
    except Exception:
        pass
    return clip

# Image failover provider from pollination (Upgraded strictly to Flux for high definition features)
def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        res = session.get(url, timeout=30)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# Text to speech async to sync wrapper
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

# High quality placeholder generator 
def generate_high_quality_placeholder(w, h, seed, active_watermark):
    try:
        im = Image.new("RGB", (w, h), color=(30, 41, 59))
        draw = ImageDraw.Draw(im)
        if active_watermark:
            draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
        img_byte_arr = io.BytesIO()
        im.save(img_byte_arr, format='JPEG')
        return img_byte_arr.getvalue()
    except Exception:
        return b""

# ADVANCED CANVA TYPOGRAPHY WITH FROSTED GLASS EFFECT (International Grade)
def apply_canva_typography(img_path, text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            draw = ImageDraw.Draw(im)
            w, h = im.size
            
            font_size = int(h * 0.04) if h * 0.04 > 16 else 16
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
                
            overlay = Image.new('RGBA', im.size, (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            box_h = int(font_size * 2.5)
            box_y = h - box_h - 25
            
            draw_overlay.rounded_rectangle([30, box_y, w - 30, h - 25], radius=12, fill=(15, 23, 42, 200))
            im = Image.alpha_composite(im.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(im)
            
            text_x = 50
            text_y = box_y + (box_h - font_size) // 2
            
            draw.text((text_x + 1, text_y + 1), text, fill=(0, 0, 0), font=font)
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
            
            im.save(img_path, "JPEG")
    except Exception:
        pass

# ==========================================
# 4. FIXED V40 RENDER SYSTEM CORE (SaaS VERIFIED & CHARACTER ID LOCK)
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", video_model="wan-fast", advanced_params=None):
    if not MOVIEPY_AVAILABLE:
        st.error(f"MoviePy is not available on this server. Error: {MOVIEPY_ERROR}. Please check requirements.txt.")
        return "Error"
        
    u_id = str(uuid.uuid4())[:8]
    
    global active_renderers
    with render_lock:
        active_renderers += 1
        my_pos = active_renderers
        
    status = st.empty()
    if my_pos > 2:
        status.info(f"⏳ Waiting in Queue... Your Position: #{my_pos - 2}. (High concurrency protection active to avoid server crash)")
        
    with render_semaphore:
        with render_lock:
            active_renderers -= 1
            
        progress_bar = st.progress(0.0)
        
        audio_file = f"a_{u_id}.mp3"
        generated_images = []
        generated_prompts = []
        temporary_audio_tracks = []
        has_bg_music = False
        cached_bg_path = None
        
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
        
        raw_male_url = get_public_url(uploaded_male_img) if uploaded_male_img is not None else None
        raw_female_url = get_public_url(uploaded_female_img) if uploaded_female_img is not None else None
        
        active_api_key = pollinations_key.strip()
        if not active_api_key:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            row = cursor.fetchone()
            if row and row['value'].strip():
                active_api_key = row['value'].strip()
            conn.close()
        
        try:
            progress_bar.progress(0.05)
            status.info("🎙️ Processing Dialogue Voiceovers...")
            
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
            if not sentences: sentences = [story]
            
            clips = []
            
            for idx, scene in enumerate(sentences):
                # SMART DYNAMIC SPEAKER SELECTION
                is_female_voice = any(k in scene or k in scene.lower() for k in ["صبا", "saba", "larki", "woman", "girl", "she", "her", "عائشہ", "ayisha"])
                is_male_voice = any(k in scene or k in scene.lower() for k in ["عیسی", "essa", "awan", "احمد", "ahmad", "man", "boy", "he", "him", "adventurer", "maseeha", "mushaf"])
                
                if is_female_voice and not is_male_voice:
                    v_code_scene = "ur-PK-UzmaNeural"
                elif is_male_voice:
                    v_code_scene = "ur-PK-AsadNeural"
                else:
                    v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
                    
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                save_audio_success = save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path)
                if not save_audio_success:
                    raise Exception("Voice generation failed.")
                temporary_audio_tracks.append(sub_audio_path)
                
            progress_bar.progress(0.12)
            
            if enable_bg_music:
                status.info("🎵 Querying Cached Ambient Soundtracks...")
                story_lower = story.lower()
                is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "بھوت", "تاریک", "ڈراؤنی", "grave", "torment", "punishment", "scary", "ghost", "dark", "death", "screaming", "blood", "bloody", "horror"])
                is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "شاہی", "تاریخ", "بہادر", "king", "queen", "throne", "palace", "empire", "warrior", "brave", "history", "castle"])
                
                cached_bg_path = get_cached_bg_music(is_horror, is_epic)
                if cached_bg_path and os.path.exists(cached_bg_path):
                    has_bg_music = True
                    
            progress_bar.progress(0.18)
            
            res_map = {
                "YouTube (16:9)": (1280, 720), 
                "TikTok/Reels (9:16)": (720, 1280), 
                "Instagram (1:1)": (720, 720),
                "CinemaScope (21:9)": (1680, 720),
                "Standard Box (4:3)": (1024, 768)
            }
            w, h = res_map[ratio]
            w = make_even(w)
            h = make_even(h)
            
            flux_prompt_urls = []
            img_paths = []
            
            for i, scene in enumerate(sentences):
                english_scene = translate_ur_to_en_enhanced(scene)
                
                is_spiritual = False
                if enable_islamic_filter:
                    is_spiritual, safe_scene_en = apply_islamic_safety_filter(english_scene, scene)
                    if is_spiritual:
                        english_scene = safe_scene_en
                
                dir_settings = analyze_scene_for_director(english_scene)
                if camera_motion != "AI Hollywood Director (Auto)":
                    dir_settings["motion"] = camera_motion
                    
                active_motion = dir_settings["motion"]
                
                refined_p = generate_enhanced_cinematic_prompt(
                    urdu_scene=scene,
                    style=style,
                    character_heritage=character_heritage,
                    enable_islamic_filter=enable_islamic_filter,
                    raw_male_url=raw_male_url,
                    raw_female_url=raw_female_url
                )
                
                if not is_spiritual:
                    refined_p += " [Avoid cross-gender blending, absolutely no woman with beard, absolutely no female with facial hair, anatomically perfect, symmetrical eyes, detailed limbs]"
                
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}, shot on ARRI Alexa LF, 35mm lens, high-fashion realism, photorealistic texture"
                generated_prompts.append(refined_p)
                
                # --- Non-blocking AI Video Motion API ---
                if "Real AI Video" in gen_mode and active_api_key:
                    status.info(f"🎥 Rendering 3D Video Frame {i+1} via {video_model} API...")
                    aspect_ratio_param = "16:9" if "16:9" in ratio else "9:16"
                    
                    motion_prompt = refined_p
                    motion_prompt = re.sub(r'(portrait|standing|sitting|symmetrical face|still image|static)', '', motion_prompt, flags=re.IGNORECASE)
                    motion_prompt = f"high motion, extreme 3D physics movement, character physically walking forward, head moving, eyes blinking, wind blowing, natural realistic animation, {motion_prompt}"
                    
                    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt[:400])}?model={video_model}&aspectRatio={aspect_ratio_param}&key={active_api_key}&duration=4"
                    
                    ref_url = None
                    if "Saba" in scene or "saba" in scene.lower() or "female" in scene.lower():
                        ref_url = raw_female_url if raw_female_url else raw_male_url
                    else:
                        ref_url = raw_male_url if raw_male_url else raw_female_url
                        
                    if ref_url:
                        vid_url += f"&image={urllib.parse.quote(ref_url)}"
                        
                    vid_path = f"v_{u_id}_{i}.mp4"
                    
                    # Call safe non-blocking downloader
                    video_success = download_video_safely(vid_url, vid_path, status)
                    if video_success:
                        try:
                            sub_audio_path = temporary_audio_tracks[i]
                            scene_voice_clip = AudioFileClip(sub_audio_path)
                            dur_scene = scene_voice_clip.duration
                            
                            clip = VideoFileClip(vid_path).resize((w, h)).set_duration(dur_scene)
                            
                            sfx_file = download_scene_sfx(scene, u_id, i)
                            if sfx_file and os.path.exists(sfx_file):
                                try:
                                    sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                                    clip_composite_audio = CompositeAudioClip([scene_voice_clip.volumex(1.2), sfx_audio])
                                    clip = clip.set_audio(clip_composite_audio)
                                    generated_images.append(sfx_file)
                                except Exception:
                                    clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                            else:
                                clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                                
                            clip = apply_clip_transition(clip, transition_style, dur_scene)
                            clips.append(clip)
                            generated_images.append(vid_path) 
                            continue
                        except Exception as e:
                            st.warning(f"Failed to load video subclip: {e}. Falling back to Cinematic Zoom...")
                
                w_target = make_even(w * 1.25)
                h_target = make_even(h * 1.25)
                
                unique_seed = seed
                
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={unique_seed}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_path = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_path)
                generated_images.append(img_path)
                
            progress_bar.progress(0.25)
            status.info("🎨 Running Parallel Flux Image Downloaders (5x Speed Optimization Active)...")
            
            parallel_download_flux_images(flux_prompt_urls, img_paths, sentences, w, h)
            
            progress_bar.progress(0.45)
            status.info("🎞️ Assembling Audio Syncing and Camera Motions...")
            
            for i, scene in enumerate(sentences):
                if len(clips) > i:
                    continue
                    
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                
                ensure_image_exists(img_path, w, h, scene)
                apply_color_lut_harmony(img_path, style)
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                
                english_scene_temp = translate_ur_to_en_enhanced(scene)
                dir_settings = analyze_scene_for_director(english_scene_temp)
                if camera_motion != "AI Hollywood Director (Auto)":
                    dir_settings["motion"] = camera_motion
                active_motion = dir_settings["motion"]
                
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h)
                
                if clip is None:
                    clip = ImageClip(np.zeros((h, w, 3), dtype=np.uint8)).set_duration(dur_scene)
                
                sfx_file = download_scene_sfx(scene, u_id, i)
                if sfx_file and os.path.exists(sfx_file):
                    try:
                        sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                        clip_composite_audio = CompositeAudioClip([scene_voice_clip.volumex(1.2), sfx_audio])
                        clip = clip.set_audio(clip_composite_audio)
                        generated_images.append(sfx_file)
                    except Exception:
                        clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                else:
                    clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                    
                clip = apply_clip_transition(clip, transition_style, dur_scene)
                clips.append(clip)
                
            progress_bar.progress(0.70)
            status.info("🎞️ Stitching final video elements...")
            
            final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
            
            if has_bg_music and cached_bg_path and os.path.exists(cached_bg_path):
                try:
                    bg_track = AudioFileClip(cached_bg_path).volumex(0.04).set_duration(final_video.duration)
                    combined_master_audio = CompositeAudioClip([final_video.audio, bg_track])
                    final_video = final_video.set_audio(combined_master_audio)
                except Exception as e:
                    st.warning(f"Background music mixing warning: {e}")
                    
            out_name = f"Sglowina_{u_id}.mp4"
            
            write_kwargs = {"codec": "libx264", "audio_codec": "aac", "fps": 24, "ffmpeg_params": ["-pix_fmt", "yuv420p"]}
            try:
                final_video.write_videofile(out_name, logger=None, **write_kwargs)
            except TypeError:
                try:
                    final_video.write_videofile(out_name, verbose=False, **write_kwargs)
                except Exception:
                    final_video.write_videofile(out_name, **write_kwargs)
            
            final_video.close()
            
            for sub_voice in temporary_audio_tracks:
                try:
                    if os.path.exists(sub_voice): os.remove(sub_voice)
                except: pass
                
            try:
                for file_p in generated_images:
                    if os.path.exists(file_p) and file_p != cached_bg_path: 
                        os.remove(file_p)
            except Exception:
                pass
                
            progress_bar.progress(1.0)
            status.success("🚀 Video Generated Successfully!")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (id, user_id, project_name, type, file_path, prompt, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (u_id, user_id, f"Video Project {u_id}", "Video", out_name, " | ".join(generated_prompts), time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            backup_db_to_json()
            conn.close()
            
            deduct_user_credits(st.session_state.logged_in_user, 15)
            log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
            
            return out_name
        except Exception as e: 
            for sub_voice in temporary_audio_tracks:
                try:
                    if os.path.exists(sub_voice): os.remove(sub_voice)
                except: pass
            try:
                for file_p in generated_images:
                    if os.path.exists(file_p) and file_p != cached_bg_path: 
                        os.remove(file_p)
            except: pass
            progress_bar.empty()
            return f"Error Details: {e}"
        finally:
            gc.collect()

# ==========================================
# 5. UI & PREMIUM CYBERPUNK SAAS STYLING (Streamlit Overrides)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    /* High-Contrast Cyberpunk Layout Theme */
    .stApp { 
        background: #090d16 !important; 
        color: #f1f5f9 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    .glow-title { 
        font-size: 2.5rem; 
        font-weight: 900; 
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #00f2fe, #4facfe, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 242, 254, 0.4);
        margin-top: 15px;
        margin-bottom: 5px;
        letter-spacing: 3px;
    }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    
    .circular-s {
        width: 120px; height: 120px; 
        background: linear-gradient(135deg, #00f2fe, #0072ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: #ffffff !important;
        border: 4px solid #00f2fe !important;
        box-shadow: 0 0 40px rgba(0, 242, 254, 0.6), inset 0 0 15px rgba(255, 255, 255, 0.5);
        animation: rotateShua 4s infinite linear, lightningGlow 1.5s infinite alternate;
    }
    
    @keyframes rotateShua {
        0% { transform: perspective(1000px) rotateY(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg); }
    }
    @keyframes lightningGlow {
        0%, 100% { box-shadow: 0 0 20px #0072ff, 0 0 40px #00f2fe, inset 0 0 15px #ffffff; }
        50% { box-shadow: 0 0 40px #00f2fe, 0 0 60px #00d4ff, inset 0 0 20px #ffffff; }
    }

    /* Premium Glow Button Styles */
    .stButton>button { 
        background: linear-gradient(90deg, #00f2fe, #0072ff) !important; 
        color: white !important; 
        border-radius: 12px !important; 
        height: 55px; 
        width: 100%; 
        font-size: 20px; 
        font-weight: bold; 
        border: none;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.8);
        transform: scale(1.02);
    }
    
    [data-testid="stSidebar"] { 
        background-color: #0b1329 !important; 
        border-right: 1px solid #1e293b; 
    }
    [data-testid="stSidebar"] * { 
        color: #f1f5f9 !important; 
        font-weight: bold !important; 
    }
    
    /* FIXED: HIGH-CONTRAST INPUT BOXES WITH BRIGHT TYPING TEXT */
    textarea, input, select, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input, .stTextArea textarea, .stTextInput input {
        background-color: #111827 !important; /* Rich Dark Charcoal background */
        color: #ffffff !important; /* Bright White Typing Text */
        -webkit-text-fill-color: #ffffff !important;
        border: 2px solid #3b82f6 !important; /* Strong Blue borders for high contrast */
        border-radius: 10px !important;
        font-size: 16px !important;
    }
    textarea:focus, input:focus, select:focus {
        border-color: #00f2fe !important;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.6) !important;
        background-color: #090d16 !important;
    }
    textarea::placeholder, input::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
    }
    
    /* FIXED: Option names (labels) on top of input fields are now beautifully bright and glowing */
    label, [data-testid="stWidgetLabel"] p, .stWidgetLabel {
        color: #60a5fa !important; /* Radiant light blue labels */
        -webkit-text-fill-color: #60a5fa !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        text-shadow: 0 0 10px rgba(96, 165, 250, 0.2);
    }
    
    /* Headers, subheaders, and Markdown text fixes */
    h1, h2, h3, h4, h5, h6, .stSubheader, .stCaption {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    .stMarkdown p {
        color: #f1f5f9 !important;
        -webkit-text-fill-color: #f1f5f9 !important;
    }
    
    /* Dark Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0b1329;
        border-radius: 12px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] p {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] p {
        color: #00f2fe !important;
        -webkit-text-fill-color: #00f2fe !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 6. UI NAVIGATION & CONTROL PANEL
# ==========================================
tab_auth, tab_chat, tab_movie, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In & Registrations",
    "💬 Electric AI Chat", 
    "🎬 Pro Master Studio", 
    "🎨 Pro Image Studio",
    "👤 Enterprise Center"
])

# -----------------
# TAB 1: AUTHENTICATION
# -----------------
with tab_auth:
    st.write("### 🔑 Sglowina Secure Authentication Portal")
    auth_mode = st.radio("Choose Action", ["Sign In", "Create New Account"])
    
    if auth_mode == "Sign In":
        with st.form("login_form"):
            u_name = st.text_input("Username")
            p_word = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("Sign In 🚀")
            if btn_login:
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    if st.session_state.logged_in_user in ["essasaba", "essa_awan", "saba_wahid"]:
                        st.success("Welcome back to SGLOWINA AI, Muhammad Essa Awan & Saba Wahid! (Admin Authorized) 🟢")
                    else:
                        st.success(f"Welcome to SGLOWINA AI, {u_name}! (Authorized User) 🟢")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    else:
        with st.form("reg_form"):
            new_u = st.text_input("Choose Username")
            new_e = st.text_input("Email Address")
            new_p = st.text_input("Password", type="password")
            btn_reg = st.form_submit_button("Register Account 🎯")
            if btn_reg:
                if new_u and new_e and new_p:
                    success, msg = register_saas_user(new_u, new_e, new_p)
                    if success:
                        st.success(f"Welcome to SGLOWINA AI! Account for '{new_u}' registered successfully. Please sign in. 🟢")
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill out all fields.")

# -----------------
# TAB 2: CHAT INTERACTION
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            translated_response = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            st.write(translated_response)
            st.session_state.msgs.append({"role": "assistant", "content": translated_response})

# -----------------
# TAB 3: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    st.subheader("⚙️ AI Generation Mode")
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"])
    pollinations_key = ""
    if "Real AI Video" in gen_mode:
        pollinations_key = st.text_input("Enter Pollinations API Key (sk_* or pk_*):", type="password")
        
        with st.expander("🔑 Pollinations AI API Key حاصل کرنے کا طریقہ (Guide)"):
            st.markdown("""
            1. سب سے پہلے **[Pollinations AI کے آفیشل پورٹل](https://enter.pollinations.ai/)** پر جائیں۔
            2. اگر آپ کا اکاؤنٹ نہیں ہے تو **Sign Up** کریں، ورنہ اپنے اکاؤنٹ میں **Log In** کریں۔
            3. لاگ اِن کرنے کے بعد **API Keys** یا **Developer** سیکشن پر جائیں، وہاں سے ایک نئی API Key تخلیق کریں اور اسے کاپی کر لیں۔
            4. کاپی کی گئی Key کو اوپر دیے گئے **Enter Pollinations API Key** والے باکس میں پیسٹ کریں۔
            5. آپ کے اکاؤنٹ میں روزانہ کے مفت کریڈٹس (Daily Free Credits) شامل ہوں گے، جنہیں آپ لائیو ویڈیو بنانے کے لیے استعمال کر سکتے ہیں.
            """)

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True)
    
    st.write("##### 👤 Consistent Character Identity References (مخصوص تصویر کی بنیاد پر کارٹون لک دینے کے لیے)")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Upload Male Character Reference Image (مرد کردار کی تصویر):", type=["jpg", "png", "jpeg"])
        if uploaded_male_img is not None:
            st.image(uploaded_male_img, caption="Male Identity Loaded ✅", width=120)
    with col_up2:
        uploaded_female_img = st.file_uploader("Upload Female Character Reference Image (عورت کردار کی تصویر):", type=["jpg", "png", "jpeg"])
        if uploaded_female_img is not None:
            st.image(uploaded_female_img, caption="Female Identity Loaded ✅", width=120)

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9, mc10 = st.columns(10)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch (بھاری پن):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", [
        "AI Hollywood Director (Auto)",
        "Zoom Out (v40 Default)",
        "Zoom In",
        "Pan Left",
        "Pan Right",
        "Pan Up",
        "Pan Down",
        "Dolly In",
        "Dolly Out",
        "Orbit Camera",
        "Crane Shot",
        "Drone Shot",
        "Tracking Shot",
        "Follow Shot",
        "Push In",
        "Pull Out",
        "Arc Shot",
        "Handheld Camera",
        "Shoulder Camera",
        "Cinematic Reveal",
        "Whip Pan",
        "Tilt Up",
        "Tilt Down",
        "Roll Camera",
        "Parallax Motion",
        "Ken Burns Effect",
        "Rack Focus"
    ])
    with mc7: transition_style = st.selectbox("Transition Effect:", ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Film Dissolve (Muted)", "Instant Cut"])
    with mc8: character_heritage = st.selectbox("Cultural Heritage (مشرقی یا مغربی لباس):", ["Automatic", "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)", "Ancient Arabian", "Western / Modern", "Far Eastern"])
    with mc9: video_model = st.selectbox("AI Video Model:", ["wan-fast", "seedance", "veo"])
    with mc10: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        
        pitch_map = {
            "Normal (نارمل)": "+0Hz",
            "Deep (بھاری آواز)": "-15Hz",
            "Very Deep (موٹی آواز)": "-28Hz"
        }
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Sglowina AI is generating your video with voice and motion... Please wait..."):
            v_res = create_cinematic_v40(
                story=m_script, 
                voice_gen=mv, 
                rate=rate_val, 
                pitch=pitch_val, 
                ratio=mr, 
                style=ms, 
                seed=sd, 
                camera_motion=camera_motion, 
                transition_style=transition_style,
                enable_watermark=enable_watermark, 
                enable_bg_music=enable_bg_music, 
                uploaded_male_img=uploaded_male_img, 
                uploaded_female_img=uploaded_female_img, 
                enable_islamic_filter=enable_islamic_filter,
                character_heritage=character_heritage,
                gen_mode=gen_mode, 
                pollinations_key=pollinations_key,
                video_model=video_model,
                advanced_params=None
            )
            
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

# -----------------
# TAB 4: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    
    tab_txt, tab_img = st.tabs(["🎨 Text to Image", "📤 Image Modify & Upload"])
    
    with tab_txt:
        p_i = st.text_area("Describe Image (One per line for batch):", height=150)
        
        char_desc_img = st.text_input("Consistent Character Description:", 
                                      placeholder="Example: A young girl, blue eyes, brown braided hair, red scarf")
        
        canva_overlay_text = st.text_input("Canva Text Overlay (Text overlay on image):", placeholder="Example: Sglowina Studio V1.5")
                                      
        ic1, ic2, ic3 = st.columns(3)
        with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "Cinematic Film", "Anime Art", "Logo Design", "3D Cartoon", "Rustic Village Life", "Historical Epic"])
        with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok", "CinemaScope (21:9)", "Standard Box (4:3)"])
        with ic3: count = st.slider("Quantity:", 1, 10, 1)
        
        if st.button("Generate Titan Visuals 🚀"):
            u_db = get_user_data(st.session_state.logged_in_user)
            if u_db and u_db['credits'] >= 2 * count:
                dim = {
                    "Square (1:1)": (1024, 1024), 
                    "YouTube HD": (1280, 720), 
                    "TikTok": (720, 1280),
                    "CinemaScope (21:9)": (1680, 720),
                    "Standard Box (4:3)": (1024, 768)
                }
                w, h = dim[i_size]
                prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
                for idx, single_p in enumerate(prompt_list):
                    for q in range(count):
                        final_p = single_p
                        
                        style_boosters_img = {
                            "Realistic HD": "ultra photorealistic, 8k resolution, highly detailed, sharp focus, natural skin textures, professional studio lighting, shot on 35mm lens",
                            "Cinematic Film": "cinematic movie style, dramatic Hollywood cinematic lighting, Arri Alexa LF camera, deep shadows, cinematic color grade, depth of field",
                            "3D Cartoon": "3D cartoon animation style, Pixar and Disney style, smooth 3D renders, stylized charming characters, vibrant colorful environment, claymation textures, adorable animated movie aesthetic, beautiful 3D digital art",
                            "Anime Art": "beautiful anime illustration, high-quality Japanese anime art style, clean lines, vibrant cel shading, detailed background, Makoto Shinkai or Kyoto Animation aesthetic",
                            "Logo Design": "minimalist professional vector logo design, clean graphic art, solid flat colors, high contrast, elegant emblem, icon style",
                            "Historical Epic": "grand historical epic movie style, majestic ancient atmosphere, rich cultural heritage textures, cinematic golden hour lighting, dramatic historical film frame",
                            "Rustic Village Life": "rustic traditional old village life aesthetic, raw earthy tones, authentic rural setting, natural rustic lighting, historical simplicity",
                            "Dark Gothic / Mystery": "moody dark gothic mystery aesthetic, eerie misty atmosphere, shadows and contrast, dramatic cinematic suspense look, dark fantasy style"
                        }
                        style_tag_img = style_boosters_img.get(i_style, "")
                        
                        if char_desc_img.strip():
                            final_p = f"Character is {char_desc_img.strip()}. Action/Scene: {single_p}"
                            
                        if style_tag_img:
                            final_p = f"{final_p}, visual style: {style_tag_img}"
                            
                        img_data = fetch_img_failover(final_p, w, h, random.randint(1,999999))
                        if img_data:
                            img_path_temp = f"temp_canvas_{idx}_{q}.jpg"
                            with open(img_path_temp, "wb") as f_temp:
                                f_temp.write(img_data)
                                
                            if canva_overlay_text.strip():
                                apply_canva_typography(img_path_temp, canva_overlay_text.strip())
                                
                            with Image.open(img_path_temp) as im:
                                st.image(im, caption=f"Prompt: {single_p[:30]}...")
                                
                            try:
                                if os.path.exists(img_path_temp):
                                    os.remove(img_path_temp)
                            except Exception:
                                pass
                                
                            deduct_user_credits(st.session_state.logged_in_user, 2)
                            log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
                        else:
                            st.error(f"Image generation failed for prompt: {single_p}")
            else:
                st.error("Deduction failed: Sglowina requires 2 credits per generated image or login required.")

    with tab_img:
        uploaded_file = st.file_uploader("Upload Image to Modify:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Original Image", use_container_width=True)
            
        modify_prompt = st.text_input("Modification Instructions:", placeholder="Example: Make the background dark green, add cinematic volumetric light")
        i_style_mod = st.selectbox("Modification Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
        
        canva_overlay_text_mod = st.text_input("Canva Text Overlay for Modified Image:", placeholder="Example: Sglowina Studio V1.5")
        
        if st.button("Modify & Re-render Image 🎨"):
            if uploaded_file and modify_prompt:
                u_db = get_user_data(st.session_state.logged_in_user)
                if u_db and u_db['credits'] >= 5:
                    with st.spinner("Modifying image..."):
                        img_name = translate_ur_to_en_enhanced(modify_prompt)
                        
                        style_boosters_mod = {
                            "Realistic HD": "ultra photorealistic, 8k resolution, highly detailed, sharp focus, natural skin textures, professional studio lighting",
                            "Cinematic Film": "cinematic movie style, dramatic Hollywood cinematic lighting, Arri Alexa, deep shadows, depth of field",
                            "3D Cartoon": "3D cartoon animation style, Pixar and Disney style, smooth 3D renders, claymation textures"
                        }
                        style_tag_mod = style_boosters_mod.get(i_style_mod, "")
                        if style_tag_mod:
                            img_name = f"{img_name}, visual style: {style_tag_mod}"
                            
                        img_data = fetch_img_failover(img_name, 1024, 1024, random.randint(1,999999))
                        if img_data:
                            img_path_temp_mod = "temp_canvas_mod.jpg"
                            with open(img_path_temp_mod, "wb") as f_temp_mod:
                                f_temp_mod.write(img_data)
                                
                            if canva_overlay_text_mod.strip():
                                apply_canva_typography(img_path_temp_mod, canva_overlay_text_mod.strip())
                                
                            with Image.open(img_path_temp_mod) as im:
                                st.image(im, caption="Modified Masterpiece")
                                
                            try:
                                if os.path.exists(img_path_temp_mod):
                                    os.remove(img_path_temp_mod)
                            except Exception:
                                pass
                                
                            deduct_user_credits(st.session_state.logged_in_user, 5)
                            log_credit_usage(u_db['id'], "Image Modification", 5, u_db['credits'] - 5)
                        else:
                            st.error("Modification failed.")
                else:
                    st.error("Deduction failed: Sglowina requires 5 credits to modify images (or please sign in).")
            else:
                st.warning("Please upload an image and write instructions first.")

# -----------------
# TAB 5: ENTERPRISE CENTER
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina Enterprise Administration Center")
    
    ent_tab_user, ent_tab_history, ent_tab_billing, ent_tab_admin = st.tabs(["👤 User Profile", "📁 Saved Projects", "💳 Billing & Subscription Plans", "🔒 Admin Control Panel"])
    
    u_db = get_user_data(st.session_state.logged_in_user)
    
    with ent_tab_user:
        if u_db:
            st.write(f"#### Logged-in User Profile")
            st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
            st.write("Secure Session Token:")
            st.code(str(uuid.uuid5(uuid.NAMESPACE_DNS, st.session_state.logged_in_user))[:20])
            st.write("Joined Sglowina Cloud:")
            st.code(u_db['created_at'])
        else:
            st.warning("Please login first to view profile.")
        
    with ent_tab_history:
        st.write("#### 📁 Active Download Manager & Saved Projects")
        if u_db:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE user_id = ?", (u_db['id'],))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                st.write("No saved projects found.")
            else:
                for proj in rows:
                    st.write(f"🎬 **{proj['project_name']}** (Created: {proj['created_at']})")
                    st.write("Saved Prompts for this video:")
                    st.code(proj['prompt'], language="text")
                    st.markdown("---")
        else:
            st.warning("Please login first.")
                
    with ent_tab_billing:
        st.write("### 💳 Subscription Plans & Credit Packages (Pakistani Local Payment Integration)")
        
        st.success("#### 🏆 Sglowina Premium Monthly Plan")
        st.write("💰 **Price:** 1000 PKR / Month")
        st.write("🪙 **Credits Received:** 450 Credits (Guarantees at least 30 Cinematic Video Generations!)")
        
        st.markdown("---")
        st.write("### 🎁 Redeem Sglowina Promo / Coupon Code")
        with st.form("coupon_form"):
            coupon_code = st.text_input("Enter Promo Code:", placeholder="e.g. ESSASABA")
            btn_redeem = st.form_submit_button("Redeem Credits 🎁")
            if btn_redeem:
                if coupon_code.strip() and u_db:
                    conn = get_db_connection()
                    curr = conn.cursor()
                    curr.execute("SELECT * FROM coupons WHERE UPPER(code) = UPPER(?)", (coupon_code.strip(),))
                    c_row = curr.fetchone()
                    if c_row:
                        if c_row['uses_left'] > 0:
                            curr.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (c_row['credits'], u_db['id']))
                            curr.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (c_row['code'],))
                            log_credit_usage(u_db['id'], f"Coupon Redeemed: {c_row['code']}", c_row['credits'], u_db['credits'] + c_row['credits'])
                            conn.commit()
                            st.success(f"Success! {c_row['credits']} credits added to your account! 🟢")
                        else:
                            st.error("This promo code has expired.")
                    else:
                        st.error("Invalid coupon code.")
                    conn.close()
                else:
                    st.error("Please log in first to redeem coupons.")
        
        st.markdown("---")
        st.write("### 📱 How to Pay via EasyPaisa / JazzCash")
        st.write("1. Send **1000 PKR** to one of the accounts below:")
        
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.info("💚 **EasyPaisa Account**\n\n* **Account Name:** Saba Wahid\n* **Account Number:** 03086834020")
        with bcol2:
            st.warning("❤️ **JazzCash Account**\n\n* **Account Name:** Ayisha bi bi\n* **Account Number:** 03240755475")
            
        st.write("2. After transferring the money, please submit your payment request below for instant verification:")
        
        if u_db:
            with st.form("local_payment_form"):
                p_method = st.selectbox("Payment Method Used:", ["EasyPaisa", "JazzCash"])
                p_trx_id = st.text_input("Enter Transaction ID (TrxID):", placeholder="e.g., 50123456789")
                p_amount = st.number_input("Amount Sent (PKR):", min_value=500.0, max_value=50000.0, value=1000.0, step=100.0)
                btn_p_submit = st.form_submit_button("Submit Payment Proof 🚀")
                
                if btn_p_submit:
                    if p_trx_id.strip():
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            req_id = str(uuid.uuid4())[:8]
                            cursor.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                           (req_id, u_db['username'], p_method, p_trx_id.strip(), p_amount, 'Pending', time.strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            backup_db_to_json()
                            st.success("Your payment request has been submitted successfully! Sglowina administrators will verify and credit your 450 coins shortly.")
                        except sqlite3.IntegrityError:
                            st.error("This Transaction ID (TrxID) has already been submitted.")
                        finally:
                            conn.close()
                    else:
                        st.warning("Please enter a valid Transaction ID (TrxID).")
        else:
            st.error("Please log in first to submit a payment request.")
                
    with ent_tab_admin:
        st.write("#### 🔒 Secured Admin Control Settings")
        if u_db and u_db['role'] == 'Admin':
            st.success("Access Granted: Administrator Mode Activated")
            
            st.write("### 🔑 Sglowina Master API Key Configuration")
            st.info("بطور ایڈمنسٹریٹر آپ یہاں اپنی پریمیم اے پی آئی کی (API Key) لگا کر ہمیشہ کے لیے سیو کر سکتے ہیں، تاکہ تمام صارفین بغیر اپنی کی درج کیے مستقل ویڈیو جنریٹ کر سکیں۔")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            m_row = cursor.fetchone()
            current_master_key = m_row['value'] if m_row else ""
            conn.close()
            
            with st.form("master_key_config_form"):
                new_master_key_input = st.text_input("Set Master API Key (e.g. sk_... / pk_...):", value=current_master_key, type="password")
                btn_save_master_key = st.form_submit_button("Save Master API Key 💾")
                if btn_save_master_key:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('master_pollinations_key', ?)", (new_master_key_input.strip(),))
                    conn.commit()
                    backup_db_to_json()
                    conn.close()
                    st.success("Master API Key saved successfully! All user renders will now use this key. 🟢")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown("---")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(credits) FROM users")
            total_credits_allocated = cursor.fetchone()[0]
            
            st.write("### System Metrics Dashboard")
            saas_col1, saas_col2, saas_col3 = st.columns(3)
            with saas_col1:
                st.metric("Total Users Count", total_users)
            with saas_col2:
                st.metric("Total Generated Projects", total_projects)
            with saas_col3:
                st.metric("Total Allocated Credits", total_credits_allocated)
                
            st.markdown("---")
            st.write("### 📲 Pending Local Payment Requests")
            cursor.execute("SELECT * FROM local_payments WHERE status = 'Pending'")
            pending_reqs = cursor.fetchall()
            
            if not pending_reqs:
                st.info("No pending payment requests found.")
            else:
                for req in pending_reqs:
                    st.write(f"👤 **User:** `{req['username']}` | 📱 **Method:** {req['method']} | 🔑 **TrxID:** `{req['trx_id']}` | 💰 **Amount:** {req['amount']} PKR")
                    
                    app_btn_key = f"approve_{req['id']}"
                    if st.button(f"Approve Payment & Credit 450 Coins for {req['username']}", key=app_btn_key):
                        cursor.execute("UPDATE local_payments SET status = 'Approved' WHERE id = ?", (req['id'],))
                        cursor.execute("UPDATE users SET credits = credits + 450, plan = 'Premium' WHERE username = ?", (req['username'],))
                        
                        cursor.execute("SELECT id, credits FROM users WHERE username = ?", (req['username'],))
                        target_u = cursor.fetchone()
                        
                        if target_u:
                            log_credit_usage(target_u['id'], "Manual Purchase Approval", 450, target_u['credits'])
                            
                        conn.commit()
                        backup_db_to_json()
                        st.success(f"Payment {req['trx_id']} approved! 450 credits successfully loaded onto {req['username']}'s account.")
                        st.rerun()
            
            st.markdown("---")
            cursor.execute("SELECT * FROM users")
            all_users = cursor.fetchall()
            
            st.write("### User Database Management")
            for u in all_users:
                st.write(f"👤 **{u['username']}** | Role: {u['role']} | Plan: {u['plan']} | Credits: {u['credits']} 🪙 | Status: {u['status']}")
                
            st.markdown("---")
            manage_user = st.selectbox("Select User to Adjust:", [u['username'] for u in all_users])
            new_plan = st.selectbox("Change Subscription Plan:", ["Free", "Starter", "Premium", "Enterprise"])
            new_role = st.selectbox("Change User Role:", ["User", "Admin"])
            new_status = st.selectbox("Change Account Status:", ["Active", "Banned"])
            new_credits = st.number_input("Adjust Credits Balance:", min_value=0, max_value=100000, value=500)
            
            if st.button("Apply Admin Settings"):
                cursor.execute("UPDATE users SET credits = ?, plan = ?, role = ?, status = ? WHERE username = ?", (new_credits, new_plan, new_role, new_status, manage_user))
                conn.commit()
                backup_db_to_json()
                st.success(f"Successfully updated settings for {manage_user}!")
            conn.close()
        else:
            st.error("Access Denied: Only database-defined Administrators can access this control panel.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #94a3b8;'>Sglowina AI Version 2.1 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
