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
# 1. MOVIEPY CINEMATIC IMPORTS
# ==========================================
try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips, 
        CompositeAudioClip, VideoFileClip, CompositeVideoClip
    )
except ImportError:
    from moviepy import (
        ImageClip, AudioFileClip, concatenate_videoclips, 
        CompositeAudioClip, VideoFileClip, CompositeVideoClip
    )

# ==========================================
# 2. BROWSER SESSION STABILITY HEADERS
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI is an advanced generative AI cinematic video, vision & image production platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

# ==========================================
# 3. STREAMLIT INITIALIZATION & GLOBAL STATES
# ==========================================
st.set_page_config(page_title="ES Ultimate AI Studio & Anti-Copyright V5.0", layout="wide", page_icon="⚡")

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
if "current_output_video" not in st.session_state:
    st.session_state.current_output_video = None

st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark, key="sb_watermark")
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music, key="sb_bg_music")

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=2)
active_renderers = 0
render_lock = threading.Lock()

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
        if not os.path.exists(img_path): return
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
# 4. DATABASE LAYER (PostgreSQL & SQLite WAL)
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
        else:
            cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = ?", (h_admin, u))
                           
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
# 5. ROBUST UNIVERSAL MEDIA FETCHER & METADATA
# ==========================================
def clean_media_url(url):
    clean = url.strip()
    if "?" in clean and any(x in clean for x in ["instagram.com", "tiktok.com", "pinterest.com", "pin.it", "fb.watch"]):
        clean = clean.split("?")[0]
    return clean

def inspect_and_fetch_media_universal(url, target_path):
    if os.path.exists(target_path):
        try: os.remove(target_path)
        except Exception: pass
    
    clean_url = clean_media_url(url)
    info_dict = {
        'title': 'Featured Master Video',
        'uploader': 'Official Creator',
        'platform': 'Social Media',
        'categories': ['Entertainment'],
        'tags': []
    }
    
    u_lower = clean_url.lower()
    if 'tiktok' in u_lower: info_dict['platform'] = 'TikTok'
    elif 'instagram' in u_lower: info_dict['platform'] = 'Instagram'
    elif 'facebook' in u_lower or 'fb.watch' in u_lower: info_dict['platform'] = 'Facebook'
    elif 'pinterest' in u_lower or 'pin.it' in u_lower: info_dict['platform'] = 'Pinterest'
    elif 'youtu' in u_lower: info_dict['platform'] = 'YouTube'
    
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'noplaylist': True,
            'http_headers': headers_browser,
            'extractor_args': {
                'youtube': {'player_client': ['android', 'ios', 'mweb', 'web']},
                'tiktok': {'app_version': '20.2.1'}
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            info_dict['title'] = meta.get('title', meta.get('description', 'Featured Video'))
            info_dict['uploader'] = meta.get('uploader', meta.get('channel', 'Creator'))
            info_dict['categories'] = meta.get('categories', ['Entertainment'])
            info_dict['tags'] = meta.get('tags', [])
            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                return True, info_dict
    except Exception:
        pass
        
    try:
        with requests.get(clean_url, headers=headers_browser, stream=True, timeout=40) as r:
            if r.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=32768):
                        f.write(chunk)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                    return True, info_dict
    except Exception:
        pass

    return False, info_dict

def generate_smart_metadata(info):
    raw_title = info.get('title', 'Video').strip()
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', raw_title).strip()
    if not clean_title: clean_title = raw_title
    t_lower = raw_title.lower()
    
    if any(k in t_lower for k in ['motu', 'patlu', 'cartoon', 'anime', 'animation', 'chhota bheem', 'kids']):
        genre = "Animation & Kids Cartoon"
        safe_titles = [
            f"🌟 {clean_title} | Best Moments (Full HD Animation)",
            f"🔥 Iconic Animation Highlights | {clean_title[:45]}",
            f"🎉 Non-Stop Entertainment Special | {clean_title[:45]}"
        ]
        hashtags = "#Animation #Cartoons #KidsEntertainment #TrendingShow #ViralVideo"
        thumb_prompt = f"Vibrant 8K 3D animated colorful cartoon poster for '{clean_title[:35]}', joyful cartoon expressions, bright magical studio lighting, 16:9."
    elif any(k in t_lower for k in ['kapil', 'comedy', 'funny', 'laugh', 'joke', 'hasna', 'standup', 'prank']):
        genre = "Comedy / Talk Show"
        safe_titles = [
            f"😂 {clean_title} | Best Uncut Funny Moments",
            f"🤣 Comedy Special | {clean_title[:45]} (Full Laugh Attack)",
            f"🔥 Non-Stop Comedy Scene | {clean_title[:50]}"
        ]
        hashtags = "#Comedy #FunnyVideo #StandupComedy #HindiComedy #ViralShow #LaughOutLoud"
        thumb_prompt = f"Ultra realistic 8K YouTube thumbnail for comedy show scene '{clean_title[:35]}', comedian laughing happily on stage, bright cinematic studio lights, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana', 'singer']):
        genre = "Music / Lo-Fi Audio"
        safe_titles = [
            f"🎧 {clean_title} (Slowed + Reverb Lo-Fi Remix) | Midnight Chill",
            f"🌙 {clean_title} | Deep Relaxing Vibe (Lofi Master HD)",
            f"✨ Pure Nostalgia Vibes | {clean_title[:45]} (Slowed Version)"
        ]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio #MidnightVibes"
        thumb_prompt = f"Anime aesthetic 4K Lo-Fi wallpaper thumbnail for song '{clean_title[:35]}', neon cozy bedroom, rain outside window, 16:9."
    elif any(k in t_lower for k in ['trailer', 'teaser', 'promo', 'first look', 'movie', 'film', 'cinema', 'action']):
        genre = "Official Trailer / Teaser Breakdown"
        safe_titles = [
            f"🔥 {clean_title} - Full Story & Climax Explained",
            f"⚡ {clean_title} - Hidden Details & Breakdown You Missed!",
            f"😱 {clean_title} - Big Twist & Action Breakdown Reaction"
        ]
        hashtags = "#TrailerBreakdown #MovieTrailer #Blockbuster #CinemaLovers #MovieRecap"
        thumb_prompt = f"Hyper-realistic 8K cinematic movie poster thumbnail for '{clean_title[:35]}', action hero in intense dramatic lighting, cinematic sparks and explosion, 16:9."
    else:
        genre = "Blockbuster Movie Scene"
        safe_titles = [
            f"🔥 {clean_title} - Ultimate Climax Scene",
            f"⚡ {clean_title} - Unstoppable Action & Best Moments",
            f"😱 The Most Dramatic Scene of {clean_title[:40]} | Full HD Recap"
        ]
        hashtags = "#MovieRecap #ActionMovie #CinemaLovers #Blockbuster #ViralClip"
        thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', hero dramatic intense face, cinematic color grading, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

