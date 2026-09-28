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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import base64
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import concurrent.futures

# ==========================================
# MOVIEPY COMPATIBILITY ENGINE (V1 & V2 SAFE)
# ==========================================
try:
    import moviepy.editor as mp
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    import moviepy as mp
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

def safe_duration(clip, dur):
    if hasattr(clip, "set_duration"):
        return clip.set_duration(dur)
    elif hasattr(clip, "with_duration"):
        return clip.with_duration(dur)
    clip.duration = dur
    return clip

def safe_fps(clip, fps):
    if hasattr(clip, "set_fps"):
        return clip.set_fps(fps)
    elif hasattr(clip, "with_fps"):
        return clip.with_fps(fps)
    clip.fps = fps
    return clip

def safe_position(clip, pos):
    if hasattr(clip, "set_position"):
        return clip.set_position(pos)
    elif hasattr(clip, "with_position"):
        return clip.with_position(pos)
    return clip

def safe_audio(clip, audio):
    if hasattr(clip, "set_audio"):
        return clip.set_audio(audio)
    elif hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    clip.audio = audio
    return clip

def safe_resize(clip, size_or_func):
    if hasattr(clip, "resize"):
        return clip.resize(size_or_func)
    elif hasattr(clip, "resized"):
        return clip.resized(size_or_func)
    return clip

def safe_volume(audio_clip, factor):
    if hasattr(audio_clip, "volumex"):
        return audio_clip.volumex(factor)
    elif hasattr(audio_clip, "multiply_volume"):
        return audio_clip.multiply_volume(factor)
    return audio_clip

def safe_fadein(clip, duration):
    if hasattr(clip, "fadein"):
        return clip.fadein(duration)
    elif hasattr(clip, "with_effects"):
        try:
            from moviepy.video.fx import FadeIn
            return clip.with_effects([FadeIn(duration)])
        except Exception:
            pass
    return clip

def safe_fadeout(clip, duration):
    if hasattr(clip, "fadeout"):
        return clip.fadeout(duration)
    elif hasattr(clip, "with_effects"):
        try:
            from moviepy.video.fx import FadeOut
            return clip.with_effects([FadeOut(duration)])
        except Exception:
            pass
    return clip

# ==========================================
# BROWSER SESSION HEADERS
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

st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V3.8", layout="wide", page_icon="🎬")

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

render_semaphore = threading.Semaphore(value=2)
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
                return temp_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
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
# 2. DATABASE LAYER
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
    for adm, mail in [("essasaba", "essasaba@sglowina.ai"), ("essa_awan", "essa@sglowina.ai")]:
        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = ?", (adm,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (adm, mail, h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
        else:
            cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = ?", (h_admin, adm))
                       
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
# 3. AUTHENTICATION & CORE LOGIC
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

def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    motion = "Zoom Out (v40 Default)"
    lighting = "Volumetric Light"
    color_grading = "Hollywood Cinematic"
    composition = "Medium Shot, Rule of Thirds"
    
    if any(k in text for k in ["saba", "she", "her", "woman", "female", "girl"]):
        composition = "Tight close-up portrait shot, extreme details of female face"
        motion = "Push In"
    elif any(k in text for k in ["essa", "he", "him", "man", "male", "boy", "warrior", "king"]):
        composition = "Cinematic masculine close-up portrait, focus on eyes"
        motion = "Zoom In"
    elif any(k in text for k in ["run", "chase", "tractor", "drive", "car"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["rain", "storm", "dark", "grave"]):
        motion = "Dolly In"
        lighting = "Dark Cinematic, Dramatic Shadows"
        color_grading = "Horror Green"
    elif any(k in text for k in ["sword", "fight", "battle"]):
        motion = "Handheld Camera"
    else:
        motion = "Zoom In"
        
    return {
        "motion": motion,
        "lighting": lighting,
        "color_grading": color_grading,
        "composition": composition
    }

def translate_ur_to_en_enhanced(text):
    try:
        instruction = "Translate this Urdu scene into a cinematic visual English prompt for AI art. Output ONLY the English prompt."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' ' + text)}?model=openai"
        res = session.get(url, timeout=12)
        if res.status_code == 200 and len(res.text) > 5:
            return res.text.strip()
    except Exception:
        pass
    return text

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined_text = (scene_text_en + " " + scene_text_ur).lower()
    spiritual_keywords = [
        "prophet", "sahaba", "saint", "angel", "god", "allah", "messenger", "nooh", "musa", "isa", "ibrahim", "yousuf", "muhammad", 
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "غوث", "قطب", "امام"
    ]
    if any(k in combined_text for k in spiritual_keywords):
        safe_prompt = (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from the heavens, "
            "sacred light beam, peaceful glowing ancient background, majestic natural mountains. STRICTLY NO human faces, NO human figures."
        )
        return True, safe_prompt
    return False, scene_text_en

