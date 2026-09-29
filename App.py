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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
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
st.set_page_config(page_title="ES Ultimate AI Studio & Anti-Copyright Suite", layout="wide", page_icon="⚡")

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

st.sidebar.subheader("🌐 Global Language Settings")
system_language = st.sidebar.selectbox("System Language:", [
    "English",
    "Urdu",
    "Hindi",
    "Spanish",
    "Chinese",
    "Korean",
    "Arabic",
    "French",
    "German",
    "Japanese",
    "Turkish"
])

enable_watermark = st.sidebar.checkbox("Enable Branding Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)

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
                return temp_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
    except Exception:
        pass
    return None

def apply_canva_typography(img_path, overlay_text):
    try:
        if not os.path.exists(img_path):
            return
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
            return psycopg2.connect(pg_url)
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
    admin_list = [("essasaba", "essasaba@sglowina.ai"), ("essa_awan", "essa@sglowina.ai")]
    for u, e in admin_list:
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
# 5. UNIVERSAL MEDIA FETCHER & METADATA
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
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'noplaylist': True,
            'http_headers': headers_browser,
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
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
                    info_dict['title'] = "Social Highlight Video"
                    return True, info_dict
    except Exception:
        pass

    return False, info_dict

def generate_smart_metadata_dynamic(info):
    raw_title = info.get('title', 'Video').strip()
    platform = info.get('platform', 'Social Media')
    clean_title = re.sub(r'#\w+', '', raw_title)
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', clean_title).strip()
    if len(clean_title) < 4: clean_title = f"{platform} Master Video"
    t_lower = raw_title.lower()
    
    if any(k in t_lower for k in ['motu', 'patlu', 'cartoon', 'anime', 'animation', 'chhota bheem', 'kids']):
        genre = "Animation & Kids Cartoon"
        safe_titles = [
            f"🌟 {clean_title[:45]} | Full HD Animation Special",
            f"🔥 Best Moments of {clean_title[:40]} | Iconic Episodes",
            f"🎉 {clean_title[:45]} | Super Cartoon Breakdown"
        ]
        hashtags = f"#Animation #Cartoons #KidsEntertainment #{platform}Kids #TrendingAnimation"
        thumb_prompt = f"Vibrant 8K 3D colorful animation thumbnail for '{clean_title[:35]}', joyful cartoon expressions, colorful background, 16:9."
    elif any(k in t_lower for k in ['kapil', 'comedy', 'funny', 'laugh', 'joke', 'hasna', 'standup', 'prank']):
        genre = "Comedy / Entertainment"
        safe_titles = [
            f"😂 {clean_title[:45]} | Non-Stop Comedy Special",
            f"🤣 Uncut Hilarious Moments | {clean_title[:40]}",
            f"🔥 Peak Comedy Highlights | {clean_title[:45]}"
        ]
        hashtags = f"#Comedy #FunnyVideo #ViralReels #{platform}Comedy #LaughOutLoud"
        thumb_prompt = f"Ultra realistic 8K YouTube thumbnail for comedy scene '{clean_title[:35]}', comedian laughing on stage, cinematic lights, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana', 'singer', 'remix']):
        genre = "Music & Aesthetic Lo-Fi"
        safe_titles = [
            f"🎧 {clean_title[:45]} (Slowed + Reverb Lo-Fi Remix)",
            f"🌙 {clean_title[:45]} | Deep Relaxing Aesthetic Vibe",
            f"✨ Pure Nostalgia Audio | {clean_title[:40]}"
        ]
        hashtags = f"#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio #{platform}Music"
        thumb_prompt = f"Anime aesthetic 4K Lo-Fi wallpaper for song '{clean_title[:35]}', neon cozy bedroom, rain outside window, 16:9."
    elif any(k in t_lower for k in ['trailer', 'teaser', 'promo', 'movie', 'film', 'cinema', 'action']):
        genre = "Cinema & Action Climax Scene"
        safe_titles = [
            f"🔥 {clean_title[:45]} - Full Climax & Scene Breakdown",
            f"⚡ {clean_title[:45]} - Hidden Details & Story Explained",
            f"😱 Shocking Action Twist in {clean_title[:40]}"
        ]
        hashtags = f"#MovieRecap #ActionMovie #CinemaLovers #Blockbuster #{platform}Viral"
        thumb_prompt = f"Hyper-realistic 8K cinematic movie poster thumbnail for '{clean_title[:35]}', action hero in intense dramatic lighting, 16:9."
    else:
        genre = "Trending Viral Clip"
        safe_titles = [
            f"🔥 {clean_title[:45]} | Unbelievable Viral Moments",
            f"⚡ You Won't Believe What Happened in {clean_title[:40]}",
            f"😱 Best Highlights of {clean_title[:45]}"
        ]
        hashtags = f"#ViralVideo #{platform}Reels #Trending #BestMoments #Explore"
        thumb_prompt = f"Cinematic 8K viral thumbnail for '{clean_title[:35]}', vivid contrast, dynamic action frame, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

# ==========================================
# 6. FAIL-SAFE ANTI-COPYRIGHT VIDEO PROCESSOR
# ==========================================
def apply_anti_copyright_shield(in_video, out_video, style_mode, audio_mode):
    ffmpeg_exe = get_ffmpeg()
    
    probe_cmd = [ffmpeg_exe, "-i", in_video]
    probe_res = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    has_audio = "Audio:" in probe_res.stderr

    if "Pro Editor" in style_mode or "پرو ایڈیٹر" in style_mode:
        vf_filter = (
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "setpts=0.925*PTS,rotate=1.5*PI/180*sin(2*PI*t*1.2):ow=iw:oh=ih:c=black,"
            "hflip,crop=iw*0.84:ih*0.84,scale=1280:720,"
            "eq=contrast=1.14:saturation=1.20:brightness=0.02,"
            "drawbox=y=ih-85:color=black@0.75:width=iw:height=70:t=fill,"
            "noise=alls=8:allf=t+u,vignette=PI/3.5"
        )
    else:
        vf_filter = (
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "setpts=0.925*PTS,rotate=1.5*PI/180*sin(2*PI*t*1.2):ow=iw:oh=ih:c=black,"
            "hflip,crop=iw*0.82:ih*0.82,scale=1280:720,"
            "eq=contrast=1.14:saturation=1.20:brightness=0.02,"
            "drawbox=y=ih-90:color=black@0.70:width=iw:height=75:t=fill,"
            "noise=alls=8:allf=t+u,vignette=PI/3.5"
        )

    if has_audio:
        if "75%" in audio_mode or "خاموش" in audio_mode:
            af_filter = "volume=0.30,atempo=1.08,asetrate=44100*0.94,aresample=44100,bass=g=5:f=110"
        elif "Deep" in audio_mode or "بھاری" in audio_mode:
            af_filter = "atempo=1.08,asetrate=44100*0.88,aresample=44100,bass=g=5:f=120"
        else:
            af_filter = "atempo=1.08,asetrate=44100*1.04,aresample=44100,bass=g=3:f=110"
            
        cmd = [
            ffmpeg_exe, "-y", "-i", in_video,
            "-vf", vf_filter,
            "-af", af_filter,
            "-r", "25",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", out_video
        ]
    else:
        cmd = [
            ffmpeg_exe, "-y", "-i", in_video,
            "-vf", vf_filter,
            "-r", "25",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", out_video
        ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Fallback to simple bypass if complex filter graph fails
    if not (os.path.exists(out_video) and os.path.getsize(out_video) > 10000):
        simple_vf = "scale=1280:720,hflip,eq=contrast=1.08:saturation=1.12,noise=alls=6:allf=t"
        fallback_cmd = [
            ffmpeg_exe, "-y", "-i", in_video,
            "-vf", simple_vf,
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
            "Translate this story scene into descriptive English visual instructions for Flux image generation. "
            "Identify main subjects, ensure anatomical perfection and output ONLY visual descriptions."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ': ' + text)}?model=openai"
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
        status.info(f"⏳ Waiting in Queue... Position: #{my_pos - 2}")
        
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
            st.error("Authentication Error. Please sign in again.")
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
            status.info("Processing dialogue voiceovers...")
            
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
                status.info("Downloading atmospheric background track...")
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
                    status.info(f"Rendering 3D Video Frame {i+1} via {video_model}...")
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
            status.info("Rendering high-definition visual frames...")
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.55)
            status.info("Assembling synchronized audio and motions...")
            
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
            status.info("Stitching master production video...")
            
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
            status.success("Master Video Rendered Successfully!")
            
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
# 9. COMPACT UI & BRANDING STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@800&family=Inter:wght@400;600;700&display=swap');
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    .sleek-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 8px 0 14px 0;
    }
    
    .sleek-logo {
        width: 38px;
        height: 38px;
        background: linear-gradient(45deg, #ff007a, #2563eb);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 16px;
        font-weight: 800;
        color: #ffffff;
        box-shadow: 0 0 14px rgba(255, 0, 122, 0.4);
    }
    
    .sleek-title {
        font-size: 1.35rem;
        font-weight: 800;
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 1px;
    }

    .stButton>button { 
        background: #000000 !important; 
        color: white !important; 
        border-radius: 10px !important; 
        height: 48px; 
        width: 100%; 
        font-size: 17px; 
        font-weight: bold; 
        border: none; 
    }
    </style>
    
    <div class="sleek-header">
        <div class="sleek-logo">ES</div>
        <div class="sleek-title">SGLOWINA & ES AI STUDIO</div>
    </div>
    """, unsafe_allow_html=True)

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
                Click Start Live Companion to begin autonomous interaction.
            </div>

            <div class="start-overlay" id="startScreen">
                <div style="font-size:45px; margin-bottom:10px;">🧸</div>
                <h3 style="color:#ffffff; font-weight:900; margin-bottom:5px;">MUSE Live Vision Companion</h3>
                <p style="color:#94a3b8; font-size:13px; max-width:280px;">Autonomous live mobile camera vision stream.</p>
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
                    
                    startSpeechListener();
                    
                    autoScanTimer = setInterval(() => {
                        if (!isScanning) {
                            captureAndAnalyze("Describe what is in front of the camera.");
                        }
                    }, 8000);
                } catch (e) {
                    alert("Camera permission required: " + e.message);
                }
            }

            function startSpeechListener() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) return;

                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.lang = 'en-US';

                recognition.onresult = async function(event) {
                    let lastIdx = event.results.length - 1;
                    let spoken = event.results[lastIdx][0].transcript;
                    subtitles.innerText = "You: " + spoken;
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
                                            text: "You are a friendly AI mascot in a real-time live vision session. Look at this camera frame and describe objects, surroundings, or people concisely in 2 sentences: " + promptText 
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
                    subtitles.innerText = "MUSE: " + reply;
                    speakVoice(reply);
                } catch (err) {
                } finally {
                    isScanning = false;
                }
            }

            function speakVoice(text) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utter = new SpeechSynthesisUtterance(text);
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
# 11. NAVIGATION TABS (ALL 7 TABS PRESERVED)
# ==========================================
tab_auth, tab_companion, tab_es_tools, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Auth",
    "🧸 AR Live Companion",
    "⚡ Anti-Copyright Studio",
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
                        st.success("Welcome back to SGLOWINA & ES AI, Muhammad Essa Awan & Saba Wahid! (Admin Authorized) 🟢")
                    else:
                        st.success(f"Welcome back to SGLOWINA AI, {u_name}! (Authorized User) 🟢")
                    time.sleep(1)
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
# TAB 2: LIVE AR COMPANION
# -----------------
with tab_companion:
    render_autonomous_live_viewport()

# -----------------
# TAB 3: ES VIDEO PROCESSOR (ANTI-COPYRIGHT SUITE)
# -----------------
with tab_es_tools:
    st.write("### ⚡ ES Ultra Disruption & Audio Ducking Shield (Anti-Copyright Studio)")
    st.info("💡 **Supported Platforms:** Pinterest, Instagram Reels, TikTok, Facebook Watch, YouTube, Cartoons & Movies. Direct file upload or URL.")
    
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "🎬 1. Full Video / Cartoon Mode",
        "⚔️ 2. Clip Cutter Mode (10 Min Cut)",
        "🎧 3. Songs & Lo-Fi (Slowed + Reverb)"
    ])
    
    with sub_t1:
        st.subheader("Apply Anti-Fingerprint & Shield to Full Video")
        
        c_mode1, c_mode2 = st.columns(2)
        with c_mode1:
            style_choice = st.selectbox("Visual Disruption Preset:", [
                "Pro Editor Mode (Dynamic Tilt + Canvas Frame + Anti-Logo Banner)",
                "Full Screen Shield (Dynamic Tilt + Deep 80% Zoom + Film Grain)"
            ], key="s_t1")
        with c_mode2:
            audio_shield = st.selectbox("Audio Ducking Preset:", [
                "75% Ducking + Cinematic Layering (Anti-Content-ID)",
                "Deep Pitch Shift (0.90x)",
                "1.08x Speed Modulation"
            ], key="ap_t1")
        
        upload_opt1 = st.file_uploader("📂 Upload Local Video File:", type=["mp4", "mov", "mkv", "avi"], key="up_t1")
        url_input_1 = st.text_input("🔗 Or Paste URL (Pinterest, TikTok, Insta, FB, YouTube, Cartoons):", placeholder="https://...", key="url_t1")
        
        if st.button("🚀 Process & Apply Anti-Copyright Shield", type="primary", key="run_t1"):
            uid = str(uuid.uuid4())[:8]
            dyn_in = f"temp_in_{uid}.mp4"
            dyn_out = f"es_shielded_{uid}.mp4"
            has_input = False
            info = {'title': 'Featured Master Video'}
            
            if upload_opt1 is not None:
                with open(dyn_in, "wb") as f:
                    f.write(upload_opt1.getvalue())
                has_input = True
                info['title'] = upload_opt1.name
            elif url_input_1.strip():
                with st.spinner("Downloading and normalizing media stream..."):
                    success, info = inspect_and_fetch_media_universal(url_input_1.strip(), dyn_in)
                    if success:
                        has_input = True
                    else:
                        st.error("Download failed. Please check the URL or upload directly.")
                        
            if has_input:
                with st.spinner("Applying sub-second time-variant hashes, audio ducking, and anti-logo shields..."):
                    ok = apply_anti_copyright_shield(dyn_in, dyn_out, style_choice, audio_shield)
                    if ok and os.path.exists(dyn_out):
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = dyn_out
                        st.session_state.process_ready = True
                    else:
                        st.error("Processing failed. Please check file format.")
                        
                    if os.path.exists(dyn_in):
                        try: os.remove(dyn_in)
                        except Exception: pass
            else:
                st.warning("Please upload a video file or provide a valid link.")

    with sub_t2:
        st.subheader("Cut Specific Minutes & Apply Shield")
        c1, c2 = st.columns(2)
        with c1:
            scene_type = st.selectbox("Scene Start:", ["Climax Scene (Min 30)", "Suspense Scene (Min 45)", "Opening (Min 15)", "Custom Minute"], key="s_t2")
        with c2:
            clip_len = st.slider("Duration (Minutes):", 1, 20, 10, key="len_t2")
            
        start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("Start Minute:", 0, 300, 10)
        upload_opt2 = st.file_uploader("📂 Choose Video File:", type=["mp4", "mov", "mkv"], key="up_t2")
        url_input_2 = st.text_input("🔗 Or Paste Media URL:", placeholder="https://...", key="url_t2")

        if st.button("🚀 Cut Clip & Apply Shield", type="primary", key="run_t2"):
            uid = str(uuid.uuid4())[:8]
            dyn_in = f"temp_in_{uid}.mp4"
            dyn_out = f"es_clip_{uid}.mp4"
            has_input = False
            info = {'title': 'Clip Highlight'}
            
            if upload_opt2 is not None:
                with open(dyn_in, "wb") as f:
                    f.write(upload_opt2.getvalue())
                has_input = True
                info['title'] = upload_opt2.name
            elif url_input_2.strip():
                with st.spinner("Downloading video..."):
                    success, info = inspect_and_fetch_media_universal(url_input_2.strip(), dyn_in)
                    if success: has_input = True

            if has_input:
                with st.spinner("Cutting clip and applying anti-copyright shield..."):
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = start_min * 60
                    dur_sec = clip_len * 60
                    vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setpts=0.925*PTS,rotate=1.5*PI/180*sin(2*PI*t*1.2):ow=iw:oh=ih:c=black,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,eq=contrast=1.14:saturation=1.20:brightness=0.02,drawbox=y=ih-85:color=black@0.75:width=iw:height=70:t=fill,noise=alls=8:allf=t+u,vignette=PI/3.5"
                    af = "volume=0.30,atempo=1.08,asetrate=44100*0.92,aresample=44100,bass=g=5:f=120"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                        "-i", dyn_in, "-vf", vf, "-af", af,
                        "-r", "25",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "128k", dyn_out
                    ]
                    subprocess.run(cmd)
                    if os.path.exists(dyn_out) and os.path.getsize(dyn_out) > 10000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = dyn_out
                        st.session_state.process_ready = True
                    else:
                        st.error("Failed to process clip. Check time settings.")
                        
                    if os.path.exists(dyn_in):
                        try: os.remove(dyn_in)
                        except Exception: pass
            else:
                st.warning("Please upload a video or provide a valid link.")

    with sub_t3:
        st.subheader("Make Viral Slowed + Reverb Audio")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: slow_val = st.slider("Slow Speed Factor:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
        with col_s2: reverb_val = st.slider("Reverb Echo Depth:", 20, 80, 50, 5, key="rev_t3")
        with col_s3: bass_val = st.slider("Bass Boost (dB):", 0, 12, 6, key="bass_t3")
            
        upload_opt3 = st.file_uploader("📂 Choose Audio/Video:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
        song_url = st.text_input("🔗 Or Paste Song URL (TikTok/Reels/YouTube):", placeholder="https://...", key="url_t3")
        
        if st.button("🚀 Render Slowed + Reverb", type="primary", key="run_t3"):
            uid = str(uuid.uuid4())[:8]
            dyn_in_song = f"temp_song_{uid}.mp4"
            dyn_out_song = f"lofi_song_{uid}.mp4"
            has_input = False
            info = {'title': 'Lo-Fi Chill Track'}
            
            if upload_opt3 is not None:
                with open(dyn_in_song, "wb") as f:
                    f.write(upload_opt3.getvalue())
                has_input = True
                info['title'] = upload_opt3.name
            elif song_url.strip():
                with st.spinner("Downloading audio track..."):
                    success, info = inspect_and_fetch_media_universal(song_url.strip(), dyn_in_song)
                    if success: has_input = True
                        
            if has_input:
                with st.spinner("Remastering audio with Lo-Fi echo and harmonic shifts..."):
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [
                        ffmpeg_exe, "-y", "-i", dyn_in_song,
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
                        st.error("Audio processing failed.")
                        
                    if os.path.exists(dyn_in_song):
                        try: os.remove(dyn_in_song)
                        except Exception: pass
            else:
                st.warning("Please upload an audio file or provide a valid link.")

    if st.session_state.process_ready and st.session_state.current_output_video and os.path.exists(st.session_state.current_output_video):
        st.divider()
        st.success("🎉 Video Processed & Shielded Successfully! Ready to Download:")
        
        with open(st.session_state.current_output_video, 'rb') as vf:
            video_bytes = vf.read()
            st.video(video_bytes)
            
            st.download_button(
                label="📥 Download Protected Master Video (MP4)",
                data=video_bytes,
                file_name=os.path.basename(st.session_state.current_output_video),
                mime="video/mp4",
                use_container_width=True
            )

        genre, titles, tags, prompt = generate_smart_metadata_dynamic(st.session_state.detected_info)
        st.info(f"🎯 **AI Classification:** Recognized as **'{genre}'** (Source: **{st.session_state.detected_info.get('title', 'Video')}**)")
        
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            st.markdown("### 🔥 Viral SEO Titles:")
            for i, t in enumerate(titles, 1):
                st.code(t, language="text")
            st.markdown("### 🏷️ Viral Hashtags:")
            st.code(tags, language="text")

        with c_meta2:
            st.markdown("### 🎨 AI Thumbnail Prompt:")
            st.info("💡 Use this prompt in Midjourney or Bing Creator:")
            st.code(prompt, language="text")

# -----------------
# TAB 4: PRO MOVIE STUDIO (ALL FEATURES RESTORED)
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    st.subheader("⚙️ AI Generation Mode")
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"])
    pollinations_key = ""
    if "Real AI Video" in gen_mode:
        pollinations_key = st.text_input("Enter Pollinations API Key (sk_* or pk_*):", type="password")

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="Example: A courageous warrior riding a horse through an ancient forest...")
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True)
    
    char_desc = st.text_input("Character Memory (کردار کا حلیہ):", placeholder="e.g. Saba is wearing a modest dark blue hijab")
    
    st.write("##### 👤 Consistent Character Identity References (کرداروں کے چہروں کی تصاویر)")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Upload Male Character Reference Image:", type=["jpg", "png", "jpeg"])
        if uploaded_male_img is not None:
            st.image(uploaded_male_img, caption="Male Identity Loaded ✅", width=120)
    with col_up2:
        uploaded_female_img = st.file_uploader("Upload Female Character Reference Image:", type=["jpg", "png", "jpeg"])
        if uploaded_female_img is not None:
            st.image(uploaded_female_img, caption="Female Identity Loaded ✅", width=120)
        
    scene_desc = st.text_input("Scene Memory (ماحول):", placeholder="e.g. Deep green ancient forest, dark stormy night")

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9, mc10 = st.columns(10)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Speed:", ["+0% (Normal)", "+10% (Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Motion:", [
        "AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Pan Up", "Pan Down",
        "Dolly In", "Dolly Out", "Orbit Camera", "Crane Shot", "Drone Shot", "Tracking Shot", "Follow Shot", "Push In", "Pull Out",
        "Arc Shot", "Handheld Camera", "Shoulder Camera", "Cinematic Reveal", "Whip Pan", "Parallax Motion", "Ken Burns Effect"
    ])
    with mc7: transition_style = st.selectbox("Transition:", ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Film Dissolve (Muted)", "Instant Cut"])
    with mc8: character_heritage = st.selectbox("Heritage:", ["Automatic", "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)", "Ancient Arabian", "Western / Modern", "Far Eastern"])
    with mc9: video_model = st.selectbox("AI Model:", ["wan-fast", "seedance", "veo"])
    with mc10: sd = st.number_input("Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Sglowina AI is generating your video with voice and motion..."):
            v_res = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate=rate_val, pitch=pitch_val, ratio=mr, style=ms, seed=sd,
                char_desc=char_desc, scene_desc=scene_desc, camera_motion=camera_motion, transition_style=transition_style,
                enable_watermark=enable_watermark, enable_bg_music=enable_bg_music, uploaded_male_img=uploaded_male_img,
                uploaded_female_img=uploaded_female_img, enable_islamic_filter=enable_islamic_filter, character_heritage=character_heritage,
                gen_mode=gen_mode, pollinations_key=pollinations_key, video_model=video_model
            )
            
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

# -----------------
# TAB 5: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    tab_txt, tab_img = st.tabs(["🎨 Text to Image", "📤 Image Modify & Upload"])
    
    with tab_txt:
        p_i = st.text_area("Describe Image (One per line for batch):", height=120)
        char_desc_img = st.text_input("Consistent Character Description:", placeholder="Example: A young girl, blue eyes, brown braided hair")
        canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="Example: Sglowina Studio V1.5")
                                      
        ic1, ic2, ic3 = st.columns(3)
        with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Dark Gothic / Mystery"])
        with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok", "CinemaScope (21:9)"])
        with ic3: count = st.slider("Quantity:", 1, 5, 1)
        
        if st.button("Generate Visuals 🚀"):
            u_db = get_user_data(st.session_state.logged_in_user)
            if u_db and u_db['credits'] >= 2 * count:
                dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280), "CinemaScope (21:9)": (1680, 720)}
                w, h = dim[i_size]
                prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
                for idx, single_p in enumerate(prompt_list):
                    for q in range(count):
                        final_p = f"Character: {char_desc_img.strip()}. Scene: {single_p}" if char_desc_img.strip() else single_p
                        img_data = fetch_img_failover(final_p, w, h, random.randint(1,999999))
                        if img_data:
                            img_path_temp = f"temp_canvas_{idx}_{q}.jpg"
                            with open(img_path_temp, "wb") as f_temp:
                                f_temp.write(img_data)
                            if canva_overlay_text.strip():
                                apply_canva_typography(img_path_temp, canva_overlay_text.strip())
                            with Image.open(img_path_temp) as im:
                                st.image(im, caption=single_p[:35])
                            if os.path.exists(img_path_temp):
                                os.remove(img_path_temp)
                            deduct_user_credits(st.session_state.logged_in_user, 2)
                            log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
            else:
                st.error("Insufficient credits (Requires 2 credits per image).")

    with tab_img:
        uploaded_file = st.file_uploader("Upload Image to Modify:", type=["jpg", "png", "jpeg"])
        modify_prompt = st.text_input("Modification Instructions:", placeholder="Example: Add volumetric lighting, make the background dark green")
        canva_overlay_text_mod = st.text_input("Text Overlay for Modified Image:")
        
        if st.button("Modify & Re-render 🎨"):
            if uploaded_file and modify_prompt:
                u_db = get_user_data(st.session_state.logged_in_user)
                if u_db and u_db['credits'] >= 5:
                    img_data = fetch_img_failover(translate_ur_to_en_enhanced(modify_prompt), 1024, 1024, random.randint(1,999999))
                    if img_data:
                        img_path_temp_mod = "temp_canvas_mod.jpg"
                        with open(img_path_temp_mod, "wb") as f_temp_mod:
                            f_temp_mod.write(img_data)
                        if canva_overlay_text_mod.strip():
                            apply_canva_typography(img_path_temp_mod, canva_overlay_text_mod.strip())
                        with Image.open(img_path_temp_mod) as im:
                            st.image(im, caption="Modified Visual")
                        if os.path.exists(img_path_temp_mod):
                            os.remove(img_path_temp_mod)
                        deduct_user_credits(st.session_state.logged_in_user, 5)
                        log_credit_usage(u_db['id'], "Image Modification", 5, u_db['credits'] - 5)
                else:
                    st.error("Insufficient credits (Requires 5 credits).")

# -----------------
# TAB 6: CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true", timeout=15).text
        with st.chat_message("assistant"):
            translated_response = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            st.write(translated_response)
            st.session_state.msgs.append({"role": "assistant", "content": translated_response})

# -----------------
# TAB 7: ENTERPRISE CENTER (EASYPAISA & JAZZCASH & ADMIN FULLY RESTORED)
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina Enterprise Administration Center")
    ent_tab_user, ent_tab_history, ent_tab_billing, ent_tab_admin = st.tabs(["👤 User Profile", "📁 Saved Projects", "💳 Billing & Subscription Plans", "🔒 Admin Control Panel"])
    
    u_db = get_user_data(st.session_state.logged_in_user)
    
    with ent_tab_user:
        if u_db:
            st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
            st.write("Secure Session Token:")
            st.code(str(uuid.uuid5(uuid.NAMESPACE_DNS, st.session_state.logged_in_user))[:20])
            st.write("Joined Sglowina Cloud:")
            st.code(u_db['created_at'])
        else:
            st.warning("Please sign in first.")
            
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
                    st.code(proj['prompt'], language="text")
                    st.markdown("---")
        else:
            st.warning("Please sign in first.")
                
    with ent_tab_billing:
        st.write("### 💳 Subscription Plans & Credit Packages (Pakistani Local Payment Integration)")
        st.success("#### 🏆 Sglowina Premium Monthly Plan\n💰 **Price:** 1000 PKR / Month | 🪙 **Credits:** 450 Coins")
        
        st.markdown("---")
        st.write("### 🎁 Redeem Sglowina Promo / Coupon Code")
        with st.form("coupon_form"):
            coupon_code = st.text_input("Enter Promo Code (e.g. ESSASABA):")
            btn_redeem = st.form_submit_button("Redeem Credits 🎁")
            if btn_redeem and coupon_code.strip() and u_db:
                conn = get_db_connection()
                curr = conn.cursor()
                curr.execute("SELECT * FROM coupons WHERE UPPER(code) = UPPER(?)", (coupon_code.strip(),))
                c_row = curr.fetchone()
                if c_row and c_row['uses_left'] > 0:
                    curr.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (c_row['credits'], u_db['id']))
                    curr.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (c_row['code'],))
                    log_credit_usage(u_db['id'], f"Coupon: {c_row['code']}", c_row['credits'], u_db['credits'] + c_row['credits'])
                    conn.commit()
                    st.success(f"Success! {c_row['credits']} credits added to your account! 🟢")
                else:
                    st.error("Invalid or expired coupon.")
                conn.close()
        
        st.markdown("---")
        st.write("### 📱 How to Pay via EasyPaisa / JazzCash")
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.info("💚 **EasyPaisa Account**\n\n* **Name:** Saba Wahid\n* **Number:** 03086834020")
        with bcol2:
            st.warning("❤️ **JazzCash Account**\n\n* **Name:** Ayisha bi bi\n* **Number:** 03240755475")
            
        if u_db:
            with st.form("local_payment_form"):
                p_method = st.selectbox("Payment Method Used:", ["EasyPaisa", "JazzCash"])
                p_trx_id = st.text_input("Enter Transaction ID (TrxID):", placeholder="e.g., 50123456789")
                p_amount = st.number_input("Amount Sent (PKR):", min_value=500.0, max_value=50000.0, value=1000.0, step=100.0)
                if st.form_submit_button("Submit Payment Proof 🚀"):
                    if p_trx_id.strip():
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            req_id = str(uuid.uuid4())[:8]
                            cursor.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                           (req_id, u_db['username'], p_method, p_trx_id.strip(), p_amount, 'Pending', time.strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            st.success("Payment submitted! Administrator will verify and credit your coins.")
                        except sqlite3.IntegrityError:
                            st.error("This Transaction ID has already been submitted.")
                        finally:
                            conn.close()
                    else:
                        st.warning("Please enter a valid TrxID.")
                
    with ent_tab_admin:
        st.write("#### 🔒 Secured Admin Control Settings")
        if u_db and u_db['role'] == 'Admin':
            st.success("Access Granted: Administrator Mode Activated 🟢")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            m_row = cursor.fetchone()
            current_master_key = m_row['value'] if m_row else ""
            conn.close()
            
            with st.form("master_key_config_form"):
                new_master_key_input = st.text_input("Set Master API Key (e.g. sk_...):", value=current_master_key, type="password")
                if st.form_submit_button("Save Master API Key 💾"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('master_pollinations_key', ?)", (new_master_key_input.strip(),))
                    conn.commit()
                    conn.close()
                    st.success("Master API Key saved successfully! 🟢")
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
            with saas_col1: st.metric("Total Users", total_users)
            with saas_col2: st.metric("Total Projects", total_projects)
            with saas_col3: st.metric("Total Credits", total_credits_allocated)
                
            st.markdown("---")
            st.write("### 📲 Pending Payment Requests")
            cursor.execute("SELECT * FROM local_payments WHERE status = 'Pending'")
            pending_reqs = cursor.fetchall()
            
            if not pending_reqs:
                st.info("No pending payment requests found.")
            else:
                for req in pending_reqs:
                    st.write(f"👤 **User:** `{req['username']}` | 📱 **Method:** {req['method']} | 🔑 **TrxID:** `{req['trx_id']}` | 💰 **Amount:** {req['amount']} PKR")
                    if st.button(f"Approve & Credit 450 Coins ({req['trx_id']})", key=f"app_{req['id']}"):
                        cursor.execute("UPDATE local_payments SET status = 'Approved' WHERE id = ?", (req['id'],))
                        cursor.execute("UPDATE users SET credits = credits + 450, plan = 'Premium' WHERE username = ?", (req['username'],))
                        conn.commit()
                        st.success(f"Payment approved for {req['username']}!")
                        st.rerun()
            
            st.markdown("---")
            cursor.execute("SELECT * FROM users")
            all_users = cursor.fetchall()
            st.write("### User Database Management")
            for u in all_users:
                st.write(f"👤 **{u['username']}** | Role: {u['role']} | Plan: {u['plan']} | Credits: {u['credits']} 🪙 | Status: {u['status']}")
            conn.close()
        else:
            st.error("Access Denied: Only Administrators can access this tab.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>ES & Sglowina AI Studio Suite V5.0 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
