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

# PIL Compatibility Failsafe
if not hasattr(Image, 'ANTIALIAS'):
    try: Image.ANTIALIAS = Image.Resampling.LANCZOS
    except AttributeError: Image.ANTIALIAS = Image.LANCZOS

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"

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

# Page Config - Restored V1.0 [7.1]
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

def get_public_url(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        url = "https://tmpfiles.org/api/v1/upload"
        files = {'file': (uploaded_file.name, file_bytes, uploaded_file.type)}
        res = requests.post(url, files=files, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                return data["data"]["url"].replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
    except: pass
    return None

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

# Real-time Web Search Engine using pure DuckDuckGo parsing to bypass heavy APIs
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

# Fast POST Request with automated model-rotation failovers to permanently prevent 402 locks [1, 2]
def generate_text_pollinations(prompt, system_prompt=""):
    models = ["openai", "mistral", "qwen", "llama"]
    for model in models:
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "model": model,
                "jsonMode": False
            }
            res = requests.post("https://text.pollinations.ai/", json=payload, headers=headers, timeout=15)
            if res.status_code == 200 and len(res.text.strip()) > 5:
                return res.text.strip()
        except: pass
    return ""

# Official Google Translate API integration with backup translation mirror [2.2, 5.1]
def translate_ur_to_en_enhanced(text):
    # Mirror 1: Official Translate API
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            result = res.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if len(translated_text.strip()) > 3:
                return translated_text.strip()
    except: pass
    
    # Mirror 2: Alternate Web API Translate
    try:
        url = f"https://translate.google.com/translate_a/single?client=at&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            result = res.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if len(translated_text.strip()) > 3:
                return translated_text.strip()
    except: pass
    
    # Fallback to visual prompt translator
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

# Universal style-locked animal prompt cleaning system (forces style chosen in UI and purges human traits)
def clean_animal_prompt_of_humans(prompt, urdu_text, style):
    prompt_lower = prompt.lower()
    urdu_lower = urdu_text.lower()
    
    has_human_urdu = any(k in urdu_lower for k in ["لڑکا", "لڑکی", "عورت", "مرد", "انسان", "بچہ", "بچے", "لوگ", "شہزادہ", "بادشاہ", "ملکہ"])
    has_animal_urdu = any(k in urdu_lower for k in ["چوزہ", "چوزے", "بلی", "بندر", "طوطا", "خرگوش", "چوہا", "جانور", "حیوان", "شیر", "چیتا", "ہاتھی", "بھیڑیا"])
    
    # Realism Booster directly injected to bypass Flux cartoon bias for animals
    if style in ["Realistic HD", "Cinematic Hollywood", "Corporate Business", "Rustic Village Life", "Islamic Historical"]:
        realism_booster = "photographic award-winning shot of a real live animal, realistic textures, natural lighting, strictly no CGI, no 3D cartoon render, "
    else:
        realism_booster = ""

    # Map style parameter to descriptive prefixes dynamically to lock user choices
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
        
        # Explicit wide-angle landscape animal anchors with 100% sharp background focus & beautiful scenic trails
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

# Safe programmatic Visual prompt writer using Text POST to preserve requested style
def generate_enhanced_cinematic_prompt(urdu_scene, style, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url, attire_desc="", consistent_char_desc=""):
    try:
        scene_lower = urdu_scene.lower()
        gender_booster = ""
        
        style_boosters = {
            "Realistic HD": "ultra photorealistic, award-winning photography style, 8k resolution, highly detailed, sharp focus, natural real skin textures, strictly no 3D render, no CGI, no drawing",
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
        
        formatted_instruction = instruction.replace("{raw_male_url}", raw_male_url or "None").replace("{raw_female_url}", raw_female_url or "None")
        refined_p = generate_text_pollinations(prompt_input, formatted_instruction)
        if refined_p:
            refined_p = re.sub(r'^(prompt:|visual prompt:|cinematic prompt:)\s*', '', refined_p, flags=re.IGNORECASE).strip()
            return f"{refined_p}, visual style: {style_tag}"
    except: pass
    
    # Fallback prompt construction if API times out
    translated_p = translate_ur_to_en_enhanced(urdu_scene)
    return f"Highly detailed {style}, {translated_p}"

# Clean, safe image enhancement without channel splits/distortions
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
            im.save(img_path, "JPEG")
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
            bg = im.resize((target_w, target_h)).filter(ImageFilter.GaussianBlur(radius=22))
            im_ratio = im.width / im.height
            target_ratio = target_w / target_h
            if im_ratio > target_ratio:
                new_w, new_h = target_w, int(target_w / im_ratio)
            else:
                new_w, new_h = int(target_h * im_ratio), target_h
            fg = im.resize((new_w, new_h))
            bg.paste(fg, ((target_w - new_w) // 2, (target_h - new_h) // 2))
            bg.save(img_path, "JPEG")
    except: pass

# Procedural high-end cinematic soft light leaks background generator to eliminate dead black/gray frames [2.2]
def generate_cinematic_gradient_placeholder(img_path, w, h, scene_text="Sglowina AI"):
    try:
        base = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(base)
        
        # Soft atmospheric vertical lighting gradient
        for y in range(h):
            r = int(12 + (24 * (y / h)))
            g = int(20 + (4 * (y / h)))
            b = int(38 - (18 * (y / h)))
            draw.line([(0, y), (w, y)], fill=(r, g, b))
            
        # Translucent warm golden sun leak overlay
        aura = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        aura_draw = ImageDraw.Draw(aura)
        cx, cy = w // 2, h // 2
        rx, ry = int(w * 0.45), int(h * 0.45)
        
        for r_offset in range(100, 0, -5):
            alpha = int(22 * (1 - (r_offset / 100)))
            aura_draw.ellipse([cx - rx * (r_offset/100), cy - ry * (r_offset/100), 
                               cx + rx * (r_offset/100), cy + ry * (r_offset/100)], 
                              fill=(245, 200, 50, alpha))
                              
        base = Image.alpha_composite(base.convert("RGBA"), aura).convert("RGB")
        base = base.filter(ImageFilter.GaussianBlur(radius=6))
        base.save(img_path, "JPEG")
    except:
        try: Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_path, "JPEG")
        except: pass

def ensure_image_exists(img_path, w, h, scene_text="Sglowina AI"):
    if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
        generate_cinematic_gradient_placeholder(img_path, w, h, scene_text)

# Apply custom logo watermark to the image directly
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
            im.convert("RGB").save(img_path, "JPEG")
    except: pass

# High-Performance ThreadPool parallel downloader with automatic model-rotation and user-agent rotating [2.2]
def parallel_download_flux_images(urls, paths, sentences, w, h, style="Realistic HD"):
    def download_single_image(index):
        url, path, scene_text = urls[index], paths[index], sentences[index]
        success = False
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        t_session = requests.Session()
        t_session.headers.update({"User-Agent": random.choice(user_agents)})
        
        # Clean prompt keywords for secondary failovers
        clean_prompt_words = re.sub(r'[^a-zA-Z0-9\s,]', '', translate_ur_to_en_enhanced(scene_text))
        clean_prompt_words = ", ".join(clean_prompt_words.split(",")[:12])[:250]
        
        image_models = ["flux", "turbo"]
        
        # 1. Try primary high-resolution download with 25s timeout limit [2.2]
        for attempt in range(2):
            try:
                res = t_session.get(url, timeout=25)
                if res.status_code == 200 and len(res.content) > 5000:
                    with open(path, "wb") as f: f.write(res.content)
                    success = True
                    break
            except: pass
            time.sleep(0.5)
            
        # 2. Try rotating through alternative models & endpoints on failure
        if not success:
            fallback_style = "highly realistic photography, professional, highly detailed, real life"
            if style == "3D Cartoon":
                fallback_style = "3D cartoon animation Pixar style, cute, colorful"
            elif style == "Cinematic Hollywood":
                fallback_style = "cinematic Hollywood movie shot, highly detailed, dramatic"
            elif style == "Bollywood Dramatic":
                fallback_style = "vibrant Bollywood movie shot, dramatic"
            elif style == "Anime Art":
                fallback_style = "Japanese anime illustration, high quality"
                
            for img_model in image_models:
                fallback_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(fallback_style + ', ' + clean_prompt_words)}?width={w}&height={h}&nologo=true&model={img_model}&seed={random.randint(1,99999)}"
                try:
                    res = t_session.get(fallback_url, timeout=20)
                    if res.status_code == 200 and len(res.content) > 5000:
                        with open(path, "wb") as f: f.write(res.content)
                        success = True
                        break
                except: pass
            
        # 3. If everything fails, use our Stunning Procedural Cinematic Gradient
        if not success:
            generate_cinematic_gradient_placeholder(path, w, h, scene_text)

    # Launch up to 8 parallel download slots for maximum multi-threaded performance
    max_workers = min(8, len(urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(download_single_image, range(len(urls)))

def get_cached_bg_music(is_horror, is_epic):
    fn = "bg_horror.mp3" if is_horror else ("bg_epic.mp3" if is_epic else "bg_standard.mp3")
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3" if is_horror else ("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3" if is_epic else "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3")
    cf = os.path.join(AUDIO_CACHE_DIR, fn)
    if os.path.exists(cf) and os.path.getsize(cf) > 100000: return cf
    try:
        res = session.get(url, timeout=15, verify=False)
        if res.status_code == 200:
            with open(cf, "wb") as f: f.write(res.content)
            return cf
    except: pass
    return None

def download_video_safely(url, dest_path, progress_status):
    try:
        with session.get(url, stream=True, timeout=120) as r:
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                return True
    except Exception as e:
        progress_status.warning(f"Video download timeout ({e}). Falling back to Cinematic Zoom...")
    return False

# Preserved image scale factor at 1.05 to prevent blurry zooms or focus errors
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    if not MOVIEPY_AVAILABLE: return None
    ensure_image_exists(img_path, w, h, "Visualizing scene...")
    try:
        scale_factor = 1.05
        base_clip = ImageClip(img_path).set_duration(duration).set_fps(24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = base_clip.resize((cw, ch))
        
        motions_map = {
            "Zoom In": lambda: clip.resize(lambda t: 1.0 + 0.05 * (t / duration)).set_position('center'),
            "Zoom Out (v40 Default)": lambda: clip.resize(lambda t: 1.05 - 0.05 * (t / duration)).set_position('center'),
            "Pan Left": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center')),
            "Pan Right": lambda: clip.set_position(lambda t: (int((w - cw) * (1 - t / duration)), 'center')),
            "Pan Up": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))),
            "Pan Down": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration)))),
            "Dolly In": lambda: clip.resize(lambda t: 1.0 + 0.05 * (t / duration)).set_position('center'),
            "Dolly Out": lambda: clip.resize(lambda t: 1.05 - 0.05 * (t / duration)).set_position('center'),
            "Orbit Camera": lambda: clip.rotate(lambda t: -1 + 2 * (t / duration)).resize(lambda t: 1.02 + 0.03 * (t / duration)).set_position('center'),
            "Crane Shot": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))).rotate(lambda t: -1 * (t / duration)),
            "Drone Shot": lambda: clip.resize(lambda t: 1.05 - 0.05 * (t / duration)).rotate(lambda t: 2 * (t / duration)).set_position('center'),
            "Tracking Shot": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), int((h - ch)/2 + (2 * np.sin(2 * np.pi * t * 1.5))))),
            "Follow Shot": lambda: clip.set_position(lambda t: (int((w - cw) * (t / duration)), int((h - ch)/2 + (2 * np.sin(2 * np.pi * t * 1.5))))),
            "Handheld Camera": lambda: clip.set_position(lambda t: (int((w - cw)/2 + (2 * np.sin(2 * np.pi * t * 2.0))), int((h - ch)/2 + (2 * np.cos(2 * np.pi * t * 1.7))))).rotate(lambda t: 0.5 * np.sin(2 * np.pi * t * 1.0)),
            "Shoulder Camera": lambda: clip.set_position(lambda t: (int((w - cw)/2 + (2 * np.sin(2 * np.pi * t * 2.0))), int((h - ch)/2 + (2 * np.cos(2 * np.pi * t * 1.7))))).rotate(lambda t: 0.5 * np.sin(2 * np.pi * t * 1.0)),
            "Cinematic Reveal": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration)))),
            "Whip Pan": lambda: clip.set_position(lambda t: (int((w - cw) * ((t / duration) ** 3)), 'center')),
            "Tilt Up": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))),
            "Tilt Down": lambda: clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration)))),
            "Roll Camera": lambda: clip.rotate(lambda t: 3 * (t / duration)).set_position('center'),
            "Parallax Motion": lambda: clip.resize(lambda t: 1.01 + 0.04 * (t / duration)).set_position(lambda t: (int((w - cw) * (t / duration)), 'center')),
            "Ken Burns Effect": lambda: clip.resize(lambda t: 1.01 + 0.04 * (t / duration)).set_position(lambda t: (int((w - cw) * (t / duration)), 'center')),
            "Rack Focus": lambda: clip.resize(lambda t: 1.05 - 0.05 * (t / duration)).set_position('center'),
            "Motion Blur": lambda: clip.resize(lambda t: 1.05 - 0.05 * (t / duration)).set_position('center')
        }
        try:
            animated_clip = motions_map.get(motion, motions_map["Zoom Out (v40 Default)"])()
            return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
        except:
            return ImageClip(img_path).set_duration(duration).resize((w, h))
    except Exception as ex:
        st.warning(f"Motion error '{motion}': {ex}. Falling back.")
    try: return ImageClip(img_path).set_duration(duration).resize((w, h))
    except: return ImageClip(np.zeros((h, w, 3), dtype=np.uint8)).set_duration(duration)

