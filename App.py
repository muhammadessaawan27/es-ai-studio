import sys
# 1. Globally patch PIL.Image for Pillow 10+ compatibility with MoviePy
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS if hasattr(PIL.Image, 'Resampling') else 1
    sys.modules['PIL.Image'] = PIL.Image
except:
    pass

import streamlit as st
import asyncio
import requests
import urllib.parse
import os
import time
import re
import uuid
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import sqlite3
import hashlib
import json

# Safe Asyncio Patch for Edge-TTS
try:
    import nest_asyncio
    nest_asyncio.apply()
except:
    pass

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"
TRANSITION_SFX_FILE = "transition_whoosh.mp3"

def download_transition_sfx():
    if os.path.exists(TRANSITION_SFX_FILE) and os.path.getsize(TRANSITION_SFX_FILE) > 5000:
        return
    try:
        res = requests.get("https://www.soundjay.com/mechanical/sounds/whoosh-1.mp3", timeout=12)
        if res.status_code == 200:
            with open(TRANSITION_SFX_FILE, "wb") as f: f.write(res.content)
    except: pass

download_transition_sfx()

if "gen_mode" not in st.session_state:
    st.session_state.gen_mode = "Cinematic Photo Zoom & Pan (100% Free & Unlimited)"
if "pollinations_key" not in st.session_state:
    st.session_state.pollinations_key = ""

UR_EN_DICT = {
    "درخت": "trees", "جنگل": "forest", "baag": "garden", "باغات": "gardens",
    "پرندے": "birds", "پرندہ": "bird", "بارش": "rain", "طوفان": "storm",
    "بادل": "clouds", "ہوا": "wind", "آگ": "fire", "پانی": "water",
    "لڑکا": "boy", "لڑکی": "girl", "عورت": "woman", "مرد": "man",
    "بادشاہ": "king", "ملکہ": "queen", "محل": "palace", "تخت": "throne",
    "شیر": "lion", "تلوار": "sword", "جنگ": "war", "قبر": "grave",
    "خوفناک": "scary", "جن": "ghost", "اندھیرا": "dark", "موت": "death",
    "خوبصورت": "beautiful", "جادو": "magic", "جادوئی": "magical",
    "مسجد": "mosque", "نماز": "prayer", "دعا": "pray", "نور": "holy light",
    "چوزہ": "cute fluffy yellow chick", "چوزے": "cute fluffy yellow chicks",
    "بلی": "cute cat", "بندر": "funny monkey", "طوطا": "colorful parrot",
    "خرگوش": "fluffy cartoon rabbit", "بالٹی": "bucket", "سر": "head", "چوہا": "cute mouse",
    "سپر ہیرو": "superhero", "ہنستے": "laughing", "لوٹ پوٹ": "hilariously rolling and laughing"
}

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
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

st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V1.0", layout="wide", page_icon="🎬")

if "enable_watermark" not in st.session_state: st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)
custom_watermark_file = st.sidebar.file_uploader("Upload Custom Watermark Logo (Premium Only):", type=["png", "jpg", "jpeg"])

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=1)
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
                return data["data"]["url"].replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
    except: pass
    return None

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

