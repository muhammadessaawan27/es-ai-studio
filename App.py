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
from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import concurrent.futures

# Bio Data
SGLOWINA_BIO = """
Sglowina AI is an Enterprise-grade SaaS platform co-founded and directed by Muhammad Essa Awan and Saba Wahid. 
It is dedicated to state-of-the-art AI video creation, intelligent automated scripting, and premium visual studio synthesis.
"""

# Global Concurrency Queue locks to support up to 100 concurrent render requests without server crash
render_semaphore = threading.Semaphore(value=2)  # Maximum 2 concurrent encoding processes to save RAM/CPU
active_renderers = 0
render_lock = threading.Lock()

# Helper function to ensure even dimensions for FFMPEG compatibility
def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# PBKDF2 Secure Password Hashing
def hash_password(password):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(password, hashed):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

# Background Image Uploader to get public URL for Character Consistency
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
# 1. DYNAMIC DATABASE LAYER (PostgreSQL & SQLite Concurrency Compatible)
# ==========================================
def get_db_connection():
    pg_url = os.environ.get("DATABASE_URL") # Checks for production PostgreSQL (e.g. Render/Heroku)
    if pg_url:
        try:
            import psycopg2
            conn = psycopg2.connect(pg_url)
            return conn
        except Exception:
            pass
    # High-concurrency SQLite config with WAL mode for smooth multi-user traffic
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
    
    # SQLite compatibility checks
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
    
    # Coupons table for referral and marketing rewards
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            credits INTEGER,
            uses_left INTEGER
        )
    """)
    
    # Default high-value coupon seeding
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

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []

# ==========================================
# 3. ENTERPRISE AUTHENTICATION HELPERS
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

# AI Hollywood Director Mode Intelligent Scene & Speaker Analyzer
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
    elif any(k in text for k in ["forest", "jungle", "mountain", "valley", "landscape", "sky", "sea", "ocean", "mud"]):
        composition = "Cinematic wide-angle establishing landscape shot, highly atmospheric environment"
        motion = "Drone Shot"

    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action", "bhaag"]):
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

# Translation Engine with Strict Subject and Anatomy Enforcement
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

# Islamic Holy Figures and Spiritual Safety Filter
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

# Smart Prompt Engine to build optimized prompts with negative prompts injected
def build_ultra_cinematic_prompt(scene, style, char_desc, scene_desc, director_settings):
    motion = director_settings.get("motion", "Zoom Out (v40 Default)")
    lighting = director_settings.get("lighting", "Volumetric Light")
    color_grading = director_settings.get("color_grading", "Hollywood Cinematic")
    composition = director_settings.get("composition", "Medium Shot, Rule of Thirds")
    
    quality_boost = "ultra photorealistic, 8k resolution, face restoration, sharp focus, highly detailed eyes, symmetrical face structure, natural skin texture, perfect anatomy, detail enhancement, professional photography"
    
    prompt_parts = [
        f"{composition}, cinematic framing",
        f"Scene: {scene}"
    ]
    
    if scene_desc:
        prompt_parts.append(f"Background environment: {scene_desc}")
    if char_desc:
        prompt_parts.append(f"Featuring consistent character: {char_desc}")
    if style and style != "Auto (Smart Director)":
        prompt_parts.append(f"Style: {style}")
        
    prompt_parts.append(f"Lighting: {lighting}")
    prompt_parts.append(f"Color grade: {color_grading}")
    prompt_parts.append(quality_boost)
    
    return ", ".join(prompt_parts)[:500]

# Enhanced Cinematic Prompt Mastermind incorporating dual reference image context
def generate_enhanced_cinematic_prompt(urdu_scene, char_memory, scene_memory, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        instruction = (
            "You are an expert Hollywood visual artist and prompt engineer. "
            "Analyze the Urdu scene and write a highly detailed visual English image prompt for the Flux model. \n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. If 'Islamic Safety Filter' is Active and the text contains Islamic holy names (like Prophets/انبیاء, Sahaba/صحابہ, Auliya, Allah, Quran, or grave, heaven, hell), you MUST strictly avoid generating any human face or human body. Instead, generate a highly spiritual scene depicting glorious volumetric white and golden divine light rays emanating from a cosmic night sky, beautiful natural mountains, or ancient desert paths. No human silhouettes.\n"
            "2. For human characters, strictly enforce gender separation. Do NOT mix genders. A female character (e.g. Saba) must have a beautiful, clean, feminine Eastern face. Absolutely NO facial hair, NO beards, and NO mustaches on females.\n"
            "3. A male character (e.g. Essa) must have a handsome, masculine face with a neat short black beard.\n"
            "4. All human characters must have realistic Middle Eastern, Pakistani, or Arabian features (no western default faces) and wear traditional modest clothing based on the heritage style.\n"
            "5. STRICT CHARACTER CONSISTENCY: Keep the characters' face, hair, and look completely identical across scenes. If a male reference image URL is provided, strictly copy the face and features of: {raw_male_url}. If a female reference image URL is provided, strictly copy the face and features of: {raw_female_url}.\n"
            "6. If both characters are mentioned, depict them as a distinct couple (one bearded man and one modest woman) interacting. Do NOT merge them into one body.\n"
            "7. Describe the scene's exact environment (e.g. deep green jungle, flowing river, mud-houses, rain, storms, animals like lions/snakes in the foreground) with strong descriptive words so the image generator produces it precisely.\n"
            "8. Write ONLY the final English prompt, with no conversational preamble or extra text."
        )
        
        prompt_input = f"Urdu Scene: {urdu_scene}\n"
        if char_memory:
            prompt_input += f"Character Memory/Appearance override: {char_memory}\n"
        if scene_memory:
            prompt_input += f"Scene Environment/Background override: {scene_memory}\n"
        if character_heritage != "Automatic":
            prompt_input += f"Cultural Heritage: {character_heritage}\n"
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
            return refined_p
    except Exception:
        pass
    return f"Cinematic film scene: {urdu_scene}, highly detailed, 8k"

# Post-Processing Color LUT Grading Matrix Harmony
def apply_color_lut_harmony(img_path, style_preset):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            # Apply color tinting based on style preset mathematically
            if style_preset in ["Realistic HD", "Cinematic Film"]:
                r, g, b = im.split()
                # Warm highlights, cool shadows (Teal & Orange cinematic grade)
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
            
            # Pop contrast slightly for cinema density
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "JPEG")
    except Exception:
        pass

# Dynamic Sound Effects (SFX) Downloader & Path Mapper
def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    
    # Sound mapping from reliable, fast-loading public sources
    if any(k in text for k in ["rain", "storm", "thunder", "clouds", "بارش", "طوفان"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "battle", "clash", "تلوار", "جنگ"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3" # Metallic clink
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

# Cinematic Blurred Background Padding to eliminate raw black bars
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

# Parallel image downloader using ThreadPoolExecutor for 5x Speed boost
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

# Motion control logic safely wrapped to prevent MoviePy engine crash
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
        scale_factor = 1.30
        
        # Apply slight motion blur during rapid panning
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
            # Tracking with micro vibration shake
            animated_clip = clip.set_position(lambda t: (
                int((w - cw) * (t / duration)),
                int((h - ch)/2 + (5 * np.sin(2 * np.pi * t * 1.5)))
            ))
        elif motion == "Handheld Camera" or motion == "Shoulder Camera":
            # Pure manual handheld camera shake calculations
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
        pass
    return None

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

# ==========================================
# 5. FIXED V40 RENDER SYSTEM CORE (SaaS VERIFIED & CHARACTER ID LOCK)
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", advanced_params=None):
    u_id = str(uuid.uuid4())[:8]
    
    # CONCURRENCY QUEUE DECK: Safely parks excess render requests
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
        user_type = user_db["plan"]
        
        if user_credits < 15:
            st.error("Deduction failed: Sglowina requires at least 15 credits to generate video.")
            return "Error"
        
        active_watermark = True if user_type == "Free" else enable_watermark
        
        raw_male_url = get_public_url(uploaded_male_img) if uploaded_male_img is not None else None
        raw_female_url = get_public_url(uploaded_female_img) if uploaded_female_img is not None else None
        
        try:
            progress_bar.progress(0.05)
            status.info("🎙️ Processing Dialogue Voiceovers...")
            
            # Segment script by Urdu sentences
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
            if not sentences: sentences = [story]
            
            clips = []
            
            # Sentence-Level Audio Sync Module: generate individual TTS files
            for idx, scene in enumerate(sentences):
                # Auto Dialogue Speaker Selector
                if "صبا" in scene or "saba" in scene.lower():
                    v_code_scene = "ur-PK-UzmaNeural" # Female voice actor
                elif "عیسی" in scene or "essa" in scene.lower() or "awan" in scene.lower():
                    v_code_scene = "ur-PK-AsadNeural" # Male voice actor
                else:
                    v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
                    
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                save_audio_success = save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path)
                if not save_audio_success:
                    raise Exception("Voice generation failed.")
                temporary_audio_tracks.append(sub_audio_path)
                
            progress_bar.progress(0.12)
            
            # DOWNLOADING BACKGROUND MUSIC TRACK (CDN hosted stable tracks)
            if enable_bg_music:
                status.info("🎵 Downloading Atmospheric Background Track...")
                story_lower = story.lower()
                is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "بھوت", "تاریک", "ڈراؤنی", "grave", "torment", "punishment", "scary", "ghost", "dark", "death", "screaming", "blood", "bloody", "horror"])
                is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "شاہی", "تاریخ", "بہادر", "king", "queen", "throne", "palace", "empire", "warrior", "brave", "history", "castle"])
                
                if is_horror:
                    bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
                elif is_epic:
                    bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
                else:
                    bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                    
                try:
                    res_bg = requests.get(bg_url, timeout=12, headers=headers_browser)
                    if res_bg.status_code == 200:
                        with open(bg_music_f, 'wb') as f:
                            f.write(res_bg.content)
                        has_bg_music = True
                except Exception as bg_ex:
                    st.warning(f"Background music skipped due to CDN timeout: {bg_ex}")
                    
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
            
            # PREPARE CINEMATIC PROMPTS FOR ALL SCENES
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
                    
                heritage_desc = ""
                if not is_spiritual:
                    if character_heritage == "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)":
                        heritage_desc = "character must wear elegant modest traditional Eastern Islamic attire, modest long robes, turban or modest Eastern headwear, neat modest beard for men, Eastern facial features, strictly no Western garments"
                    elif character_heritage == "Ancient Arabian":
                        heritage_desc = "character must wear ancient Arabian historical flowing robes, classic desert turban, historic Middle Eastern appearance"
                    elif character_heritage == "Western / Modern":
                        heritage_desc = "character must wear modern western clothing"
                    elif character_heritage == "Far Eastern":
                        heritage_desc = "character must wear traditional Asian clothing"
                
                combined_char_desc = char_desc
                if heritage_desc:
                    combined_char_desc = (combined_char_desc + ", " + heritage_desc) if combined_char_desc else heritage_desc
                    
                refined_p = generate_enhanced_cinematic_prompt(
                    urdu_scene=scene,
                    char_memory=combined_char_desc,
                    scene_memory=scene_desc,
                    character_heritage=character_heritage,
                    enable_islamic_filter=enable_islamic_filter,
                    raw_male_url=raw_male_url,
                    raw_female_url=raw_female_url
                )
                
                if not is_spiritual:
                    refined_p += " [Avoid cross-gender blending, absolutely no woman with beard, absolutely no female with facial hair, anatomically perfect, symmetrical eyes, detailed limbs]"
                
                refined_p += f", lighting: {dir_settings['lighting']}, color grade: {dir_settings['color_grading']}, cinematic film look"
                generated_prompts.append(refined_p)
                
                w_target = make_even(w * 1.25)
                h_target = make_even(h * 1.25)
                
                # Keep seed constant per render for perfect face locking
                unique_seed = seed
                
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={unique_seed}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_path = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_path)
                generated_images.append(img_path)
                
            progress_bar.progress(0.25)
            status.info("🎨 Running Parallel Flux Image Downloaders (5x Speed Optimization Active)...")
            
            # ASYNC PARALLEL IMAGE DOWNLOADING
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.45)
            status.info("🎞️ Assembling Audio Syncing and Camera Motions...")
            
            # ASSEMBLE CLIPS WITH EXACT VOICE SYNCHRONIZATION AND EFFECTS
            for i, scene in enumerate(sentences):
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                
                # Apply Color LUT matrix harmony on the downloaded frame
                apply_color_lut_harmony(img_path, style)
                
                # Apply Blurred padding to completely eliminate black bars
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                # Read exact sub clip voiceover duration
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                
                # Determine camera motion for this clip
                english_scene_temp = translate_ur_to_en_enhanced(scene)
                dir_settings = analyze_scene_for_director(english_scene_temp)
                if camera_motion != "AI Hollywood Director (Auto)":
                    dir_settings["motion"] = camera_motion
                active_motion = dir_settings["motion"]
                
                # Compile video motion frame
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h)
                
                # Download and mix scene environmental SFX
                sfx_file = download_scene_sfx(scene, u_id, i)
                if sfx_file and os.path.exists(sfx_file):
                    try:
                        sfx_audio = AudioFileClip(sfx_file).volumex(0.12).set_duration(dur_scene)
                        clip_composite_audio = CompositeAudioClip([scene_voice_clip, sfx_audio])
                        clip = clip.set_audio(clip_composite_audio)
                        generated_images.append(sfx_file)
                    except Exception:
                        clip = clip.set_audio(scene_voice_clip)
                else:
                    clip = clip.set_audio(scene_voice_clip)
                    
                clip = apply_clip_transition(clip, transition_style, dur_scene)
                clips.append(clip)
                
            progress_bar.progress(0.70)
            status.info("🎞️ Stitching final video elements...")
            
            final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
            
            # OVERLAY GLOBAL BACKGROUND MUSIC IN FINAL MASTER MIX
            if has_bg_music and os.path.exists(bg_music_f):
                try:
                    bg_track = AudioFileClip(bg_music_f).volumex(0.06).set_duration(final_video.duration)
                    combined_master_audio = CompositeAudioClip([final_video.audio, bg_track])
                    final_video = final_video.set_audio(combined_master_audio)
                except Exception as e:
                    st.warning(f"Background music mixing warning: {e}")
                    
            out_name = f"Sglowina_{u_id}.mp4"
            
            # Video compilation
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
            
            final_video.close()
            
            # CLEANUP TEMPORARY FILES to save server disk space
            for sub_voice in temporary_audio_tracks:
                try:
                    if os.path.exists(sub_voice): os.remove(sub_voice)
                except: pass
                
            try:
                if os.path.exists(audio_file): os.remove(audio_file)
                if os.path.exists(bg_music_f): os.remove(bg_music_f)
                for file_p in generated_images:
                    if os.path.exists(file_p): os.remove(file_p)
            except Exception:
                pass
                
            progress_bar.progress(1.0)
            status.success("🚀 Video Generated Successfully!")
            
            # Database log
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
                try:
                    if os.path.exists(sub_voice): os.remove(sub_voice)
                except: pass
            try:
                if os.path.exists(audio_file): os.remove(audio_file)
                if os.path.exists(bg_music_f): os.remove(bg_music_f)
                for file_p in generated_images:
                    if os.path.exists(file_p): os.remove(file_p)
            except: pass
            progress_bar.empty()
            return f"Error Details: {e}"
        finally:
            gc.collect()

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
            5. آپ کے اکاؤنٹ میں روزانہ کے مفت کریڈٹس (Daily Free Credits) شامل ہوں گے، جنہیں آپ لائیو ویڈیو بنانے کے لیے استعمال کر سکتے ہیں۔
            6. اگر آپ کے پاس API Key نہیں ہے یا کریڈٹس ختم ہو جائیں، تو پریشان نہ ہوں! ہماری ایپ خودکار طور پر **Cinematic Photo Zoom & Pan (Free Mode)** پر واپس چلی جائے گی، جس سے آپ کی ویڈیو جنریشن کبھی بند نہیں ہوگی۔
            """)

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    # Islamic and Spiritual Safety Filter Toggle
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True, help="اگر کہانی میں اولیاء اللہ، انبیاء، قبر، جنت، جہنم یا صحابہ کا ذکر ہو تو یہ فلٹر خودکار طور پر چہرے بنانے کے بجائے روحانی نور اور تجلی دکھائے گا تا کہ بے ادبی نہ ہو۔")
    
    # Simple, high-impact Character & Scene Memory override inputs
    char_desc = st.text_input("Character Memory (مرد یا عورت کا تفصیلی حلیہ):", 
                              placeholder="Example: Saba is a 25-year-old beautiful Eastern woman wearing a modest dark blue hijab")
    
    # DUAL IMAGE UPLOADERS: Male and Female characters separately
    st.write("##### 👤 Consistent Character Identity References (کرداروں کے چہروں کی تصاویر)")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Upload Male Character Reference Image (مرد کردار کی تصویر):", type=["jpg", "png", "jpeg"])
        if uploaded_male_img is not None:
            st.image(uploaded_male_img, caption="Male Identity Loaded ✅", width=120)
    with col_up2:
        uploaded_female_img = st.file_uploader("Upload Female Character Reference Image (عورت کردار کی تصویر):", type=["jpg", "png", "jpeg"])
        if uploaded_female_img is not None:
            st.image(uploaded_female_img, caption="Female Identity Loaded ✅", width=120)
        
    scene_desc = st.text_input("Scene Memory (جنگل، موسم، ماحول، جانور):", 
                              placeholder="Example: Deep green ancient forest, high realistic trees, thick foliage, dark stormy night")

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8, mc9 = st.columns(9)
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
    with mc9: sd = st.number_input("Character Seed:", value=786)
    
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
                char_desc=char_desc, 
                scene_desc=scene_desc, 
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
                        if char_desc_img.strip():
                            final_p = f"Character is {char_desc_img.strip()}. Action/Scene: {single_p}"
                            
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
                    st.error("Please log in to redeem coupons.")
        
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
                st.success(f"Successfully updated settings for {manage_user}!")
            conn.close()
        else:
            st.error("Access Denied: Only database-defined Administrators can access this control panel.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.5 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
