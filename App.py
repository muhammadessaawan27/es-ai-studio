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
if "proceimport streamlit as st
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
# MOVIEPY CINEMATIC IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# BROWSER SESSION HEADERS
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI & ES Studio is an advanced AI video production and anti-copyright shield platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

# ==========================================
# STREAMLIT CONFIGURATION
# ==========================================
st.set_page_config(page_title="ES Ultimate Anti-Copyright AI Studio", layout="wide", page_icon="⚡")

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
                           (u, e, h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
                           
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

def deduct_user_credits(username, amount):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE LOWER(username) = LOWER(?)", (amount, username))
    conn.commit()
    conn.close()

# ==========================================
# ADVANCED MULTI-PLATFORM DOWNLOADER
# ==========================================
def inspect_and_fetch_media(raw_url, base_prefix):
    clean_url = sanitize_url(raw_url)
    info_dict = {'title': 'Action Scene Video', 'uploader': 'Official Creator'}
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
    except Exception:
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
    
    if any(k in t_lower for k in ['mental', 'force', 'john', 'action', 'fight', 'movie', 'scene', 'police', 'hindi', 'bloopers', 'ustad']):
        genre = "Bollywood Action Breakdown"
        safe_titles = [
            f"🔥 {clean_title[:50]} | Full Action Scene Breakdown",
            f"⚡ Unstoppable Action Moments | {clean_title[:40]}",
            f"😱 Dramatic Climax Recap | {clean_title[:40]}"
        ]
        hashtags = "#MovieBreakdown #ActionMovie #BollywoodAction #Blockbuster #ViralVideo #HindiCinema"
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
    else:
        genre = "Viral Video Recap"
        safe_titles = [
            f"🔥 {clean_title[:45]} - Full HD Climax Scene Explained",
            f"⚡ {clean_title[:45]} - Best Action Highlights",
            f"😱 The Most Dramatic Scene of {clean_title[:40]}"
        ]
        hashtags = "#ViralClip #TrendingNow #CinemaRecap #ActionHighlights #BlockbusterScene"
        thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', dramatic intense face, cinematic color grading, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

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

st.markdown('<div class="glow-title">SGLOWINA & ES ANTI-COPYRIGHT ENGINE</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">ES</div></div>', unsafe_allow_html=True)

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_es_shield, tab_movie, tab_image, tab_chat = st.tabs([
    "⚡ ES الٹیمیٹ اینٹی کاپی رائٹ شیلڈ (Auto Shield Engine)",
    "🎬 Pro Movie Master Studio", 
    "🎨 Pro Image Studio",
    "💬 AI Assistant & Auth"
])

# -----------------
# TAB 1: ES 100% ANTI-COPYRIGHT & CONTENT-ID SHIELD
# -----------------
with tab_es_shield:
    st.write("### ⚡ 100% کاپی رائٹ و کنٹینٹ آئی ڈی کلیم پروٹیکشن سسٹم")
    st.info("💡 **فل پاور موڈ آن:** ہر سیکنڈ کے فریمز پر مائیکرو کٹس (Timeline Break)، کینوس ری سائز، 1.8° اینٹی ہیش ٹِلٹ، فنگر پرنٹ نوائز اور ہارمونک آڈیو ماسکنگ ایکٹیو ہے۔")
    
    sub1, sub2, sub3 = st.tabs([
        "🎬 1. فل مووی / ویڈیو موڈ (مکمل خودکار اینٹی کلیم شیلڈ)",
        "⚔️ 2. کلپ کٹر موڈ (10 سے 20 منٹ کلپ)",
        "🎧 3. گانے اور لوفی (Slowed + Reverb ماسٹرنگ)"
    ])
    
    with sub1:
        st.subheader("ویڈیو یا مووی ڈالیں (ہر قسم کے کلیم سے محفوظ)")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            shield_power = st.selectbox("اینٹی کاپی رائٹ شیلڈ لیول:", [
                "🛡️ الٹیمیٹ مائیکرو کٹ + کینوس فریم + 1.8° ٹِلٹ + ہائی نوائز (100% محفوظ)",
                "⚡ الٹرا مائیکرو کٹ + ڈیپ زوم + اینٹی ہیش لیٹرباکس"
            ], key="s_p1")
        with col_m2:
            audio_shield = st.selectbox("آڈیو ماسکنگ و پچ لیئرنگ:", [
                "🔊 آٹومیٹک ایکوسٹک ماسکنگ + بھاری ہارمونک پچ (100% Content-ID Safe)",
                "🎵 اسمارٹ پچ شفٹ (Smart Pitch Shift)"
            ], key="a_p1")
            
        up_file1 = st.file_uploader("📂 اپنے موبائل یا کمپیوٹر سے ویڈیو اپلوڈ کریں (انتہائی تیز):", type=["mp4", "mov", "mkv", "avi", "webm"], key="u_f1")
        link_url1 = st.text_input("🔗 یا ویڈیو کا لنک پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="l_u1")
        
        if st.button("🚀 100% اینٹی کاپی رائٹ شیلڈ لگا کر ویڈیو تیار کریں", type="primary", key="btn_run1"):
            uid = str(uuid.uuid4())[:8]
            base_prefix = f"in_vid_{uid}"
            target_out = f"out_shielded_{uid}.mp4"
            info = {'title': 'Action Scene'}
            input_file = None
            
            if up_file1 is not None:
                with st.spinner("📂 ویڈیو محفوظ ہو رہی ہے..."):
                    ext = up_file1.name.split('.')[-1] if '.' in up_file1.name else "mp4"
                    target_in = f"{base_prefix}.{ext}"
                    with open(target_in, "wb") as f:
                        up_file1.seek(0)
                        while True:
                            chunk = up_file1.read(1024 * 1024 * 4)
                            if not chunk: break
                            f.write(chunk)
                    if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                        input_file = target_in
                        info['title'] = up_file1.name
            elif link_url1.strip():
                with st.spinner("🔗 لنک سے ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    info, d_file = inspect_and_fetch_media(link_url1.strip(), base_prefix)
                    if d_file and os.path.exists(d_file) and os.path.getsize(d_file) > 1000:
                        input_file = d_file
                    else:
                        st.error("❌ لنک سے ویڈیو ڈاؤنلوڈ نہیں ہو سکی۔ براہِ کرم اوپر فائل اپلوڈر استعمال کریں۔")

            if input_file and os.path.exists(input_file):
                with st.spinner("⚡ ہر فریم پر مائیکرو کٹس (Timeline Break)، اینٹی ہیشنگ اور آڈیو ماسکنگ لگ رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    
                    # 100% CONTENT-ID BREAKING VIDEO FILTER
                    # Drops micro-frames every 3 seconds to break continuous Content-ID hashing
                    if "کینوس فریم" in shield_power:
                        vf_str = (
                            "[0:v]scale=1280:720,boxblur=24:4[bg];"
                            "[0:v]select='mod(n\\,72)<67',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.82:ih*0.82,scale=980:552,"
                            "eq=contrast=1.15:saturation=1.22:brightness=0.018,"
                            "noise=alls=7:allf=t+u,vignette=PI/3.6[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                            "drawbox=y=0:h=44:color=black@0.75:t=fill,"
                            "drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                        )
                    else:
                        vf_str = (
                            "select='mod(n\\,72)<67',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                            "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                            "eq=contrast=1.15:saturation=1.22:brightness=0.018,"
                            "noise=alls=7:allf=t+u,vignette=PI/3.6,"
                            "drawbox=y=0:h=44:color=black@0.75:t=fill,"
                            "drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                        )
                    
                    # 100% ACOUSTIC MASKING FILTER
                    if "ماسکنگ" in audio_shield:
                        af_str = "volume=0.32,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.086957,equalizer=f=1000:t=q:w=1:g=-3,bass=g=6:f=110,treble=g=-4:f=3200"
                    else:
                        af_str = "volume=0.80,asetrate=44100*1.04,aresample=44100:async=1,atempo=0.961538,bass=g=4:f=110"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-i", input_file,
                        "-map_metadata", "-1",
                        "-filter_complex" if "کینوس فریم" in shield_power else "-vf", vf_str,
                        "-af", af_str,
                        "-r", "24",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                        "-g", "48", "-keyint_min", "24",
                        "-b:v", "850k", "-maxrate", "1100k", "-bufsize", "2000k",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                    ]
                    
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file)
                        except Exception: pass
                    else:
                        st.error("❌ ویڈیو پروسیسنگ فیل ہو گئی۔ براہ کرم فائل دوبارہ اپلوڈ کریں۔")
            elif not input_file and not link_url1.strip() and up_file1 is None:
                st.error("❌ برائے مہربانی ویڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    with sub2:
        st.subheader("ویڈیو سے کلپ کاٹیں (اینٹی کلیم پروٹیکشن کے ساتھ)")
        sc_col1, sc_col2 = st.columns(2)
        with sc_col1:
            clip_start_type = st.selectbox("سین کا وقت:", ["⚔️ اہم سین (منٹ 30)", "👻 سسپنس موڑ (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
        with sc_col2:
            clip_dur = st.slider("کلپ کا دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
            
        st_min = 30 if "30" in clip_start_type else 45 if "45" in clip_start_type else 15 if "15" in clip_start_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
        up_file2 = st.file_uploader("📂 کلپ کے لیے ویڈیو منتخب کریں:", type=["mp4", "mov", "mkv", "webm"], key="u_f2")
        link_url2 = st.text_input("🔗 یا لنک ڈالیں:", placeholder="https://...", key="l_u2")

        if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="btn_run2"):
            uid = str(uuid.uuid4())[:8]
            base_prefix = f"clip_in_{uid}"
            target_out = f"clip_out_{uid}.mp4"
            info = {'title': 'Clip Highlight'}
            input_file = None
            
            if up_file2 is not None:
                ext = up_file2.name.split('.')[-1] if '.' in up_file2.name else "mp4"
                target_in = f"{base_prefix}.{ext}"
                with open(target_in, "wb") as f:
                    up_file2.seek(0)
                    while True:
                        chunk = up_file2.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    input_file = target_in
                    info['title'] = up_file2.name
            elif link_url2.strip():
                with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    info, d_file = inspect_and_fetch_media(link_url2.strip(), base_prefix)
                    if d_file and os.path.exists(d_file) and os.path.getsize(d_file) > 1000:
                        input_file = d_file

            if input_file and os.path.exists(input_file):
                with st.spinner("کلپ کاٹ کر اینٹی کاپی رائٹ شیلڈ لگائی جا رہی ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = st_min * 60
                    dur_sec = clip_dur * 60
                    vf = "select='mod(n\\,72)<67',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,hflip,crop=iw*0.82:ih*0.82,scale=1280:720,eq=contrast=1.15:saturation=1.22:brightness=0.018,noise=alls=7:allf=t+u,vignette=PI/3.6,drawbox=y=0:h=44:color=black@0.75:t=fill,drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                    af = "volume=0.35,asetrate=44100*0.92,aresample=44100:async=1,atempo=1.086957,bass=g=5:f=120"
                    
                    cmd = [
                        ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                        "-i", input_file, "-map_metadata", "-1", "-vf", vf, "-af", af,
                        "-r", "24", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                        "-b:v", "850k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file)
                        except Exception: pass
                    else:
                        st.error("❌ ویڈیو سیٹنگز چیک کریں۔")
            else:
                st.error("❌ ویڈیو اپلوڈ کریں یا درست لنک دیں۔")

    with sub3:
        st.subheader("گانے کو Slowed + Reverb لوفی میں بدلیں")
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
        with col_g2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
        with col_g3: bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3")
            
        up_file3 = st.file_uploader("📂 گانے کی آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="u_f3")
        link_url3 = st.text_input("🔗 یا گانے کا لنک پیسٹ کریں:", placeholder="https://...", key="l_u3")
        
        if st.button("🚀 گانے کو وائرل لوفی بنائیں", type="primary", key="btn_run3"):
            uid = str(uuid.uuid4())[:8]
            base_prefix = f"dyn_song_in_{uid}"
            target_out = f"dyn_song_out_{uid}.mp4"
            info = {'title': 'Lo-Fi Chill Track'}
            input_file = None
            
            if up_file3 is not None:
                ext = up_file3.name.split('.')[-1] if '.' in up_file3.name else "mp4"
                target_in = f"{base_prefix}.{ext}"
                with open(target_in, "wb") as f:
                    up_file3.seek(0)
                    while True:
                        chunk = up_file3.read(1024 * 1024 * 4)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    input_file = target_in
                    info['title'] = up_file3.name
            elif link_url3.strip():
                with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                    info, d_file = inspect_and_fetch_media(link_url3.strip(), base_prefix)
                    if d_file and os.path.exists(d_file) and os.path.getsize(d_file) > 1000:
                        input_file = d_file
                        
            if input_file and os.path.exists(input_file):
                with st.spinner("لوفی گانا ماسٹر ہو رہا ہے..."):
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [
                        ffmpeg_exe, "-y", "-i", input_file,
                        "-map_metadata", "-1",
                        "-af", af_filter, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", target_out
                    ]
                    subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                        st.session_state.detected_info = info
                        st.session_state.current_output_video = target_out
                        st.session_state.process_ready = True
                        try: os.remove(input_file)
                        except Exception: pass
                    else:
                        st.error("❌ آڈیو پروسیسنگ فیل ہو گئی۔")
            else:
                st.error("❌ آڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

    # Output Video Player & Fast Download
    active_out = st.session_state.current_output_video
    if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
        st.divider()
        st.success("🎉 آپ کی ویڈیو 100% اینٹی کاپی رائٹ شیلڈ اور کم سائز (Lightweight) کے ساتھ تیار ہے:")
        
        video_bytes = open(active_out, 'rb').read()
        st.video(video_bytes)
        
        st.download_button(
            label="📥 یہاں کلک کر کے محفوظ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
            data=video_bytes,
            file_name=f"es_protected_{os.path.basename(active_out)}",
            mime="video/mp4",
            use_container_width=True
        )

        genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
        st.info(f"🎯 **AI نے پہچانا:** یہ ویڈیو **'{genre}'** کیٹگری کی ہے۔ (اصل نام: **{st.session_state.detected_info.get('title', 'Video')}**)")
        
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1:
            st.markdown(f"### 🔥 وائرل ٹائٹلز ({genre}):")
            for t in titles:
                st.code(t, language="text")
            st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
            st.code(tags, language="text")

        with c_meta2:
            st.markdown("### 🎨 تھمب نیل کا پرامپٹ (Thumbnail Prompt):")
            st.info("💡 اسے Midjourney یا Bing Image Creator میں ڈال کر نیا تھمب نیل بنائیں۔")
            st.code(prompt, language="text")

# -----------------
# TAB 2: PRO MOVIE MASTER STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 AI اینیمیٹڈ مووی جنریٹر")
    m_script = st.text_area("مووی کی کہانی یا اسکرپٹ یہاں لکھیں:", height=140, placeholder="ایک کسان ٹریکٹر چلا رہا ہے اور کھیت میں گندم کی فصل تیار ہے...")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with col_v2: mr = st.selectbox("فارمیٹ:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col_v3: ms = st.selectbox("اسٹائل:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
    
    if st.button("Generate Master Movie 🚀"):
        st.info("مووی کی تیاری شروع ہو چکی ہے...")

# -----------------
# TAB 3: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 الٹرا ایچ ڈی AI امیج جنریٹر")
    img_p = st.text_area("امیج کے لیے تفصیل لکھیں:", height=100)
    col_i1, col_i2 = st.columns(2)
    with col_i1: i_style = st.selectbox("اسٹائل منتخب کریں:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
    with col_i2: i_size = st.selectbox("سائز:", ["YouTube HD", "Square (1:1)", "TikTok"])
    
    if st.button("Generate Visual 🎨"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        img_bytes = fetch_img_failover(img_p, w, h, random.randint(1, 999999))
        if img_bytes:
            st.image(img_bytes, caption="AI Generated Image")

# -----------------
# TAB 4: CHAT & ACCOUNT
# -----------------
with tab_chat:
    st.write("### 💬 AI Assistant & Auth")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask anything..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true", timeout=15).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>ES & Sglowina AI Studio Suite | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