# ==========================================
# 6. FAIL-SAFE ULTRAFAST ANTI-COPYRIGHT ENGINE
# ==========================================
def apply_anti_copyright_shield(in_video, out_video, style_mode, audio_mode):
    ffmpeg_exe = get_ffmpeg()
    
    probe_cmd = [ffmpeg_exe, "-i", in_video]
    probe_res = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    has_audio = "Audio:" in probe_res.stderr

    if "پرو ایڈیٹر" in style_mode or "Pro Editor" in style_mode:
        vf_filter = (
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "setpts=0.96*PTS,hflip,crop=iw*0.84:ih*0.84,scale=1280:720,"
            "eq=contrast=1.12:saturation=1.18:brightness=0.02,"
            "drawbox=y=ih-85:color=black@0.75:width=iw:height=70:t=fill,"
            "noise=alls=7:allf=t"
        )
    else:
        vf_filter = (
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "setpts=0.96*PTS,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,"
            "eq=contrast=1.12:saturation=1.18:brightness=0.02,"
            "drawbox=y=ih-90:color=black@0.70:width=iw:height=75:t=fill,"
            "noise=alls=7:allf=t"
        )

    if has_audio:
        if "75%" in audio_mode or "خاموش" in audio_mode:
            af_filter = "volume=0.30,atempo=1.0416,asetrate=44100*0.96,aresample=44100,bass=g=5:f=110"
        elif "Deep" in audio_mode or "بھاری" in audio_mode:
            af_filter = "atempo=1.0416,asetrate=44100*0.90,aresample=44100,bass=g=5:f=120"
        else:
            af_filter = "atempo=1.0416,asetrate=44100*1.04,aresample=44100,bass=g=3:f=110"
            
        cmd = [
            ffmpeg_exe, "-y", "-threads", "0", "-i", in_video,
            "-vf", vf_filter,
            "-af", af_filter,
            "-r", "25",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", out_video
        ]
    else:
        cmd = [
            ffmpeg_exe, "-y", "-threads", "0", "-i", in_video,
            "-vf", vf_filter,
            "-r", "25",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", out_video
        ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if not (os.path.exists(out_video) and os.path.getsize(out_video) > 10000):
        fallback_vf = "scale=1280:720,hflip,eq=contrast=1.08:saturation=1.12"
        fallback_cmd = [
            ffmpeg_exe, "-y", "-threads", "0", "-i", in_video,
            "-vf", fallback_vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
            "-pix_fmt", "yuv420p", "-c:a", "aac", out_video
        ]
        subprocess.run(fallback_cmd)

    return os.path.exists(out_video) and os.path.getsize(out_video) > 10000

# ==========================================
# 7. AI DIRECTOR & CINEMATIC HELPERS
# ==========================================
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
            "1. Explicitly identify the main subjects.\n"
            "2. Do NOT blend genders.\n"
            "3. Ensure anatomical perfection.\n"
            "4. Output ONLY the English translation and visual descriptions."
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
            "STRICTLY NO human faces, NO visible bodies, NO portraits, NO human figures. "
            "Pure sacred light, beautiful symbolic representation."
        )
        return True, safe_prompt
    return False, scene_text_en

def generate_enhanced_cinematic_prompt(urdu_scene, char_memory, scene_memory, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        scene_lower = urdu_scene.lower()
        gender_booster = ""
        
        if character_heritage == "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)":
            if any(k in scene_lower for k in ["صبا", "saba", "woman", "female", "girl"]):
                gender_booster = (
                    "beautiful elegant Eastern Pakistani Punjabi Pathan woman, realistic South Asian sharp facial features, "
                    "wearing traditional modest cotton Shalwar Kameez with a clean modest Dupatta elegantly draped over her head as a hijab, "
                    "extremely realistic, 8k resolution, highly detailed, strictly no western look, modest posture"
                )
            elif any(k in scene_lower for k in ["عیسی", "essa", "man", "male", "boy"]):
                gender_booster = (
                    "handsome majestic Eastern Pakistani Punjabi Pathan man, highly realistic South Asian facial structure, "
                    "wearing a traditional modest cotton Shalwar Kameez with high collar, neat short Islamic beard, "
                    "strictly no western look, photorealistic, 8k resolution"
                )
            else:
                gender_booster = (
                    "traditional modest Eastern Islamic attire, Shalwar Kameez, modest clothing, "
                    "Pakistani/Arabian traditional South Asian features, strictly no western exposure"
                )
        elif character_heritage == "Ancient Arabian":
            gender_booster = "wearing ancient traditional Arabian flowing historical robes, classic desert turban, Middle Eastern facial features"
        elif character_heritage == "Western / Modern":
            gender_booster = "modern stylish contemporary Western clothing, jeans and jacket"
        elif character_heritage == "Far Eastern":
            gender_booster = "traditional East Asian oriental attire"

        instruction = (
            "You are an expert Hollywood visual artist and prompt engineer. Analyze the Urdu scene and write a descriptive English prompt for Flux.\n"
            "STRICT RULES: Gender separation, no female beards, modest attire, no human depictions for sacred Islamic topics. Output ONLY final prompt."
        )
        
        prompt_input = f"Urdu Scene: {urdu_scene}\n"
        if char_memory: prompt_input += f"Character Memory: {char_memory}\n"
        if gender_booster: prompt_input += f"Attire tags: {gender_booster}\n"
        if scene_memory: prompt_input += f"Scene Memory: {scene_memory}\n"
        if raw_male_url: prompt_input += f"Male reference image URL: {raw_male_url}\n"
        if raw_female_url: prompt_input += f"Female reference image URL: {raw_female_url}\n"

        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' ' + prompt_input)}?model=openai"
        res = session.get(url, timeout=20)
        if res.status_code == 200:
            refined_p = res.text.strip()
            return re.sub(r'^(prompt:|visual prompt:|cinematic prompt:)\s*', '', refined_p, flags=re.IGNORECASE)
    except Exception:
        pass
    return f"Cinematic film scene: {urdu_scene}, highly detailed, 8k"

def apply_color_lut_harmony(img_path, style_preset):
    try:
        if not os.path.exists(img_path): return
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
    elif any(k in text for k in ["forest", "jungle", "birds", "nature", "درخت", "جنگل"]):
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
        if not os.path.exists(img_path): return
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

def parallel_download_flux_images(urls, paths):
    def download_single(url, path):
        try:
            res = session.get(url, timeout=40)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception:
            pass
        try:
            im = Image.new("RGB", (1280, 720), color=(20, 24, 33))
            im.save(path, "JPEG")
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

