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
# 2. BROWSER HEADERS & GLOBAL CONSTANTS
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI is an advanced generative AI cinematic video, live vision & image production platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

# ==========================================
# 3. STREAMLIT CONFIGURATION & STATES
# ==========================================
st.set_page_config(
    page_title="Sglowina AI - SaaS Enterprise & Anti-Copyright Studio", 
    layout="wide", 
    page_icon="⚡"
)

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
target_lang = st.sidebar.selectbox("🌐 Choose System Language:", [
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
# 4. DATABASE LAYER
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
    admin_users = [
        ("essasaba", "essasaba@sglowina.ai"),
        ("essa_awan", "essa@sglowina.ai")
    ]
    for u, e in admin_users:
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
# 5. TRANSLATION & PROMPT DIRECTOR
# ==========================================
def translate_to_language(text, target_language_name):
    if not text.strip() or "Urdu" in target_language_name:
        return text
    try:
        inst = f"Translate the following text naturally into {target_language_name}. Output ONLY the translated text."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(inst + ': ' + text)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return text

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
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "کفن", "غوث", "قطب", "امام", "پیمغبر"
    ]
    if any(k in combined_text for k in spiritual_keywords):
        safe_prompt = (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from the heavens, "
            "sacred light beam, peaceful glowing ancient background, majestic natural mountains. "
            "STRICTLY NO human faces, NO visible bodies. Pure sacred light."
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

        prompt_input = f"Scene: {urdu_scene}\n"
        if char_memory: prompt_input += f"Character Details: {char_memory}\n"
        if gender_booster: prompt_input += f"Attire Details: {gender_booster}\n"
        if scene_memory: prompt_input += f"Environment: {scene_memory}\n"

        url = f"https://text.pollinations.ai/{urllib.parse.quote('Write Flux 8k cinematic prompt: ' + prompt_input)}?model=openai"
        res = session.get(url, timeout=20)
        if res.status_code == 200:
            return re.sub(r'^(prompt:|visual prompt:|cinematic prompt:)\s*', '', res.text.strip(), flags=re.IGNORECASE)
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
            if res.status_code == 200:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception:
            pass
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
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
        elif motion == "Drone Shot":
            animated_clip = clip.resize(lambda t: 1.30 - 0.30 * (t / duration)).rotate(lambda t: 5 * (t / duration)).set_position('center')
        else:
            animated_clip = clip.resize(lambda t: 1.05 + 0.10 * (t / duration)).set_position('center')

        return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
    except Exception:
        pass
    try:
        return ImageClip(img_path).set_duration(duration).resize((w, h))
    except Exception:
        pass
    return None

def apply_clip_transition(clip, transition, duration):
    try:
        if transition == "Cross Dissolve (Fade)":
            return clip.fadein(0.4).fadeout(0.4)
        elif transition == "Flash Transition (White Glow)":
            return clip.fadein(0.2).fadeout(0.2)
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
    except Exception as e:
        st.error(f"Voice synthesis error: {e}")
        return False

# ==========================================
# 6. MASTER VIDEO GENERATOR CORE
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free & Unlimited)", pollinations_key="", video_model="wan-fast"):
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
            
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
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
                if not save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path):
                    raise Exception("Voice generation failed.")
                temporary_audio_tracks.append(sub_audio_path)
                
            progress_bar.progress(0.15)
            
            if enable_bg_music:
                status.info("🎵 Downloading Background Track...")
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
                    urdu_scene=scene,
                    char_memory=char_desc,
                    scene_memory=scene_desc,
                    character_heritage=character_heritage,
                    enable_islamic_filter=enable_islamic_filter,
                    raw_male_url=raw_male_url,
                    raw_female_url=raw_female_url
                )
                
                if not is_spiritual:
                    refined_p += " [Avoid cross-gender blending, absolutely no woman with beard, symmetrical eyes]"
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}"
                generated_prompts.append(refined_p)
                
                if "Real AI Video" in gen_mode and active_api_key:
                    status.info(f"🎥 Rendering 3D Video Frame {i+1} via {video_model}...")
                    aspect_param = "16:9" if "16:9" in ratio else "9:16"
                    motion_prompt = f"high motion, natural realistic animation, {refined_p[:350]}"
                    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt)}?model={video_model}&aspectRatio={aspect_param}&key={active_api_key}&duration=4"
                    
                    ref_url = raw_female_url if "saba" in scene.lower() else raw_male_url
                    if ref_url: vid_url += f"&image={urllib.parse.quote(ref_url)}"
                    
                    vid_path = f"v_{u_id}_{i}.mp4"
                    try:
                        res_vid = session.get(vid_url, timeout=90)
                        if res_vid.status_code == 200:
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
            status.info("🎨 Downloading Visual Frames in Parallel...")
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.55)
            status.info("🎞️ Assembling Audio Syncing and Camera Motions...")
            
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
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
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
# 7. ANTI-COPYRIGHT BYPASS ENGINE
# ==========================================
def process_anti_copyright_video(in_path, out_path, flip_h, spd, color_mod, add_grain, smart_zoom, shift_audio, border_mode, crop_margin):
    try:
        ffmpeg_cmd = get_ffmpeg()
        vf_filters = []
        
        if flip_h:
            vf_filters.append("hflip")
        if smart_zoom:
            vf_filters.append("scale=iw*1.04:ih*1.04,crop=iw/1.04:ih/1.04")
        if crop_margin > 0:
            vf_filters.append(f"crop=iw-{crop_margin*2}:ih-{crop_margin*2}:{crop_margin}:{crop_margin}")
        if color_mod:
            vf_filters.append("eq=contrast=1.05:brightness=0.02:saturation=1.08")
        if add_grain:
            vf_filters.append("noise=alls=12:allf=t+u")
        if border_mode:
            vf_filters.append("pad=iw+16:ih+16:8:8:color=black")
            
        vf_str = ",".join(vf_filters) if vf_filters else "null"
        
        af_filters = []
        if shift_audio:
            af_filters.append("asetrate=44100*1.03,aresample=44100")
        if spd != 1.0:
            vf_str += f",setpts={1/spd}*PTS"
            af_filters.append(f"atempo={spd}")
            
        af_str = ",".join(af_filters) if af_filters else "anull"
        
        cmd = [
            ffmpeg_cmd, "-y", "-i", in_path,
            "-vf", vf_str,
            "-af", af_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            out_path
        ]
        
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception:
        return False