def generate_enhanced_cinematic_prompt(urdu_scene, char_memory, scene_memory, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        scene_lower = urdu_scene.lower()
        gender_booster = ""
        if character_heritage == "Traditional Eastern / Islamic (مسلم اور مشرقی لباس)":
            if any(k in scene_lower for k in ["صبا", "saba", "woman", "female"]):
                gender_booster = "Pakistani woman wearing modest traditional Shalwar Kameez with Dupatta head covering, sharp 8k photorealistic face"
            elif any(k in scene_lower for k in ["عیسی", "essa", "man", "male"]):
                gender_booster = "Pakistani man wearing traditional Shalwar Kameez with neat short beard, photorealistic 8k face"
        
        prompt_input = f"Scene: {urdu_scene}. "
        if char_memory: prompt_input += f"Characters: {char_memory}. "
        if gender_booster: prompt_input += f"Attire: {gender_booster}. "
        if scene_memory: prompt_input += f"Environment: {scene_memory}. "
        
        instruction = "Write a high-resolution cinematic descriptive prompt for Flux image generator. Output ONLY the English prompt."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' ' + prompt_input)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return re.sub(r'^(prompt:|visual prompt:)\s*', '', res.text.strip(), flags=re.IGNORECASE)
    except Exception:
        pass
    return f"Cinematic film scene: {urdu_scene}, highly detailed, 8k resolution"

def apply_blurred_background_padding(img_path, target_w, target_h):
    try:
        if not os.path.exists(img_path): return
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            bg = im.resize((target_w, target_h)).filter(ImageFilter.GaussianBlur(radius=20))
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
            res = session.get(url, timeout=35)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception:
            pass
        try:
            im = Image.new("RGB", (1280, 720), color=(15, 23, 42))
            im.save(path, "JPEG")
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_path, "JPEG")
            
        scale_factor = 1.25
        base_clip = safe_duration(ImageClip(img_path), duration)
        base_clip = safe_fps(base_clip, 24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = safe_resize(base_clip, (cw, ch))
        
        if motion == "Zoom In":
            animated_clip = safe_position(safe_resize(clip, lambda t: 1.0 + 0.12 * (t / max(duration, 0.1))), 'center')
        elif motion == "Pan Left":
            animated_clip = safe_position(clip, lambda t: (int((w - cw) * (t / max(duration, 0.1))), 'center'))
        elif motion == "Pan Right":
            animated_clip = safe_position(clip, lambda t: (int((w - cw) * (1 - t / max(duration, 0.1))), 'center'))
        else:
            animated_clip = safe_position(safe_resize(clip, lambda t: 1.12 - 0.12 * (t / max(duration, 0.1))), 'center')

        comp = CompositeVideoClip([animated_clip], size=(w, h))
        return safe_duration(comp, duration)
    except Exception:
        fallback = ImageClip(img_path)
        fallback = safe_duration(fallback, duration)
        return safe_resize(fallback, (w, h))

def apply_clip_transition(clip, transition, duration):
    try:
        if clip is not None:
            if transition == "Cross Dissolve (Fade)":
                return safe_fadeout(safe_fadein(clip, 0.3), 0.3)
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
# 4. MASTER V40 VIDEO ENGINE
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
        
        try:
            progress_bar.progress(0.10)
            status.info("🎙️ Processing Dialogue Voiceovers (Edge-TTS)...")
            
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
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
                
            progress_bar.progress(0.20)
            
            if enable_bg_music:
                status.info("🎵 Downloading Atmospheric Background Music...")
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                try:
                    res_bg = session.get(bg_url, timeout=8)
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
            w, h = res_map.get(ratio, (1280, 720))
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
                refined_p = generate_enhanced_cinematic_prompt(
                    urdu_scene=scene, char_memory=char_desc, scene_memory=scene_desc,
                    character_heritage=character_heritage, enable_islamic_filter=enable_islamic_filter,
                    raw_male_url=raw_male_url, raw_female_url=raw_female_url
                )
                
                generated_prompts.append(refined_p)
                w_target, h_target = make_even(w * 1.25), make_even(h * 1.25)
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_path = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_path)
                generated_images.append(img_path)
                
            progress_bar.progress(0.40)
            status.info("🎨 Rendering High-Definition Visual Frames...")
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.65)
            status.info("🎞️ Assembling Synchronized Audio and Motions...")
            
            for i, scene in enumerate(sentences):
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = max(scene_voice_clip.duration, 1.5)
                
                english_scene_temp = translate_ur_to_en_enhanced(scene)
                dir_settings = analyze_scene_for_director(english_scene_temp)
                active_motion = camera_motion if camera_motion != "AI Hollywood Director (Auto)" else dir_settings["motion"]
                
                clip = apply_camera_motion_v40(img_path, active_motion, dur_scene, w, h)
                clip = safe_audio(clip, scene_voice_clip)
                clip = apply_clip_transition(clip, transition_style, dur_scene)
                clips.append(clip)
                
            progress_bar.progress(0.85)
            status.info("🎞️ Final Master Video Stitching...")
            
            final_video = concatenate_videoclips(clips, method="compose")
            final_video = safe_resize(final_video, (w, h))
            
            if has_bg_music and os.path.exists(bg_music_f):
                try:
                    bg_track = safe_volume(AudioFileClip(bg_music_f), 0.05)
                    bg_track = safe_duration(bg_track, final_video.duration)
                    final_video = safe_audio(final_video, CompositeAudioClip([final_video.audio, bg_track]))
                except Exception:
                    pass
                    
            out_name = f"Sglowina_{u_id}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
            final_video.close()
            
            for sub_voice in temporary_audio_tracks:
                if os.path.exists(sub_voice): os.remove(sub_voice)
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
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for file_p in generated_images:
                if os.path.exists(file_p): os.remove(file_p)
            progress_bar.empty()
            return f"Error Details: {e}"
        finally:
            gc.collect()

