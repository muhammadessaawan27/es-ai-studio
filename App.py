import sys
# 1. Pillow 10+ Monkey-patch for MoviePy
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS if hasattr(PIL.Image, 'Resampling') else 1
    sys.modules['PIL.Image'] = PIL.Image
except:
    pass

import os
import io
import re
import time
import uuid
import json
import random
import sqlite3
import hashlib
import asyncio
import threading
import subprocess
import requests
import urllib.parse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import streamlit as st

# Safe Asyncio for Edge-TTS in Streamlit
try:
    import nest_asyncio
    nest_asyncio.apply()
except:
    pass

# Auto-detect bundled FFmpeg executable from imageio-ffmpeg
try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except:
    FFMPEG_BIN = "ffmpeg"

try:
    from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, CompositeVideoClip, CompositeAudioClip
    MOVIEPY_AVAILABLE = True
    MOVIEPY_ERROR = ""
except Exception as e:
    MOVIEPY_AVAILABLE = False
    MOVIEPY_ERROR = str(e)

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"
TRANSITION_SFX_FILE = "transition_whoosh.mp3"

st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V2.0 (Engineered)", layout="wide", page_icon="🎬")

if "gen_mode" not in st.session_state:
    st.session_state.gen_mode = "Cinematic Photo Zoom & Pan (100% Free & Unlimited)"
if "pollinations_key" not in st.session_state:
    st.session_state.pollinations_key = ""
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []

render_semaphore = threading.Semaphore(value=1)
render_lock = threading.Lock()

# ================= Database & Core Utilities =================
def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

def hash_password(password):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(password, hashed):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

def get_db_connection():
    pg_url = os.environ.get("DATABASE_URL")
    if pg_url:
        try:
            import psycopg2
            return psycopg2.connect(pg_url)
        except: pass
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try: conn.execute("PRAGMA journal_mode=WAL;")
    except: pass
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    is_sqlite = "sqlite" in str(type(conn))
    sp = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    ph = "?" if is_sqlite else "%s"
    c.execute(f"""CREATE TABLE IF NOT EXISTS users (
        id {sp}, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, plan TEXT DEFAULT 'Free', credits INTEGER DEFAULT 50,
        role TEXT DEFAULT 'User', status TEXT DEFAULT 'Active', created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, user_id INTEGER, project_name TEXT,
        type TEXT, file_path TEXT, prompt TEXT, created_at TEXT, is_favorite INTEGER DEFAULT 0
    )""")
    c.execute(f"CREATE TABLE IF NOT EXISTS credits_history (id {sp}, user_id INTEGER, action TEXT, credits_used INTEGER, balance_after INTEGER, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS local_payments (id TEXT PRIMARY KEY, username TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Pending', created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

def authenticate_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    ph = "?" if "sqlite" in str(type(conn)) else "%s"
    try:
        c.execute(f"SELECT password_hash FROM users WHERE LOWER(username) = LOWER({ph})", (username.strip().lower(),))
        row = c.fetchone()
        if row:
            hashed = row['password_hash'] if hasattr(row, 'keys') else row[0]
            return verify_password(password.strip(), hashed)
    except: pass
    finally: conn.close()
    return False

def get_user_data(username):
    conn = get_db_connection()
    c = conn.cursor()
    ph = "?" if "sqlite" in str(type(conn)) else "%s"
    try:
        c.execute(f"SELECT * FROM users WHERE LOWER(username) = LOWER({ph})", (username.strip().lower(),))
        row = c.fetchone()
        if row: return dict(row)
    except: pass
    finally: conn.close()
    return None

def deduct_user_credits(username, amount):
    conn = get_db_connection()
    c = conn.cursor()
    ph = "?" if "sqlite" in str(type(conn)) else "%s"
    try:
        c.execute(f"UPDATE users SET credits = MAX(0, credits - {ph}) WHERE LOWER(username) = LOWER({ph})", (amount, username.strip().lower()))
        conn.commit()
    except: pass
    finally: conn.close()

# ================= Edge-TTS Audio Generation =================
def save_audio_safe(text, voice, rate, pitch, filename):
    async def _tts_exec():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_tts_exec())
            # Wait cleanly for synchronous completion
            t_end = time.time() + 20
            while not os.path.exists(filename) and time.time() < t_end:
                time.sleep(0.1)
        else:
            loop.run_until_complete(_tts_exec())
        return os.path.exists(filename) and os.path.getsize(filename) > 500
    except Exception:
        try:
            asyncio.run(_tts_exec())
            return os.path.exists(filename) and os.path.getsize(filename) > 500
        except Exception as e:
            st.error(f"Voice Synthesis Error: {e}")
            return False

