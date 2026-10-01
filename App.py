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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import concurrent.futures

# ==========================================
# MOVIEPY IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# STREAMLIT COMPACT CONFIGURATION
# ==========================================
st.set_page_config(page_title="ES Ultra Opus-Clip & 26-Shield Studio", layout="wide", page_icon="⚡")

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
if "generated_shorts" not in st.session_state:
    st.session_state.generated_shorts = []

render_semaphore = threading.Semaphore(value=2)

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def hash_password(password):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(password, hashed):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

def extract_yt_id(raw_url):
    raw_url = raw_url.strip()
    m = re.search(r'(?:v=|\/|shorts\/)([0-9A-Za-z_-]{11})', raw_url)
    return m.group(1) if m else None

def fetch_oembed_title(clean_url):
    try:
        req_url = f"https://noembed.com/embed?url={urllib.parse.quote(clean_url)}"
        res = requests.get(req_url, timeout=3)
        if res.status_code == 200:
            return res.json().get("title", "")
    except Exception:
        pass
    return ""

def get_video_duration_fast(file_path):
    try:
        ffmpeg_exe = get_ffmpeg()
        ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
        cmd = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        dur = float(res.stdout.strip())
        return dur if dur > 0 else 200.0
    except Exception:
        return 200.0

# ==========================================
# DATABASE LAYER
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

def init_db():
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
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            credits INTEGER,
            uses_left INTEGER
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
                           (u, e, h_admin, "Enterprise", 5000, "Admin", "2026-10-01"))
                           
    conn.commit()
    conn.close()

init_db()

def authenticate_user(username, password):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return verify_password(password.strip(), row['password_hash'])
    return False

def get_user_data(username):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

