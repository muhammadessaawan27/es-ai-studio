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
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageFilter, ImageEnhance
import io
import base64
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import concurrent.futures

# ==========================================
# MOVIEPY CINEMATIC IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# BROWSER SESSION STABILITY HEADERS
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI is an advanced generative AI cinematic video, vision & image production platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

# ==========================================
# STREAMLIT INITIALIZATION & GLOBAL STATES
# ==========================================
st.set_page_config(page_title="ES Ultimate Multi-Language AI Studio V6.0", layout="wide", page_icon="⚡")

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "process_ready" not in st.session_state:
    st.session_state.process_ready = False
if "detected_info" not in st.session_state:
    st.session_state.detected_info = {}
if "last_processed_file" not in st.session_state:
    st.session_state.last_processed_file = None

st.sidebar.subheader("🎬 Global Multi-Language Settings")
target_lang = st.sidebar.selectbox("🌐 Choose Global Language (زبان کا انتخاب):", [
    "Urdu (اردو)",
    "English (English)",
    "Hindi (हिंदी)",
    "Spanish (Español)",
    "Chinese (中文)",
    "Korean (한국어)",
    "Arabic (العربية)",
    "French (Français)",
    "German (Deutsch)",
    "Japanese (日本語)",
    "Turkish (Türkçe)"
])

enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=2)
active_renderers = 0
render_lock = threading.Lock()

# Multi-Language Voice Map for Edge-TTS
VOICE_MAP = {
    "Urdu (اردو)": {"male": "ur-PK-AsadNeural", "female": "ur-PK-UzmaNeural", "code": "Urdu"},
    "English (English)": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural", "code": "English"},
    "Hindi (हिंदी)": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural", "code": "Hindi"},
    "Spanish (Español)": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural", "code": "Spanish"},
    "Chinese (中文)": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural", "code": "Chinese"},
    "Korean (한국어)": {"male": "ko-KR-InJoonNeural", "female": "ko-KR-SunHiNeural", "code": "Korean"},
    "Arabic (العربية)": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural", "code": "Arabic"},
    "French (Français)": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural", "code": "French"},
    "German (Deutsch)": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural", "code": "German"},
    "Japanese (日本語)": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural", "code": "Japanese"},
    "Turkish (Türkçe)": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural", "code": "Turkish"}
}

# Safe FFmpeg Locator
def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

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

def apply_canva_typography(img_path, overlay_text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            txt_overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_overlay)
            font_size = max(24, int(im.width / 25))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), overlay_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (im.width - text_w) // 2
            y = im.height - text_h - 40
            draw.rectangle([(x - 20, y - 10), (x + text_w + 20, y + text_h + 10)], fill=(0, 0, 0, 160))
            draw.text((x, y), overlay_text, font=font, fill=(255, 255, 255, 240))
            combined = Image.alpha_composite(im, txt_overlay).convert("RGB")
            combined.save(img_path, "JPEG")
    except Exception:
        pass

# ==========================================
# 2. DYNAMIC DATABASE LAYER (PostgreSQL & SQLite WAL)
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
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            character_name TEXT,
            description TEXT,
            reference_data TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenes (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            scene_name TEXT,
            environment TEXT,
            lighting TEXT,
            camera_style TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            credits INTEGER,
            uses_left INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM coupons WHERE code = 'ESSASABA'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO coupons (code, credits, uses_left) VALUES ('ESSASABA', 100, 1000)")
    
    h_admin = hash_password("786")
    for u, e in [("essasaba", "essasaba@sglowina.ai"), ("essa_awan", "essa@sglowina.ai")]:
        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = ?", (u,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (u, e, h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
                           
    h_saba = hash_password("1234")
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'saba_wahid'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("saba_wahid", "saba@sglowina.ai", h_saba, "Enterprise", 5000, "Admin", "2026-07-21"))
                       
    conn.commit()
    conn.close()

init_db_v21()

# Auth Helpers
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
    conn.close()

