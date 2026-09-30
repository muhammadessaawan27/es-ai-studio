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
import glob
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
    if "shorts/" in raw_url:
        vid_id = raw_url.split("shorts/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={vid_id}"
    elif "youtu.be" in raw_url:
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
# DATABASE LAYER
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
# ROBUST MULTI-PLATFORM DOWNLOADER
# ==========================================
def inspect_and_fetch_media(raw_url, base_prefix):
    clean_url = sanitize_url(raw_url)
    info_dict = {'title': 'Action Scene Video', 'uploader': 'Official Creator', 'categories': ['Entertainment'], 'tags': []}
    
    outtmpl = f"{base_prefix}.%(ext)s"
    found_file = None
    
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {'player_client': ['android', 'ios', 'web']}
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            if meta:
                info_dict['title'] = meta.get('title', 'Action Scene Video')
                info_dict['uploader'] = meta.get('uploader', 'Official Creator')
                info_dict['categories'] = meta.get('categories', ['Entertainment'])
                info_dict['tags'] = meta.get('tags', [])
    except Exception as e:
        pass
        
    matching = glob.glob(f"{base_prefix}.*")
    for f in matching:
        if os.path.exists(f) and os.path.getsize(f) > 5000:
            found_file = f
            break
            
    return info_dict, found_file

def generate_smart_metadata(info):
    raw_title = info.get('title', 'Video').strip()
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', raw_title).strip()
    if not clean_title: clean_title = raw_title
    t_lower = raw_title.lower()
    
    if any(k in t_lower for k in ['mental', 'force', 'john', 'action', 'fight', 'movie', 'scene', 'police', 'hindi', 'bloopers', 'ustad', 'bhagat']):
        genre = "Bollywood Action Breakdown"
        safe_titles = [
            f"🔥 {clean_title[:50]} | Full Action Scene Recap",
            f"⚡ Unstoppable Action Breakdown | {clean_title[:40]}",
            f"😱 Dramatic Climax Reaction | {clean_title[:40]}"
        ]
        hashtags = "#MovieBreakdown #ActionMovie #BollywoodAction #Blockbuster #ViralVideo #HindiCinema #MovieReaction"
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
        genre = "Viral Video Recap"
        safe_titles = [
            f"🔥 {clean_title[:45]} - Full HD Climax Scene Explained",
            f"⚡ {clean_title[:45]} - Best Uncut Action Highlights",
            f"😱 The Most Dramatic Scene of {clean_title[:40]}"
        ]
        hashtags = "#ViralClip #TrendingNow #CinemaRecap #ActionHighlights #BlockbusterScene"
        thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', dramatic intense face, cinematic color grading, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

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
        generated_images = []
        temporary_audio_tracks = []
        
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
                refined_p = generate_enhanced_cinematic_prompt(scene, char_desc, scene_desc, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url)
                
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

# ==========================================
# UI STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    .glow-title { 
        font-size: 2.2rem; font-weight: 900; text-align: center; font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-top: 10px; margin-bottom: 5px; letter-spacing: 2px;
    }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 10px 0; }
    .circular-s {
        width: 100px; height: 100px; background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 42px; color: #ffffff !important;
    }
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; 
    }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA & ES AI STUDIO</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">ES</div></div>', unsafe_allow_html=True)

# ==========================================
# TABS
# ==========================================
tab_auth, tab_es_tools, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Auth",
    "⚡ ES Video Processor (آٹومیٹک کٹ و شیلڈ)",
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
            if st.form_submit_button("Sign In 🚀"):
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    st.success(f"Welcome back, {u_name}! 🟢")
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
                else:
                    st.warning("Please fill out all fields.")