def apply_clip_transition(clip, transition, duration):
    try:
        fade_dur = min(0.3, duration / 3.0)
        if transition in ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Film Dissolve (Muted)"]:
            return clip.fadein(fade_dur).fadeout(fade_dur)
    except: pass
    return clip

def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
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

# Urdu Font Finder to safely load beautiful Nastaliq rendering [2.2]
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

# Secure subtitle burning function to overlay text elegantly [2.2]
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
            im.save(img_path, "JPEG")
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
            im.save(img_path, "JPEG")
    except: pass

# ==========================================
# 4. SINGLE CLICK DIRECT MOVIE GENERATION (V1.0 restored with step progress text and custom watermark)
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", video_model="wan-fast", custom_wm_bytes=None, enable_sub=False):
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
            
            # Step progress feedback text
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
                # Update progress per scene voiceover
                status.info(f"🎙️ Voiceovers: Compiling speech for Scene {idx + 1} of {total_scenes}...")
                is_female_voice = any(k in scene or k in scene.lower() for k in female_keywords)
                is_male_voice = any(k in scene or k in scene.lower() for k in male_keywords)
                if not is_female_voice and not is_male_voice:
                    if primary_gender == "female": is_female_voice = True
                    elif primary_gender == "male": is_male_voice = True
                
                v_code_scene = "ur-PK-UzmaNeural" if (is_female_voice and not is_male_voice) else "ur-PK-AsadNeural"
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path):
                    raise Exception("Voice generation failed.")
                temporary_audio_tracks[idx] = sub_audio_path
                
            progress_bar.progress(0.12)
            if enable_bg_music:
                story_lower = story.lower()
                is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوف", "جن", "grave", "death", "scary", "ghost"])
                is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "king", "queen", "throne", "palace"])
                cached_bg_path = get_cached_bg_music(is_horror, is_epic)
                if cached_bg_path and os.path.exists(cached_bg_path): has_bg_music = True
                
            progress_bar.progress(0.18)
            res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
            w, h = res_map.get(ratio, (1280, 720))
            w, h = make_even(w), make_even(h)
            
            for i, scene in enumerate(sentences):
                # Update progress per scene prompt formulation
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
                
                active_male_ref = raw_male_url if (character_present and (primary_gender == "male" or local_human)) else None
                active_female_ref = raw_female_url if (character_present and (primary_gender == "female" or local_human)) else None
                
                active_heritage = character_heritage
                if character_heritage == "Automatic" or not character_heritage:
                    active_heritage = "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)" if (any(k in scene.lower() for k in female_keywords + male_keywords) or primary_gender) else "Western / Modern"
                
                refined_p = generate_enhanced_cinematic_prompt(scene, style, active_heritage, enable_islamic_filter, active_male_ref, active_female_ref, attire_tag if character_present else "", consistent_char_desc)
                # Enforce programmatic human stripper cleaner to strictly protect animal visual fidelity & lock selected style
                refined_p = clean_animal_prompt_of_humans(refined_p, scene, style)
                
                if not is_spiritual and character_present:
                    refined_p += " [Avoid cross-gender blending, anatomically correct]"
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}, {dir_settings['composition']}"
                generated_prompts[i] = refined_p
                
                if "Real AI Video" in gen_mode and active_api_key:
                    status.info(f"🎥 Rendering Video Scene {i+1}/{total_scenes} via {video_model}...")
                    aspect_ratio_param = "16:9" if "16:9" in ratio else "9:16"
                    motion_prompt = f"high motion, realistic physics movement, wind blowing, {refined_p}"
                    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt[:400])}?model={video_model}&aspectRatio={aspect_ratio_param}&key={active_api_key}&duration=4"
                    ref_url = raw_female_url if (primary_gender == "female") else raw_male_url
                    if ref_url: vid_url += f"&image={urllib.parse.quote(ref_url)}"
                    
                    vid_path = f"v_{u_id}_{i}.mp4"
                    if download_video_safely(vid_url, vid_path, status):
                        try:
                            scene_voice_clip = AudioFileClip(temporary_audio_tracks[i])
                            dur_scene = scene_voice_clip.duration
                            clip = VideoFileClip(vid_path).resize((w, h)).set_duration(dur_scene)
                            
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
                
                w_target, h_target = make_even(w * 1.25), make_even(h * 1.25)
                # Safeguard: Truncate prompt passed to Flux to 400 chars to avoid HTTP 414 URI Too Long errors
                truncated_prompt = refined_p[:400]
                flux_prompt_urls[i] = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(truncated_prompt)}?width={w_target}&height={h_target}&seed={seed + i * 17}&nologo=true&model=flux"
                img_paths[i] = f"i_{u_id}_{i}.jpg"
                
            progress_bar.progress(0.25)
            indices_needing_images = [idx for idx, c in enumerate(clips) if c is None]
            if indices_needing_images:
                # Update progress for frame generation (Capped at 12s sequential processing for high speed)
                status.info("🎨 Visuals: Actively generating custom AI scenes with Flux AI (تخلیق کا عمل جاری ہے)...")
                parallel_download_flux_images(
                    [flux_prompt_urls[idx] for idx in indices_needing_images],
                    [img_paths[idx] for idx in indices_needing_images],
                    [sentences[idx] for idx in indices_needing_images], w, h, style
                )
                for idx in indices_needing_images:
                    if img_paths[idx]: generated_images.append(img_paths[idx])
            
            progress_bar.progress(0.45)
            
            for i in range(total_scenes):
                if clips[i] is not None: continue
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                scene = sentences[i]
                
                # Update progress per scene rendering
                status.info(f"🎞️ Video: Applying camera motion and compiling Scene {i + 1} of {total_scenes}...")
                ensure_image_exists(img_path, w, h, scene)
                apply_color_lut_harmony(img_path, style)
                # Dynamically write Nastaliq Urdu subtitles on image safely
                if enable_sub:
                    burn_subtitles_to_image(img_path, scene)
                # Apply custom watermark if provided
                if custom_wm_bytes is not None:
                    apply_custom_watermark(img_path, custom_wm_bytes)
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                
                dir_settings = analyze_scene_for_director(scene)
                active_motion = camera_motion if camera_motion != "AI Hollywood Director (Auto)" else dir_settings["motion"]
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h)
                if clip is None:
                    try: clip = ImageClip(img_path).set_duration(dur_scene).resize((w, h))
                    except: clip = ImageClip(np.zeros((h, w, 3), dtype=np.uint8)).set_duration(dur_scene)
                
                sfx_file = download_scene_sfx(scene, u_id, i)
                if sfx_file and os.path.exists(sfx_file):
                    sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                    clip = clip.set_audio(CompositeAudioClip([scene_voice_clip.volumex(1.2), sfx_audio]))
                    generated_images.append(sfx_file)
                else:
                    clip = clip.set_audio(scene_voice_clip.volumex(1.2))
                    
                clips[i] = apply_clip_transition(clip, transition_style, dur_scene)
                
            progress_bar.progress(0.70)
            status.info("🎵 Audio Mixer: Ducking background music and mixing elements...")
            valid_clips = [c for c in clips if c is not None]
            if not valid_clips: raise Exception("No valid scenes were generated.")
            
            final_video = concatenate_videoclips(valid_clips, method="compose").resize((w, h))
            if has_bg_music and cached_bg_path:
                try:
                    bg_track = AudioFileClip(cached_bg_path).volumex(0.03).set_duration(final_video.duration)
                    final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                except Exception as e: st.warning(f"Background music error: {e}")
                
            # Randomize output file name completely with timestamp to forcefully bypass browser caches [1.1]
            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            status.info("🎬 Rendering: Stitching elements into final master video (Ultrafast compression active)...")
            # 100x Speedup parameters injected directly into moviepy writer
            write_kwargs = {"codec": "libx264", "audio_codec": "aac", "fps": 24, "preset": "ultrafast", "threads": 4, "ffmpeg_params": ["-pix_fmt", "yuv420p"]}
            try: final_video.write_videofile(out_name, logger=None, **write_kwargs)
            except: final_video.write_videofile(out_name, verbose=False, **write_kwargs)
            
            final_video.close()
            for sub_voice in temporary_audio_tracks:
                try: os.remove(sub_voice)
                except: pass
            for file_p in generated_images:
                try:
                    if file_p != cached_bg_path: os.remove(file_p)
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
                    if file_p != cached_bg_path: os.remove(file_p)
                except: pass
            progress_bar.empty()
            return f"Error Details: {e}"
        finally: gc.collect()