# ==========================================
# 8. UI STYLING & NAVIGATION
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
        margin-top: 15px;
        margin-bottom: 5px;
        letter-spacing: 2px;
    }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 15px 0; }
    
    .circular-s {
        width: 120px; height: 120px; 
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 50px; color: #ffffff !important;
        border: 5px solid #ffffff !important;
        box-shadow: 0 0 50px #ff007a, inset 0 0 20px #ffffff;
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
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI ENTERPRISE STUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

tab_auth, tab_chat, tab_movie, tab_image, tab_bypass, tab_chars, tab_enterprise = st.tabs([
    "🔑 Sign In & Registrations",
    "💬 Electric AI Chat", 
    "🎬 Pro Master Studio", 
    "🎨 Pro Image Studio",
    "🛡️ Anti-Copyright Video Suite",
    "🎭 Character & Scene Library",
    "👤 Enterprise & Billing Center"
])

# -----------------
# TAB 1: AUTH
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
                    st.success(f"Welcome back, {u_name}! 🟢")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
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
                        st.success(f"Account '{new_u}' created! Please sign in. 🟢")
                    else:
                        st.error(msg)

# -----------------
# TAB 2: CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Creative Assistant")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask for a story idea, prompt, or video script..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]):
            translated_response = SGLOWINA_BIO
        else:
            try:
                res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true", timeout=15).text
                translated_response = res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")
            except Exception:
                translated_response = "I am ready to assist your creative productions."
        with st.chat_message("assistant"):
            st.write(translated_response)
            st.session_state.msgs.append({"role": "assistant", "content": translated_response})

# -----------------
# TAB 3: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Hollywood Power)")
    gen_mode = st.selectbox("Select Generator Engine:", [
        "Cinematic Photo Zoom & Pan (100% Free & Unlimited)", 
        "Real AI Video Motion (Beta - Pollinations Video API)"
    ])
    pollinations_key = ""
    if "Real AI Video" in gen_mode:
        pollinations_key = st.text_input("Enter Pollinations API Key (Optional if master key is set in Admin Panel):", type="password")
        
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=140, placeholder="مثال: ایک لڑکا گھنے جنگل میں تیزی سے دوڑ رہا ہے...")
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True)
    char_desc = st.text_input("Character Memory (کردار کا حلیہ):", placeholder="e.g. Saba is wearing a modest dark blue hijab")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Upload Male Reference Image:", type=["jpg", "png", "jpeg"])
    with col_up2:
        uploaded_female_img = st.file_uploader("Upload Female Reference Image:", type=["jpg", "png", "jpeg"])
        
    scene_desc = st.text_input("Scene Memory (ماحول):", placeholder="e.g. Deep green ancient forest, dark stormy night")

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Dark Gothic / Mystery"])
    
    mc6, mc7, mc8, mc9, mc10 = st.columns(5)
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Dolly In", "Orbit Camera", "Drone Shot"])
    with mc7: transition_style = st.selectbox("Transition:", ["Cross Dissolve (Fade)", "Flash Transition (White Glow)", "Instant Cut"])
    with mc8: character_heritage = st.selectbox("Attire Heritage:", ["Automatic", "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)", "Ancient Arabian", "Western / Modern"])
    with mc9: video_model = st.selectbox("Video Model:", ["wan-fast", "seedance", "veo"])
    with mc10: sd = st.number_input("Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Generating master cinematic movie..."):
            v_res = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate=rate_val, pitch=pitch_val, ratio=mr, style=ms, seed=sd,
                char_desc=char_desc, scene_desc=scene_desc, camera_motion=camera_motion, transition_style=transition_style,
                enable_watermark=enable_watermark, enable_bg_music=enable_bg_music, uploaded_male_img=uploaded_male_img,
                uploaded_female_img=uploaded_female_img, enable_islamic_filter=enable_islamic_filter, character_heritage=character_heritage,
                gen_mode=gen_mode, pollinations_key=pollinations_key, video_model=video_model
            )
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD 📥", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

