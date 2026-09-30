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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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
st.set_page_config(page_title="ES Ultimate AI Studio & Anti-Copyright", layout="wide", page_icon="⚡")

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
    st.session_state.current_output_video = ""

st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
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

def sanitize_url(raw_url):
    raw_url = raw_url.strip()
    if "youtu.be" in raw_url:
        vid_id = raw_url.split("youtu.be/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={vid_id}"
    elif "youtube.com/watch" in raw_url:
        parsed = urllib.parse.urlparse(raw_url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'v' in params:
            return f"https://www.youtube.com/watch?v={params['v'][0]}"
    return raw_url

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
# 3. UNIVERSAL MULTI-PLATFORM DOWNLOADER & DYNAMIC METADATA
# ==========================================
def inspect_and_fetch_media(raw_url, target_path):
    if os.path.exists(target_path):
        try: os.remove(target_path)
        except Exception: pass
    
    clean_url = sanitize_url(raw_url)
    info_dict = {'title': 'Action Scene Video', 'uploader': 'Official Creator', 'categories': ['Entertainment'], 'tags': []}
    
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {'player_client': ['android', 'ios', 'mweb', 'web', 'tvhtml5']}
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            if meta:
                info_dict['title'] = meta.get('title', 'Action Scene Video')
                info_dict['uploader'] = meta.get('uploader', 'Official Creator')
                info_dict['categories'] = meta.get('categories', ['Entertainment'])
                info_dict['tags'] = meta.get('tags', [])
    except Exception:
        pass
        
    return info_dict

def generate_smart_metadata(info):
    raw_title = info.get('title', 'Video').strip()
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', raw_title).strip()
    if not clean_title: clean_title = raw_title
    t_lower = raw_title.lower()
    
    if any(k in t_lower for k in ['mental', 'force', 'john', 'action', 'fight', 'movie', 'scene', 'police', 'hindi', 'bloopers']):
        genre = "Bollywood Action & Blockbuster Scene"
        safe_titles = [
            f"🔥 {clean_title[:50]} | Best Action Scene (Full HD)",
            f"⚡ Unstoppable Action Moments | {clean_title[:45]}",
            f"😱 Most Intense Fight Scene | {clean_title[:45]}"
        ]
        hashtags = "#Force2 #JohnAbraham #ActionScene #BollywoodAction #Blockbuster #ViralVideo #HindiCinema"
        thumb_prompt = f"Hyper-realistic 8K cinematic movie thumbnail for '{clean_title[:35]}', intense muscular hero dramatic angry face, action sparks background, 16:9."
    elif any(k in t_lower for k in ['kapil', 'comedy', 'funny', 'laugh', 'joke', 'hasna', 'standup', 'prank']):
        genre = "Comedy / Entertainment Show"
        safe_titles = [
            f"😂 {clean_title} | Non-Stop Uncut Funny Moments",
            f"🤣 Ultimate Comedy Highlights | {clean_title[:45]} (Best Laughs)",
            f"🔥 Funniest Scene Ever | {clean_title[:50]}"
        ]
        hashtags = "#Comedy #FunnyVideo #ViralComedy #StandupComedy #TrendingReels #LaughOutLoud"
        thumb_prompt = f"Ultra realistic 8K YouTube thumbnail for comedy show scene '{clean_title[:35]}', comedian laughing happily on stage, bright cinematic studio lights, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana', 'singer', 'remix']):
        genre = "Music / Lo-Fi Audio Track"
        safe_titles = [
            f"🎧 {clean_title} (Slowed + Reverb Lo-Fi Remix) | Midnight Chill",
            f"🌙 {clean_title} | Deep Relaxing Aesthetic Vibe (Master HD)",
            f"✨ Pure Nostalgia Vibes | {clean_title[:45]} (Slowed Version)"
        ]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio #MidnightVibes #LoFiBeats"
        thumb_prompt = f"Anime aesthetic 4K Lo-Fi wallpaper thumbnail for song '{clean_title[:35]}', neon cozy bedroom, rain outside window, 16:9."
    else:
        genre = "Viral Video Highlight"
        safe_titles = [
            f"🔥 {clean_title[:45]} - Full HD Climax Scene",
            f"⚡ {clean_title[:45]} - Best Uncut Action Moments",
            f"😱 The Most Dramatic Scene of {clean_title[:40]}"
        ]
        hashtags = "#ViralClip #TrendingNow #CinemaRecap #ActionHighlights #BlockbusterScene"
        thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', dramatic intense face, cinematic color grading, 16:9."
        
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
# 4. MASTER V40 RENDER SYSTEM CORE
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
# 5. UI & PREMIUM BRANDING STYLING
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
# 6. NAVIGATION TABS (ALL 6 MAIN TABS)
# ==========================================
tab_auth, tab_es_tools, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Auth",
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
                        st.success(f"Welcome to SGLOWINA AI, {u_name}! (Authorized User) 🟢")
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
# TAB 2: ES VIDEO PROCESSOR & 100% LIP-SYNC ANTI-COPYRIGHT ENGINE
# -----------------
with tab_es_tools:
    st.write("### ⚡ ES ہالی ووڈ پرو ڈسرپشن اینٹی کاپی رائٹ شیلڈ (100% Lipsync Locked)")
    st.info("💡 **پرو فارمولا ایکٹیو:** 1.8° جیو میٹرک ٹِلٹ، 70% کینوس اوورلے فریم، ٹاپ/باٹم اینٹی او سی آر شیلڈ اور ویڈیو کے ساتھ آواز کا 100% کامل سنک۔")
    
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "🎬 1. فل ویڈیو / مووی / ریلز موڈ",
        "⚔️ 2. کلپ کٹر موڈ (10 منٹ کٹ)",
        "🎧 3. گانے اور لوفی (Slowed + Reverb)"
    ])
    
    with sub_t1:
        st.subheader("یوٹیوب، ٹک ٹاک، فیس بک یا انسٹاگرام لنک یا فائل پروسیس کریں")
        
        c_mode1, c_mode2 = st.columns(2)
        with c_mode1:
            style_choice = st.selectbox("حفاظتی ویژول اسٹائل:", [
                "👑 پرو ایڈیٹر موڈ (100% محفوظ - 1.8° Tilt + Canvas Frame + Text Shield)",
                "⚡ الٹرا فل اسکرین اینٹی ہیش (1.8° Tilt + 82% Deep Zoom + Letterbox Bars)"
            ], key="s_t1")
        with c_mode2:
            audio_pitch_choice = st.selectbox("آواز اور میوزک موڈیولیشن (Audio Frequency Disruption):", [
                "🔊 بیک گراؤنڈ میوزک 75% خاموش + بھاری آواز (Heavy Ducking - 100% Lipsync Safe)",
                "🎵 تیز اور اسمارٹ پچ شفٹ (Smart Shift 1.08x)",
                "🎧 لوفی سلور پچ (Lo-Fi Pitch)"
            ], key="ap_t1")
        
        upload_opt1 = st.file_uploader("📂 اپنے موبائل یا کمپیوٹر سے ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi"], key="up_t1")
        url_input_1 = st.text_input("🔗 یا کسی بھی پلیٹ فارم (YouTube, TikTok, Insta, Facebook) کا نیا لنک ڈالیں:", placeholder="https://...", key="url_t1")
        
        if st.button("🚀 پرو اینٹی کاپی رائٹ ڈسرپشن شیلڈ لگائیں", type="primary", key="run_t1"):
            curr_uid = str(uuid.uuid4())[:8]
            target_in = f"in_vid_{curr_uid}.mp4"
            target_out = f"out_vid_{curr_uid}.mp4"
            
            info = {'title': 'Action Scene Video'}
            has_input = False
            
            if upload_opt1 is not None:
                with st.spinner("📂 ویڈیو فائل سسٹم میں لوڈ ہو رہی ہے..."):
                    with open(target_in, "wb") as f:
                        upload_opt1.seek(0)
                        while True:
                            chunk = upload_opt1.read(1024 * 1024 * 4)
                            if not chunk: break
                            f.write(chunk)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        has_input = True
                        info['title'] = upload_opt1.name
            elif url_input_1.strip():
                with st.spinner("🔗 لنک سے تازہ ویڈیو ڈاؤنلوڈ ہو رہی ہے (Universal Multi-Platform Downloader)..."):
                    info = inspect_and_fetch_media(url_input_1.strip(), target_in)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        has_input = True
                        
            if has_input:
                with st.spinner("⚡ ویڈیو اور آڈیو کو پرفیکٹ لپ سنک (Lip-Sync) کے ساتھ پروسیس کیا جا رہا ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    
                    # 1.08x Speed = 0.925926 PTS
                    if "پرو ایڈیٹر" in style_choice:
                        vf_str = (
                            "[0:v]scale=1280:720,boxblur=25:5[bg];"
                            "[0:v]setpts=0.925926*PTS,rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.82:ih*0.82,scale=980:552,"
                            "eq=contrast=1.16:saturation=1.22:brightness=0.02,"
                            "noise=alls=8:allf=t+u,vignette=PI/3.5[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                            "drawbox=y=0:h=45:color=black@0.65:t=fill,"
                            "drawbox=y=ih-55:h=55:color=black@0.75:t=fill"
                        )
                    else:
                        vf_str = (
                            "setpts=0.925926*PTS,rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                            "eq=contrast=1.16:saturation=1.22:brightness=0.02,"
                            "noise=alls=8:allf=t+u,vignette=PI/3.5,"
                            "drawbox=y=0:h=45:color=black@0.65:t=fill,"
                            "drawbox=y=ih-55:h=55:color=black@0.75:t=fill"
                        )
                    
                    # MATHEMATICALLY PERFECT LIP-SYNC (atempo = 1.08 / 0.92 = 1.173913)
                    if "خاموش" in audio_pitch_choice or "Heavy Ducking" in audio_pitch_choice:
                        af_str = "volume=0.35,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.173913,bass=g=5:f=120,treble=g=-3:f=3500"
                    elif "لوفی" in audio_pitch_choice:
                        af_str = "asetrate=44100*0.90,aresample=44100:async=1,atempo=1.20,bass=g=6:f=110,aecho=0.8:0.88:50:0.35"
                    else:
                        af_str = "volume=0.85,asetrate=44100*1.05,aresample=44100:async=1,atempo=1.028571,bass=g=3:f=110"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-i", target_in,
                        "-filter_complex" if "پرو ایڈیٹر" in style_choice else "-vf", vf_str,
                        "-af", af_str,
                        "-r", "25",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", target_out
                    ]
                    
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        if os.path.exists(target_in):
                            try: os.remove(target_in)
                            except Exception: pass
                    else:
                        st.error("❌ ویڈیو پروسیسنگ مکمل نہ ہو سکی۔ براہِ کرم دوبارہ ٹرائی کریں۔")
            else:
                st.error("❌ برائے مہربانی کوئی کام کرنے والا ویڈیو لنک یا فائل فراہم کریں۔")

    with sub_t2:
        st.subheader("کسی بھی شو یا ویڈیو کا 10 منٹ کلپ نکالیں")
        c1, c2 = st.columns(2)
        with c1:
            scene_type = st.selectbox("سین کا آغاز:", ["⚔️ اہم سین / کلائمیکس (منٹ 30)", "👻 سسپنس موڑ (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
        with c2:
            clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
            
        start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
        upload_opt2 = st.file_uploader("📂 ویڈیو فائل منتخب کریں:", type=["mp4", "mov", "mkv"], key="up_t2")
        url_input_2 = st.text_input("🔗 یا کسی بھی پلیٹ فارم کا نیا لنک ڈالیں:", placeholder="https://...", key="url_t2")

        if st.button("🚀 کلپ کاٹیں اور ڈائنامک شیلڈ لگائیں", type="primary", key="run_t2"):
            curr_uid = str(uuid.uuid4())[:8]
            target_in = f"clip_in_{curr_uid}.mp4"
            target_out = f"clip_out_{curr_uid}.mp4"
            
            info = {'title': 'Clip Highlight'}
            has_input = False
            
            if upload_opt2 is not None:
                with open(target_in, "wb") as f:
                    upload_opt2.seek(0)
                    while True:
                        chunk = upload_opt2.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    has_input = True
                    info['title'] = upload_opt2.name
            elif url_input_2.strip():
                with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    info = inspect_and_fetch_media(url_input_2.strip(), target_in)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        has_input = True

            if has_input:
                with st.spinner("کلپ کٹ کر کے 100% پرفیکٹ سنک اور پرو شیلڈ لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = start_min * 60
                    dur_sec = clip_len * 60
                    vf = "setpts=0.925926*PTS,rotate=1.8*PI/180:ow=iw:oh=ih:c=black,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,eq=contrast=1.16:saturation=1.22:brightness=0.02,noise=alls=8:allf=t+u,vignette=PI/3.5,drawbox=y=0:h=45:color=black@0.65:t=fill,drawbox=y=ih-55:h=55:color=black@0.75:t=fill"
                    af = "volume=0.45,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.173913,bass=g=5:f=120"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                        "-i", target_in, "-vf", vf, "-af", af,
                        "-r", "25",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", target_out
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        if os.path.exists(target_in):
                            try: os.remove(target_in)
                            except Exception: pass
                    else:
                        st.error("❌ ویڈیو ٹائم سیٹنگز چیک کریں۔")
            else:
                st.error("❌ ویڈیو اپلوڈ کریں یا درست لنک دیں۔")

    with sub_t3:
        st.subheader("گانے کا لنک ڈالیں اور وائرل Slowed + Reverb بنائیں")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
        with col_s2:
            reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
        with col_s3:
            bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3")
            
        upload_opt3 = st.file_uploader("📂 آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
        song_url = st.text_input("🔗 یا گانے کا لنک یہاں پیسٹ کریں:", placeholder="https://...", key="url_t3")
        
        if st.button("🚀 گانے کو Slowed + Reverb بنائیں", type="primary", key="run_t3"):
            curr_uid = str(uuid.uuid4())[:8]
            temp_audio_in = f"dyn_song_in_{curr_uid}.mp4"
            target_out = f"dyn_song_out_{curr_uid}.mp4"
            
            info = {'title': 'Lo-Fi Chill Track'}
            has_input = False
            
            if upload_opt3 is not None:
                with open(temp_audio_in, "wb") as f:
                    upload_opt3.seek(0)
                    while True:
                        chunk = upload_opt3.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(temp_audio_in) and os.path.getsize(temp_audio_in) > 1000:
                    has_input = True
                    info['title'] = upload_opt3.name
            elif song_url.strip():
                with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                    info = inspect_and_fetch_media(song_url.strip(), temp_audio_in)
                    if os.path.exists(temp_audio_in) and os.path.getsize(temp_audio_in) > 1000:
                        has_input = True
                        
            if has_input:
                with st.spinner("لوفی گانا ماسٹر ہو رہا ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [
                        ffmpeg_exe, "-y", "-i", temp_audio_in,
                        "-af", af_filter, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", target_out
                    ]
                    subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        if os.path.exists(temp_audio_in):
                            try: os.remove(temp_audio_in)
                            except Exception: pass
                    else:
                        st.error("❌ آڈیو پروسیسنگ فیل ہو گئی۔")
            else:
                st.error("❌ آڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    # 100% Guaranteed Output Video Player & Download
    active_out = st.session_state.current_output_video
    if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
        st.divider()
        st.success("🎉 ویڈیو اینٹی کاپی رائٹ شیلڈ اور پرفیکٹ ڈبنگ کے ساتھ تیار ہے:")
        
        video_bytes = open(active_out, 'rb').read()
        st.video(video_bytes)
        
        st.download_button(
            label="📥 یہاں کلک کر کے پروسیس شدہ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
            data=video_bytes,
            file_name=f"es_protected_{os.path.basename(active_out)}",
            mime="video/mp4",
            use_container_width=True
        )

        genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
        st.info(f"🎯 **AI نے پہچانا:** یہ ویڈیو **'{genre}'** کیٹگری کی ہے۔ (اصل ٹائٹل: **{st.session_state.detected_info.get('title', 'Video')}**)")
        
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
# TAB 3: PRO MOVIE STUDIO (ALL 25 MOTIONS & PRODUCTION TOOLS)
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    st.subheader("⚙️ AI Generation Mode")
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"])
    pollinations_key = ""
    if "Real AI Video" in gen_mode:
        pollinations_key = st.text_input("Enter Pollinations API Key (sk_* or pk_*):", type="password")

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے اور کھیت میں کام کر رہا ہے...")
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
        "Arc Shot", "Handheld Camera", "Shoulder Camera", "Cinematic Reveal", "Whip Pan", "Tilt Up", "Tilt Down", "Roll Camera", "Parallax Motion", "Ken Burns Effect"
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
# TAB 4: PRO IMAGE STUDIO
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
# TAB 5: CHAT
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
# TAB 6: ENTERPRISE CENTER (EASYPAISA & JAZZCASH & ADMIN FULLY RESTORED)
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

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>ES & Sglowina AI Studio Suite | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