# ==========================================
# 5. UI SYSTEM STYLE (Streamlit Theme Sync)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    
    /* FLAT, SMALLER UNLIT TITLE DESIGN (Speed-optimized, zero graphics lag, thin text font-weight 300, font-size reduced to 1.2rem) */
    .glow-title { 
        font-size: 1.2rem !important; font-weight: 300 !important; font-family: 'Inter', sans-serif;
        color: #1e3a8a !important; letter-spacing: 2px; margin: 0 !important;
    }
    
    /* FLEX CONTAINER FOR TITLE AND LOGO SIDE-BY-SIDE */
    .dashboard-header {
        display: flex; justify-content: center; align-items: center; gap: 15px;
        margin-top: 15px; margin-bottom: 20px;
    }
    
    /* RADIAL GLOW METALLIC SPINNING CONTAINER (GPU optimized, clean white background, electric blue borders) */
    .circular-s {
        width: 50px !important; height: 50px !important; background: #ffffff !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        border: 2px solid #2563eb !important;
        animation: rotateSpins 10s infinite linear;
    }
    
    /* FLAT ELECTRIC BLUE 'S' TEXT */
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

# Restored side-by-side unlit dashboard header layout with thin text (Sglowina AI | ایس گلووینا)
st.markdown("""
    <div class="dashboard-header">
        <div class="circular-s"><span class="metallic-s">S</span></div>
        <h1 class="glow-title">Sglowina AI | ایس گلووینا</h1>
    </div>
""", unsafe_allow_html=True)

