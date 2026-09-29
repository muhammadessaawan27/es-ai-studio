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

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI is an advanced generative AI cinematic video, vision & image production platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

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
    
    if any(k in t_lower for k in ['mental', 'force', 'john', 'action', 'fight', 'movie', 'scene', 'police', 'hindi']):
        genre = "Bollywood Action Scene"
        safe_titles = [
            f"🔥 {clean_title[:50]} | Best Action Scene (Full HD)",
            f"⚡ Unstoppable Action Moments | {clean_title[:45]}",
            f"😱 Most Intense Fight Scene | {clean_title[:45]}"
        ]
        hashtags = "#Force2 #JohnAbraham #ActionScene #BollywoodAction #Blockbuster #ViralVideo"
        thumb_prompt = f"Hyper-realistic 8K cinematic movie thumbnail for '{clean_title[:35]}', intense muscular hero dramatic angry face, action sparks background, 16:9."
    elif any(k in t_lower for k in ['kapil', 'comedy', 'funny', 'laugh', 'joke', 'hasna', 'standup']):
        genre = "Comedy / Entertainment Show"
        safe_titles = [
            f"😂 {clean_title} | Non-Stop Uncut Funny Moments",
            f"🤣 Ultimate Comedy Highlights | {clean_title[:45]}",
            f"🔥 Funniest Scene Ever | {clean_title[:50]}"
        ]
        hashtags = "#Comedy #FunnyVideo #ViralComedy #StandupComedy #TrendingReels"
        thumb_prompt = f"Ultra realistic 8K YouTube thumbnail for comedy show scene '{clean_title[:35]}', comedian laughing happily on stage, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana']):
        genre = "Music / Lo-Fi Audio Track"
        safe_titles = [
            f"🎧 {clean_title} (Slowed + Reverb Lo-Fi Remix) | Midnight Chill",
            f"🌙 {clean_title} | Deep Relaxing Aesthetic Vibe (Master HD)",
            f"✨ Pure Nostalgia Vibes | {clean_title[:45]}"
        ]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio"
        thumb_prompt = f"Anime aesthetic 4K Lo-Fi wallpaper thumbnail for song '{clean_title[:35]}', neon cozy bedroom, rain outside window, 16:9."
    else:
        genre = "Viral Video Highlight"
        safe_titles = [
            f"🔥 {clean_title[:45]} - Full HD Climax Scene",
            f"⚡ {clean_title[:45]} - Best Uncut Moments",
            f"😱 The Most Dramatic Scene of {clean_title[:40]}"
        ]
        hashtags = "#ViralClip #TrendingNow #CinemaRecap #ActionHighlights"
        thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', dramatic intense face, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

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
    elif any(k in text for k in ["forest", "jungle", "mountain", "valley", "landscape", "sky"]):
        composition = "Cinematic wide-angle establishing landscape shot"
        motion = "Drone Shot"

    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["fight", "battle", "sword", "war"]):
        motion = "Handheld Camera"
        
    return {
        "motion": motion,
        "lighting": lighting,
        "color_grading": color_grading,
        "composition": composition
    }

def translate_ur_to_en_enhanced(text):
    try:
        instruction = "Translate the following Urdu story scene into descriptive English prompt for visuals. Output ONLY English translation."
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
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "کفن", "غوث", "قطب", "امام"
    ]
    if any(k in combined_text for k in spiritual_keywords):
        safe_prompt = (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light from heavens, "
            "peaceful glowing background, majestic mountains and sand, sacred atmosphere. "
            "STRICTLY NO human faces, NO visible bodies, NO portraits. Pure sacred light."
        )
        return True, safe_prompt
    return False, scene_text_en

def generate_enhanced_cinematic_prompt(urdu_scene, char_memory, scene_memory, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        instruction = "You are an expert cinematic visual artist. Analyze the Urdu scene and write a descriptive English prompt for Flux. Output ONLY final prompt."
        prompt_input = f"Urdu Scene: {urdu_scene}\n"
        if char_memory: prompt_input += f"Character Memory: {char_memory}\n"
        if scene_memory: prompt_input += f"Scene Memory: {scene_memory}\n"

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
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "JPEG")
    except Exception:
        pass

