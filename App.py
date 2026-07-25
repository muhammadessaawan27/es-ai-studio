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
from PIL import Image, ImageDraw, ImageFont, ImageStat
import io
import numpy as np
import threading
import gc
import sqlite3
import hashlib

# Bio Data
SGLOWINA_BIO = """
Sglowina AI is an Enterprise-grade SaaS platform co-founded and directed by Muhammad Essa Awan and Saba Wahid. 
It is dedicated to state-of-the-art AI video creation, intelligent automated scripting, and premium visual studio synthesis.
"""

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
                # Convert view URL to direct file download URL for Pollinations
                raw_url = temp_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                return raw_url
    except Exception:
        pass
    return None

# ==========================================
# 1. DATABASE CONFIGURATION (SQLITE SAAS LAYER)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credits_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            credits_used INTEGER,
            balance_after INTEGER,
            date TEXT
        )
    """)
    
    # Secure Local Payment Request Ledger
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
    
    # Secure force seeding for administrative passwords (including the unified EssaSaba login)
    h_admin = hash_password("786")
    
    # 1. New Combined Founder User: EssaSaba (Password: 786)
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'essasaba'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("essasaba", "essasaba@sglowina.ai", h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = 'essasaba'", (h_admin,))

    # 2. Individual Admin: essa_awan (Password: 786)
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'essa_awan'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("essa_awan", "essa@sglowina.ai", h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = 'essa_awan'", (h_admin,))
                       
    # 3. Individual Admin: saba_wahid (Password: 1234)
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
    except sqlite3.IntegrityError:
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
# 4. INDUSTRIAL STABILITY & LOAD BALANCING
# ==========================================
session = requests.Session()
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session.headers.update(headers_browser)

adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
    from moviepy.video.fx.all import fadein
except Exception:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
        import moviepy.video.fx.all as vfx
        fadein = vfx.fadein
    except Exception:
        pass

# ==========================================
# 5. UI & PREMIUM BRANDING STYLING (V2.1)
# ==========================================
st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V2.1", layout="wide", page_icon="🎬")

# Sidebar Settings (Rendered strictly once to avoid duplicate widget keys)
st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=True)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=True)

# Sglowina Enterprise Center sidebar credits log
st.sidebar.markdown("---")
st.sidebar.subheader("👤 Sglowina Enterprise Center")
st.sidebar.write(f"Logged in as: **{st.session_state.logged_in_user}**")
u_sidebar_db = get_user_data(st.session_state.logged_in_user)
if u_sidebar_db:
    st.sidebar.write(f"Credits Remaining: **{u_sidebar_db['credits']}** 🪙")
    st.sidebar.write(f"Plan: **{u_sidebar_db['plan']}**")
else:
    st.sidebar.write("Credits Remaining: **Guest Mode**")
    st.sidebar.write("Plan: **Free Trial**")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    /* شاندار چمکدار نیون پنک اور الیکٹرک بلیو لائٹنگ ٹائٹل کے لیے (صحیح سائز میں فٹ) */
    .glow-title { 
        font-size: 2.2rem; 
        font-weight: 900; 
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 15px rgba(255, 0, 122, 0.2);
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
        animation: rotateShua 4s infinite linear, lightningGlow 1.5s infinite alternate;
    }
    
    @keyframes rotateShua {
        0% { transform: perspective(1000px) rotateY(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg); }
    }
    @keyframes lightningGlow {
        0%, 100% { box-shadow: 0 0 25px #2563eb, 0 0 50px #ff007a, inset 0 0 15px #ffffff; }
        50% { box-shadow: 0 0 50px #ff007a, 0 0 80px #00d4ff, inset 0 0 25px #ffffff; }
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
    
    div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.3s ease !important;
    }
    div[data-baseweb="textarea"] textarea:focus, div[data-baseweb="input"] input:focus {
        border-color: #00d4ff !important;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.2) !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="textarea"] textarea::placeholder, div[data-baseweb="input"] input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 6. SAAS INTEGRATED CORE ENGINE & UTILS
# ==========================================
def apply_canva_typography(image_path, text):
    try:
        with Image.open(image_path) as im:
            draw = ImageDraw.Draw(im)
            w, h = im.size
            font_size = int(h * 0.06)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            
            text_width = len(text) * (font_size * 0.5)
            x = int((w - text_width) / 2) if w > text_width else 20
            y = int(h * 0.82)
            
            draw.text((x + 3, y + 3), text, fill=(0, 0, 0), font=font)
            draw.text((x, y), text, fill=(255, 223, 0), font=font)
            im.save(image_path, "JPEG")
    except Exception:
        pass

def run_ai_prompt_assistant(story_text):
    try:
        instruction = (
            "Analyze this story and breakdown into these exact fields: "
            "1. Scene Breakdown, 2. Character Description, 3. Scene Memory, "
            "4. Camera Prompt, 5. Image Prompt, 6. Video Prompt. Output only these six fields."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' Story: ' + story_text)}?model=openai"
        res = session.get(url, timeout=20)
        if res.status_code == 200:
            return res.text
    except Exception:
        pass
    return "Failed to analyze story."

# AI Hollywood Director Mode Intelligent Scene Analyzer
def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    
    # Defaults
    motion = "Zoom Out (v40 Default)"
    lighting = "Volumetric Light"
    color_grading = "Hollywood Cinematic"
    composition = "Medium Shot, Rule of Thirds"
    
    # Analyze motions dynamically
    if any(k in text for k in ["run", "chase", " भाग", "بھاگ", "دوڑ", "fast", "speed", "action"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["crying", "sad", "رویا", "اداس", "آنسو", "tears", "love", "eyes", "face", "look"]):
        motion = "Push In"
    elif any(k in text for k in ["scary", "ghost", "خوفناک", "بھوت", "ڈراؤنی", "grave", "dark", "shadow"]):
        motion = "Dolly In"
        lighting = "Dark Cinematic, Horror Shadows"
        color_grading = "Horror Green"
    elif any(k in text for k in ["palace", "castle", "mountain", "valley", "سلطنت", "محل", "پہاڑ", "وسیع", "landscape", "sky", "sea", "ocean"]):
        motion = "Drone Shot"
        composition = "Extreme Wide Shot"
    elif any(k in text for k in ["king", "throne", "emperor", "بادشاہ", "تخت"]):
        motion = "Crane Shot"
        composition = "Wide Shot, Low Angle"
    elif any(k in text for k in ["fight", "battle", "sword", "جنگ", "تلوار"]):
        motion = "Handheld Camera"
    elif any(k in text for k in ["walk", "stroll", "چل رہا", "چلتے"]):
        motion = "Follow Shot"
    elif any(k in text for k in ["think", "silent", "quiet", "صبر", "سوچ"]):
        motion = "Ken Burns Effect"
        composition = "Close-up"
    else:
        motion = random.choice(["Zoom In", "Zoom Out (v40 Default)", "Parallax Motion", "Orbit Camera", "Ken Burns Effect"])
        
    # Tone and Lighting detection
    if any(k in text for k in ["نماز", "دعا", "مسجد", "ولی", "صبر", "سکون", "اللہ", "holy", "pray", "prayer", "mosque", "peace"]):
        lighting = "Golden Hour"
        color_grading = "Warm"
    elif any(k in text for k in ["night", "رات", "اندھیرا"]):
        lighting = "Moonlight"
        color_grading = "Cold Blue"
        
    return {
        "motion": motion,
        "lighting": lighting,
        "color_grading": color_grading,
        "composition": composition
    }

# Smart Prompt Engine to build optimized prompts
def build_ultra_cinematic_prompt(scene, style, char_desc, scene_desc, director_settings):
    motion = director_settings.get("motion", "Zoom Out (v40 Default)")
    lighting = director_settings.get("lighting", "Volumetric Light")
    color_grading = director_settings.get("color_grading", "Hollywood Cinematic")
    composition = director_settings.get("composition", "Medium Shot, Rule of Thirds")
    
    # 10/10 quality keywords boost
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

# Motion control logic safely wrapped to prevent MoviePy engine crash (Dynamic Slide bounding boxes)
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
        scale_factor = 1.30
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

# Translate Urdu text automatically to english
def translate_ur_to_en(text):
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote('Translate this text to English visual instructions, output translation only: ' + text)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return text

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
# 7. FIXED V40 RENDER SYSTEM CORE (SaaS VERIFIED & CHARACTER ID LOCK)
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_char_img=None, gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", advanced_params=None):
    u_id = str(uuid.uuid4())[:8]
    progress_bar = st.progress(0.0)
    status = st.empty()
    
    audio_file = f"a_{u_id}.mp3"
    bg_music_f = f"bg_{u_id}.mp3"
    generated_images = []
    generated_prompts = []
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
    
    # Get public URL of consistent character image
    raw_char_url = get_public_url(uploaded_char_img) if uploaded_char_img is not None else None
    
    final_char_desc = char_desc
    if raw_char_url:
        final_char_desc += f" (Strictly maintain identical facial appearance, age, gender, clothing, hair, and identical features matching the reference character image: {raw_char_url})"
    
    try:
        progress_bar.progress(0.05)
        status.info("🎙️ Generating Voiceover Track...")
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        
        save_audio_success = save_audio_safe(story, v_code, rate, pitch, audio_file)
        if not save_audio_success:
            raise Exception("Voice generation failed.")
            
        voice_audio = AudioFileClip(audio_file)
        progress_bar.progress(0.15)
        
        if enable_bg_music:
            status.info("🎵 Downloading Atmospheric Background Track...")
            story_lower = story.lower()
            is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "بھوت", "تاریک", "ڈراؤنی", "grave", "torment", "punishment", "scary", "ghost", "dark", "death", "screaming", "blood", "bloody", "horror"])
            is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "شاہی", "تاریخ", "بہادر", "king", "queen", "throne", "palace", "empire", "warrior", "brave", "history", "castle"])
            is_peaceful = any(k in story_lower or k in story for k in ["نماز", "دعا", "مسجد", "ولی", "صبر", "سکون", "اللہ", "pray", "prayer", "mosque", "peace", "peaceful", "sad", "crying", "tears"])
            
            if is_horror:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/1/18/Beethoven_-_Moonlight_Sonata_-_1st_movement.mp3"
            elif is_epic:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/d/df/Johann_Sebastian_Bach_-_Air_on_the_G_String_-_arranged_for_piano_and_violin.mp3"
            elif is_peaceful:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/e/e6/Chopin_-_Nocturne_op._9_no._2.mp3"
            else:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/e/e6/Chopin_-_Nocturne_op._9_no._2.mp3"
                
            try:
                res_bg = session.get(bg_url, timeout=20, verify=False)
                if res_bg.status_code == 200:
                    with open(bg_music_f, 'wb') as f:
                        f.write(res_bg.content)
                    has_bg_music = True
            except:
                pass
                
        progress_bar.progress(0.20)
        
        # Dimensions mapping
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
        
        # Split by Sentences
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        
        # v40 RENDER PIPELINE CORE FLOW
        for i, scene in enumerate(sentences):
            progress_bar.progress(0.20 + (i / len(sentences)) * 0.60)
            status.info(f"🎨 Generating visual scene {i+1}...")
            
            # Translate Urdu story block directly to English to ensure accurate context matching
            english_scene = translate_ur_to_en(scene)
            
            # Get default analyzed settings from AI Director
            dir_settings = analyze_scene_for_director(english_scene)
            
            # Override if user selected a specific non-auto motion
            if camera_motion != "AI Hollywood Director (Auto)":
                dir_settings["motion"] = camera_motion
                
            # Respect other Advanced Controls if modified from 'Auto'
            if advanced_params:
                if advanced_params.get("v_lighting") != "Auto (Smart Director)":
                    dir_settings["lighting"] = advanced_params.get("v_lighting")
                if advanced_params.get("v_color") != "Auto (Smart Director)":
                    dir_settings["color_grading"] = advanced_params.get("v_color")
                if advanced_params.get("v_env") != "Auto (Smart Director)":
                    scene_desc = (scene_desc + ", " + advanced_params.get("v_env")) if scene_desc else advanced_params.get("v_env")
                if advanced_params.get("v_weather") != "Auto (Smart Director)":
                    scene_desc = (scene_desc + ", " + advanced_params.get("v_weather")) if scene_desc else advanced_params.get("v_weather")
                if advanced_params.get("v_mood") != "Auto (Smart Director)":
                    dir_settings["composition"] = dir_settings["composition"] + f", {advanced_params.get('v_mood')} mood"
            
            active_motion = dir_settings["motion"]
            
            # Build smart descriptive prompt with Flux optimized composition and styling rules
            refined_p = build_ultra_cinematic_prompt(english_scene, style, final_char_desc, scene_desc, dir_settings)
            generated_prompts.append(refined_p)
            
            # --- Real AI Video Video Mode (WAN-FAST) ---
            if "Real AI Video" in gen_mode and pollinations_key.strip():
                status.info(f"🎥 Rendering 3D Video Frame {i+1} via Wan-Fast API...")
                aspect_ratio_param = "16:9" if "16:9" in ratio else "9:16"
                vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(refined_p)}?model=wan-fast&aspectRatio={aspect_ratio_param}&key={pollinations_key}&duration=4"
                if raw_char_url:
                    vid_url += f"&image={urllib.parse.quote(raw_char_url)}"
                vid_path = f"v_{u_id}_{i}.mp4"
                try:
                    res_vid = session.get(vid_url, timeout=90)
                    if res_vid.status_code == 200:
                        with open(vid_path, "wb") as f_vid:
                            f_vid.write(res_vid.content)
                        clip = VideoFileClip(vid_path).resize((w, h)).set_duration(dur_per)
                        clip = apply_clip_transition(clip, transition_style, dur_per)
                        clips.append(clip)
                        generated_images.append(vid_path) 
                        continue
                except Exception:
                    st.warning(f"Video API failed, falling back to static photo...")
            
            # Headroom target scaling to prevent black boundaries on cinematic pan/scale
            w_target = make_even(w * 1.25)
            h_target = make_even(h * 1.25)
                
            # Upgraded strictly to model=flux for perfect eyes, faces, and fine details
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed + i}&nologo=true&model=flux&negative=double_faces,double_heads,multiple_faces,overlapping_limbs,extra_limbs,extra_hands,extra_fingers,mutated_hands,two_bodies,deformed,blurry,bad_anatomy,clones,twins"
            if raw_char_url:
                img_url += f"&image={urllib.parse.quote(raw_char_url)}"
            
            img_path = f"i_{u_id}_{i}.jpg"
            generated_images.append(img_path)
            
            img_data = session.get(img_url, timeout=60).content
            with open(img_path, "wb") as f:
                f.write(img_data)
                
            # PIL Image Verification to lock even boundaries (Urdu Subtitles removed completely to satisfy full screen requirement)
            try:
                with Image.open(img_path) as img_obj:
                    img_obj = img_obj.convert("RGB").resize((w_target, h_target))
                        
                    if active_watermark:
                        draw = ImageDraw.Draw(img_obj)
                        draw.text((w_target - 140, h_target - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                        
                    img_obj.save(img_path, "JPEG")
            except Exception:
                im = Image.new("RGB", (w_target, h_target), color=(30, 41, 59))
                if active_watermark:
                    draw = ImageDraw.Draw(im)
                    draw.text((w_target - 140, h_target - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                im.save(img_path, "JPEG")
                
            clip = apply_camera_motion_v40(img_path, active_motion, dur_per, w, h)
            clip = apply_clip_transition(clip, transition_style, dur_per)
            clips.append(clip)
            
        if not clips:
            fallback_p = f"i_{u_id}_fallback.jpg"
            img_data = generate_high_quality_placeholder(w, h, 1, active_watermark)
            with open(fallback_p, 'wb') as f:
                f.write(img_data)
            generated_images.append(fallback_p)
            clip = apply_camera_motion_v40(fallback_p, "Zoom Out (v40 Default)", voice_audio.duration, w, h)
            clip = apply_clip_transition(clip, transition_style, voice_audio.duration)
            clips.append(clip)
            
        progress_bar.progress(0.85)
        status.info("🎞️ Rendering final MP4 movie...")
        
        final_audio = voice_audio
        bg_audio = None
        if has_bg_music and os.path.exists(bg_music_f):
            try:
                bg_audio = AudioFileClip(bg_music_f).volumex(0.10)
                bg_audio = bg_audio.set_duration(voice_audio.duration)
                final_audio = CompositeAudioClip([voice_audio, bg_audio])
            except Exception:
                pass
                
        # Force size-locked canvas resizing on concatenate_videoclips to prevent ffmpeg odd-height broken pipe crash
        final_video = concatenate_videoclips(clips, method="compose").resize((w, h)).set_audio(final_audio)
        out_name = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        if bg_audio:
            bg_audio.close()
        final_video.close()
        
        try:
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except Exception:
            pass
            
        progress_bar.progress(1.0)
        status.success("🚀 Video Generated Successfully!")
        
        # Save project to SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (id, user_id, project_name, type, file_path, prompt, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (u_id, user_id, f"Video Project {u_id}", "Video", out_name, " | ".join(generated_prompts), time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        # Deduct credits
        deduct_user_credits(st.session_state.logged_in_user, 15)
        log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
        
        return out_name
    except Exception as e: 
        try:
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except: pass
        progress_bar.empty()
        return f"Error Details: {e}"
    finally:
        gc.collect()

# ==========================================
# 8. UI NAVIGATION & CONTROL PANEL
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
                    st.success(f"Welcome back, {u_name}! Session authorized.")
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
                        st.success(msg)
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
        
        # Guide expander inside UI
        with st.expander("🔑 Pollinations AI API Key حاصل کرنے کا طریقہ (Guide)"):
            st.markdown("""
            1. سب سے پہلے **[Pollinations AI کے آفیشل پورٹل](https://enter.pollinations.ai/)** پر جائیں۔
            2. اگر آپ کا اکاؤنٹ نہیں ہے تو **Sign Up** کریں، ورنہ اپنے اکاؤنٹ میں **Log In** کریں۔
            3. لاگ اِن کرنے کے بعد **API Keys** یا **Developer** سیکشن پر جائیں، وہاں سے ایک نئی API Key تخلیق کریں اور اسے کاپی کر لیں۔
            4. کاپی کی گئی Key کو اوپر دیے گئے **Enter Pollinations API Key** والے باکس میں پیسٹ کریں۔
            5. آپ کے اکاؤنٹ میں روزانہ کے مفت کریڈٹس (Daily Free Credits) شامل ہوں گے، جنہیں آپ لائیو ویڈیو بنانے کے لیے استعمال کر سکتے ہیں۔
            6. اگر آپ کے پاس API Key نہیں ہے یا کریڈٹس ختم ہو جائیں، تو پریشان نہ ہوں! ہماری ایپ خودکار طور پر **Cinematic Photo Zoom & Pan (Free Mode)** پر واپس چلی جائے گی، جس سے آپ کی ویڈیو جنریشن کبھی بند نہیں ہوگی۔
            """)
            
    # AI Prompt Assistant Module Layer
    with st.expander("🔮 AI Script & Prompt Assistant Module", expanded=False):
        raw_story_input = st.text_area("Write your story here (AI will generate breakdown & prompts):", height=120)
        if st.button("Analyze Story with AI Assistant 🔮"):
            if raw_story_input:
                analysis_output = run_ai_prompt_assistant(raw_story_input)
                st.write(analysis_output)
            else:
                st.warning("Write story first.")

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    # Character & Scene Memory with Libraries
    char_col1, char_col2 = st.columns([2, 1])
    with char_col1:
        char_desc = st.text_input("Character Memory (e.g. clothing, age, style):", 
                                  placeholder="Example: A 30-year-old brave warrior, short black beard, wearing a traditional dark green turban")
    
    # Upload character reference image
    uploaded_char_img = st.file_uploader("Upload Consistent Character Image:", type=["jpg", "png", "jpeg"])
    if uploaded_char_img is not None:
        st.image(uploaded_char_img, caption="Character Identity Locked ✅", width=120)
        
    with char_col2:
        char_name_save = st.text_input("Save/Name Character:", key="char_name")
        if st.button("Save Character to Library 💾"):
            if char_name_save and char_desc:
                conn = get_db_connection()
                cursor = conn.cursor()
                u_db = get_user_data(st.session_state.logged_in_user)
                if u_db:
                    cursor.execute("INSERT INTO characters VALUES (?, ?, ?, ?, ?)", 
                                   (str(uuid.uuid4())[:8], u_db['id'], char_name_save, char_desc, ""))
                    conn.commit()
                    st.success(f"Saved {char_name_save} to Sglowina library!")
                conn.close()
                
    # Reuse Character Library Selection
    conn = get_db_connection()
    cursor = conn.cursor()
    u_db = get_user_data(st.session_state.logged_in_user)
    char_list = []
    if u_db:
        cursor.execute("SELECT character_name, description FROM characters WHERE user_id = ?", (u_db['id'],))
        char_list = cursor.fetchall()
    conn.close()
    
    if char_list:
        sel_char = st.selectbox("Reuse Saved Character:", ["None"] + [c['character_name'] for c in char_list])
        if sel_char != "None":
            char_desc = next(c['description'] for c in char_list if c['character_name'] == sel_char)
            st.info(f"Loaded Character: {char_desc}")

    scene_col1, scene_col2 = st.columns([2, 1])
    with scene_col1:
        scene_desc = st.text_input("Scene Memory (e.g. mud houses, rainy night, fog):", 
                                  placeholder="Example: Ancient rustic mud houses, dark rainy night, traditional old village background")
    with scene_col2:
        scene_name_save = st.text_input("Save/Name Scene Environment:", key="scene_name")
        if st.button("Save Scene to Library 💾"):
            if scene_name_save and scene_desc:
                conn = get_db_connection()
                cursor = conn.cursor()
                if u_db:
                    cursor.execute("INSERT INTO scenes VALUES (?, ?, ?, ?, ?, ?)", 
                                   (str(uuid.uuid4())[:8], u_db['id'], scene_name_save, scene_desc, "", ""))
                    conn.commit()
                    st.success(f"Saved {scene_name_save} to Sglowina library!")
                conn.close()

    # Reuse Scene Library Selection
    conn = get_db_connection()
    cursor = conn.cursor()
    scene_list = []
    if u_db:
        cursor.execute("SELECT scene_name, environment FROM scenes WHERE user_id = ?", (u_db['id'],))
        scene_list = cursor.fetchall()
    conn.close()
    
    if scene_list:
        sel_scene = st.selectbox("Reuse Saved Scene Environment:", ["None"] + [s['scene_name'] for s in scene_list])
        if sel_scene != "None":
            scene_desc = next(s['environment'] for s in scene_list if s['scene_name'] == sel_scene)
            st.info(f"Loaded Scene Background: {scene_desc}")

    # Cinematic Parameters
    with st.expander("🎬 Advanced Cinematic Director Controls", expanded=False):
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            v_style = st.selectbox("Visual Style:", ["Auto (Smart Director)", "Realistic", "Cinematic Realistic", "Ultra Photorealistic", "Documentary Style", "Found Footage", "Horror", "Mystery", "Adventure", "Ancient Ruins", "Jungle Exploration", "Fantasy", "Historical", "Islamic Historical", "Dark Fantasy", "Epic Movie", "Action Movie", "Survival", "Sci-Fi", "Post Apocalypse", "Medieval", "Pirate Adventure"])
        with ac2:
            v_lighting = st.selectbox("Lighting:", ["Auto (Smart Director)", "Natural Daylight", "Golden Hour", "Blue Hour", "Moonlight", "Torch Light", "Candle Light", "Volumetric Light", "Volumetric Fog", "Misty Atmosphere", "Storm Lighting", "Lightning Effects", "Dark Cinematic", "Horror Shadows", "Fire Glow", "Soft Studio Light", "Neon Light", "Sunset", "Sunrise"])
        with ac3:
            v_mood = st.selectbox("Mood:", ["Auto (Smart Director)", "Peaceful", "Emotional", "Suspense", "Horror", "Mystery", "Epic", "Dangerous", "Tense", "Lonely", "Magical", "Survival", "Thriller", "Psychological", "Dark", "Inspirational", "Heroic"])
        with ac4:
            v_env = st.selectbox("Environment:", ["Auto (Smart Director)", "Dense Jungle", "Ancient Temple", "Haunted Village", "Dark Cave", "Underground Tunnel", "Desert Ruins", "Snow Mountains", "Rain Forest", "Abandoned City", "Old Castle", "Fog Forest", "Swamp", "Waterfall", "River", "Volcano", "Ocean", "Ancient Library", "Underground Palace", "Abandoned Hospital", "Secret Laboratory"])

        ac5, ac6, ac7, ac8 = st.columns(4)
        with ac5:
            v_weather = st.selectbox("Weather:", ["Auto (Smart Director)", "Clear", "Rain", "Heavy Rain", "Thunderstorm", "Fog", "Snow", "Wind", "Dust Storm", "Sandstorm", "Heavy Clouds", "Sunset Sky", "Night Sky", "Aurora"])
        with ac6:
            v_color = st.selectbox("Color Grading:", ["Auto (Smart Director)", "Hollywood Cinematic", "Horror Green", "Teal & Orange", "Warm", "Cold Blue", "Desaturated", "Vintage", "High Contrast", "Film Look", "Netflix Style", "IMAX Style", "HDR Cinema"])
        with ac7:
            v_anim = st.selectbox("Animation Style:", ["Auto (Smart Director)", "Automatic Cinematic Motion", "AI Smart Camera", "Smooth Motion", "Character Focus", "Face Tracking", "Motion Blur", "Depth Effect", "Dynamic Zoom", "Intelligent Scene Transition", "Cinematic Motion Blur", "Smart Object Tracking", "AI Camera Director", "Auto Frame", "Smart Focus"])
        with ac8:
            v_quality = st.selectbox("Video Quality:", ["Auto (Smart Director)", "HD", "Full HD", "2K", "4K", "8K", "Ultra Detail", "HDR", "Ultra HDR", "Maximum Quality"])

    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8 = st.columns(8)
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
    with mc8: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        
        pitch_map = {
            "Normal (نارمل)": "+0Hz",
            "Deep (بھاری آواز)": "-15Hz",
            "Very Deep (موٹی آواز)": "-28Hz"
        }
        pitch_val = pitch_map[mv_pitch]
        
        adv_params = {
            "v_style": v_style,
            "v_lighting": v_lighting,
            "v_mood": v_mood,
            "v_env": v_env,
            "v_weather": v_weather,
            "v_color": v_color,
            "v_anim": v_anim,
            "v_quality": v_quality
        }
        
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
                uploaded_char_img=uploaded_char_img, 
                gen_mode=gen_mode, 
                pollinations_key=pollinations_key,
                advanced_params=adv_params
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
                        img_name = translate_ur_to_en(modify_prompt)
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
        
        # Sglowina Premium Monthly Plan setup
        st.success("#### 🏆 Sglowina Premium Monthly Plan")
        st.write("💰 **Price:** 1000 PKR / Month")
        st.write("🪙 **Credits Received:** 450 Credits (Guarantees at least 30 Cinematic Video Generations!)")
        
        st.markdown("---")
        st.write("### 📱 How to Pay via EasyPaisa / JazzCash")
        st.write("1. Send **1000 PKR** to one of the accounts below:")
        
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.info("💚 **EasyPaisa Account**\n\n* **Account Name:** Saba Wahid\n* **Account Number:** 03086834020")
        with bcol2:
            st.warning("❤️ **JazzCash Account**\n\n* **Account Name:** Ayisha bi bi\n* **Account Number:** 03240755475")
            
        st.write("2. After transferring the money, please submit your payment request below for instant verification:")
        
        # Payment verification form for customers
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
            
            # Fetch SaaS Stats
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
                
            # -----------------
            # NEW: Local Payment Approval Desk
            # -----------------
            st.markdown("---")
            st.write("### 📲 Pending Local Payment Requests")
            cursor.execute("SELECT * FROM local_payments WHERE status = 'Pending'")
            pending_reqs = cursor.fetchall()
            
            if not pending_reqs:
                st.info("No pending payment requests found.")
            else:
                for req in pending_reqs:
                    st.write(f"👤 **User:** `{req['username']}` | 📱 **Method:** {req['method']} | 🔑 **TrxID:** `{req['trx_id']}` | 💰 **Amount:** {req['amount']} PKR")
                    
                    # Generate a unique key for button click
                    app_btn_key = f"approve_{req['id']}"
                    if st.button(f"Approve Payment & Credit 450 Coins for {req['username']}", key=app_btn_key):
                        # Update request status
                        cursor.execute("UPDATE local_payments SET status = 'Approved' WHERE id = ?", (req['id'],))
                        
                        # Add 450 credits to user and upgrade plan to Premium
                        cursor.execute("UPDATE users SET credits = credits + 450, plan = 'Premium' WHERE username = ?", (req['username'],))
                        
                        # Get user's new balance for logging
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