# Tabs Initialization
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
                    # Correct English-only success greetings
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

# Chat Bot (Connected to Google Live Web Search & Copy Container Card)
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # Real-time search criteria check
        web_snippets = ""
        p_lower = p.lower()
        if any(k in p_lower for k in ["search", "live", "latest", "who is", "what is", "current", "news", "گوگل", "سرچ", "اج کل"]):
            web_snippets = search_web_ddg(p)
            
        system_prompt = "You are Sglowina AI, an advanced real-time assistant developed by Sglowina Team. "
        if web_snippets:
            system_prompt += f"\n[Live Web Search Context]:\n{web_snippets}\nUse this real-time context to accurately formulate your response."
            
        # Clean anonymous request with model=openai
        res = generate_text_pollinations(p, system_prompt)
        translated_res = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
        
        with st.chat_message("assistant"):
            st.write(translated_res)
            # Copy Option Container Card (allows copying the whole story/response in 1 click)
            st.info("📋 Click the Copy icon in the top right of the box below to copy the full response:")
            st.code(translated_res, language="")
            st.session_state.msgs.append({"role": "assistant", "content": translated_res})

# Pro Movie Studio
with tab_movie:
    st.write("### 🎥 Movie Studio")
    
    # Restored selectbox and text input with global session state fallbacks
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"], key="gen_mode_select")
    st.session_state.gen_mode = gen_mode
    pollinations_key = st.text_input("Enter Pollinations API Key (if using video mode):", type="password", key="pollinations_key_input") if "Real AI Video" in st.session_state.gen_mode else ""
    st.session_state.pollinations_key = pollinations_key
    
    # 1. Sglowina AI Script Writer Integration (Step 1 of Auto Script generation)
    st.write("#### 📝 Sglowina AI Script Writer (Optional)")
    with st.expander("Write a story automatically with Sglowina AI"):
        script_genre = st.selectbox("Story Genre:", ["Moral Animal Story", "Islamic Historical Story", "Business Explainer Script", "Hollywood Action Plot", "Fun Educational Kid Story"])
        script_topic = st.text_input("Enter Topic/Theme:", placeholder="e.g. A brave rabbit saving the forest")
        if st.button("Generate Script with AI ✨"):
            if script_topic.strip():
                with st.spinner("AI is crafting your story..."):
                    story_prompt = f"Write a scenic, detailed {script_genre} in Urdu language, with clear, separate sentences divided by periods. Topic: {script_topic}. Keep it engaging for a cinematic video narration."
                    ai_story = generate_text_pollinations(story_prompt, "You are a professional creative Urdu storyteller.")
                    if ai_story:
                        st.session_state.movie_script_val = ai_story.strip()
                        st.success("Story Generated! It has been copied to the Script Box below.")
                        st.rerun()
                    else:
                        st.error("AI service is currently busy. Please try again in a few seconds.")
            else:
                st.error("Please enter a topic first.")

    # Script Box
    script_box_default = st.session_state.get("movie_script_val", "")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", value=script_box_default, height=150)
    enable_islamic_filter = st.checkbox("Enable Islamic Safety Filter 🛡️", value=True)
    
    col_up1, col_up2 = st.columns(2)
    with col_up1: uploaded_male_img = st.file_uploader("Upload Male Reference Image:", type=["jpg", "png", "jpeg"])
    with col_up2: uploaded_female_img = st.file_uploader("Upload Female Reference Image:", type=["jpg", "png", "jpeg"])

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9 = st.columns(9)
    # Multi-Language Edge-TTS Voices Support Added (Urdu, English, Arabic, Persian)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    # Style Dropdown reordered with Realistic HD first, added Hollywood, Bollywood, Lollywood, Corporate Business, Islamic & Educational/Learning styles
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "3D Cartoon", "Cinematic Hollywood", "Bollywood Dramatic", "Lollywood Classic", "Islamic Historical", "Corporate Business", "Educational Explainer", "Anime Art", "Logo Design", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Pan Up", "Pan Down", "Dolly In", "Dolly Out", "Orbit Camera", "Crane Shot", "Drone Shot", "Tracking Shot", "Follow Shot", "Handheld Camera", "Shoulder Camera", "Cinematic Reveal", "Whip Pan", "Tilt Up", "Tilt Down", "Roll Camera", "Parallax Motion", "Ken Burns Effect", "Rack Focus", "Motion Blur"])
    with mc7: transition_style = st.selectbox("Transition Effect:", ["Cross Dissolve (Fade)", "Instant Cut"])
    with mc8: video_model = st.selectbox("AI Video Model:", ["wan-fast", "seedance", "veo"])
    with mc9: sd = st.number_input("Character Seed:", value=786)
    
    # Restored to 1-Click Generation Action (Safely resolved st.video NameError and TypeError by passing session state variables and removing incompatible key parameter)
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map[mv_pitch]
        
        # Read custom watermark bytes if uploaded
        wm_bytes = custom_watermark_file.getvalue() if custom_watermark_file else None
        
        # Map voice choice locale to Edge-TTS correctly
        voice_map = {
            "Urdu Male (Asad)": "ur-PK-AsadNeural",
            "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
            "English US Male (Guy)": "en-US-GuyNeural",
            "English US Female (Jenny)": "en-US-JennyNeural",
            "Arabic Egypt Male (Shakir)": "ar-EG-ShakirNeural",
            "Persian Male (Farid)": "fa-IR-FaridNeural"
        }
        active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
        
        # Safe extraction of gen_mode and pollinations_key to prevent any NameError
        active_gen_mode = st.session_state.gen_mode
        active_key = st.session_state.pollinations_key
        
        with st.spinner("🎬 Generating Sglowina Masterpiece..."):
            v_res = create_cinematic_v40(
                m_script, active_voice, rate_val, pitch_val, mr, ms, sd, camera_motion, transition_style,
                enable_watermark, enable_bg_music, uploaded_male_img, uploaded_female_img,
                enable_islamic_filter, "Automatic", active_gen_mode, active_key, video_model,
                custom_wm_bytes=wm_bytes, enable_sub=False # Hardcoded subtitles to False as requested (سکرین کی لکھائی مستقل ختم)
            )
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res):
            st.video(v_res) # Completely removed key parameter from st.video to prevent TypeErrors on Streamlit
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: st.error(v_res)

# Pro Image Studio
with tab_image:
    st.write("### 🎨 Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    char_desc_img = st.text_input("Consistent Character Description:", placeholder="e.g. A young girl with blue eyes")
    canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="e.g. Studio Title")
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["3D Cartoon", "Realistic HD", "Cinematic Film", "Anime Art", "Logo Design"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 5, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        # Corrected Python logical 'and' operator
        if u_db and u_db['credits'] >= 2 * count:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim.get(i_size, (1024, 1024))
            final_p = p_i
            if char_desc_img.strip(): final_p = f"Character is {char_desc_img.strip()}. {p_i}"
            img_data = fetch_img_failover(f"{final_p}, visual style: {i_style}", w, h, random.randint(1,999999))
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