# ALL 25+ HOLLYWOOD CAMERA MOTIONS
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_path, "JPEG")
            
        scale_factor = 1.30
        base_clip = ImageClip(img_path).set_duration(duration).set_fps(24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = base_clip.resize((cw, ch))
        
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
        elif motion in ["Dolly In", "Push In"]:
            animated_clip = clip.resize(lambda t: 1.0 + 0.25 * (t / duration)).set_position('center')
        elif motion in ["Dolly Out", "Pull Out"]:
            animated_clip = clip.resize(lambda t: 1.25 - 0.25 * (t / duration)).set_position('center')
        elif motion in ["Orbit Camera", "Arc Shot"]:
            animated_clip = clip.rotate(lambda t: -3 + 6 * (t / duration)).resize(lambda t: 1.1 + 0.1 * (t / duration)).set_position('center')
        elif motion == "Crane Shot":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (t / duration)))).rotate(lambda t: -2 * (t / duration))
        elif motion == "Drone Shot":
            animated_clip = clip.resize(lambda t: 1.30 - 0.30 * (t / duration)).rotate(lambda t: 5 * (t / duration)).set_position('center')
        elif motion in ["Tracking Shot", "Follow Shot"]:
            animated_clip = clip.set_position(lambda t: (
                int((w - cw) * (t / duration)),
                int((h - ch)/2 + (5 * np.sin(2 * np.pi * t * 1.5)))
            ))
        elif motion in ["Handheld Camera", "Shoulder Camera"]:
            animated_clip = clip.set_position(lambda t: (
                int((w - cw)/2 + (8 * np.sin(2 * np.pi * t * 2.0))),
                int((h - ch)/2 + (6 * np.cos(2 * np.pi * t * 1.7)))
            )).rotate(lambda t: 1.5 * np.sin(2 * np.pi * t * 1.0))
        elif motion == "Cinematic Reveal":
            animated_clip = clip.set_position(lambda t: ('center', int((h - ch) * (1 - t / duration))))
        elif motion == "Whip Pan":
            animated_clip = clip.set_position(lambda t: (int((w - cw) * ((t / duration) ** 3)), 'center'))
        elif motion in ["Parallax Motion", "Ken Burns Effect"]:
            animated_clip = clip.resize(lambda t: 1.05 + 0.15 * (t / duration)).set_position(lambda t: (int((w - cw) * (t / duration)), 'center'))
        else:
            animated_clip = clip.resize(lambda t: 1.10 - 0.10 * (t / duration)).set_position('center')

        return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
    except Exception:
        return ImageClip(img_path).set_duration(duration).resize((w, h))

def apply_clip_transition(clip, transition, duration):
    try:
        if clip is not None:
            if transition == "Cross Dissolve (Fade)":
                return clip.fadein(0.4).fadeout(0.4)
            elif transition == "Flash Transition (White Glow)":
                return clip.fadein(0.2).fadeout(0.2)
            elif transition == "Film Dissolve (Muted)":
                return clip.fadein(0.3).fadeout(0.3)
    except Exception:
        pass
    return clip

def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        res = session.get(url, timeout=30)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

def save_audio_safe(text, voice, rate, pitch, filename):
    try:
        async def amain():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(filename)
        asyncio.run(amain())
        return True
    except Exception:
        return False