# ================= Visual & Flux Prompt Engine =================
def translate_ur_to_en(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            res = r.json()
            return "".join([s[0] for s in res[0] if s[0]]).strip()
    except: pass
    return text

def download_image_flux(prompt, path, w, h, seed):
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
    for attempt in range(2):
        try:
            r = session.get(url, timeout=25)
            if r.status_code == 200 and len(r.content) > 3000:
                with open(path, "wb") as f: f.write(r.content)
                with Image.open(path) as im: im.load()
                return True
        except: time.sleep(0.5)
    
    # Fallback Gradient on dropouts
    im = Image.new("RGB", (w, h), color=(15, 23, 42))
    d = ImageDraw.Draw(im)
    d.text((50, h//2), "Sglowina AI Visual Render", fill=(255, 255, 255))
    im.save(path, "PNG")
    return True

# ================= Low-RAM FFmpeg Video Rendering =================
def render_single_scene(img_path, audio_path, out_clip_path, duration, w, h, motion="Zoom Out"):
    """Creates a standalone MP4 clip without keeping full composite memory buffers in RAM"""
    temp_resized = img_path.replace(".png", "_scaled.png")
    scale = 1.06
    cw, ch = make_even(w * scale), make_even(h * scale)
    with Image.open(img_path) as im:
        im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_resized, "PNG")

    img_clip = ImageClip(temp_resized).set_duration(duration).set_fps(24)
    if motion == "Pan Left":
        animated = img_clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center'))
    elif motion == "Pan Right":
        animated = img_clip.set_position(lambda t: (int((w - cw) * (1 - t / duration)), 'center'))
    else:
        animated = img_clip.set_position('center')

    comp_clip = CompositeVideoClip([animated], size=(w, h)).set_duration(duration)
    a_clip = AudioFileClip(audio_path)
    comp_clip = comp_clip.set_audio(a_clip)

    comp_clip.write_videofile(
        out_clip_path, codec="libx264", audio_codec="aac",
        fps=24, preset="ultrafast", threads=2, logger=None,
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    comp_clip.close()
    a_clip.close()
    img_clip.close()
    if os.path.exists(temp_resized): os.remove(temp_resized)

def concat_clips_ffmpeg(clip_paths, final_output_path):
    """Zero-RAM direct file concatenation via FFmpeg Demuxer"""
    list_file = os.path.join(TEMP_DIR, f"list_{uuid.uuid4().hex[:6]}.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
            
    cmd = [
        FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", final_output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(list_file): os.remove(list_file)
    return os.path.exists(final_output_path)

# ================= Master Cinematic Pipeline =================
def run_production_pipeline(story, voice, rate, pitch, ratio, style, seed, user_char_anchor=""):
    u_id = uuid.uuid4().hex[:6]
    progress = st.progress(0.0)
    status = st.empty()
    
    # 1. Parse Script cleanly
    sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story) if len(s.strip()) > 3]
    if not sentences: sentences = [story.strip()]
    total = len(sentences)
    
    res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
    w, h = res_map.get(ratio, (1280, 720))
    w, h = make_even(w), make_even(h)

    # 2. Lock Character Consistency Anchor
    base_character_anchor = user_char_anchor.strip()
    if not base_character_anchor:
        base_character_anchor = "cinematic character, clear facial details, detailed outfit, highly coherent"

    scene_clips = []
    temp_files_to_clean = []

    try:
        for i, scene in enumerate(sentences):
            status.info(f"⚙️ پروسیسنگ سین {i+1} از {total}: آڈیو اور ویژول سنکرونائزیشن...")
            progress.progress((i / total) * 0.8)

            # Audio
            aud_path = os.path.join(TEMP_DIR, f"aud_{u_id}_{i}.mp3")
            if not save_audio_safe(scene, voice, rate, pitch, aud_path):
                raise RuntimeError("آڈیو تیار کرنے میں ناکامی۔")
            temp_files_to_clean.append(aud_path)

            dur = AudioFileClip(aud_path).duration

            # Visual Prompt with Anchor DNA and FIXED SEED
            trans_en = translate_ur_to_en(scene)
            # Prepend fixed anchor to enforce Flux character consistency
            full_prompt = f"{base_character_anchor}, {trans_en}, visual style: {style}, 8k, sharp focus, cinematic lighting"

            img_path = os.path.join(TEMP_DIR, f"img_{u_id}_{i}.png")
            download_image_flux(full_prompt, img_path, w, h, seed=seed) # FIXED SEED MAINTAINED
            temp_files_to_clean.append(img_path)

            # Render Independent Scene File to Disk (RAM stays clean)
            clip_path = os.path.join(TEMP_DIR, f"clip_{u_id}_{i}.mp4")
            render_single_scene(img_path, aud_path, clip_path, dur, w, h, motion="Zoom Out" if i%2==0 else "Pan Left")
            scene_clips.append(clip_path)
            temp_files_to_clean.append(clip_path)

        # 3. Stitching with Zero-RAM FFmpeg Demuxer
        progress.progress(0.9)
        status.info("🎬 فائنل ویڈیو رینڈر ہو رہی ہے (FFmpeg Concat)...")
        final_mp4 = f"Master_{u_id}.mp4"
        
        if concat_clips_ffmpeg(scene_clips, final_mp4):
            progress.progress(1.0)
            status.success("🚀 ویڈیو کامیابی سے تیار ہو گئی!")
            return final_mp4
        else:
            raise RuntimeError("ویڈیو اسپلائسنگ کا عمل ناکام ہو گیا۔")

    finally:
        # Clean temporary disk files
        for f in temp_files_to_clean:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass

# ================= UI & Dashboard =================
st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🎬 Sglowina AI - Studio Dashboard</h2>", unsafe_allow_html=True)

with st.container():
    c1, c2 = st.columns([2, 1])
    with c1:
        story_input = st.text_area("کہانی یا اسکرپٹ یہاں درج کریں (Urdu / English):", height=140, placeholder="ایک بہادر عقاب جو جنگل کے بلند پہاڑوں پر رہتا تھا...")
        char_anchor_input = st.text_input("کردار کا فکسڈ اینکر (Character Consistency Anchor):", placeholder="مثال: A sharp-eyed young prince wearing green traditional robes, distinctive scar on cheek")
    with c2:
        v_voice = st.selectbox("آواز منتخب کریں:", ["ur-PK-AsadNeural", "ur-PK-UzmaNeural", "en-US-GuyNeural", "en-US-JennyNeural"])
        v_ratio = st.selectbox("سائز (Aspect Ratio):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
        v_style = st.selectbox("ویژول اسٹائل:", ["Realistic HD", "Cinematic Hollywood", "3D Cartoon", "Anime Art", "Dark Gothic"])
        v_seed = st.number_input("فکسڈ سیڈ (Fixed Seed for Coherence):", value=786, step=1)

if st.button("ماسٹر مووی جنریٹ کریں 🚀", use_container_width=True):
    if not story_input.strip():
        st.error("پہلے اسکرپٹ لکھو!")
    else:
        with render_semaphore:
            out_file = run_production_pipeline(story_input, v_voice, "+0%", "+0Hz", v_ratio, v_style, int(v_seed), char_anchor_input)
            if out_file and os.path.exists(out_file):
                st.video(out_file)
                with open(out_file, "rb") as f:
                    st.download_button("ڈاؤنلوڈ ویڈیو (Full HD)", f.read(), file_name=out_file, mime="video/mp4")