# -----------------
# TAB 4: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual & Canva Overlay Studio")
    tab_txt, tab_img = st.tabs(["🎨 Text to Image", "📤 Image Modify & Canva Overlay"])
    
    with tab_txt:
        p_i = st.text_area("Describe Image (One per line for batch):", height=100)
        char_desc_img = st.text_input("Character Details for Image:", placeholder="e.g. A young girl, blue eyes, red scarf")
        canva_overlay_text = st.text_input("Canva Typography Banner Overlay:", placeholder="e.g. SGlowina Pro Studio")
        
        ic1, ic2, ic3 = st.columns(3)
        with ic1: i_style = st.selectbox("Style Preset:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
        with ic2: i_size = st.selectbox("Format Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
        with ic3: count = st.slider("Images Quantity:", 1, 4, 1)
        
        if st.button("Generate Visual Frames 🚀"):
            u_db = get_user_data(st.session_state.logged_in_user)
            if u_db and u_db['credits'] >= 2 * count:
                dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
                w, h = dim[i_size]
                prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
                for idx, single_p in enumerate(prompt_list):
                    for q in range(count):
                        final_p = f"Character: {char_desc_img.strip()}. Scene: {single_p}" if char_desc_img.strip() else single_p
                        img_data = fetch_img_failover(final_p, w, h, random.randint(1, 999999))
                        if img_data:
                            img_path_temp = f"temp_canvas_{idx}_{q}.jpg"
                            with open(img_path_temp, "wb") as f_temp:
                                f_temp.write(img_data)
                            if canva_overlay_text.strip():
                                apply_canva_typography(img_path_temp, canva_overlay_text.strip())
                            with Image.open(img_path_temp) as im:
                                st.image(im, caption=single_p[:40])
                            if os.path.exists(img_path_temp):
                                os.remove(img_path_temp)
                            deduct_user_credits(st.session_state.logged_in_user, 2)
                            log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
            else:
                st.error("Insufficient credits (Requires 2 credits per image).")

    with tab_img:
        uploaded_file = st.file_uploader("Upload Image:", type=["jpg", "png", "jpeg"])
        modify_prompt = st.text_input("Modification Instructions:", placeholder="e.g. Add volumetric neon light")
        canva_overlay_text_mod = st.text_input("Typography Overlay for Image:")
        
        if st.button("Modify & Re-render Image 🎨"):
            if uploaded_file and modify_prompt:
                u_db = get_user_data(st.session_state.logged_in_user)
                if u_db and u_db['credits'] >= 5:
                    img_data = fetch_img_failover(modify_prompt, 1024, 1024, random.randint(1, 999999))
                    if img_data:
                        img_path_temp_mod = "temp_canvas_mod.jpg"
                        with open(img_path_temp_mod, "wb") as f_temp_mod:
                            f_temp_mod.write(img_data)
                        if canva_overlay_text_mod.strip():
                            apply_canva_typography(img_path_temp_mod, canva_overlay_text_mod.strip())
                        with Image.open(img_path_temp_mod) as im:
                            st.image(im, caption="Modified Visual Output")
                        if os.path.exists(img_path_temp_mod):
                            os.remove(img_path_temp_mod)
                        deduct_user_credits(st.session_state.logged_in_user, 5)
                        log_credit_usage(u_db['id'], "Image Modification", 5, u_db['credits'] - 5)
                else:
                    st.error("Insufficient credits (Requires 5 credits).")

# -----------------
# TAB 5: ANTI-COPYRIGHT SUITE
# -----------------
with tab_bypass:
    st.write("### 🛡️ Dynamic Anti-Copyright Bypass Suite & Video Remixer")
    st.info("Bypass automated Content-ID audio & video filters using multi-layer dynamic transformation.")
    
    source_type = st.radio("Media Source:", ["Upload Local Video File", "Paste Video Link"])
    raw_video_in = "temp_bypass_input.mp4"
    processed_out = "temp_bypass_output.mp4"
    
    if source_type == "Upload Local Video File":
        up_v = st.file_uploader("Upload MP4 / MOV Video:", type=["mp4", "mov", "mkv"])
        if up_v:
            with open(raw_video_in, "wb") as f:
                f.write(up_v.read())
            st.session_state.process_ready = True
    else:
        v_url = st.text_input("Paste Direct Video URL:")
        if st.button("Fetch & Download Video 📥"):
            if v_url.strip():
                with st.spinner("Downloading stream..."):
                    try:
                        r = requests.get(v_url, headers=headers_browser, timeout=30)
                        if r.status_code == 200:
                            with open(raw_video_in, "wb") as f:
                                f.write(r.content)
                            st.session_state.process_ready = True
                            st.success("Video fetched successfully!")
                    except Exception as e:
                        st.error(f"Download failed: {e}")
                        
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        flip_h = st.checkbox("Horizontal Flip (Mirroring)", value=True)
        smart_zoom = st.checkbox("Smart 4% Dynamic Zoom", value=True)
    with col_b2:
        color_mod = st.checkbox("Color Grade & Contrast Shift", value=True)
        add_grain = st.checkbox("Anti-Bot Micro Noise Grain", value=True)
    with col_b3:
        shift_audio = st.checkbox("Pitch & Harmonic Audio Shift", value=True)
        border_mode = st.checkbox("Micro Edge Border", value=False)
        
    spd = st.slider("Playback Speed Factor:", 0.90, 1.15, 1.02, 0.01)
    crop_margin = st.slider("Edge Pixel Crop (px):", 0, 20, 4)
    
    if st.button("Process & Shield Video ⚡"):
        if os.path.exists(raw_video_in):
            with st.spinner("Applying anti-copyright bypass layers..."):
                ok = process_anti_copyright_video(
                    raw_video_in, processed_out, flip_h, spd, color_mod, add_grain, smart_zoom, shift_audio, border_mode, crop_margin
                )
                if ok and os.path.exists(processed_out):
                    st.success("Video Shielded & Processed Successfully! 🟢")
                    st.video(processed_out)
                    with open(processed_out, "rb") as pf:
                        st.download_button("Download Shielded Video 📥", pf.read(), file_name="Bypassed_Video.mp4")
                else:
                    st.error("Processing failed. Please check video codecs.")
        else:
            st.warning("Please upload or provide a video first.")

# -----------------
# TAB 6: CHARACTERS & SCENES
# -----------------
with tab_chars:
    st.write("### 🎭 Saved Characters & Scene Consistency Library")
    t_ch, t_sc = st.tabs(["👤 Characters", "🌄 Environments & Scenes"])
    
    with t_ch:
        with st.form("new_char_form"):
            c_name = st.text_input("Character Name (e.g. Saba / Essa):")
            c_desc = st.text_area("Detailed Appearance & Modest Attire:")
            if st.form_submit_button("Save Character 💾"):
                if c_name and c_desc:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT OR REPLACE INTO characters (id, user_id, character_name, description, reference_data) VALUES (?, ?, ?, ?, ?)",
                                (str(uuid.uuid4())[:8], 1, c_name, c_desc, ""))
                    conn.commit()
                    conn.close()
                    st.success(f"Character '{c_name}' saved!")
                    
    with t_sc:
        with st.form("new_scene_form"):
            s_name = st.text_input("Scene Preset Name:")
            s_env = st.text_area("Environment & Lighting:")
            if st.form_submit_button("Save Scene Preset 💾"):
                if s_name and s_env:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT OR REPLACE INTO scenes (id, user_id, scene_name, environment, lighting, camera_style) VALUES (?, ?, ?, ?, ?, ?)",
                                (str(uuid.uuid4())[:8], 1, s_name, s_env, "Cinematic", "Auto"))
                    conn.commit()
                    conn.close()
                    st.success(f"Scene preset '{s_name}' saved!")