def backup_db_to_json():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        users = [dict(row) for row in cursor.execute("SELECT * FROM users").fetchall()]
        payments = [dict(row) for row in cursor.execute("SELECT * FROM local_payments").fetchall()]
        config = [dict(row) for row in cursor.execute("SELECT * FROM system_config").fetchall()]
        conn.close()
        backup_data = {"users": users, "payments": payments, "config": config}
        with open(DB_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
    except: pass

def restore_db_from_json():
    if not os.path.exists(DB_BACKUP_FILE): return
    try:
        with open(DB_BACKUP_FILE, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        conn = get_db_connection()
        cursor = conn.cursor()
        for user in backup_data.get("users", []):
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, username, email, password_hash, plan, credits, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.get("id"), user["username"], user["email"], user["password_hash"], user["plan"], user["credits"], user["role"], user["status"], user["created_at"]))
        for pay in backup_data.get("payments", []):
            cursor.execute("""
                INSERT OR IGNORE INTO local_payments (id, username, method, trx_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pay["id"], pay["username"], pay["method"], pay["trx_id"], pay["amount"], pay["status"], pay["created_at"]))
        for cfg in backup_data.get("config", []):
            cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (cfg["key"], cfg["value"]))
        conn.commit()
        conn.close()
    except: pass

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    is_sqlite = "sqlite" in str(type(conn))
    serial_primary = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    placeholder = "?" if is_sqlite else "%s"
    
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
            id TEXT PRIMARY KEY, user_id INTEGER, project_name TEXT,
            type TEXT, file_path TEXT, prompt TEXT, created_at TEXT, is_favorite INTEGER DEFAULT 0
        )
    """)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS credits_history (id {serial_primary}, user_id INTEGER, action TEXT, credits_used INTEGER, balance_after INTEGER, date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS local_payments (id TEXT PRIMARY KEY, username TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, credits INTEGER, uses_left INTEGER)")
    
    cursor.execute(f"SELECT COUNT(*) FROM coupons WHERE code = {placeholder}", ('ESSASABA',))
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"INSERT INTO coupons (code, credits, uses_left) VALUES ({placeholder}, 100, 1000)", ('ESSASABA',))
    
    # Honors Founders: Muhammad Essa Awan & Saba Wahid
    h_admin = hash_password("786")
    for adm in ["essasaba", "essa_awan"]:
        cursor.execute(f"SELECT COUNT(*) FROM users WHERE LOWER(username) = {placeholder}", (adm,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 5000, {placeholder}, {placeholder})",
                           (adm, f"{adm}@sglowina.ai", h_admin, "Enterprise", "Admin", "2026-07-21"))
    
    h_saba = hash_password("1234")
    cursor.execute(f"SELECT COUNT(*) FROM users WHERE LOWER(username) = {placeholder}", ("saba_wahid",))
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 5000, {placeholder}, {placeholder})",
                       ("saba_wahid", "saba@sglowina.ai", h_saba, "Enterprise", "Admin", "2026-07-21"))
                       
    conn.commit()
    conn.close()

init_db_v21()
restore_db_from_json()

def register_saas_user(username, email, password):
    username = username.strip().lower()
    email = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        h = hash_password(password)
        cursor.execute(f"INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES ({placeholder}, {placeholder}, {placeholder}, 'Free', 50, 'User', {placeholder})",
                       (username, email, h, time.strftime("%Y-%m-%d")))
        conn.commit()
        backup_db_to_json()
        return True, "User registered successfully!"
    except: return False, "Username or Email already exists."
    finally: conn.close()

def authenticate_user(username, password):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"SELECT password_hash FROM users WHERE LOWER(username) = LOWER({placeholder})", (username,))
        row = cursor.fetchone()
        if row:
            hashed = row[0] if not isinstance(row, dict) and not hasattr(row, 'keys') else row['password_hash']
            return verify_password(password.strip(), hashed)
        return False
    except: return False
    finally: conn.close()

def get_user_data(username):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"SELECT * FROM users WHERE LOWER(username) = LOWER({placeholder})", (username,))
        row = cursor.fetchone()
        if row:
            if not isinstance(row, dict) and hasattr(row, '_fields'):
                return dict(row)
            elif isinstance(row, dict):
                return row
            else:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
        return None
    except: return None
    finally: conn.close()

def deduct_user_credits(username, amount):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"UPDATE users SET credits = MAX(0, credits - {placeholder}) WHERE LOWER(username) = LOWER({placeholder})", (amount, username))
        conn.commit()
        backup_db_to_json()
    except: pass
    finally: conn.close()