# -----------------
# TAB 2: ES VIDEO PROCESSOR (FIXED & FULLY STABLE)
# -----------------
with tab_es_tools:
    st.write("### ⚡ ES آٹومیٹک مائیکرو کٹس و آڈیو ماسکنگ شیلڈ (Auto Anti-Copyright)")
    st.info("💡 **پرو فارمولا ایکٹیو:** ہر 3 سیکنڈ بعد آٹومیٹک مائیکرو کٹ، کینوس فریم، 1.8° ٹِلٹ، آڈیو ماسکنگ اور فاسٹ اپلوڈنگ کمپریشن۔")
    
    sub_t1, sub_t2, sub_t3 = st.tabs([
        "🎬 1. فل ویڈیو / مووی موڈ (آٹومیٹک کٹ و ماسکنگ)",
        "⚔️ 2. کلپ کٹر موڈ (10 منٹ کٹ)",
        "🎧 3. گانے اور لوفی (Slowed + Reverb)"
    ])
    
    with sub_t1:
        st.subheader("مووی، ٹریلر یا ویڈیو اپلوڈ کریں (100% خودکار پروسیسنگ)")
        
        c_mode1, c_mode2 = st.columns(2)
        with c_mode1:
            cut_style = st.selectbox("خودکار کٹس اور شیلڈ اسٹائل:", [
                "🛡️ آٹومیٹک مائیکرو کٹ + کینوس فریم + 1.8° ٹِلٹ (100% تجویز کردہ)",
                "⚡ فاسٹ مائیکرو کٹ + ڈیپ زوم + اینٹی ہیش لیٹرباکس"
            ], key="s_t1")
        with c_mode2:
            audio_pitch_choice = st.selectbox("آواز اور ساؤنڈ لیئرنگ:", [
                "🔊 آٹومیٹک ساؤنڈ ماسکنگ + بھاری پچ (Auto Acoustic Masking - 100% Safe)",
                "🎵 تیز اسمارٹ پچ (Smart Pitch Shift)"
            ], key="ap_t1")
        
        upload_opt1 = st.file_uploader("📂 ویڈیو فائل اپلوڈ کریں (mp4/mkv/mov):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_t1")
        url_input_1 = st.text_input("🔗 یا کسی بھی ویڈیو کا لنک یہاں پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="url_t1")
        
        if st.button("🚀 آٹومیٹک کٹس اور اینٹی کاپی رائٹ شیلڈ لگائیں", type="primary", key="run_t1"):
            curr_uid = str(uuid.uuid4())[:8]
            base_in = f"in_vid_{curr_uid}"
            target_out = f"out_vid_{curr_uid}.mp4"
            
            info = {'title': 'Action Scene Video'}
            input_file_path = None
            
            if upload_opt1 is not None:
                with st.spinner("📂 ویڈیو فائل اپلوڈ ہو رہی ہے..."):
                    ext = upload_opt1.name.split('.')[-1] if '.' in upload_opt1.name else "mp4"
                    target_in = f"{base_in}.{ext}"
                    with open(target_in, "wb") as f:
                        upload_opt1.seek(0)
                        while True:
                            chunk = upload_opt1.read(1024 * 1024 * 4)
                            if not chunk: break
                            f.write(chunk)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        input_file_path = target_in
                        info['title'] = upload_opt1.name
            elif url_input_1.strip():
                with st.spinner("🔗 لنک سے ویڈیو ڈاؤنلوڈ کی جا رہی ہے..."):
                    info, downloaded_file = inspect_and_fetch_media(url_input_1.strip(), base_in)
                    if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 1000:
                        input_file_path = downloaded_file
                    else:
                        st.error("❌ یوٹیوب نے اس لنک کو بلاک کیا ہے یا لنک غلط ہے۔ برائے مہربانی ویڈیو کو ڈائریکٹ فائل اپلوڈر سے اپلوڈ کریں۔")
                        
            if input_file_path and os.path.exists(input_file_path):
                with st.spinner("⚡ ویڈیو پر آٹومیٹک مائیکرو کٹس (Timeline Break)، آڈیو ماسکنگ اور کمپریشن لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    
                    if "کینوس فریم" in cut_style:
                        vf_str = (
                            "[0:v]scale=1280:720,boxblur=22:4[bg];"
                            "[0:v]select='mod(n\\,75)<70',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.82:ih*0.82,scale=980:552,"
                            "eq=contrast=1.14:saturation=1.20:brightness=0.02,"
                            "noise=alls=6:allf=t+u,vignette=PI/3.5[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                            "drawbox=y=0:h=42:color=black@0.70:t=fill,"
                            "drawbox=y=ih-50:h=50:color=black@0.80:t=fill"
                        )
                    else:
                        vf_str = (
                            "select='mod(n\\,75)<70',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                            "eq=contrast=1.14:saturation=1.20:brightness=0.02,"
                            "noise=alls=6:allf=t+u,vignette=PI/3.5,"
                            "drawbox=y=0:h=42:color=black@0.70:t=fill,"
                            "drawbox=y=ih-50:h=50:color=black@0.80:t=fill"
                        )
                    
                    if "ماسکنگ" in audio_pitch_choice:
                        af_str = "volume=0.30,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.086957,bass=g=6:f=110,treble=g=-4:f=3200"
                    else:
                        af_str = "volume=0.80,asetrate=44100*1.04,aresample=44100:async=1,atempo=0.961538,bass=g=3:f=110"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-i", input_file_path,
                        "-filter_complex" if "کینوس فریم" in cut_style else "-vf", vf_str,
                        "-af", af_str,
                        "-r", "24",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
                        "-b:v", "850k", "-maxrate", "1100k", "-bufsize", "2000k",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                    ]
                    
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file_path)
                        except Exception: pass
                    else:
                        st.error("❌ FFmpeg پروسیسنگ مکمل نہ ہو سکی۔ براہ کرم دوبارہ کوشش کریں۔")
            elif not input_file_path and not url_input_1.strip() and upload_opt1 is None:
                st.error("❌ برائے مہربانی ویڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    with sub_t2:
        st.subheader("ویڈیو سے کلپ نکالیں (مائیکرو کٹ شیلڈ کے ساتھ)")
        c1, c2 = st.columns(2)
        with c1:
            scene_type = st.selectbox("سین کا آغاز:", ["⚔️ اہم سین (منٹ 30)", "👻 سسپنس موڑ (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
        with c2:
            clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
            
        start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
        upload_opt2 = st.file_uploader("📂 ویڈیو فائل منتخب کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t2")
        url_input_2 = st.text_input("🔗 یا نیا لنک ڈالیں:", placeholder="https://...", key="url_t2")

        if st.button("🚀 کلپ کاٹیں اور مائیکرو شیلڈ لگائیں", type="primary", key="run_t2"):
            curr_uid = str(uuid.uuid4())[:8]
            base_in = f"clip_in_{curr_uid}"
            target_out = f"clip_out_{curr_uid}.mp4"
            
            info = {'title': 'Clip Highlight'}
            input_file_path = None
            
            if upload_opt2 is not None:
                ext = upload_opt2.name.split('.')[-1] if '.' in upload_opt2.name else "mp4"
                target_in = f"{base_in}.{ext}"
                with open(target_in, "wb") as f:
                    upload_opt2.seek(0)
                    while True:
                        chunk = upload_opt2.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    input_file_path = target_in
                    info['title'] = upload_opt2.name
            elif url_input_2.strip():
                with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    info, downloaded_file = inspect_and_fetch_media(url_input_2.strip(), base_in)
                    if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 1000:
                        input_file_path = downloaded_file

            if input_file_path and os.path.exists(input_file_path):
                with st.spinner("کلپ کٹ کر کے آٹومیٹک مائیکرو کٹس اور شیلڈ لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = start_min * 60
                    dur_sec = clip_len * 60
                    vf = "select='mod(n\\,75)<70',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,eq=contrast=1.14:saturation=1.20:brightness=0.02,noise=alls=6:allf=t+u,vignette=PI/3.5,drawbox=y=0:h=42:color=black@0.70:t=fill,drawbox=y=ih-50:h=50:color=black@0.80:t=fill"
                    af = "volume=0.35,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.086957,bass=g=5:f=120"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                        "-i", input_file_path, "-vf", vf, "-af", af,
                        "-r", "24",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
                        "-b:v", "850k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file_path)
                        except Exception: pass
                    else:
                        st.error("❌ ویڈیو ٹائم سیٹنگز چیک کریں۔")
            else:
                st.error("❌ ویڈیو اپلوڈ کریں یا درست لنک دیں۔")

    with sub_t3:
        st.subheader("گانے کا لنک ڈالیں اور وائرل Slowed + Reverb بنائیں")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
        with col_s2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
        with col_s3: bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3")
            
        upload_opt3 = st.file_uploader("📂 آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
        song_url = st.text_input("🔗 یا گانے کا لنک یہاں پیسٹ کریں:", placeholder="https://...", key="url_t3")
        
        if st.button("🚀 گانے کو Slowed + Reverb بنائیں", type="primary", key="run_t3"):
            curr_uid = str(uuid.uuid4())[:8]
            base_in = f"dyn_song_in_{curr_uid}"
            target_out = f"dyn_song_out_{curr_uid}.mp4"
            
            info = {'title': 'Lo-Fi Chill Track'}
            input_file_path = None
            
            if upload_opt3 is not None:
                ext = upload_opt3.name.split('.')[-1] if '.' in upload_opt3.name else "mp4"
                target_in = f"{base_in}.{ext}"
                with open(target_in, "wb") as f:
                    upload_opt3.seek(0)
                    while True:
                        chunk = upload_opt3.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    input_file_path = target_in
                    info['title'] = upload_opt3.name
            elif song_url.strip():
                with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                    info, downloaded_file = inspect_and_fetch_media(song_url.strip(), base_in)
                    if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 1000:
                        input_file_path = downloaded_file
                        
            if input_file_path and os.path.exists(input_file_path):
                with st.spinner("لوفی گانا ماسٹر ہو رہا ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [
                        ffmpeg_exe, "-y", "-i", input_file_path,
                        "-af", af_filter, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", target_out
                    ]
                    subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file_path)
                        except Exception: pass
                    else:
                        st.error("❌ آڈیو پروسیسنگ فیل ہو گئی۔")
            else:
                st.error("❌ آڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    # Output Video Player & Fast Download
    active_out = st.session_state.current_output_video
    if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
        st.divider()
        st.success("🎉 ویڈیو مائیکرو کٹ شیلڈ، آڈیو ماسکنگ اور کم سائز (Lightweight) کے ساتھ تیار ہے:")
        
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
# TAB 3: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    gen_mode = st.selectbox("Select Generator Engine:", ["Cinematic Photo Zoom & Pan (100% Free & Unlimited)", "Real AI Video Motion (Beta - Pollinations Video API)"])
    pollinations_key = st.text_input("Enter Pollinations API Key (Optional):", type="password") if "Real AI Video" in gen_mode else ""
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="مثال: ایک کسان ٹریکٹر چلا رہا ہے اور کھیت میں کام کر رہا ہے...")
    enable_islamic_filter = st.checkbox("Enable Islamic & Spiritual Safety Filter (حرمتِ انبیاء و اولیاء فلٹر) 🛡️", value=True)
    char_desc = st.text_input("Character Memory (کردار کا حلیہ):", placeholder="e.g. Saba is wearing a modest dark blue hijab")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1: uploaded_male_img = st.file_uploader("Upload Male Reference Image:", type=["jpg", "png", "jpeg"])
    with col_up2: uploaded_female_img = st.file_uploader("Upload Female Reference Image:", type=["jpg", "png", "jpeg"])
        
    scene_desc = st.text_input("Scene Memory (ماحول):", placeholder="e.g. Deep green ancient forest, dark stormy night")

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Speed:", ["+0% (Normal)", "+10% (Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Pitch:", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Dark Gothic / Mystery"])
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Sglowina AI is generating your video with voice and motion..."):
            v_res = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate=rate_val, pitch=pitch_val, ratio=mr, style=ms, seed=786,
                char_desc=char_desc, scene_desc=scene_desc, enable_watermark=enable_watermark, enable_bg_music=enable_bg_music,
                uploaded_male_img=uploaded_male_img, uploaded_female_img=uploaded_female_img, enable_islamic_filter=enable_islamic_filter,
                gen_mode=gen_mode, pollinations_key=pollinations_key
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
    p_i = st.text_area("Describe Image (One per line for batch):", height=120)
    ic1, ic2 = st.columns(2)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    
    if st.button("Generate Visuals 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        if u_db and u_db['credits'] >= 2:
            dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
            w, h = dim[i_size]
            img_data = fetch_img_failover(p_i, w, h, random.randint(1,999999))
            if img_data:
                img_path_temp = "temp_canvas.jpg"
                with open(img_path_temp, "wb") as f_temp:
                    f_temp.write(img_data)
                with Image.open(img_path_temp) as im:
                    st.image(im, caption="Generated Visual")
                if os.path.exists(img_path_temp): os.remove(img_path_temp)
                deduct_user_credits(st.session_state.logged_in_user, 2)
        else:
            st.error("Insufficient credits.")

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
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# -----------------
# TAB 6: ENTERPRISE CENTER
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina Enterprise Administration Center")
    u_db = get_user_data(st.session_state.logged_in_user)
    if u_db:
        st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
    else:
        st.warning("Please sign in first.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>ES & Sglowina AI Studio Suite | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