def log_credit_usage(user_id, action, used, balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO credits_history (user_id, action, credits_used, balance_after, date) VALUES (?, ?, ?, ?, ?)",
                   (user_id, action, used, balance, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ==========================================
# 3. UNIVERSAL TRANSLATOR & MULTI-LANGUAGE ENGINE
# ==========================================
def translate_to_language(text, target_language_name):
    if not text.strip() or "Urdu" in target_language_name:
        return text
    try:
        inst = f"Translate the following text accurately and naturally into {target_language_name}. Output ONLY the translated text without conversational intro."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(inst + ': ' + text)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return text

# Universal Social Media Downloader (Zero-Cache Dynamic IDs)
def inspect_and_fetch_media_universal(url, target_path):
    if os.path.exists(target_path):
        try: os.remove(target_path)
        except Exception: pass
    
    info_dict = {
        'title': 'Trending Viral Video',
        'uploader': 'Original Creator',
        'platform': 'Social Media',
        'tags': []
    }
    
    u_low = url.lower()
    if 'tiktok' in u_low: info_dict['platform'] = 'TikTok'
    elif 'instagram' in u_low: info_dict['platform'] = 'Instagram'
    elif 'facebook' in u_low or 'fb.watch' in u_low: info_dict['platform'] = 'Facebook'
    elif 'pinterest' in u_low or 'pin.it' in u_low: info_dict['platform'] = 'Pinterest'
    elif 'youtu' in u_low: info_dict['platform'] = 'YouTube'
    
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'http_headers': headers_browser,
            'extractor_args': {
                'youtube': {'player_client': ['android', 'ios', 'mweb', 'web']},
                'tiktok': {'app_version': '20.2.1'}
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            info_dict['title'] = meta.get('title', meta.get('description', 'Viral Video'))
            info_dict['uploader'] = meta.get('uploader', meta.get('channel', 'Creator'))
            info_dict['tags'] = meta.get('tags', [])
    except Exception:
        try:
            with requests.get(url, headers=headers_browser, stream=True, timeout=40) as r:
                if r.status_code == 200:
                    with open(target_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=16384):
                            f.write(chunk)
                    info_dict['title'] = "Social Media Video"
        except Exception:
            pass

    return info_dict

def generate_smart_metadata_dynamic(info, lang="Urdu"):
    raw_title = info.get('title', 'Video').strip()
    platform = info.get('platform', 'Social Media')
    
    clean_title = re.sub(r'#\w+', '', raw_title)
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', clean_title).strip()
    if len(clean_title) < 5: clean_title = f"{platform} Viral Video"
    
    t_lower = raw_title.lower()
    genre = "Trending Viral Clip"
    
    if any(k in t_lower for k in ['comedy', 'funny', 'laugh', 'joke', 'hasna', 'prank']):
        genre = "Comedy / Entertainment"
        safe_titles = [
            f"😂 {clean_title[:50]} | Non-Stop Funny Moments",
            f"🤣 Uncut Comedy Special | {clean_title[:45]}",
            f"🔥 When Fun Reaches Peak! | {clean_title[:50]}"
        ]
        hashtags = "#Comedy #FunnyVideo #LaughOutLoud #ViralClip #TrendingReels"
        thumb_prompt = f"8K YouTube comedy thumbnail for '{clean_title[:35]}', funny expression, bright stage lighting, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana', 'remix']):
        genre = "Music / Audio Vibe"
        safe_titles = [
            f"🎧 {clean_title[:50]} (Slowed + Reverb Lo-Fi Remix)",
            f"🌙 {clean_title[:50]} | Midnight Relaxing Vibe",
            f"✨ Deep Aesthetic Audio | {clean_title[:45]}"
        ]
        hashtags = "#SlowedAndReverb #LofiMusic #ChillVibes #AestheticAudio"
        thumb_prompt = f"Cozy Lo-Fi anime aesthetic 4K wallpaper thumbnail for '{clean_title[:35]}', neon room, rain, 16:9."
    elif any(k in t_lower for k in ['trailer', 'teaser', 'movie', 'film', 'cinema', 'scene', 'action']):
        genre = "Movie / Action Scene"
        safe_titles = [
            f"🔥 {clean_title[:50]} - Full Scene & Climax Breakdown",
            f"⚡ {clean_title[:50]} - Hidden Details & Story Explained",
            f"😱 Unbelievable Twist in {clean_title[:45]} | Full Review"
        ]
        hashtags = "#MovieRecap #ActionScene #CinemaLovers #Blockbuster"
        thumb_prompt = f"8K cinematic action movie thumbnail for '{clean_title[:35]}', dramatic lighting, explosion sparks, 16:9."
    else:
        safe_titles = [
            f"🔥 {clean_title[:50]} | Viral Trending Video",
            f"⚡ You Won't Believe What Happened in {clean_title[:45]}",
            f"😱 Best Moments of {clean_title[:50]} | Must Watch!"
        ]
        hashtags = f"#ViralVideo #{platform}Reels #Trending #MustWatch #BestMoments"
        thumb_prompt = f"High contrast 8K viral thumbnail for '{clean_title[:35]}', vivid colors, dynamic composition, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

# AI Director Analyzer
def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    motion = "Zoom Out (v40 Default)"
    lighting = "Volumetric Light"
    color_grading = "Hollywood Cinematic"
    composition = "Medium Shot, Rule of Thirds"
    
    if any(k in text for k in ["saba", "she", "her", "woman", "female", "girl"]):
        composition = "Tight close-up portrait shot, extreme details of female face, emotional expression"
        motion = "Push In"
    elif any(k in text for k in ["essa", "he", "him", "man", "male", "boy", "warrior", "king"]):
        composition = "Cinematic masculine close-up portrait, focus on eyes and facial details"
        motion = "Zoom In"
    elif any(k in text for k in ["together", "couple", "they", "them", "sitting with", "walking with"]):
        composition = "Cinematic medium shot of a couple, side-by-side interacting"
        motion = "Orbit Camera"
    elif any(k in text for k in ["forest", "jungle", "mountain", "valley", "landscape", "sky", "sea", "ocean", "mud", "field"]):
        composition = "Cinematic wide-angle establishing landscape shot, highly atmospheric environment"
        motion = "Drone Shot"

    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action", "bhaag", "tractor", "drive", "car"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["scary", "ghost", "dark", "grave", "death", "haunted", "scared"]):
        motion = "Dolly In"
        lighting = "Dark Cinematic, Horror Shadows"
        color_grading = "Horror Green"
    elif any(k in text for k in ["fight", "battle", "sword", "war"]):
        motion = "Handheld Camera"
    elif any(k in text for k in ["walk", "stroll"]):
        motion = "Follow Shot"
    elif any(k in text for k in ["think", "silent", "quiet", "meditate"]):
        motion = "Ken Burns Effect"
        
    if any(k in text for k in