def log_credit_usage(user_id, action, used, balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if "psycopg2" in str(type(conn)) else "?"
    try:
        cursor.execute(f"INSERT INTO credits_history (user_id, action, credits_used, balance_after, date) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
                       (user_id, action, used, balance, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except: pass
    finally: conn.close()

# ================= RESTORED MISSING FUNCTIONS =================
def burn_subtitles_to_image(img_path, scene_text):
    """Safely renders subtitles at bottom of image to prevent NameError"""
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            w, h = im.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            bar_height = int(h * 0.12)
            draw.rectangle([(0, h - bar_height), (w, h)], fill=(0, 0, 0, 160))
            clean_sub = scene_text[:85]
            try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.038))
            except: font = ImageFont.load_default()
            draw.text((w // 2, h - (bar_height // 2)), clean_sub, font=font, fill=(255, 255, 255, 240), anchor="mm")
            Image.alpha_composite(im, overlay).convert("RGB").save(img_path, "PNG")
    except: pass

def apply_canva_typography(img_path, overlay_text):
    """Safely applies Canva style bold text banner to prevent NameError"""
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            w, h = im.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.06))
            except: font = ImageFont.load_default()
            draw.rectangle([(int(w * 0.08), int(h * 0.08)), (int(w * 0.92), int(h * 0.22))], fill=(37, 99, 235, 200))
            draw.text((w // 2, int(h * 0.15)), overlay_text, font=font, fill=(255, 255, 255, 255), anchor="mm")
            Image.alpha_composite(im, overlay).convert("RGB").save(img_path, "PNG")
    except: pass

def search_web_ddg(query):
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text, re.DOTALL)
            if snippets:
                clean_snippets = []
                for s in snippets[:3]:
                    clean_s = re.sub(r'<[^>]*>', '', s).strip()
                    clean_snippets.append(clean_s)
                return "\n".join(clean_snippets)
    except: pass
    return ""

def analyze_scene_for_director(scene_text):
    text = scene_text.lower()
    motion, lighting, color_grading, composition = "Zoom Out (v40 Default)", "Volumetric Light", "Hollywood Cinematic", "Cinematic Wide Shot"
    if any(k in text for k in ["run", "chase", "flee", "fast", "speed", "action", "bhaag", "بھاگ", "دوڑ", "تیز"]):
        motion = "Tracking Shot"
    elif any(k in text for k in ["scary", "ghost", "dark", "grave", "death", "haunted", "scared", "قبر", "خوف", "جن", "بھوت", "تاریک", "ڈرا", "موت"]):
        motion = "Dolly In"
        lighting, color_grading = "Dark Cinematic, Shadows", "Horror Green"
    elif any(k in text for k in ["fight", "battle", "sword", "war", "تلوار", "جنگ", "لڑائی"]):
        motion = "Handheld Camera"
    elif any(k in text for k in ["walk", "stroll", "چلنا", "گھوم", "سیر"]):
        motion = "Follow Shot"
    elif any(k in text for k in ["think", "silent", "quiet", "meditate", "سوچ", "خاموش"]):
        motion = "Ken Burns Effect"
    return {"motion": motion, "lighting": lighting, "color_grading": color_grading, "composition": composition}

def generate_text_pollinations(prompt, system_prompt=""):
    models = ["openai-fast", "openai", "mistral"]
    for model in models:
        try:
            payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], "model": model, "jsonMode": False}
            res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    text_out = data["choices"][0]["message"]["content"]
                    if len(text_out.strip()) > 5: return text_out.strip()
        except: pass
    return ""

def translate_ur_to_en_enhanced(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            result = res.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if len(translated_text.strip()) > 3: return translated_text.strip()
    except: pass
    return text

def generate_local_fallback_script(topic, genre, style):
    topic_ur = topic.strip()
    scenes_ur = [
        f"ایک عظیم سرزمین پر {topic_ur} کی حیرت انگیز داستان شروع ہوتی ہے۔",
        f"ہر طرف {topic_ur} کے چرچے تھے اور ایک نیا موڑ سامنے آیا۔",
        f"پھر اس سفر میں غیر متوقع چیلنجز اور رکاوٹیں کھڑی ہو گئیں۔",
        f"بہادری اور عزم کے ساتھ تمام مشکلات پر قابو پا لیا گیا۔",
        f"اور یوں {topic_ur} کی یہ شاندار کہانی ایک پُر اثر پیغام کے ساتھ انجام پذیر ہوئی۔"
    ]
    return " ۔ ".join(scenes_ur)

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined = (scene_text_en + " " + scene_text_ur).lower()
    if any(k in combined for k in ["prophet", "sahaba", "saint", "angel", "god", "allah", "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ"]):
        return True, "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from heavens, STRICTLY NO human faces, pure sacred light."
    return False, scene_text_en

def is_human_character_present(scene):
    scene_l = scene.lower()
    return any(k in scene_l for k in ["man", "male", "boy", "مرد", "لڑکا", "احمد", "علی", "بادشاہ", "woman", "female", "girl", "عورت", "لڑکی", "زارا", "سارہ"])

def analyze_consistent_subject(story_text, style):
    story_l = story_text.lower()
    style_theme = "cartoon" if style == "3D Cartoon" else "photorealistic"
    if any(k in story_l for k in ["چوزہ", "chick", "چوزے"]):
        return f"a cute fluffy yellow {style_theme} chick wearing an upside-down metallic bucket on its head as superhero helmet"
    if any(k in story_l for k in ["چوہا", "mouse"]):
        return f"a cute tiny {style_theme} brown mouse wearing superhero attire"
    if any(k in story_l for k in ["بندر", "monkey"]):
        return f"a funny goofy {style_theme} brown monkey"
    return ""

def clean_animal_prompt_of_humans(prompt, urdu_text, style):
    if any(k in urdu_text for k in ["چوزہ", "بلی", "بندر", "طوطا", "خرگوش", "چوہا", "شیر"]) and not any(k in urdu_text for k in ["لڑکا", "لڑکی", "مرد", "عورت"]):
        for w in ["boy", "girl", "man", "woman", "person", "human", "child"]:
            prompt = re.sub(r'\b' + w + r'\b', '', prompt, flags=re.IGNORECASE)
    return prompt

def generate_enhanced_cinematic_prompt(urdu_scene, style, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url, attire_desc="", consistent_char_desc=""):
    trans = translate_ur_to_en_enhanced(urdu_scene)
    style_tag = f"cinematic film style, {style}, highly detailed, sharp focus, 8k resolution"
    char_tag = f"Main Character: {consistent_char_desc}, " if consistent_char_desc else ""
    return f"{char_tag}{trans}, {style_tag}"

def apply_color_lut_harmony(img_path, style_preset):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.15)
            im = ImageEnhance.Contrast(im).enhance(1.05)
            im.save(img_path, "PNG")
    except: pass