# ==========================================
# 8. MASTER V40 RENDER SYSTEM CORE
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free & Unlimited)", pollinations_key="", video_model="wan-fast", advanced_params=None):
    u_id = str(uuid.uuid4())[:8]
    
    global active_renderers
    with render_lock:
        active_renderers += 1
        my_pos = active_renderers
        
    status = st.empty()
    if my_pos > 2:
        status.info(f"⏳ Waiting in Queue... Your Position: #{my_pos - 2}")
        
    with render_semaphore:
        with render_lock:
            active_renderers -= 1
            
        progress_bar = st.progress(0.0)
        audio_file = f"a_{u_id}.mp3"
        bg_music_f = f"bg_{u_id}.mp3"
        generated_images = []
        generated_prompts = []
        temporary_audio_tracks = []
        has_bg_music = False
        
        user_db = get_user_data(st.session_state.logged_in_user)
        if not user_db:
            st.error("Authentication Error. Please login again.")
            return "Error"
        
        user_id = user_db["id"]
        user_credits = user_db["credits"]
        
        if user_credits < 15:
            st.error("Deduction failed: Sglowina requires at least 15 credits to generate video.")
            return "Error"
        
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
            
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
            if not sentences: sentences = [story]
            
            clips = []
            
            for idx, scene in enumerate(sentences):
                if any(k in scene.lower() for k in ["صبا", "saba"]):
                    v_code_scene = "ur-PK-UzmaNeural"
                elif any(k in scene.lower() for k in ["عیسی", "essa", "awan"]):
                    v_code_scene = "ur-PK-AsadNeural"
                else:
                    v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
                    
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path)
                temporary_audio_tracks.append(sub_audio_path)
                
            progress_bar.progress(0.15)
            
            if enable_bg_music:
                status.info("🎵 Downloading Atmospheric Background Track...")
                story_lower = story.lower()
                is_horror = any(k in story_lower for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "grave", "horror", "ghost", "dark"])
                is_epic = any(k in story_lower for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "king", "warrior", "palace", "empire"])
                
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3" if is_horror else (
                    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3" if is_epic else "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                )
                try:
                    res_bg = session.get(bg_url, timeout=12)
                    if res_bg.status_code == 200:
                        with open(bg_music_f, 'wb') as f:
                            f.write(res_bg.content)
                        has_bg_music = True
                except Exception:
                    pass
                    
            res_map = {
                "YouTube (16:9)": (1280, 720), 
                "TikTok/Reels (9:16)": (720, 1280), 
                "Instagram (1:1)": (720, 720),
                "CinemaScope (21:9)": (1680, 720),
                "Standard Box (4:3)": (1024, 768)
            }
            w, h = res_map[ratio]
            w, h = make_even(w), make_even(h)
            
            flux_prompt_urls = []
            img_paths = []
            
            for i, scene in enumerate(sentences):
                english_scene = translate_ur_to_en_enhanced(scene)
                is_spiritual = False
                if enable_islamic_filter:
                    is_spiritual, safe_scene_en = apply_islamic_safety_filter(english_scene, scene)
                    if is_spiritual: english_scene = safe_scene_en
                
                dir_settings = analyze_scene_for_director(english_scene)
                if camera_motion != "AI Hollywood Director (Auto)":
                    dir_settings["motion"] = camera_motion
                
                refined_p = generate_enhanced_cinematic_prompt(
                    urdu_scene=scene, char_memory=char_desc, scene_memory=scene_desc,
                    character_heritage=character_heritage, enable_islamic_filter=enable_islamic_filter,
                    raw_male_url=raw_male_url, raw_female_url=raw_female_url
                )
                
                if not is_spiritual:
                    refined_p += " [Avoid cross-gender blending, absolutely no woman with beard, symmetrical eyes]"
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}"
                generated_prompts.append(refined_p)
                
                # Real AI Video Mode
                if "Real AI Video" in gen_mode and active_api_key:
                    status.info(f"🎥 Rendering 3D Video Frame {i+1} via {video_model}...")
                    aspect_param = "16:9" if "16:9" in ratio else "9:16"
                    motion_prompt = f"high motion, dynamic realistic animation, {refined_p[:350]}"
                    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt)}?model={video_model}&aspectRatio={aspect_param}&key={active_api_key}&duration=4"
                    ref_url = raw_female_url if "saba" in scene.lower() else raw_male_url
                    if ref_url: vid_url += f"&image={urllib.parse.quote(ref_url)}"
                    
                    vid_path = f"v_{u_id}_{i}.mp4"
                    try:
                        res_vid = session.get(vid_url, timeout=90)
                        if res_vid.status_code == 200 and len(res_vid.content) > 50000:
                            with open(vid_path, "wb") as f_vid:
                                f_vid.write(res_vid.content)
                            dur_per = 4.0
                            clip = VideoFileClip(vid_path).resize((w, h)).set_duration(dur_per)
                            clip = apply_clip_transition(clip, transition_style, dur_per)
                            clips.append(clip)
                            generated_images.append(vid_path)
                            continue
                    except Exception:
                        pass
                
                w_target, h_target = make_even(w * 1.25), make_even(h * 1.25)
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_path = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_path)
                generated_images.append(img_path)
                
            progress_bar.progress(0.35)
            status.info("🎨 Rendering High-Definition Visual Frames...")
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.55)
            status.info("🎞️ Assembling Synchronized Audio and Motions...")
            
            for i, scene in enumerate(sentences):
                if len(clips) > i:
                    continue
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                
                apply_color_lut_harmony(img_path, style)
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                
                english_scene_temp = translate_ur_to_en_enhanced(scene)
                dir_settings = analyze_scene_for_director(english_scene_temp)
                active_motion = camera_motion if camera_motion != "AI Hollywood Director (Auto)" else dir_settings["motion"]
                
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h)
                
                sfx_file = download_scene_sfx(scene, u_id, i)
                if sfx_file and os.path.exists(sfx_file):
                    try:
                        sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                        clip = clip.set_audio(CompositeAudioClip([scene_voice_clip, sfx_audio]))
                        generated_images.append(sfx_file)
                    except Exception:
                        clip = clip.set_audio(scene_voice_clip)
                else:
                    clip = clip.set_audio(scene_voice_clip)
                    
                clip = apply_clip_transition(clip, transition_style, dur_scene)
                clips.append(clip)
                
            progress_bar.progress(0.75)
            status.info("🎞️ Final Master Video Stitching...")
            
            final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
            
            if has_bg_music and os.path.exists(bg_music_f):
                try:
                    bg_track = AudioFileClip(bg_music_f).volumex(0.06).set_duration(final_video.duration)
                    final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                except Exception:
                    pass
                    
            out_name = f"Sglowina_{u_id}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"], logger=None)
            final_video.close()
            
            for sub_voice in temporary_audio_tracks:
                if os.path.exists(sub_voice): os.remove(sub_voice)
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for file_p in generated_images:
                if os.path.exists(file_p): os.remove(file_p)
                
            progress_bar.progress(1.0)
            status.success("🚀 Video Generated Successfully!")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (id, user_id, project_name, type, file_path, prompt, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (u_id, user_id, f"Video Project {u_id}", "Video", out_name, " | ".join(generated_prompts), time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            
            deduct_user_credits(st.session_state.logged_in_user, 15)
            log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
            
            return out_name
        except Exception as e:
            for sub_voice in temporary_audio_tracks:
                if os.path.exists(sub_voice): os.remove(sub_voice)
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for file_p in generated_images:
                if os.path.exists(file_p): os.remove(file_p)
            progress_bar.empty()
            return f"Error Details: {e}"
        finally:
            gc.collect()

# ==========================================
# 9. UI & PREMIUM BRANDING STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    .glow-title { 
        font-size: 2.2rem; 
        font-weight: 900; 
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 15px rgba(255, 0, 122, 0.2);
        margin-top: 10px;
        margin-bottom: 5px;
        letter-spacing: 2px;
    }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 10px 0; }
    
    .circular-s {
        width: 100px; height: 100px; 
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 42px; color: #ffffff !important;
        border: 4px solid #ffffff !important;
        box-shadow: 0 0 40px #ff007a, inset 0 0 15px #ffffff;
    }

    .stButton>button { 
        background: #000000 !important; 
        color: white !important; 
        border-radius: 12px !important; 
        height: 55px; 
        width: 100%; 
        font-size: 20px; 
        font-weight: bold; 
        border: none; 
    }
    
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #e2e8f0; 
    }
    [data-testid="stSidebar"] * { 
        color: #000000 !important; 
        font-weight: bold !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA & ES AI STUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">ES</div></div>', unsafe_allow_html=True)

# ==========================================
# 10. SEAMLESS AR LIVE VIEWPORT HTML5 ENGINE
# ==========================================
def render_autonomous_live_viewport():
    viewport_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background: transparent; display: flex; justify-content: center; }
            
            .viewport-container {
                width: 100%;
                max-width: 480px;
                height: 520px;
                background: #000;
                border-radius: 28px;
                position: relative;
                overflow: hidden;
                box-shadow: 0 12px 35px rgba(0,0,0,0.5), 0 0 20px rgba(245, 158, 11, 0.3);
                border: 3px solid #f59e0b;
            }

            #liveVideo {
                width: 100%;
                height: 100%;
                object-fit: cover;
                transform: scaleX(-1);
            }

            .hud-header {
                position: absolute;
                top: 14px;
                left: 14px;
                right: 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 10;
            }
            .hud-badge {
                background: rgba(0, 0, 0, 0.75);
                backdrop-filter: blur(8px);
                border: 1px solid #10b981;
                color: #10b981;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 800;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .pulse-dot {
                width: 8px;
                height: 8px;
                background: #10b981;
                border-radius: 50%;
                animation: livePulse 1.5s infinite;
            }

            .mascot-overlay {
                position: absolute;
                bottom: 85px;
                right: 14px;
                width: 110px;
                height: 130px;
                z-index: 15;
                pointer-events: none;
            }
            .fluffy-body {
                width: 100px;
                height: 115px;
                background: radial-gradient(circle at 35% 30%, #fef3c7, #fde68a 60%, #f59e0b 100%);
                border-radius: 50px 50px 45px 45px;
                position: relative;
                box-shadow: 0 8px 20px rgba(0,0,0,0.4);
                animation: mascotBounce 2.5s infinite ease-in-out alternate;
            }
            .ear {
                width: 24px;
                height: 30px;
                background: #f59e0b;
                border-radius: 50%;
                position: absolute;
                top: -6px;
            }
            .ear-l { left: 8px; transform: rotate(-20deg); }
            .ear-r { right: 8px; transform: rotate(20deg); }
            .sleep-mask {
                width: 70px;
                height: 22px;
                background: #fed7aa;
                border-radius: 12px;
                position: absolute;
                top: 10px;
                left: 15px;
                border: 1.5px solid #f97316;
            }
            .face-box {
                width: 80px;
                height: 65px;
                background: #fffbeb;
                border-radius: 50%;
                position: absolute;
                top: 32px;
                left: 10px;
            }
            .eye-row {
                display: flex;
                justify-content: space-around;
                width: 46px;
                position: absolute;
                top: 20px;
                left: 17px;
            }
            .eye-dot {
                width: 8px;
                height: 6px;
                background: #451a03;
                border-radius: 0 0 8px 8px;
                animation: eyeBlink 3.5s infinite;
            }
            .blush-dot {
                width: 12px;
                height: 6px;
                background: #fca5a5;
                border-radius: 50%;
                position: absolute;
                top: 26px;
            }
            .blush-l { left: 6px; }
            .blush-r { right: 6px; }
            .mascot-mouth {
                width: 14px;
                height: 6px;
                background: #e11d48;
                border-radius: 0 0 8px 8px;
                position: absolute;
                bottom: 16px;
                left: 33px;
                transition: all 0.15s ease;
            }
            .speaking .mascot-mouth {
                animation: mouthMove 0.25s infinite alternate;
            }
            .speaking .fluffy-body {
                animation: speakingBounce 0.3s infinite alternate;
            }

            .subtitle-bar {
                position: absolute;
                bottom: 14px;
                left: 14px;
                right: 14px;
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 16px;
                padding: 10px 16px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                text-align: right;
                direction: rtl;
                z-index: 10;
                min-height: 48px;
                display: flex;
                align-items: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            }

            .start-overlay {
                position: absolute;
                inset: 0;
                background: rgba(0,0,0,0.88);
                backdrop-filter: blur(10px);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 30;
                padding: 20px;
                text-align: center;
            }
            .start-btn {
                background: linear-gradient(45deg, #f59e0b, #ec4899);
                color: #000000;
                border: none;
                padding: 16px 32px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: 900;
                cursor: pointer;
                box-shadow: 0 0 25px rgba(245, 158, 11, 0.6);
                transition: 0.3s;
                margin-top: 15px;
            }
            .start-btn:hover { transform: scale(1.05); }

            @keyframes livePulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.2); } }
            @keyframes mascotBounce { 0% { transform: translateY(0); } 100% { transform: translateY(-8px); } }
            @keyframes speakingBounce { 0% { transform: scale(1); } 100% { transform: scale(1.05) translateY(-4px); } }
            @keyframes eyeBlink { 0%, 90%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.1); } }
            @keyframes mouthMove { 0% { height: 4px; border-radius: 0 0 4px 4px; } 100% { height: 18px; border-radius: 8px; transform: scaleX(1.3); } }
        </style>
    </head>
    <body>
        <div class="viewport-container">
            <video id="liveVideo" autoplay playsinline></video>

            <div class="hud-header">
                <div class="hud-badge"><div class="pulse-dot"></div> <span id="statusLabel">STANDBY</span></div>
                <div style="background:rgba(0,0,0,0.6); padding:5px 12px; border-radius:20px; font-size:12px; color:#f59e0b; font-weight:800;">🧸 MUSE AI</div>
            </div>

            <div class="mascot-overlay" id="mascotBox">
                <div class="fluffy-body">
                    <div class="ear ear-l"></div>
                    <div class="ear ear-r"></div>
                    <div class="sleep-mask"></div>
                    <div class="face-box">
                        <div class="blush-dot blush-l"></div>
                        <div class="blush-dot blush-r"></div>
                        <div class="eye-row">
                            <div class="eye-dot"></div>
                            <div class="eye-dot"></div>
                        </div>
                        <div class="mascot-mouth"></div>
                    </div>
                </div>
            </div>

            <div class="subtitle-bar" id="subtitles">
                السلام علیکم! نیچے "Start Live Companion" دبائیں، میں کیمرے سے دیکھ کر لائیو بولوں گا!
            </div>

            <div class="start-overlay" id="startScreen">
                <div style="font-size:45px; margin-bottom:10px;">🧸</div>
                <h3 style="color:#ffffff; font-weight:900; margin-bottom:5px;">MUSE Live Vision Companion</h3>
                <p style="color:#94a3b8; font-size:13px; max-width:280px;">موبائل کیمرہ لائیو رہے گا اور AI بغیر بٹن دبائے خودکار اردو بولے گا!</p>
                <button class="start-btn" onclick="startAutonomousMUSE()">🚀 Start Live Companion</button>
            </div>
        </div>

        <canvas id="frameCanvas" style="display:none;"></canvas>

        <script>
            let video = document.getElementById('liveVideo');
            let startScreen = document.getElementById('startScreen');
            let mascotBox = document.getElementById('mascotBox');
            let subtitles = document.getElementById('subtitles');
            let statusLabel = document.getElementById('statusLabel');
            let recognition = null;
            let isScanning = false;
            let autoScanTimer = null;

            async function startAutonomousMUSE() {
                try {
                    startScreen.style.display = 'none';
                    statusLabel.innerText = "CONNECTING...";
                    
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "environment", width: 640, height: 480 },
                        audio: false
                    });
                    video.srcObject = stream;
                    statusLabel.innerText = "AUTONOMOUS LIVE";
                    
                    speakUrdu("السلام علیکم! میں آپ کا پیارا AI دوست ہوں۔ کیمرہ لائیو ہے، آپ جو پوچھیں میں دیکھ کر بتاؤں گا!");
                    startSpeechListener();
                    
                    autoScanTimer = setInterval(() => {
                        if (!isScanning) {
                            captureAndAnalyze("Describe what is in front of the camera in friendly Urdu.");
                        }
                    }, 8000);
                } catch (e) {
                    alert("کیمرہ پرمیشن الاؤ کریں: " + e.message);
                }
            }

            function startSpeechListener() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) return;

                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.lang = 'ur-PK';

                recognition.onresult = async function(event) {
                    let lastIdx = event.results.length - 1;
                    let spoken = event.results[lastIdx][0].transcript;
                    subtitles.innerText = "👂 آپ: " + spoken;
                    await captureAndAnalyze(spoken);
                };

                recognition.onerror = function() { try { recognition.start(); } catch(e){} };
                recognition.onend = function() { try { recognition.start(); } catch(e){} };
                recognition.start();
            }

            async function captureAndAnalyze(promptText) {
                if (isScanning) return;
                isScanning = true;

                let canvas = document.getElementById('frameCanvas');
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                let ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                let base64Img = canvas.toDataURL('image/jpeg', 0.75).split(',')[1];

                try {
                    let res = await fetch("https://text.pollinations.ai/openai", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            model: "openai",
                            messages: [
                                {
                                    role: "user",
                                    content: [
                                        { 
                                            type: "text", 
                                            text: "You are a super cute, friendly AI mascot in a real-time live vision session. Look at this camera frame and explain directly in fluent, sweet, natural Urdu (اردو). Explain vehicles, tractors, objects, people or surroundings in 2 sweet concise sentences: " + promptText 
                                        },
                                        { 
                                            type: "image_url", 
                                            image_url: { url: "data:image/jpeg;base64," + base64Img } 
                                        }
                                    ]
                                }
                            ]
                        })
                    });

                    let reply = await res.text();
                    subtitles.innerText = "🧸: " + reply;
                    speakUrdu(reply);
                } catch (err) {
                } finally {
                    isScanning = false;
                }
            }

            function speakUrdu(text) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utter = new SpeechSynthesisUtterance(text);
                    utter.lang = 'ur-PK';
                    utter.rate = 1.0;
                    utter.pitch = 1.15;

                    utter.onstart = function() { mascotBox.classList.add('speaking'); };
                    utter.onend = function() { mascotBox.classList.remove('speaking'); };
                    utter.onerror = function() { mascotBox.classList.remove('speaking'); };

                    window.speechSynthesis.speak(utter);
                }
            }
        </script>
    </body>
    </html>
    """
    st.components.v1.html(viewport_html, height=540)

# ==========================================
# 11. NAVIGATION TABS (ALL 7 TABS)
# ==========================================
tab_auth, tab_companion, tab_es_tools, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Auth",
    "🧸 Live AR Companion (لائیو ویژن)",
    "⚡ ES Video Processor (اینٹی کاپی رائٹ اسٹوڈیو)",
    "🎬 Pro Master Studio", 
    "🎨 Pro Image Studio",
    "💬 Electric AI Chat", 
    "👤 Enterprise Center"
])

# -----------------
# TAB 1: AUTHENTICATION
# -----------------
with tab_auth:
    st.write("### 🔑 Sglowina Secure Authentication Portal")
    auth_mode = st.radio("Choose Action", ["Sign In", "Create New Account"], key="auth_mode_choice")
    
    if auth_mode == "Sign In":
        with st.form("login_form"):
            u_name = st.text_input("Username", key="login_u_name")
            p_word = st.text_input("Password", type="password", key="login_p_word")
            btn_login = st.form_submit_button("Sign In 🚀")
            if btn_login:
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    if st.session_state.logged_in_user in ["essasaba", "essa_awan", "saba_wahid"]:
                        st.success("Welcome back to SGLOWINA & ES AI, Muhammad Essa Awan & Saba Wahid! (Admin Authorized) 🟢")
                    else:
                        st.success(f"Welcome to SGLOWINA AI, {u_name}! (Authorized User) 🟢")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    else:
        with st.form("reg_form"):
            new_u = st.text_input("Choose Username", key="reg_new_u")
            new_e = st.text_input("Email Address", key="reg_new_e")
            new_p = st.text_input("Password", type="password", key="reg_new_p")
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
# TAB 2: LIVE AR COMPANION
# -----------------
with tab_companion:
    render_autonomous_live_viewport()

# -----------------
# TAB 3: ES VIDEO PROCESSOR (PRO AUDIO DUCKING & ANTI-COPYRIGHT)
# -----------------
with tab_es_tools:
    st.write("### ⚡ ES ہالی ووڈ الٹرا ڈسرپشن و آڈیو ڈکنگ شیلڈ (100% Anti-Copyright)")
    st.info("💡 **تمام سوشل لنکس سپورٹڈ:** یوٹیوب، پن ٹریسٹ، ٹک ٹاک، انسٹاگرام، فیس بک یا موٹو پتلو و کارٹونز۔ فائل اپلوڈ کریں یا لنک درج کریں۔")
    
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "🎬 1. فل ویڈیو / مووی / ٹریلر موڈ",
        "⚔️ 2. کلپ کٹر موڈ (10 منٹ کٹ)",
        "🎧 3. گانے اور لوفی (Slowed + Reverb)"
    ])
    
    with sub_t1:
        st.subheader("پوری ویڈیو / شو / ٹریلر پر آڈیو ڈکنگ اور پرو شیلڈ لگائیں")
        
        c_mode1, c_mode2 = st.columns(2)
        with c_mode1:
            style_choice = st.selectbox("حفاظتی ویژول اسٹائل:", [
                "👑 100% پرو ایڈیٹر موڈ (1.8° Tilt + Canvas Frame + Text Shield Banner)",
                "⚡ الٹرا فل اسکرین اینٹی ہیش (1.8° Tilt + Deep 80% Zoom + Film Grain)"
            ], key="s_t1_choice")
        with c_mode2:
            audio_shield = st.selectbox("میوزک اور آواز کا حل (Audio Music Ducking):", [
                "🔇 اصل میوزک 75% خاموش (Ducking) + نیا سنیمٹک ٹریک مکس (100% پکا حل)",
                "🔊 بھاری اور گہری موٹی آواز (Deep Pitch 0.90x)",
                "🎵 1.08x اسپیڈ پچ ماڈیولیشن"
            ], key="ap_t1_choice")
        
        upload_opt1 = st.file_uploader("📂 اپنے موبائل سے ویڈیو/ٹریلر اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi"], key="up_t1_file")
        url_input_1 = st.text_input("🔗 یا کسی بھی پلیٹ فارم کا لنک درج کریں (YouTube, TikTok, Insta, Pinterest, Cartoons):", placeholder="https://...", key="url_t1_input")
        
        if st.button("🚀 الٹرا اینٹی کاپی رائٹ شیلڈ لگائیں", type="primary", key="run_t1_btn"):
            uid = str(uuid.uuid4())[:8]
            dyn_in = f"temp_in_{uid}.mp4"
            dyn_out = f"es_shielded_{uid}.mp4"
            info = {'title': 'Featured Movie Video'}
            has_input = False
            
            if upload_opt1 is not None:
                with open(dyn_in, "wb") as f:
                    f.write(upload_opt1.getvalue())
                has_input = True
                info['title'] = upload_opt1.name
            elif url_input_1.strip():
                with st.spinner("سوشل میڈیا سے اصل ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    success, info = inspect_and_fetch_media_universal(url_input_1.strip(), dyn_in)
                    if success and os.path.exists(dyn_in) and os.path.getsize(dyn_in) > 10000:
                        has_input = True
                    else:
                        st.error("❌ ویڈیو ڈاؤنلوڈ نہیں ہو سکی۔ براہ کرم ویڈیو فائل ڈائریکٹ اپلوڈ کریں۔")
                        
            if has_input:
                with st.spinner("ویڈیو پر آڈیو ڈکنگ، میوزک میوٹنگ اور اینٹی ہیش بینر لگ رہا ہے..."):
                    ok = apply_anti_copyright_shield(dyn_in, dyn_out, style_choice, audio_shield)
                    if ok and os.path.exists(dyn_out):
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = dyn_out
                        st.session_state.process_ready = True
                    else:
                        st.error("❌ ویڈیو پروسیسنگ فیل ہو گئی۔ فائل فارمیٹ چیک کریں۔")
                        
                    if os.path.exists(dyn_in):
                        try: os.remove(dyn_in)
                        except Exception: pass
            else:
                st.error("❌ ویڈیو فائل اپلوڈ کریں یا درست لنک درج کریں۔")

    with sub_t2:
        st.subheader("ویڈیو یا شو سے 10 منٹ کا کلپ کاٹیں")
        c1, c2 = st.columns(2)
        with c1:
            scene_type = st.selectbox("سین کا آغاز:", ["⚔️ اہم سین / کلائمیکس (منٹ 30)", "👻 سسپنس موڑ (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2_scene")
        with c2:
            clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2_slider")
            
        start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10, key="num_t2_start")
        upload_opt2 = st.file_uploader("📂 اپنے موبائل سے ویڈیو فائل منتخب کریں:", type=["mp4", "mov", "mkv"], key="up_t2_file")
        url_input_2 = st.text_input("🔗 یا ویڈیو کا لنک درج کریں:", placeholder="https://...", key="url_t2_input")

        if st.button("🚀 کلپ کاٹیں اور آڈیو ڈکنگ لگائیں", type="primary", key="run_t2_btn"):
            uid = str(uuid.uuid4())[:8]
            dyn_in = f"temp_in_{uid}.mp4"
            dyn_out = f"es_clip_{uid}.mp4"
            info = {'title': 'Clip Highlight'}
            has_input = False
            
            if upload_opt2 is not None:
                with open(dyn_in, "wb") as f:
                    f.write(upload_opt2.getvalue())
                has_input = True
                info['title'] = upload_opt2.name
            elif url_input_2.strip():
                with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    success, info = inspect_and_fetch_media_universal(url_input_2.strip(), dyn_in)
                    if success: has_input = True

            if has_input:
                with st.spinner("کلپ کٹ کر کے آڈیو ڈکنگ اور پرو شیلڈ لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = start_min * 60
                    dur_sec = clip_len * 60
                    vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setpts=0.96*PTS,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,eq=contrast=1.12:saturation=1.18:brightness=0.02,drawbox=y=ih-85:color=black@0.75:width=iw:height=70:t=fill,noise=alls=7:allf=t"
                    af = "volume=0.35,atempo=1.0416,asetrate=44100*0.92,aresample=44100,bass=g=5:f=120"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-threads", "0", "-ss", str(start_sec), "-t", str(dur_sec),
                        "-i", dyn_in, "-vf", vf, "-af", af,
                        "-r", "25",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "128k", dyn_out
                    ]
                    subprocess.run(cmd)
                    if os.path.exists(dyn_out) and os.path.getsize(dyn_out) > 10000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = dyn_out
                        st.session_state.process_ready = True
                    else:
                        st.error("❌ ویڈیو ٹائم سیٹنگز چیک کریں۔")
                        
                    if os.path.exists(dyn_in):
                        try: os.remove(dyn_in)
                        except Exception: pass
            else:
                st.error("❌ ویڈیو اپلوڈ کریں یا درست لنک دیں۔")

    with sub_t3:
        st.subheader("گانے کا لنک ڈالیں اور وائرل Slowed + Reverb بنائیں")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3_slider")
        with col_s2:
            reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3_slider")
        with col_s3:
            bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3_slider")
            
        upload_opt3 = st.file_uploader("📂 آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3_file")
        song_url = st.text_input("🔗 یا گانے کا لنک یہاں پیسٹ کریں:", placeholder="https://...", key="url_t3_input")
        
        if st.button("🚀 گانے کو Slowed + Reverb بنائیں", type="primary", key="run_t3_btn"):
            uid = str(uuid.uuid4())[:8]
            dyn_in_song = f"temp_song_{uid}.mp4"
            dyn_out_song = f"lofi_song_{uid}.mp4"
            info = {'title': 'Lo-Fi Chill Track'}
            has_input = False
            
            if upload_opt3 is not None:
                with open(dyn_in_song, "wb") as f:
                    f.write(upload_opt3.getvalue())
                has_input = True
                info['title'] = upload_opt3.name
            elif song_url.strip():
                with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                    success, info = inspect_and_fetch_media_universal(song_url.strip(), dyn_in_song)
                    if success: has_input = True
                        
            if has_input:
                with st.spinner("لوفی گانا ماسٹر ہو رہا ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [
                        ffmpeg_exe, "-y", "-threads", "0", "-i", dyn_in_song,
                        "-af", af_filter, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", dyn_out_song
                    ]
                    subprocess.run(cmd_song)
                    if os.path.exists(dyn_out_song) and os.path.getsize(dyn_out_song) > 10000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = dyn_out_song
                        st.session_state.process_ready = True
                    else:
                        st.error("❌ آڈیو پروسیسنگ فیل ہو گئی۔")
                        
                    if os.path.exists(dyn_in_song):
                        try: os.remove(dyn_in_song)
                        except Exception: pass
            else:
                st.error("❌ آڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    if st.session_state.process_ready and st.session_state.current_output_video and os.path.exists(st.session_state.current_output_video):
        st.divider()
        st.success("🎉 ویڈیو 75% آڈیو ڈکنگ، بینر شیلڈ اور اینٹی کاپی رائٹ شیلڈ کے ساتھ تیار ہے:")
        
        with open(st.session_state.current_output_video, 'rb') as vf:
            video_bytes = vf.read()
            st.video(video_bytes)
            
            st.download_button(
                label="📥 یہاں کلک کر کے مکمل ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
                data=video_bytes,
                file_name=os.path.basename(st.session_state.current_output_video),
                mime="video/mp4",
                use_container_width=True,
                key="dl_processed_video_btn"
            )

        genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
        st.info(f"🎯 **AI نے پہچانا:** یہ ویڈیو **'{genre}'** کیٹگری کی ہے۔ (اصل نام: **{st.session_state.detected_info.get('title', 'Video')}**)")
        
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            st.markdown(f"### 🔥 وائرل ٹائٹلز ({genre}):")
            for i, t in enumerate(titles, 1):
                st.code(t, language="text")
            st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
            st.code(tags, language="text")

        with c_meta2:
            st.markdown("### 🎨 AI تھمب نیل پرامپٹ (Thumbnail Prompt):")
            st.info("💡 اسے Midjourney یا Bing Creator میں ڈال کر نیا تھمب نیل بنائیں۔")
            st.code(prompt, language="text")

# -----------------
# TAB 4: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    st.subheader("⚙️ AI Generation Mode")
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"], key="mv_gen_mode")
    pollinations_key = ""
    if "Real AI Video" in gen_mode:
        pollinations_key = st.text_input("Enter Pollinations API Key (sk_* or pk_*):", type="password", key="mv_api_key")

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے اور کھیت میں کام کر رہا ہے...", key="mv_script_input")
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True, key="mv_islamic_filter")
    
    char_desc = st.text_input("Character Memory (کردار کا حلیہ):", placeholder="e.g. Saba is wearing a modest dark blue hijab", key="mv_char_desc")
    
    st.write("##### 👤 Consistent Character Identity References (کرداروں کے چہروں کی تصاویر)")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Upload Male Character Reference Image:", type=["jpg", "png", "jpeg"], key="mv_up_male")
        if uploaded_male_img is not None:
            st.image(uploaded_male_img, caption="Male Identity Loaded ✅", width=120)
    with col_up2:
        uploaded_female_img = st.file_uploader("Upload Female Character Reference Image:", type=["jpg", "png", "jpeg"], key="mv_up_female")
        if uploaded_female_img is not None:
            st.image(uploaded_female_img, caption="Female Identity Loaded ✅", width=120)
        
    scene_desc = st.text_input("Scene Memory (ماحول):", placeholder="e.g. Deep green ancient forest, dark stormy night", key="mv_scene_desc")

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9, mc10 = st.columns(10)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv_voice_select")
    with mc2: mv_rate = st.selectbox("Speed:", ["+0% (Normal)", "+10% (Fast)", "-10% (Slow)"], key="mv_speed_select")
    with mc3: mv_pitch = st.selectbox("Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"], key="mv_pitch_select")
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"], key="mv_format_select")
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Dark Gothic / Mystery"], key="mv_style_select")
    with mc6: camera_motion = st.selectbox("Motion:", [
        "AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Pan Up", "Pan Down",
        "Dolly In", "Dolly Out", "Orbit Camera", "Crane Shot", "Drone Shot", "Tracking Shot", "Follow Shot", "Push In", "Pull Out",
        "Arc Shot", "Handheld Camera", "Shoulder Camera", "Cinematic Reveal", "Whip Pan", "Parallax Motion", "Ken Burns Effect"
    ], key="mv_motion_select")
    with mc7: transition_style = st.selectbox("Transition:", ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Film Dissolve (Muted)", "Instant Cut"], key="mv_trans_select")
    with mc8: character_heritage = st.selectbox("Heritage:", ["Automatic", "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)", "Ancient Arabian", "Western / Modern", "Far Eastern"], key="mv_heritage_select")
    with mc9: video_model = st.selectbox("AI Model:", ["wan-fast", "seedance", "veo"], key="mv_model_select")
    with mc10: sd = st.number_input("Seed:", value=786, key="mv_seed_select")
    
    if st.button("Generate Master Movie 🚀", key="mv_generate_btn"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map.get(mv_pitch, "+0Hz")
        
        with st.spinner("Generating Hollywood Master Film..."):
            out_v = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate=rate_val, pitch=pitch_val, ratio=mr,
                style=ms, seed=sd, char_desc=char_desc, scene_desc=scene_desc,
                camera_motion=camera_motion, transition_style=transition_style,
                enable_watermark=st.session_state.enable_watermark,
                enable_bg_music=st.session_state.enable_bg_music,
                uploaded_male_img=uploaded_male_img, uploaded_female_img=uploaded_female_img,
                enable_islamic_filter=enable_islamic_filter, character_heritage=character_heritage,
                gen_mode=gen_mode, pollinations_key=pollinations_key, video_model=video_model
            )
            if "Error" not in out_v and os.path.exists(out_v):
                with open(out_v, 'rb') as fv:
                    v_bytes = fv.read()
                    st.video(v_bytes)
                    st.download_button("📥 Download Cinematic Movie", data=v_bytes, file_name=out_v, mime="video/mp4", key="dl_movie_btn")
            else:
                st.error(f"❌ {out_v}")

# -----------------
# TAB 5: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Pro 8K Image Generation & Typography Studio")
    col_i1, col_i2 = st.columns([2, 1])
    with col_i1:
        img_prompt = st.text_area("Image Prompt (Urdu/English):", placeholder="e.g. A handsome Eastern warrior standing on mountain peak, dramatic volumetric lighting, 8k resolution", key="img_prompt_input")
        overlay_text = st.text_input("Overlay Banner Text (Canva Typography):", placeholder="e.g. EPISODE 1: THE BEGINNING", key="img_text_overlay")
    with col_i2:
        img_style = st.selectbox("Visual Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Dark Gothic / Mystery"], key="img_style_select")
        img_aspect = st.selectbox("Aspect Ratio:", ["16:9 (Landscape)", "9:16 (Story/Reel)", "1:1 (Square)", "21:9 (CinemaScope)"], key="img_aspect_select")
        img_seed = st.number_input("Random Seed:", value=random.randint(100, 99999), key="img_seed_input")
        
    if st.button("Generate 8K Image 🎨", key="img_generate_btn"):
        if img_prompt.strip():
            with st.spinner("Generating 8K Photorealistic Artwork..."):
                ar_map = {"16:9 (Landscape)": (1280, 720), "9:16 (Story/Reel)": (720, 1280), "1:1 (Square)": (1024, 1024), "21:9 (CinemaScope)": (1680, 720)}
                target_w, target_h = ar_map[img_aspect]
                img_data = fetch_img_failover(img_prompt, target_w, target_h, img_seed)
                if img_data:
                    temp_img = f"img_{uuid.uuid4().hex[:6]}.jpg"
                    with open(temp_img, "wb") as fi:
                        fi.write(img_data)
                    apply_color_lut_harmony(temp_img, img_style)
                    if overlay_text.strip():
                        apply_canva_typography(temp_img, overlay_text.strip())
                    st.image(temp_img, caption="Generated 8K Image", use_container_width=True)
                    with open(temp_img, "rb") as fi:
                        st.download_button("📥 Download 8K Image", data=fi.read(), file_name=temp_img, mime="image/jpeg", key="dl_img_btn")
                else:
                    st.error("Failed to generate image. Please check prompt.")
        else:
            st.warning("Please enter an image prompt.")

# -----------------
# TAB 6: ELECTRIC AI CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Electric AI Assistant")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_query = st.chat_input("Ask Sglowina AI anything (Urdu / English)...", key="chat_query_input")
    if user_query:
        st.session_state.msgs.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    sys_prompt = "You are Sglowina AI, an intelligent, helpful multilingual SaaS assistant created by Muhammad Essa Awan & Saba Wahid. Answer naturally in Urdu or English."
                    u_url = f"https://text.pollinations.ai/{urllib.parse.quote(sys_prompt + ' User query: ' + user_query)}?model=openai"
                    r = session.get(u_url, timeout=20)
                    reply = r.text.strip() if r.status_code == 200 else "I am here to assist you with all video and AI creation needs!"
                except Exception:
                    reply = "Sglowina AI is ready to generate your movies, bypass copyright, and handle media!"
                st.markdown(reply)
                st.session_state.msgs.append({"role": "assistant", "content": reply})

# -----------------
# TAB 7: ENTERPRISE CENTER & BILLING
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina SaaS & Enterprise Billing Hub")
    u_info = get_user_data(st.session_state.logged_in_user)
    
    if u_info:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("User", u_info["username"])
        c2.metric("Plan", u_info["plan"])
        c3.metric("Credits Left", u_info["credits"])
        c4.metric("Role", u_info["role"])
    
    st.divider()
    st.write("### 💳 Pakistani Direct Payment Gateways (EasyPaisa & JazzCash)")
    st.info("💡 رقم بھیجنے کے بعد نیچے اپنی Transaction ID درج کر کے فوری کریڈٹس ایکٹیویٹ کریں۔")
    
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown("""
        #### 🟢 EasyPaisa Account
        - **اکاؤنٹ ٹائٹل:** Saba Wahid (صبا واحد)
        - **اکاؤنٹ نمبر:** `0308-6834020`
        """)
    with p_col2:
        st.markdown("""
        #### 🔴 JazzCash Account
        - **اکاؤنٹ ٹائٹل:** Ayesha Bibi (عائشہ بی بی)
        - **اکاؤنٹ نمبر:** `0324-0755475`
        """)

    st.write("#### 📩 جمع شدہ پیمنٹ کی تصدیق (Submit TRX ID):")
    with st.form("trx_verify_form"):
        trx_method = st.selectbox("پیمنٹ کا طریقہ:", ["EasyPaisa", "JazzCash"], key="trx_method_select")
        trx_id_val = st.text_input("Transaction ID (TRX ID):", placeholder="e.g. 8492049281", key="trx_id_input")
        trx_amount = st.number_input("ادا کردہ رقم (PKR):", min_value=500, max_value=100000, value=2500, step=500, key="trx_amount_input")
        sub_trx_btn = st.form_submit_button("تصدیق کے لیے بھیجیں 🚀")
        if sub_trx_btn:
            if trx_id_val.strip():
                conn = get_db_connection()
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (str(uuid.uuid4())[:8], st.session_state.logged_in_user, trx_method, trx_id_val.strip(), trx_amount, "Pending", time.strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    st.success("✅ آپ کی Transaction ID درج ہو گئی ہے۔ ایڈمن فوری طور پر کریڈٹس جاری کر دے گا۔")
                except Exception:
                    st.error("❌ یہ TRX ID پہلے سے سسٹم میں موجود ہے۔")
                finally:
                    conn.close()
            else:
                st.warning("براہ کرم درست TRX ID درج کریں۔")

    st.write("#### 🎟️ کوپن کوڈ کلیم کریں (Claim Coupon):")
    c_code = st.text_input("Coupon Code:", placeholder="e.g. ESSASABA", key="coupon_input")
    if st.button("کوپن کوڈ لگائیں", key="claim_coupon_btn"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM coupons WHERE code = ? AND uses_left > 0", (c_code.strip().upper(),))
        row = cur.fetchone()
        if row:
            add_c = row["credits"]
            cur.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (c_code.strip().upper(),))
            cur.execute("UPDATE users SET credits = credits + ? WHERE LOWER(username) = LOWER(?)", (add_c, st.session_state.logged_in_user))
            conn.commit()
            st.success(f"🎉 مبارک ہو! آپ کو {add_c} کریڈٹس مل گئے ہیں!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ غلط یا زائد المعیاد کوپن کوڈ۔")
        conn.close()