# -----------------
# TAB 7: ENTERPRISE & BILLING
# -----------------
with tab_enterprise:
    st.write("### 👤 Enterprise Administration & Billing Center")
    ent_tab_user, ent_tab_billing, ent_tab_admin = st.tabs(["👤 User Profile", "💳 Billing & Credits", "🔒 Admin Panel"])
    u_db = get_user_data(st.session_state.logged_in_user)
    
    with ent_tab_user:
        if u_db:
            st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
        else:
            st.warning("Please sign in.")
            
    with ent_tab_billing:
        st.write("### 🎁 Redeem Coupon Code")
        with st.form("coupon_form"):
            coupon_code = st.text_input("Enter Coupon (e.g. ESSASABA):")
            if st.form_submit_button("Redeem 🎁") and u_db and coupon_code.strip():
                conn = get_db_connection()
                curr = conn.cursor()
                curr.execute("SELECT * FROM coupons WHERE UPPER(code) = UPPER(?)", (coupon_code.strip(),))
                c_row = curr.fetchone()
                if c_row and c_row['uses_left'] > 0:
                    curr.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (c_row['credits'], u_db['id']))
                    curr.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (c_row['code'],))
                    conn.commit()
                    st.success(f"{c_row['credits']} credits added successfully! 🟢")
                else:
                    st.error("Invalid or expired coupon code.")
                conn.close()

        st.write("---")
        st.write("### 🇵🇰 Easypaisa / JazzCash Local Payment Confirmation")
        with st.form("local_pay_form"):
            pay_method = st.selectbox("Method:", ["JazzCash", "Easypaisa", "Bank Transfer"])
            trx_id = st.text_input("Transaction ID (TID):")
            amount = st.number_input("Amount (PKR):", value=500, step=100)
            if st.form_submit_button("Submit Payment Verification 📤"):
                if trx_id.strip():
                    conn = get_db_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, 'Pending', ?)",
                                    (str(uuid.uuid4())[:8], st.session_state.logged_in_user, pay_method, trx_id.strip(), amount, time.strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.success("Payment submitted! Admin will verify and top-up credits.")
                    except Exception:
                        st.error("Transaction ID already submitted.")
                    conn.close()

    with ent_tab_admin:
        if u_db and u_db['role'] == 'Admin':
            st.success("Administrator Mode Active 🟢")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'master_pollinations_key'")
            m_row = cursor.fetchone()
            current_key = m_row['value'] if m_row else ""
            
            with st.form("master_key_form"):
                new_key = st.text_input("Set Global Master API Key:", value=current_key, type="password")
                if st.form_submit_button("Save Global Master Key 💾"):
                    cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('master_pollinations_key', ?)", (new_key.strip(),))
                    conn.commit()
                    st.success("Master key saved globally!")
            conn.close()
        else:
            st.error("Administrator access only.")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px;'>Sglowina AI Enterprise V2.1 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