def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    if any(k in text for k in ["rain", "storm", "بارش", "طوفان"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "تلوار", "جنگ"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3"
    if sfx_url:
        fn = f"sfx_{u_id}_{idx}.mp3"
        try:
            r = session.get(sfx_url, timeout=10)
            if r.status_code == 200:
                with open(fn, "wb") as f: f.write(r.content)
                return fn
        except: pass
    return None

def apply_blurred_background_padding(img_path, target_w, target_h):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            bg = im.resize((target_w, target_h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=20))
            im_ratio = im.width / im.height
            target_ratio = target_w / target_h
            if im_ratio > target_ratio:
                nw, nh = target_w, int(target_w / im_ratio)
            else:
                nw, nh = int(target_h * im_ratio), target_h
            fg = im.resize((nw, nh), Image.Resampling.LANCZOS)
            bg.paste(fg, ((target_w - nw) // 2, (target_h - nh) // 2))
            bg.save(img_path, "PNG")
    except: pass

def ensure_image_exists(img_path, w, h, scene_text="Sglowina AI"):
    if not os.path.exists(img_path) or os.path.getsize(img_path) < 1000:
        im = Image.new("RGB", (w, h), color=(15, 23, 42))
        im.save(img_path, "PNG")

def apply_custom_watermark(img_path, watermark_bytes):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            with Image.open(io.BytesIO(watermark_bytes)) as wm:
                wm = wm.convert("RGBA")
                wm_w = int(im.width * 0.15)
                wm_h = int(wm_w * (wm.height / wm.width))
                wm = wm.resize((wm_w, wm_h))
                im.paste(wm, (im.width - wm_w - 20, im.height - wm_h - 20), wm)
            im.convert("RGB").save(img_path, "PNG")
    except: pass

def parallel_download_flux_images(urls, paths, prompts, w, h, style="Realistic HD"):
    for idx in range(len(urls)):
        try:
            r = session.get(urls[idx], timeout=25)
            if r.status_code == 200 and len(r.content) > 3000:
                with open(paths[idx], "wb") as f: f.write(r.content)
            else:
                Image.new("RGB", (w, h), color=(15, 23, 42)).save(paths[idx], "PNG")
        except:
            Image.new("RGB", (w, h), color=(15, 23, 42)).save(paths[idx], "PNG")

def get_cached_bg_music(is_horror, is_epic):
    fn = "bg_horror.mp3" if is_horror else ("bg_epic.mp3" if is_epic else "bg_standard.mp3")
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3" if is_horror else "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
    cf = os.path.join(AUDIO_CACHE_DIR, fn)
    if os.path.exists(cf) and os.path.getsize(cf) > 100000: return cf
    try:
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            with open(cf, "wb") as f: f.write(res.content)
            return cf
    except: pass
    return None

def download_video_safely(url, dest_path, progress_status):
    try:
        with session.get(url, stream=True, timeout=90) as r:
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                return True
    except: pass
    return False

# ================= DYNAMIC CAMERA MOTION ENGINE =================
def apply_camera_motion_v40(img_path, motion, duration, w, h):
    if not MOVIEPY_AVAILABLE: return None
    scale_factor = 1.15
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_img = img_path.replace(".png", "_scaled.png")
    try:
        with Image.open(img_path) as im:
            im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_img, "PNG")
    except: temp_img = img_path

    try:
        clip = ImageClip(temp_img).set_duration(duration).set_fps(24)
        if motion == "Pan Left":
            animated = clip.set_position(lambda t: (int((w - cw) * (t / duration)), 'center'))
        elif motion == "Pan Right":
            animated = clip.set_position(lambda t: (int((w - cw) * (1 - t / duration)), 'center'))
        elif motion == "Handheld Camera":
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (3 * np.sin(2 * np.pi * t * 1.5))), int((h - ch)/2 + (3 * np.cos(2 * np.pi * t * 1.2)))))
        else: # Default Dynamic Zoom
            animated = clip.set_position('center')
        return CompositeVideoClip([animated], size=(w, h)).set_duration(duration)
    except:
        return ImageClip(img_path).set_duration(duration)