# ==========================================
# 5. UI STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;900&display=swap');
    
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    .glow-title { 
        font-size: 2.2rem; font-weight: 900; text-align: center; font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 10px 0 5px 0; letter-spacing: 2px;
    }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 5px 0; }
    .circular-s {
        width: 80px; height: 80px; 
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 36px; color: #ffffff !important;
        border: 3px solid #ffffff !important; box-shadow: 0 0 30px #ff007a;
    }
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 10px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none; 
    }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 6. LIVE AR COMPANION (NO LOOP, REAL SPEAKER AUDIO)
# ==========================================
def render_live_companion_viewport():
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
                width: 100%; max-width: 480px; height: 540px; background: #000;
                border-radius: 24px; position: relative; overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 2px solid #f59e0b;
            }
            #liveVideo { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
            .hud-header {
                position: absolute; top: 12px; left: 12px; right: 12px;
                display: flex; justify-content: space-between; align-items: center; z-index: 10;
            }
            .hud-badge {
                background: rgba(0,0,0,0.75); border: 1px solid #10b981; color: #10b981;
                padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
            }
            .mascot-overlay {
                position: absolute; bottom: 100px; right: 14px; width: 90px; height: 105px; z-index: 15;
            }
            .fluffy-body {
                width: 85px; height: 95px; background: radial-gradient(circle at 35% 30%, #fef3c7, #f59e0b);
                border-radius: 40px; position: relative; box-shadow: 0 6px 15px rgba(0,0,0,0.4);
            }
            .subtitle-bar {
                position: absolute; bottom: 65px; left: 12px; right: 12px;
                background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255,255,255,0.2);
                border-radius: 12px; padding: 8px 12px; color: #ffffff; font-size: 13px;
                font-weight: 600; text-align: right; direction: rtl; z-index: 10; min-height: 40px;
            }
            .controls-bar {
                position: absolute; bottom: 12px; left: 12px; right: 12px;
                display: flex; gap: 8px; z-index: 20;
            }
            .action-btn {
                flex: 1; background: linear-gradient(45deg, #f59e0b, #ec4899); color: #000;
                border: none; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: 900;
                cursor: pointer; box-shadow: 0 4px 15px rgba(245,158,11,0.4);
            }
            .start-overlay {
                position: absolute; inset: 0; background: rgba(0,0,0,0.9);
                display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 30; padding: 20px; text-align: center;
            }
            .start-btn {
                background: linear-gradient(45deg, #f59e0b, #ec4899); color: #000; border: none;
                padding: 14px 28px; border-radius: 50px; font-size: 16px; font-weight: 900; cursor: pointer; margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <div class="viewport-container">
            <video id="liveVideo" autoplay playsinline></video>

            <div class="hud-header">
                <div class="hud-badge" id="statusLabel">STANDBY</div>
                <div style="background:rgba(0,0,0,0.6); padding:4px 10px; border-radius:15px; font-size:11px; color:#f59e0b; font-weight:bold;">🧸 MUSE AI</div>
            </div>

            <div class="mascot-overlay">
                <div class="fluffy-body">
                    <div style="position:absolute; top:25px; left:20px; width:45px; display:flex; justify-content:space-around;">
                        <div style="width:6px; height:6px; background:#451a03; border-radius:50%;"></div>
                        <div style="width:6px; height:6px; background:#451a03; border-radius:50%;"></div>
                    </div>
                    <div style="position:absolute; bottom:25px; left:35px; width:15px; height:6px; background:#e11d48; border-radius:0 0 10px 10px;"></div>
                </div>
            </div>

            <div class="subtitle-bar" id="subtitles">
                کیمرہ کھولیں اور "دیکھ کر بتاؤ" یا "بولیں" دبائیں، AI اسپیکر سے اردو میں بولے گا!
            </div>

            <div class="controls-bar" id="liveControls" style="display:none;">
                <button class="action-btn" onclick="captureAndExplain('اردو میں دیکھ کر بتاؤ یہ کیا ہے؟')">📸 دیکھ کر بتاؤ (اردو)</button>
                <button class="action-btn" onclick="captureAndExplain('Explain what you see in English concisely.')">🌐 Tell in English</button>
            </div>

            <div class="start-overlay" id="startScreen">
                <div style="font-size:40px; margin-bottom:10px;">🧸</div>
                <h3 style="color:#ffffff; font-weight:900; margin-bottom:5px;">MUSE Live Vision Companion</h3>
                <p style="color:#94a3b8; font-size:12px; max-width:260px;">کیمرہ لائیو رہے گا اور بٹن دبانے پر اسپیکر سے باقاعدہ واضح آواز آئے گی!</p>
                <button class="start-btn" onclick="startCamera()">🚀 کیمرہ شروع کریں</button>
            </div>
        </div>

        <canvas id="frameCanvas" style="display:none;"></canvas>
        <audio id="realSpeakerAudio" autoplay></audio>

        <script>
            let video = document.getElementById('liveVideo');
            let startScreen = document.getElementById('startScreen');
            let liveControls = document.getElementById('liveControls');
            let subtitles = document.getElementById('subtitles');
            let statusLabel = document.getElementById('statusLabel');
            let audioElement = document.getElementById('realSpeakerAudio');

            async function startCamera() {
                try {
                    startScreen.style.display = 'none';
                    liveControls.style.display = 'flex';
                    statusLabel.innerText = "LIVE READY";
                    
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "environment", width: 640, height: 480 },
                        audio: false
                    });
                    video.srcObject = stream;
                    speakVoice("السلام علیکم! کیمرہ تیار ہے، نیچے دیے گئے بٹن سے جو مرضی پوچھیں میں دیکھ کر بتاؤں گا۔");
                } catch (e) {
                    alert("کیمرہ پرمیشن الاؤ کریں: " + e.message);
                }
            }

            async function captureAndExplain(userPrompt) {
                statusLabel.innerText = "ANALYZING...";
                subtitles.innerText = "⏳ سوچ رہا ہوں...";

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
                                            text: "Look at this camera frame. Answer directly in 2 sweet concise natural sentences in the requested language: " + userPrompt 
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
                    statusLabel.innerText = "SPEAKING...";
                    speakVoice(reply);
                } catch (err) {
                    subtitles.innerText = "Error: " + err.message;
                } finally {
                    setTimeout(() => { statusLabel.innerText = "LIVE READY"; }, 3000);
                }
            }

            function speakVoice(text) {
                try {
                    let cleanText = encodeURIComponent(text.substring(0, 200));
                    let audioUrl = "https://text.pollinations.ai/" + cleanText + "?model=openai-audio";
                    audioElement.src = audioUrl;
                    audioElement.play().catch(e => {
                        if ('speechSynthesis' in window) {
                            let utter = new SpeechSynthesisUtterance(text);
                            window.speechSynthesis.speak(utter);
                        }
                    });
                } catch(e) {}
            }
        </script>
    </body>
    </html>
    """
    st.components.v1.html(viewport_html, height=560)

# ==========================================
# 7. NAVIGATION TABS
# ==========================================
tab_auth, tab_companion, tab_chat, tab_movie, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In & Registrations",
    "🧸 Live AR Companion (لائیو ویژن)",
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
            if st.form_submit_button("Sign In 🚀"):
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    st.success(f"Welcome back to SGLOWINA AI, {u_name}! 🟢")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    else:
        with st.form("reg_form"):
            new_u = st.text_input("Choose Username")
            new_e = st.text_input("Email Address")
            new_p = st.text_input("Password", type="password")
            if st.form_submit_button("Register Account 🎯"):
                if new_u and new_e and new_p:
                    success, msg = register_saas_user(new_u, new_e, new_p)
                    if success:
                        st.success(f"Account for '{new_u}' registered! Please sign in. 🟢")
                    else:
                        st.error(msg)

# -----------------
# TAB 2: LIVE AR COMPANION
# -----------------
with tab_companion:
    render_live_companion_viewport()

# -----------------
# TAB 3: CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai", timeout=12).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# -----------------
# TAB 4: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=140, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے اور بارش شروع ہو گئی...")
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True)
    
    char_desc = st.text_input("Character Memory:", placeholder="e.g. Saba is wearing a modest dark blue hijab")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        uploaded_male_img = st.file_uploader("Male Character Image:", type=["jpg", "png", "jpeg"])
    with col_up2:
        uploaded_female_img = st.file_uploader("Female Character Image:", type=["jpg", "png", "jpeg"])
        
    scene_desc = st.text_input("Scene Memory:", placeholder="e.g. Ancient dark rainy jungle")

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Speed:", ["+0% (Normal)", "+10% (Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Pitch:", ["Normal (نارمل)", "Deep (بھاری)", "Very Deep (موٹی)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc5: camera_motion = st.selectbox("Motion:", ["AI Hollywood Director (Auto)", "Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right"])
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری)": "-15Hz", "Very Deep (موٹی)": "-28Hz"}
        pitch_val = pitch_map.get(mv_pitch, "+0Hz")
        
        with st.spinner("🎬 Generating video with Edge-TTS voice and animations..."):
            v_res = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate=rate_val, pitch=pitch_val, ratio=mr, style="Cinematic Film", seed=786,
                char_desc=char_desc, scene_desc=scene_desc, camera_motion=camera_motion, transition_style="Cross Dissolve (Fade)",
                enable_watermark=enable_watermark, enable_bg_music=enable_bg_music, uploaded_male_img=uploaded_male_img,
                uploaded_female_img=uploaded_female_img, enable_islamic_filter=enable_islamic_filter
            )
            
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD Video", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

# -----------------
# TAB 5: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="e.g. Sglowina AI")
    
    if st.button("Generate Visual 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        if u_db and u_db['credits'] >= 2:
            img_data = fetch_img_failover(p_i, 1280, 720, random.randint(1, 999999))
            if img_data:
                img_path_temp = f"temp_canvas.jpg"
                with open(img_path_temp, "wb") as f_temp:
                    f_temp.write(img_data)
                if canva_overlay_text.strip():
                    apply_canva_typography(img_path_temp, canva_overlay_text.strip())
                with Image.open(img_path_temp) as im:
                    st.image(im, caption=p_i[:40])
                if os.path.exists(img_path_temp): os.remove(img_path_temp)
                deduct_user_credits(st.session_state.logged_in_user, 2)
                log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
        else:
            st.error("Insufficient credits (Requires 2 credits).")

# -----------------
# TAB 6: ENTERPRISE CENTER
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina Enterprise Administration Center")
    u_db = get_user_data(st.session_state.logged_in_user)
    
    if u_db:
        st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
        
        st.write("### 📱 How to Pay via EasyPaisa / JazzCash")
        bcol1, bcol2 = st.columns(2)
        with bcol1: st.info("💚 **EasyPaisa Account**\n\n* **Name:** Saba Wahid\n* **Number:** 03086834020")
        with bcol2: st.warning("❤️ **JazzCash Account**\n\n* **Name:** Ayisha bi bi\n* **Number:** 03240755475")
            
        with st.form("local_payment_form"):
            p_method = st.selectbox("Payment Method Used:", ["EasyPaisa", "JazzCash"])
            p_trx_id = st.text_input("Enter Transaction ID (TrxID):")
            p_amount = st.number_input("Amount Sent (PKR):", min_value=500.0, value=1000.0, step=100.0)
            if st.form_submit_button("Submit Payment Proof 🚀"):
                if p_trx_id.strip():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                       (str(uuid.uuid4())[:8], u_db['username'], p_method, p_trx_id.strip(), p_amount, 'Pending', time.strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.success("Payment submitted! Administrator will verify and credit your coins.")
                    except sqlite3.IntegrityError:
                        st.error("This TrxID has already been submitted.")
                    finally:
                        conn.close()
    else:
        st.warning("Please sign in first.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 3.8 Full Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