def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    if any(k in text for k in ["rain", "storm", "thunder"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "battle"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3"
        
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
        else:
            animated_clip = clip.resize(lambda t: 1.15 - 0.15 * (t / duration)).set_position('center')

        return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
    except Exception:
        return ImageClip(img_path).set_duration(duration).resize((w, h))

def apply_clip_transition(clip, transition, duration):
    try:
        if clip is not None:
            if transition == "Cross Dissolve (Fade)":
                return clip.fadein(0.4).fadeout(0.4)
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

def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free & Unlimited)", pollinations_key="", video_model="wan-fast", advanced_params=None):
    u_id = str(uuid.uuid4())[:8]
    
    global active_renderers
    with render_lock:
        active_renderers += 1
        
    status = st.empty()
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
        
        try:
            progress_bar.progress(0.05)
            status.info("🎙️ Processing Dialogue Voiceovers...")
            
            sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
            if not sentences: sentences = [story]
            
            clips = []
            for idx, scene in enumerate(sentences):
                v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
                sub_audio_path = f"a_{u_id}_{idx}.mp3"
                save_audio_safe(scene, v_code_scene, rate, pitch, sub_audio_path)
                temporary_audio_tracks.append(sub_audio_path)
                
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
                refined_p = generate_enhanced_cinematic_prompt(scene, char_desc, scene_desc, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url)
                generated_prompts.append(refined_p)
                
                w_target, h_target = make_even(w * 1.25), make_even(h * 1.25)
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_path = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_path)
                generated_images.append(img_path)
                
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            for i, scene in enumerate(sentences):
                img_path = img_paths[i]
                sub_audio_path = temporary_audio_tracks[i]
                apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
                
                scene_voice_clip = AudioFileClip(sub_audio_path)
                dur_scene = scene_voice_clip.duration
                clip = apply_camera_motion_v40(img_path, camera_motion, dur_scene, w, h)
                clip = clip.set_audio(scene_voice_clip)
                clips.append(clip)
                
            final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
            out_name = f"Sglowina_{u_id}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"], logger=None)
            final_video.close()
            
            for sub_voice in temporary_audio_tracks:
                if os.path.exists(sub_voice): os.remove(sub_voice)
            for file_p in generated_images:
                if os.path.exists(file_p): os.remove(file_p)
                
            deduct_user_credits(st.session_state.logged_in_user, 15)
            log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
            return out_name
        except Exception as e:
            return f"Error Details: {e}"
        finally:
            gc.collect()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 2.2rem; font-weight: 900; text-align: center; font-family: 'Orbitron', sans-serif; background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 10px; margin-bottom: 5px; }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 10px 0; }
    .circular-s { width: 100px; height: 100px; background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Orbitron', sans-serif; font-size: 42px; color: #ffffff !important; }
    .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA & ES AI STUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">ES</div></div>', unsafe_allow_html=True)

def render_autonomous_live_viewport():
    viewport_html = """
    <div style="background:#000;border-radius:20px;padding:20px;text-align:center;color:#fff;">
        <h3>🧸 MUSE AR Live Companion</h3>
        <p>Real-time visual processing enabled.</p>
    </div>
    """
    st.components.v1.html(viewport_html, height=200)

tab_auth, tab_companion, tab_es_tools, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Auth", "🧸 Live AR Companion", "⚡ ES Video Processor (اینٹی کاپی رائٹ)",
    "🎬 Pro Master Studio", "🎨 Pro Image Studio", "💬 Electric AI Chat", "👤 Enterprise Center"
])

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
                    st.success(f"Welcome {u_name}! 🟢")
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
                    if success: st.success("Account created successfully! Please sign in.")
                    else: st.error(msg)

with tab_companion:
    render_autonomous_live_viewport()