def apply_clip_transition(clip, transition, duration):
    try:
        fade_dur = min(0.3, duration / 3.0)
        return clip.fadein(fade_dur).fadeout(fade_dur)
    except: return clip

def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        res = session.get(url, timeout=25)
        if res.status_code == 200: return res.content
    except: pass
    return None

def save_audio_safe(text, voice, rate, pitch, filename):
    async def amain():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(amain())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except: return False

# Master Movie Pipeline
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free)", pollinations_key="", video_model="wan-fast", custom_wm_bytes=None, enable_sub=False):
    if not MOVIEPY_AVAILABLE: return "MoviePy missing"
    u_id = str(uuid.uuid4())[:8]
    
    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()
        
        user_db = get_user_data(st.session_state.logged_in_user)
        if not user_db: return "Auth Error"
        
        sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        total_scenes = len(sentences)
        
        clips = [None] * total_scenes
        generated_prompts = [None] * total_scenes
        img_paths = [None] * total_scenes
        flux_prompt_urls = [None] * total_scenes
        temporary_audio_tracks = [None] * total_scenes
        temp_files_to_clean = []
        
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)
        
        try:
            for idx, scene in enumerate(sentences):
                status.info(f"🎙️ آواز تیار ہو رہی ہے: منظر {idx + 1} از {total_scenes}...")
                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(scene, voice_gen, rate, pitch, sub_audio):
                    continue
                temporary_audio_tracks[idx] = sub_audio
                temp_files_to_clean.append(sub_audio)

            progress_bar.progress(0.2)
            consistent_char_desc = analyze_consistent_subject(story, style)

            for i, scene in enumerate(sentences):
                status.info(f"🎨 ویژول تیار ہو رہے ہیں: منظر {i + 1} از {total_scenes}...")
                refined_p = generate_enhanced_cinematic_prompt(scene, style, "Automatic", enable_islamic_filter, None, None, "", consistent_char_desc)
                generated_prompts[i] = refined_p
                
                # FIXED CHARACTER SEED LOCK (تسلسل قائم رکھنے کے لیے)
                flux_prompt_urls[i] = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
                img_paths[i] = f"i_{u_id}_{i}.png"
                temp_files_to_clean.append(img_paths[i])

            progress_bar.progress(0.4)
            parallel_download_flux_images(flux_prompt_urls, img_paths, generated_prompts, w, h, style)

            for i in range(total_scenes):
                status.info(f"🎞️ کیمرہ موشن اپلائی ہو رہا ہے: منظر {i + 1} از {total_scenes}...")
                img_p = img_paths[i]
                sub_a = temporary_audio_tracks[i]
                if not sub_a or not os.path.exists(sub_a): continue
                
                ensure_image_exists(img_p, w, h, sentences[i])
                apply_color_lut_harmony(img_p, style)
                if enable_sub: burn_subtitles_to_image(img_p, sentences[i])
                if custom_wm_bytes: apply_custom_watermark(img_p, custom_wm_bytes)
                
                scene_voice = AudioFileClip(sub_a)
                dur = scene_voice.duration
                
                c_motion = "Pan Left" if i % 2 == 0 else "Pan Right"
                clip = apply_camera_motion_v40(img_p, c_motion, dur, w, h)
                clip = clip.set_audio(scene_voice.volumex(1.2))
                clips[i] = apply_clip_transition(clip, transition_style, dur)

            progress_bar.progress(0.8)
            status.info("🎬 ویڈیو فائنل رینڈر ہو رہی ہے...")
            valid_clips = [c for c in clips if c is not None]
            if not valid_clips: raise Exception("No valid scenes generated.")

            final_video = concatenate_videoclips(valid_clips, method="compose")
            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
            
            # Close clips and free RAM
            final_video.close()
            for c in valid_clips: c.close()
            for f in temp_files_to_clean:
                try: os.remove(f)
                except: pass

            progress_bar.progress(1.0)
            status.success("🚀 ویڈیو کامیابی سے تیار ہو گئی!")
            deduct_user_credits(st.session_state.logged_in_user, 15)
            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try: os.remove(f)
                except: pass
            return f"Error: {e}"