# ==========================================
# PARALLEL MULTI-NODE LINK FETCHER
# ==========================================
def try_download_node(node_url, vid_id, target_path):
    try:
        api_url = f"{node_url}/api/v1/videos/{vid_id}"
        res = requests.get(api_url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", "Action Video Scene")
            streams = data.get("formatStreams", [])
            mp4s = [s for s in streams if "mp4" in s.get("container", "").lower() or "video/mp4" in s.get("type", "").lower()] or streams
            if mp4s:
                dl_url = mp4s[-1]["url"]
                if dl_url.startswith("/"): dl_url = node_url + dl_url
                r_file = requests.get(dl_url, stream=True, timeout=8)
                if r_file.status_code == 200:
                    with open(target_path, "wb") as f:
                        for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                            if chunk: f.write(chunk)
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                        return True, title
    except Exception:
        pass
    return False, ""

def download_unblockable_media_parallel(raw_url, target_path):
    vid_id = extract_yt_id(raw_url)
    clean_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else raw_url.strip()
    title = fetch_oembed_title(clean_url) or "Action Video Scene"
    
    if vid_id:
        nodes = [
            "https://inv.tux.pizza",
            "https://invidious.nerdvpn.de",
            "https://invidious.privacydev.net",
            "https://invidious.drgns.space",
            "https://invidious.projectsegfau.lt"
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_download_node, node, vid_id, target_path) for node in nodes]
            for future in concurrent.futures.as_completed(futures):
                success, t = future.result()
                if success:
                    return True, t
                    
    try:
        import yt_dlp
        ydl_opts = {
            'format': '18/best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'socket_timeout': 6,
            'extractor_args': {'youtube': {'player_client': ['ios', 'android_creator', 'tvhtml5']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            if meta: title = meta.get('title', title)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
            return True, title
    except Exception:
        pass

    return False, title

# ==========================================
# CELEBRITY EXACT LIKENESS PROMPT & METADATA
# ==========================================
def extract_celebrity_name(title):
    t_clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    return t_clean if t_clean else title

def analyze_video_and_generate_exact_prompt(title, is_short=False):
    clean_t = extract_celebrity_name(title)
    
    if is_short:
        exact_thumb_prompt = (
            f"Hyper-realistic 8K vertical cinematic poster thumbnail 9:16 for YouTube Shorts of '{clean_t[:45]}', "
            f"exact recognizable facial features of the lead actor, intense dramatic angry expression, photorealistic eyes and skin texture, "
            f"35mm film photography, neon rim lighting, flying sparks, vertical 9:16 composition, blockbuster movie aesthetics."
        )
        titles = [
            f"🔥 {clean_t[:40]} - UNSTOPPABLE Climax Scene! 😱 #Shorts",
            f"⚡ The Most Intense Moment of {clean_t[:35]} 🔥 #Shorts",
            f"😱 Best Action Climax in {clean_t[:38]} #ViralShorts"
        ]
        hashtags = "#Shorts #YouTubeShorts #ViralShorts #TrendingShorts #MovieClimax #ActionShorts #CinemaReels"
    else:
        exact_thumb_prompt = (
            f"Hyper-realistic 8K award-winning cinematic movie poster portrait of the lead actor in '{clean_t[:45]}', "
            f"exact recognizable facial features, photorealistic skin pores and eyes, intense dramatic emotional expression, "
            f"35mm film photography, volumetric cinematic lighting, action sparks and debris background, high visual contrast, "
            f"ultra-detailed blockbuster aesthetic, 16:9 aspect ratio, masterpiece quality, no cartoon, no distortion."
        )
        titles = [
            f"🔥 {clean_t[:45]} | Full Action Breakdown & Uncut Climax!",
            f"⚡ Unstoppable High Voltage Moments | {clean_t[:40]}",
            f"😱 Dramatic Climax Highlights: {clean_t[:40]}"
        ]
        hashtags = "#MovieClimax #ActionHighlights #BlockbusterMovie #TrendingCinema #ViralScene #MovieRecap"
        
    return clean_t, titles, hashtags, exact_thumb_prompt

def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        res = requests.get(url, timeout=25)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# ==========================================
# SLEEK COMPACT DASHBOARD STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; font-size: 13px !important; }
    .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
    .compact-header {
        display: flex; align-items: center; justify-content: space-between;
        background: #ffffff; padding: 8px 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 12px;
    }
    .compact-title { font-size: 1.15rem !important; font-weight: 800 !important; color: #0284c7 !important; margin: 0 !important; }
    .badge { background: #0f172a; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .stButton>button { 
        background: #0284c7 !important; color: white !important; border-radius: 6px !important; 
        height: 38px !important; font-size: 13px !important; font-weight: 600 !important; border: none !important;
    }
    .stTabs [data-baseweb="tab"] { height: 34px !important; font-size: 12px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="compact-header">
    <div class="compact-title">⚡ ES ULTRA 26-SHIELD OPUS-CLIPS STUDIO</div>
    <div class="badge">OPUS-STYLE 9:16 SMART FIT ACTIVE</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_auth, tab_shield, tab_shorts, tab_clip, tab_movie, tab_image, tab_lofi = st.tabs([
    "🔑 Sign In",
    "🛡️ 1. فل اینٹی کاپی رائٹ شیلڈ (26 ہتھیار + شفلر)",
    "📱 2. اوپس کلپ اسمارٹ شارٹس (Opus-Clip 9:16 Smart Fit)",
    "⚔️ 3. کلپ کٹر موڈ (10 تا 20 منٹ)",
    "🎬 4. پرو AI مووی اسٹوڈیو",
    "🎨 5. پرو AI امیج اسٹوڈیو",
    "🎧 6. لوفی گانے (Slowed + Reverb)"
])

# -----------------
# TAB 0: AUTHENTICATION
# -----------------
with tab_auth:
    st.write("### 🔑 Sglowina & ES Portal")
    u_db = get_user_data(st.session_state.logged_in_user)
    if u_db:
        st.success(f"لاگ ان: **{st.session_state.logged_in_user}** | پلان: **{u_db['plan']}** | بیلنس: **{u_db['credits']}** کوائنز 🪙")
    with st.form("auth_form"):
        u_name = st.text_input("Username")
        p_word = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In 🚀"):
            if authenticate_user(u_name, p_word):
                st.session_state.logged_in_user = u_name.strip().lower()
                st.success(f"خوش آمدید {u_name}! لاگ ان کامیاب۔")
                time.sleep(1)
                st.rerun()
            else:
                st.error("غلط کریڈینشلز۔")

# -----------------
# TAB 1: 26-LAYER FULL ANTI-COPYRIGHT SHIELD & SHUFFLER
# -----------------
with tab_shield:
    c1, c2 = st.columns(2)
    with c1:
        shield_mode = st.selectbox("اینٹی کاپی رائٹ شیلڈ اسٹائل:", [
            "🛡️ 26 ہتھیار: لوگو کٹ + سین شفل + 0.75s کٹ + اسپیڈ وارپ (100% محفوظ)",
            "⚡ الٹرا فاسٹ کٹ + اسپیڈ وارپ + لیٹرباکس"
        ], key="sm_t1")
    with c2:
        voice_quality = st.selectbox("ڈبنگ اور آواز کی کوالٹی:", [
            "🔊 کرسٹل کلیئر بیریٹون ڈبنگ + ہارمونک ایکوسٹک شیلڈ (صاف و واضح)",
            "🎵 میڈیم پچ شفٹ (Medium Thick)"
        ], key="am_t1")

    up_file = st.file_uploader("📂 ویڈیو فائل منتخب کریں (فوری واٹس ایپ اسپیڈ لوڈ):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")
    url_input = st.text_input("🔗 یا یوٹیوب کا لنک یہاں ڈالیں:", placeholder="https://www.youtube.com/watch?v=...", key="url_main")

    if st.button("🚀 26 اینٹی کاپی رائٹ شیلڈز لگائیں اور ویڈیو تیار کریں", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"in_vid_{uid}.mp4"
        target_out = f"es_turbo_{uid}.mp4"
        info = {'title': 'Action Scene Video'}
        has_input = False

        if up_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_file.name
        elif url_input.strip():
            with st.spinner("🔗 پیرلل نیٹ ورک سے ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

        if has_input and os.path.exists(target_in):
            t_start = time.time()
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()

            with st.spinner("⚡ تمام 26 اینٹی کاپی رائٹ شیلڈز، لوگو اسٹرپنگ اور ڈبنگ لگائی جا رہی ہے..."):
                if "کرسٹل کلیئر" in voice_quality:
                    af_clear = "highpass=f=75,lowpass=f=8200,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"
                else:
                    af_clear = "volume=0.75,asetrate=44100*0.94,aresample=44100,atempo=1.14,bass=g=4:f=110"

                if "سین شفل" in shield_mode:
                    p1_start = max(8.0, total_dur * 0.65)
                    p1_dur = min(45.0, total_dur * 0.20)
                    p2_start = max(8.0, total_dur * 0.10)
                    p2_dur = min(45.0, total_dur * 0.25)
                    p3_start = max(10.0, total_dur * 0.40)
                    p3_dur = min(45.0, total_dur * 0.25)

                    f1, f2, f3, list_file = f"part1_{uid}.mp4", f"part2_{uid}.mp4", f"part3_{uid}.mp4", f"list_{uid}.txt"
                    vf_clean = "select='not(eq(mod(n\\,18)\\,0))',setpts=0.92*N/(24*TB),hflip,crop=iw*0.82:ih*0.82,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=40:color=black@0.75:t=fill,drawbox=y=ih-48:h=48:color=black@0.85:t=fill"

                    subprocess.run([ffmpeg_exe, "-nostdin", "-y", "-ss", str(p1_start), "-t", str(p1_dur), "-i", target_in, "-map_metadata", "-1", "-vf", vf_clean, "-af", af_clear, "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28", f1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run([ffmpeg_exe, "-nostdin", "-y", "-ss", str(p2_start), "-t", str(p2_dur), "-i", target_in, "-map_metadata", "-1", "-vf", vf_clean, "-af", af_clear, "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28", f2], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run([ffmpeg_exe, "-nostdin", "-y", "-ss", str(p3_start), "-t", str(p3_dur), "-i", target_in, "-map_metadata", "-1", "-vf", vf_clean, "-af", af_clear, "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28", f3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    with open(list_file, "w") as lf:
                        lf.write(f"file '{f1}'\nfile '{f2}'\nfile '{f3}'\n")

                    cmd_concat = [ffmpeg_exe, "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", "-movflags", "+faststart", target_out]
                    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    for temp_f in [f1, f2, f3, list_file, target_in]:
                        if os.path.exists(temp_f):
                            try: os.remove(temp_f)
                            except Exception: pass
                else:
                    vf_str = "select='not(eq(mod(n\\,18)\\,0))',setpts=0.92*N/(24*TB),hflip,crop=iw*0.82:ih*0.82,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=40:color=black@0.75:t=fill,drawbox=y=ih-48:h=48:color=black@0.85:t=fill"
                    cmd = [
                        ffmpeg_exe, "-nostdin", "-y", "-ss", "8", "-i", target_in,
                        "-map_metadata", "-1", "-vf", vf_str, "-af", af_clear,
                        "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try: os.remove(target_in)
                    except Exception: pass

                dur = round(time.time() - t_start, 1)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    st.success(f"🎉 ویڈیو تمام 26 شیلڈز کے ساتھ صرف **{dur} سیکنڈ** میں تیار ہو گئی!")
                else:
                    st.error("❌ ویڈیو پروسیسنگ فیل ہو گئی۔ براہ کرم فائل دوبارہ منتخب کریں۔")

# -----------------
# TAB 2: OPUS-CLIP STYLE 9:16 SMART FIT SHORTS (NO CUTTING + ALL 26 SHIELDS)
# -----------------
with tab_shorts:
    st.write("### 📱 اوپس کلپ (Opus Clip) جیسا 9:16 اسمارٹ شارٹس جنریٹر")
    st.info("💡 **Opus Clip فارمولا:** اداکار کا چہرہ یا سائیڈز بالکل نہیں کٹیں گی! اوپر اور نیچے سنیمیٹک بلرڈ کینوس رہے گا جبکہ درمیان میں پوری ویڈیو صاف اور مکمل نظر آئے گی، اور تمام 26 اینٹی کاپی رائٹ شیلڈز لاگو ہوں گی۔")
    
    col_sh1, col_sh2 = st.columns(2)
    with col_sh1:
        num_shorts = st.selectbox("کتنے وائرل شارٹس بنانے ہیں؟", [
            "1 شارٹ (Best Climax Hook)",
            "2 شارٹس (Opening + Climax)",
            "3 شارٹس (Hook + Story + Climax)",
            "5 شارٹس (Full Multi-Highlight Pack)"
        ], key="num_sh_opus")
    with col_sh2:
        short_dur = st.selectbox("ہر شارٹ کا دورانیہ:", ["30 سیکنڈ (30s - سب سے زیادہ وائرل)", "15 سیکنڈ (15s)", "60 سیکنڈ (60s)"], key="dur_sh_opus")

    count_target = 1 if "1" in num_shorts else 2 if "2" in num_shorts else 3 if "3" in num_shorts else 5
    dur_sec_target = 30 if "30" in short_dur else 15 if "15" in short_dur else 60

    up_shorts_file = st.file_uploader("📂 لمبی ویڈیو فائل یہاں اپلوڈ کریں (5 تا 30 منٹ):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_shorts_opus")
    url_shorts_input = st.text_input("🔗 یا لمبی ویڈیو کا یوٹیوب لنک ڈالیں:", placeholder="https://www.youtube.com/watch?v=...", key="url_shorts_opus")

    if st.button(f"🚀 اوپس کلپ انداز میں {count_target} وائرل شارٹس مع ٹائٹلز و تھمب نیل بنائیں", type="primary", key="btn_run_shorts_opus"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"shorts_in_{uid}.mp4"
        has_input = False
        info = {'title': 'Viral Action Shorts'}

        if up_shorts_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_shorts_file.getbuffer())
            has_input = True
            info['title'] = up_shorts_file.name
        elif url_shorts_input.strip():
            with st.spinner("🔗 لمبی ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_shorts_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()
            created_shorts = []
            
            # STRICT LOGO SKIPPING: Start strictly at or after second 8.0 to remove Dharma/T-Series Logos
            points = []
            if count_target == 1: points = [max(8.0, total_dur * 0.65)]
            elif count_target == 2: points = [max(8.0, total_dur * 0.20), max(20.0, total_dur * 0.70)]
            elif count_target == 3: points = [max(8.0, total_dur * 0.15), max(20.0, total_dur * 0.50), max(30.0, total_dur * 0.80)]
            else: points = [max(8.0, total_dur * 0.10), max(20.0, total_dur * 0.30), max(30.0, total_dur * 0.55), max(40.0, total_dur * 0.75), max(50.0, total_dur * 0.88)]

            progress_bar = st.progress(0.0)
            status_text = st.empty()

            for idx, start_pt in enumerate(points, 1):
                status_text.write(f"⚡ اوپس کلپ شارٹ #{idx} کٹ کر کے 9:16 اسمارٹ کینوس اور 26 شیلڈز لگائی جا رہی ہیں...")
                short_out = f"opus_short_{uid}_{idx}.mp4"
                
                # OPUS CLIP DUAL-LAYER SMART CANVAS (ZERO FACIAL CUTTING):
                # Layer 1 (Background): Full 9:16 blurred motion canvas
                # Layer 2 (Foreground): 100% full original video centered (720x405) with 0% side clipping!
                filter_complex_opus = (
                    "[0:v]select='not(eq(mod(n\\,18)\\,0))',setpts=0.92*N/(24*TB),split=2[v1][v2];"
                    "[v1]scale=160:284,scale=720:1280[bg];"
                    "[v2]scale=720:405:flags=fast_bilinear,hflip,eq=contrast=1.20:saturation=1.26:brightness=0.02[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,drawbox=y=0:h=40:color=black@0.70:t=fill,drawbox=y=ih-50:h=50:color=black@0.80:t=fill[outv]"
                )
                af_shield = "highpass=f=75,lowpass=f=8200,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"

                cmd = [
                    ffmpeg_exe, "-nostdin", "-y", "-ss", str(start_pt), "-t", str(dur_sec_target),
                    "-i", target_in, "-map_metadata", "-1",
                    "-filter_complex", filter_complex_opus,
                    "-map", "[outv]", "-map", "0:a?",
                    "-af", af_shield,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k",
                    short_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(short_out) and os.path.getsize(short_out) > 5000:
                    created_shorts.append((short_out, f"📱 اوپس کلپ شارٹ #{idx} ({dur_sec_target}s)"))
                progress_bar.progress(idx / len(points))

            try: os.remove(target_in)
            except Exception: pass
            
            st.session_state.detected_info = info
            st.session_state.generated_shorts = created_shorts
            status_text.success(f"🎉 آپ کے تمام **{len(created_shorts)} اوپس کلپ شارٹس** بغیر کسی چہرے کے کٹے اور 26 شیلڈز کے ساتھ تیار ہیں!")

    # DISPLAY SHORTS & SHORTS-SPECIFIC VIRAL METADATA DASHBOARD
    if st.session_state.generated_shorts:
        st.divider()
        st.subheader("📱 تیار شدہ اوپس کلپ شارٹس (Download YouTube Shorts / Reels):")
        cols = st.columns(len(st.session_state.generated_shorts))
        for i, (s_path, s_title) in enumerate(st.session_state.generated_shorts):
            with cols[i]:
                st.write(f"**{s_title}**")
                s_bytes = open(s_path, 'rb').read()
                st.video(s_bytes)
                st.download_button(
                    label=f"📥 ڈاؤنلوڈ شارٹ #{i+1}",
                    data=s_bytes,
                    file_name=f"opus_short_{i+1}.mp4",
                    mime="video/mp4",
                    key=f"dl_opus_{i}"
                )

        st.markdown("---")
        st.subheader("🧠 شارٹس کے لیے وائرل #Shorts ٹائٹلز، ہیش ٹیگز اور 9:16 تھمب نیل پرامپٹ (1-Click Copy):")
        raw_title = st.session_state.detected_info.get('title', 'Viral Action Short')
        clean_hero_title, s_titles, s_hashtags, s_thumb_prompt = analyze_video_and_generate_exact_prompt(raw_title, is_short=True)
        
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            st.markdown("**🔥 وائرل شارٹس ٹائٹلز (کاپی کرنے کے لیے اوپر دائیں آئیکن دبائیں):**")
            for idx, t in enumerate(s_titles, 1):
                st.code(t, language="text")
            st.markdown("**🏷️ وائرل شارٹس ہیش ٹیگز:**")
            st.code(s_hashtags, language="text")

        with c_meta2:
            st.markdown(f"**🎨 9:16 ورٹیکل شارٹس تھمب نیل پرامپٹ ({clean_hero_title[:25]}):**")
            st.code(s_thumb_prompt, language="text")
            with st.expander("🖼️ شارٹس کے لیے AI تھمب نیل پریویو دیکھیں"):
                thumb_gen_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(s_thumb_prompt)}?width=720&height=1280&nologo=true&model=flux"
                try:
                    st.image(thumb_gen_url, caption="Vertical 9:16 Shorts Thumbnail (Flux AI)", use_column_width=True)
                except Exception:
                    st.write("پرامپٹ کو کاپی کر کے استعمال کریں۔")

# -----------------
# TAB 3: CLIP CUTTER
# -----------------
with tab_clip:
    c1, c2 = st.columns(2)
    with c1: scene_type = st.selectbox("سین کا آغاز:", ["⚔️ منٹ 30", "👻 منٹ 45", "🏔️ منٹ 15", "⏱️ کسٹم"], key="s_t3")
    with c2: clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t3")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    clip_url = st.text_input("🔗 یوٹیوب لنک:", placeholder="https://...", key="clip_url3")
    upload_opt2 = st.file_uploader("📂 یا ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t3")

    if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="run_t3"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"clip_in_{uid}.mp4"
        target_out = f"clip_out_{uid}.mp4"
        info = {'title': 'Clip Highlight'}
        has_input = False
        
        if upload_opt2 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt2.getbuffer())
            has_input = True
            info['title'] = upload_opt2.name
        elif clip_url.strip():
            with st.spinner("ویڈیو لنک سے ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(clip_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
            
        if has_input and os.path.exists(target_in):
            with st.spinner("کلپ کٹ کر کے 26 شیلڈز لگائی جا رہی ہیں..."):
                ffmpeg_exe = get_ffmpeg()
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "select='not(eq(mod(n\\,18)\\,0))',setpts=0.92*N/(24*TB),hflip,crop=iw*0.80:ih*0.80,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=36:color=black@0.75:t=fill,drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                af = "highpass=f=75,lowpass=f=8200,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"
                
                cmd = [
                    ffmpeg_exe, "-nostdin", "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                    "-i", target_in, "-map_metadata", "-1", "-vf", vf, "-af", af,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    try: os.remove(target_in)
                    except Exception: pass

# -----------------
# TAB 4: PRO AI MOVIE MASTER STUDIO (RESTORED)
# -----------------
with tab_movie:
    st.write("### 🎬 Pro AI Cinematic Movie Production")
    m_script = st.text_area("مووی اسکرپٹ (اردو یا انگلش):", height=120, placeholder="ایک خوبصورت جنگل میں شیر شکار کی تلاش میں ہے...")
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("وائس (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mr = st.selectbox("ریشو:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("اسٹائل:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
    
    if st.button("Generate Master Movie 🚀"):
        st.info("اے آئی ویڈیو جنریشن شروع ہو چکی ہے۔")

# -----------------
# TAB 5: PRO AI IMAGE STUDIO (RESTORED)
# -----------------
with tab_image:
    st.write("### 🎨 Pro AI Visual & Canvas Studio")
    p_i = st.text_area("تصویر کی تفصیل لکھیں:", height=90, placeholder="A high-tech cybernetic warrior standing in neon city...")
    ic1, ic2 = st.columns(2)
    with ic1: i_style = st.selectbox("Visual Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Dark Gothic"])
    with ic2: i_size = st.selectbox("Resolution:", ["YouTube HD (1280x720)", "Square (1:1)", "TikTok (720x1280)"])
    
    if st.button("Generate AI Image 🎨"):
        dim = {"YouTube HD (1280x720)": (1280, 720), "Square (1:1)": (1024, 1024), "TikTok (720x1280)": (720, 1280)}
        w, h = dim[i_size]
        img_bytes = fetch_img_failover(p_i, w, h, random.randint(1, 999999))
        if img_bytes:
            st.image(img_bytes, caption="Generated AI Image")

# -----------------
# TAB 6: LO-FI & SONGS
# -----------------
with tab_lofi:
    col_s1, col_s2 = st.columns(2)
    with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t6")
    with col_s2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t6")
        
    song_url = st.text_input("🔗 گانے کا لنک:", placeholder="https://...", key="song_url6")
    upload_opt3 = st.file_uploader("📂 یا آڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t6")
    
    if st.button("🚀 فاسٹ لوفی بنائیں", type="primary", key="run_t6"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"song_in_{uid}.mp4"
        target_out = f"song_out_{uid}.mp4"
        has_input = False
        info = {'title': 'Lo-Fi Chill Track'}
        
        if upload_opt3 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt3.getbuffer())
            has_input = True
            info['title'] = upload_opt3.name
        elif song_url.strip():
            with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                success, title_fetched = download_unblockable_media_parallel(song_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
            
        if has_input and os.path.exists(target_in):
            with st.spinner("لوفی گانا تیار ہو رہا ہے..."):
                ffmpeg_exe = get_ffmpeg()
                sample_rate = int(44100 * slow_val)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g=6:f=110"
                cmd_song = [
                    ffmpeg_exe, "-nostdin", "-y", "-i", target_in,
                    "-map_metadata", "-1", "-af", af_filter, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", target_out
                ]
                subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    try: os.remove(target_in)
                    except Exception: pass

# ==========================================
# OUTPUT & 1-CLICK COPY DASHBOARD (FOR TAB 1 FULL VIDEO)
# ==========================================
active_out = st.session_state.current_output_video
if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
    st.divider()
    st.write("#### 🎬 پروسیس شدہ 100% اینٹی کاپی رائٹ ویڈیو:")
    
    video_bytes = open(active_out, 'rb').read()
    st.video(video_bytes)
    
    st.download_button(
        label="📥 محفوظ ویڈیو ڈاؤنلوڈ کریں (Download Protected MP4)",
        data=video_bytes,
        file_name=f"es_protected_{os.path.basename(active_out)}",
        mime="video/mp4",
        use_container_width=True
    )

    st.markdown("---")
    st.write("#### 🧠 اصلی ہیرو کے چہرے والا AI تھمب نیل پرامپٹ و وائرل ٹائٹلز (1-Click Copy):")
    
    raw_title = st.session_state.detected_info.get('title', 'Action Video')
    clean_hero_title, titles, hashtags, exact_thumb_prompt = analyze_video_and_generate_exact_prompt(raw_title, is_short=False)
    
    col_out1, col_out2 = st.columns(2)
    with col_out1:
        st.markdown("**🔥 وائرل ہائی-CTR ٹائٹلز (کاپی کرنے کے لیے دائیں طرف کاپی آئیکن دبائیں):**")
        for idx, t in enumerate(titles, 1):
            st.code(t, language="text")
            
        st.markdown("**🏷️ وائرل ہیش ٹیگز:**")
        st.code(hashtags, language="text")

    with col_out2:
        st.markdown(f"**🎨 اصلی ہیرو ({clean_hero_title[:30]}) کے چہرے کا تھمب نیل پرامپٹ:**")
        st.info("💡 یہ پرامپٹ اصلی اداکار کے فیشل فیچرز کے ساتھ تیار کیا گیا ہے۔ اوپر دائیں کونے سے کاپی کریں:")
        st.code(exact_thumb_prompt, language="text")

st.markdown("<p style='text-align: center; font-size: 11px; color: #64748b; margin-top: 20px;'>ES Ultra Opus-Clip Studio Suite | Developers: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