with tab_es_tools:
    st.write("### ⚡ ES ہالی ووڈ پرو ڈسرپشن اینٹی کاپی رائٹ شیلڈ")
    st.info("💡 **پرو فارمولا ایکٹیو:** 1.8° ٹِلٹ + کینوس فریم + 1.08x اسپیڈ + 75% BGM ڈکنگ۔")
    
    sub_t1, sub_t2, sub_t3 = st.tabs(["🎬 فل ویڈیو / موڈ", "⚔️ کلپ کٹر موڈ", "🎧 Slowed + Reverb"])
    
    with sub_t1:
        st.subheader("ویڈیو لنک یا فائل پروسیس کریں")
        c_mode1, c_mode2 = st.columns(2)
        with c_mode1:
            style_choice = st.selectbox("حفاظتی ویژول اسٹائل:", [
                "👑 پرو ایڈیٹر موڈ (100% محفوظ - 1.8° Tilt + Canvas Frame + Text Shield)",
                "⚡ الٹرا فل اسکرین اینٹی ہیش (1.8° Tilt + 82% Deep Zoom)"
            ], key="s_t1")
        with c_mode2:
            audio_pitch_choice = st.selectbox("آواز اور میوزک موڈیولیشن:", [
                "🔊 بیک گراؤنڈ میوزک 75% خاموش + بھاری آواز (Heavy Ducking - 100% Safe)",
                "🎵 تیز اور اسمارٹ پچ شفٹ (Smart Shift 1.08x)"
            ], key="ap_t1")
        
        upload_opt1 = st.file_uploader("📂 اپنے موبائل یا کمپیوٹر سے ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi"], key="up_t1")
        url_input_1 = st.text_input("🔗 یا ویڈیو کا نیا لنک ڈالیں (YouTube, TikTok, FB, Insta):", placeholder="https://...", key="url_t1")
        
        if st.button("🚀 پرو اینٹی کاپی رائٹ ڈسرپشن شیلڈ لگائیں", type="primary", key="run_t1"):
            curr_uid = str(uuid.uuid4())[:8]
            target_in = f"in_vid_{curr_uid}.mp4"
            target_out = f"out_vid_{curr_uid}.mp4"
            info = {'title': 'Action Scene Video'}
            has_input = False
            
            if upload_opt1 is not None:
                with st.spinner("📂 فائل محفوظ ہو رہی ہے..."):
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
                with st.spinner("🔗 لنک سے ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    info = inspect_and_fetch_media(url_input_1.strip(), target_in)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        has_input = True
                        
            if has_input:
                with st.spinner("⚡ ویڈیو پر 1.8° ٹِلٹ، کینوس فریم اور آڈیو شیلڈ لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    
                    if "پرو ایڈیٹر" in style_choice:
                        vf_str = (
                            "[0:v]scale=1280:720,boxblur=25:5[bg];"
                            "[0:v]setpts=0.925*PTS,rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.82:ih*0.82,scale=980:552,"
                            "eq=contrast=1.16:saturation=1.22:brightness=0.02,"
                            "noise=alls=8:allf=t+u,vignette=PI/3.5[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                            "drawbox=y=0:h=45:color=black@0.65:t=fill,"
                            "drawbox=y=ih-55:h=55:color=black@0.75:t=fill"
                        )
                    else:
                        vf_str = (
                            "setpts=0.925*PTS,rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                            "eq=contrast=1.16:saturation=1.22:brightness=0.02,"
                            "noise=alls=8:allf=t+u,vignette=PI/3.5,"
                            "drawbox=y=0:h=45:color=black@0.65:t=fill,"
                            "drawbox=y=ih-55:h=55:color=black@0.75:t=fill"
                        )
                    
                    if "خاموش" in audio_pitch_choice or "Heavy Ducking" in audio_pitch_choice:
                        af_str = "volume=0.35,atempo=1.08,asetrate=44100*0.92,aresample=44100,bass=g=5:f=120,treble=g=-3:f=3500"
                    else:
                        af_str = "volume=0.85,atempo=1.08,asetrate=44100*1.05,aresample=44100,bass=g=3:f=110"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-i", target_in,
                        "-filter_complex" if "پرو ایڈیٹر" in style_choice else "-vf", vf_str,
                        "-af", af_str,
                        "-r", "25",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "128k", target_out
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
                        st.error("❌ پروسیسنگ مکمل نہ ہو سکی۔ براہِ کرم دوبارہ ٹرائی کریں۔")
            else:
                st.error("❌ برائے مہربانی درست لنک یا ویڈیو فائل فراہم کریں۔")

    with sub_t2:
        st.subheader("ویڈیو سے کلپ نکالیں")
        c1, c2 = st.columns(2)
        with c1: start_min = st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
        with c2: clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10)
        upload_opt2 = st.file_uploader("📂 فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv"], key="up_t2")
        url_input_2 = st.text_input("🔗 یا لنک درج کریں:", placeholder="https://...", key="url_t2")
        if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", key="run_t2"):
            curr_uid = str(uuid.uuid4())[:8]
            target_in = f"clip_in_{curr_uid}.mp4"
            target_out = f"clip_out_{curr_uid}.mp4"
            has_input = False
            info = {'title': 'Clip Video'}
            if upload_opt2 is not None:
                with open(target_in, "wb") as f:
                    f.write(upload_opt2.getvalue())
                has_input = True
            elif url_input_2.strip():
                info = inspect_and_fetch_media(url_input_2.strip(), target_in)
                if os.path.exists(target_in): has_input = True
            if has_input:
                ffmpeg_exe = get_ffmpeg()
                cmd = [
                    ffmpeg_exe, "-y", "-ss", str(start_min * 60), "-t", str(clip_len * 60),
                    "-i", target_in, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", target_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out):
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True

    with sub_t3:
        st.subheader("Slowed + Reverb Audio")
        song_url = st.text_input("🔗 گانے کا لنک درج کریں:", key="url_t3")
        if st.button("🚀 لوفی بنائیں", key="run_t3") and song_url.strip():
            curr_uid = str(uuid.uuid4())[:8]
            target_in = f"s_in_{curr_uid}.mp4"
            target_out = f"s_out_{curr_uid}.mp4"
            info = inspect_and_fetch_media(song_url.strip(), target_in)
            if os.path.exists(target_in):
                ffmpeg_exe = get_ffmpeg()
                cmd = [
                    ffmpeg_exe, "-y", "-i", target_in,
                    "-af", "asetrate=44100*0.88,aresample=44100,aecho=0.8:0.88:50:0.4,bass=g=6:f=110",
                    "-c:v", "copy", target_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out):
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True

    active_out = st.session_state.current_output_video
    if st.session_state.process_ready and active_out and os.path.exists(active_out):
        st.divider()
        st.success("🎉 ویڈیو تیار ہے:")
        video_bytes = open(active_out, 'rb').read()
        st.video(video_bytes)
        st.download_button("📥 ڈاؤنلوڈ کریں (Download MP4)", data=video_bytes, file_name=f"es_protected_{os.path.basename(active_out)}", mime="video/mp4", use_container_width=True)
        genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
        st.info(f"🎯 **کیٹگری:** {genre}")
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            st.markdown(f"### 🔥 وائرل ٹائٹلز:")
            for t in titles: st.code(t, language="text")
            st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
            st.code(tags, language="text")
        with c_meta2:
            st.markdown("### 🎨 AI تھمب نیل پرامپٹ:")
            st.code(prompt, language="text")

with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production")
    m_script = st.text_area("Enter Movie Script:", height=150, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے...")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film"])
    if st.button("Generate Master Movie 🚀"):
        with st.spinner("🎬 ویڈیو بن رہی ہے..."):
            v_res = create_cinematic_v40(story=m_script, voice_gen=mv, rate="+0%", pitch="+0Hz", ratio=mr, style=ms, seed=786)
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res):
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else:
            st.error(v_res)

with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    if st.button("Generate Visuals 🚀"):
        img_data = fetch_img_failover(p_i, 1280, 720, random.randint(1, 999999))
        if img_data:
            st.image(img_data, caption="AI Generated Visual")

with tab_chat:
    st.write("### 💬 Sglowina AI Chat")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai", timeout=15).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

with tab_enterprise:
    st.write("### 👤 Enterprise & Billing Center")
    st.info("💚 **EasyPaisa:** Saba Wahid (03086834020) | ❤️ **JazzCash:** Ayisha bi bi (03240755475)")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 20px;'>ES & Sglowina AI Studio Suite | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