# ================= UI SYSTEM STYLE =================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 1.2rem !important; font-weight: 300 !important; font-family: 'Inter', sans-serif; color: #1e3a8a !important; letter-spacing: 2px; margin: 0 !important; }
    .dashboard-header { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 15px; margin-bottom: 20px; }
    .circular-s { width: 50px !important; height: 50px !important; background: #ffffff !important; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #2563eb !important; animation: rotateSpins 10s infinite linear; }
    .metallic-s { font-family: 'Orbitron', sans-serif; font-size: 28px !important; font-weight: 900; color: #2563eb !important; }
    @keyframes rotateSpins { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .stButton>button, .stFormSubmitButton>button { background: linear-gradient(90deg, #2563eb, #1d4ed8) !important; color: white !important; border-radius: 12px !important; height: 55px !important; width: 100% !important; font-size: 20px !important; font-weight: bold !important; border: 1px solid #3b82f6 !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2) !important; }
    textarea, input, select { background-color: #ffffff !important; color: #0f172a !important; border: 2px solid #cbd5e1 !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="dashboard-header">
        <div class="circular-s"><span class="metallic-s">S</span></div>
        <h1 class="glow-title">Sglowina AI | ایس گلووینا</h1>
    </div>
""", unsafe_allow_html=True)

tab_auth, tab_chat, tab_movie, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In", "💬 Electric AI Chat", "🎬 Pro Movie Studio", "🎨 Pro Image Studio", "👤 Enterprise Center"
])

# 1. Sign-In Form
with tab_auth:
    st.write("### 🔑 Sglowina Secure Authentication")
    auth_mode = st.radio("Choose Action", ["Sign In", "Create New Account"])
    with st.form("auth_form"):
        u_name = st.text_input("Username")
        u_email = st.text_input("Email") if auth_mode != "Sign In" else ""
        p_word = st.text_input("Password", type="password")
        if st.form_submit_button("Submit 🚀"):
            if auth_mode == "Sign In":
                if authenticate_user(u_name, p_word):
                    st.session_state.logged_in_user = u_name.strip().lower()
                    u_data = get_user_data(u_name)
                    if u_data and u_data['role'] == 'Admin':
                        st.success("Welcome back, Founders Muhammad Essa Awan and Saba Wahid! 🟢")
                    else:
                        st.success(f"Welcome to Sglowina AI, {u_name}! 🟢")
                    time.sleep(1)
                    st.rerun()
                else: st.error("Invalid credentials.")
            else:
                s, msg = register_saas_user(u_name, u_email, p_word)
                if s: st.success(msg)
                else: st.error(msg)

# 2. Electric AI Chat
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        web_snippets = search_web_ddg(p) if any(k in p.lower() for k in ["search", "live", "news", "گوگل"]) else ""
        sys_p = f"You are Sglowina AI, developed by founders Muhammad Essa Awan & Saba Wahid.\nContext: {web_snippets}"
        res = generate_text_pollinations(p, sys_p)
        with st.chat_message("assistant"):
            st.write(res)
            st.code(res, language="")
            st.session_state.msgs.append({"role": "assistant", "content": res})

# 3. Pro Movie Studio
with tab_movie:
    st.write("### 🎥 Movie Studio")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="کہانی یہاں درج کریں...")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)"])
    with col2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col3: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Hollywood", "3D Cartoon", "Anime Art", "Dark Gothic / Mystery"])
    with col4: camera_motion = st.selectbox("Camera Motion:", ["AI Hollywood Director (Auto)", "Pan Left", "Pan Right", "Handheld Camera"])
    with col5: sd = st.number_input("Character Seed:", value=786)

    voice_map = {"Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural", "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural"}
    active_v = voice_map.get(mv, "ur-PK-AsadNeural")

    if st.button("Generate Master Movie 🚀"):
        if not m_script.strip(): st.error("Please enter a script first.")
        else:
            with st.spinner("🎬 Generating Cinematic Masterpiece..."):
                wm_bytes = custom_watermark_file.getvalue() if custom_watermark_file else None
                v_res = create_cinematic_v40(m_script, active_v, "+0%", "+0Hz", mr, ms, int(sd), camera_motion=camera_motion, custom_wm_bytes=wm_bytes)
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 4. Pro Image Studio
with tab_image:
    st.write("### 🎨 Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="e.g. Studio Title")
    ic1, ic2 = st.columns(2)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "3D Cartoon", "Cinematic Film", "Anime Art"])
    with ic2: i_size = st.selectbox("Resolution:", ["YouTube HD", "Square (1:1)", "TikTok"])
    
    if st.button("Generate Visual 🚀"):
        dim = {"YouTube HD": (1280, 720), "Square (1:1)": (1024, 1024), "TikTok": (720, 1280)}
        w, h = dim.get(i_size, (1280, 720))
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ', visual style: ' + i_style)}?width={w}&height={h}&nologo=true&model=flux"
        r = session.get(img_url)
        if r.status_code == 200:
            temp_p = "temp_canva.jpg"
            with open(temp_p, "wb") as f: f.write(r.content)
            if canva_overlay_text.strip(): apply_canva_typography(temp_p, canva_overlay_text.strip())
            st.image(temp_p)
            try: os.remove(temp_p)
            except: pass

# 5. Enterprise Center
with tab_enterprise:
    st.write("### 👤 Enterprise Center")
    ent_tab_user, ent_tab_billing, ent_tab_admin = st.tabs(["👤 Profile", "💳 Billing Packages", "🔒 Admin Control Panel"])
    u_db = get_user_data(st.session_state.logged_in_user)
    
    with ent_tab_user:
        if u_db:
            st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Balance: **{u_db['credits']}** 🪙")
        else: st.warning("Please sign in first.")
        
    with ent_tab_billing:
        st.write("### 📱 Pakistani Local Payment (EasyPaisa/JazzCash)")
        st.info("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")
        if u_db:
            with st.form("pay_form"):
                p_m = st.selectbox("Method:", ["EasyPaisa", "JazzCash"])
                p_tx = st.text_input("Transaction ID (TrxID):")
                p_a = st.number_input("Amount Sent:", value=1000.0)
                if st.form_submit_button("Submit Proof 🚀"):
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, 'Pending', ?)",
                                     (str(uuid.uuid4())[:8], u_db['username'], p_m, p_tx.strip(), p_a, time.strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success("Payment submitted successfully!")
                    except: st.error("TrxID already exists.")
                    finally: conn.close()
                    
    with ent_tab_admin:
        if u_db and u_db['role'] == 'Admin':
            st.success("Admin Authorized.")
            conn = get_db_connection()
            pending_reqs = conn.execute("SELECT * FROM local_payments WHERE status = 'Pending'").fetchall()
            for r in pending_reqs:
                st.write(f"👤 User: `{r['username']}` | Trx: `{r['trx_id']}` | Amount: {r['amount']} PKR")
                if st.button(f"Approve {r['trx_id']}", key=f"app_{r['id']}"):
                    conn.execute("UPDATE local_payments SET status = 'Approved' WHERE id = ?", (r['id'],))
                    conn.execute("UPDATE users SET credits = credits + 450, plan = 'Premium' WHERE username = ?", (r['username'],))
                    conn.commit()
                    st.success("Approved!")
                    st.rerun()
            conn.close()
        else: st.error("Admin access denied.")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 20px; color: #475569;'>Sglowina AI Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
