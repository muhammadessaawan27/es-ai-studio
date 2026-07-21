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
import threading
import gc
import sqlite3
import hashlib

# Safe PBKDF2 Password Hashing Fallback to prevent bcrypt import issues on some servers
try:
    import bcrypt
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    def verify_password(password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
except ImportError:
    def hash_password(password):
        salt = b"sglowina_saas_salt_1234"
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()
    def verify_password(password, hashed):
        salt = b"sglowina_saas_salt_1234"
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

# ==========================================
# 1. DATABASE CONFIGURATION (SQLITE SAAS LAYER)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("sglowina_saas_v15.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_v15():
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            package TEXT,
            amount REAL,
            status TEXT,
            date TEXT
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
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'essa_awan'")
    if cursor.fetchone()[0] == 0:
        h1 = hash_password("786")
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("essa_awan", "essa@sglowina.ai", h1, "Enterprise", 5000, "Admin", "2026-07-21"))
                       
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'saba_wahid'")
    if cursor.fetchone()[0] == 0:
        h2 = hash_password("1234")
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("saba_wahid", "saba@sglowina.ai", h2, "Enterprise", 5000, "Admin", "2026-07-21"))
                       
    conn.commit()
    conn.close()

init_db_v15()

# ==========================================
# 2. SAAS USER CONTROLS & SECURITY HELPERS
# ==========================================
def register_saas_user(username, email, password):
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

def get_user_data(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_user_credits_db(username, credits):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = ? WHERE username = ?", (credits, username))
    conn.commit()
    conn.close()

def update_user_status_db(username, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
    conn.commit()
    conn.close()

def update_user_plan_db(username, plan):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET plan = ? WHERE username = ?", (plan, username))
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
# 3. INDUSTRIAL STABILITY & LOAD BALANCING
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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
        import moviepy.video.fx.all as vfx
        fadein = vfx.fadein
    except Exception as inner_e:
        print(f"MoviePy import warning: {inner_e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 4. EXECUTIVE UI & PREMIUM STYLING
# ==========================================
st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V1.5", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    .executive-header {
        text-align: center; 
        padding: 10px; 
        border-bottom: 1px solid #e2e8f0; 
        margin-bottom: 15px; 
        color: #000000 !important;
    }
    
    .main-names { 
        font-size: 1.8rem; 
        font-weight: 900; 
        background: linear-gradient(45deg, #ff007a, #2563eb, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-family: 'Inter', sans-serif;
        animation: pulseGlow-text 1.5s infinite alternate;
        filter: drop-shadow(0 0 8px rgba(37, 99, 235, 0.4));
    }
    
    @keyframes pulseGlow-text {
        0% { filter: drop-shadow(0 0 5px rgba(37, 99, 235, 0.3)); }
        100% { filter: drop-shadow(0 0 15px rgba(255, 0, 122, 0.6)); }
    }
    
    .title-tag { 
        font-size: 0.9rem; 
        font-weight: bold; 
        color: #64748b !important; 
        letter-spacing: 4px; 
        text-transform: uppercase; 
    }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 20px 0; }
    
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

st.markdown("""<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
    <div class="title-tag">Founders & CEOs | SGLOWINA AI OFFICIAL STUDIO</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 5. USER IDENTITY & ISLAMIC POLICY ENGINE
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead visionary.
Muhammad Essa Awan is the spouse of Saba Wahid. (Official SaaS Version 1.5 Release).
"""

def apply_islamic_visual_logic(text):
    holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah", "Buzurg"]
    islamic_keywords = ["مسلم", "اسلام", "تاریخ", "Muslim", "Islamic", "قبر", "عذاب", "آخرت", "نماز", "دعا", "مسجد", "موت", "Grave", "Punishment of Grave", "Deen"]
    village_keywords = ["دیہات", "دیہاتی", "پنڈ", "گاؤں", "Village", "Rural", "Fields", "Desi"]
    
    is_holy = any(k in text for k in holy_keywords)
    if is_holy:
        return ", STRICTLY NO FACE, person represented with bright white Noorani light, back view only, extremely respectful, historical context"
    
    is_islamic = any(k in text for k in islamic_keywords)
    if is_islamic:
        return ", traditional modest Muslim clothing, long robes, white turbans, historical authentic Islamic appearance, strictly no modern Western clothing, respectful facial hair, dignified posture"
        
    is_village = any(k in text for k in village_keywords)
    if is_village:
        return ", authentic rustic traditional village environment, mud houses, farming fields, South Asian rural setting, traditional simple clothing, organic background"
        
    return ""

def translate_ur_to_en(text):
    if not text or not text.strip():
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'ur',
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        res = session.get(url, params=params, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            translated = "".join([part[0] for part in json_data[0] if part and part[0]])
            if translated.strip():
                return translated.strip()
    except Exception:
        pass
    return text

def get_visual_prompt_v40(urdu_text, style, char_desc="", scene_desc=""):
    shariah = apply_islamic_visual_logic(urdu_text)
    english_translation = translate_ur_to_en(urdu_text)
    
    style_details = {
        "Realistic": "hyperrealistic photograph, highly detailed 8k resolution, sharp focus, realistic textures, natural volumetric lighting, cinematic photography style",
        "Cinematic": "epic cinematic lighting, highly detailed fantasy masterpiece, majestic atmosphere, octane render, volumetric god rays, detailed beautiful environment, realistic fine textures, cinematic look",
        "3D Cartoon": "professional 3D animated character, Pixar style, highly detailed, vibrant colors, clean rendering, smooth textures",
        "Historical Epic": "historical authentic scene, epic detail, ancient historical painting style, dramatic historical atmosphere, highly detailed oil painting, fine details",
        "Rustic Village Life": "rustic rural setting, highly detailed, natural lighting, authentic organic village environment, earthy tones, mud houses, natural textures",
        "Dark Gothic / Mystery": "dark gothic fantasy, mysterious foggy atmosphere, dramatic moody lighting, highly detailed, masterpiece, dark mist"
    }
    style_prompt = style_details.get(style, "epic cinematic lighting, highly detailed masterpiece")
    
    prompt_parts = [f"{style_prompt} style"]
    if char_desc.strip():
        prompt_parts.append(f"character is {char_desc.strip()}. Use the same character identity in every scene, identical face, identical clothing, consistent appearance, same age, same body shape, same hairstyle, same identity")
    if scene_desc.strip():
        prompt_parts.append(f"scene background is {scene_desc.strip()}, same environment")
    prompt_parts.append(english_translation)
    if shariah:
        prompt_parts.append(shariah)
    prompt_parts.append("highly detailed, cinematic lighting, 8k, realistic masterpiece, vivid colors, maintain exact same character identity across all scenes")
    
    return ", ".join(prompt_parts)

def fetch_img_failover(prompt, w, h, seed):
    try:
        herc_url = f"https://hercai.onrender.com/v3/text2image?prompt={urllib.parse.quote(prompt)}"
        res = session.get(herc_url, timeout=20)
        if res.status_code == 200:
            img_url = res.json().get("url")
            if img_url:
                res_img = session.get(img_url, timeout=25)
                if res_img.status_code == 200 and len(res_img.content) > 5000:
                    return res_img.content
    except Exception:
        pass

    try:
        poll_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
        res = session.get(poll_url, timeout=25)
        if res.status_code == 200 and len(res.content) > 5000:
            return res.content
    except Exception:
        pass

    return None

def generate_high_quality_placeholder(w, h, scene_num, enable_watermark=True):
    im = Image.new("RGB", (w, h), color=(30, 41, 59))
    draw = ImageDraw.Draw(im)
    draw.rectangle([(20, 20), (w - 20, h - 20)], outline=(71, 85, 105), width=4)
    for offset in range(100, w, 200):
        draw.line([(offset, 0), (offset, h)], fill=(40, 55, 75), width=1)
    for offset in range(100, h, 200):
        draw.line([(0, offset), (w, offset)], fill=(40, 55, 75), width=1)
    text_str = f"Sglowina Scene {scene_num}"
    draw.text((w // 2 - 80, h // 2 - 15), text_str, fill=(203, 213, 225))
    if enable_watermark:
        draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
    
    img_byte_arr = io.BytesIO()
    im.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def save_audio_safe(story, v_code, rate, pitch, audio_f):
    for attempt in range(2):
        try:
            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(edge_tts.Communicate(story, v_code, rate=rate, pitch=pitch).save(audio_f))
                except Exception:
                    pass
                finally:
                    loop.close()

            thread = threading.Thread(target=_run)
            thread.start()
            thread.join()
            if os.path.exists(audio_f) and os.path.getsize(audio_f) > 1000:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def make_even(val):
    return int((val // 2) * 2)

def apply_camera_motion_v40(clip, motion, duration, w, h):
    try:
        x_max = int(w * 0.15)
        y_max = int(h * 0.15)
        
        if motion == "Zoom Out (v40 Default)" or motion == "Slow Zoom Out" or motion == "Pull Out" or motion == "Dolly Out":
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t / duration)).set_position('center')
        elif motion == "Slow Zoom In" or motion == "Push In" or motion == "Dolly In":
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t / duration)).set_position('center')
        elif motion == "Pan Left" or motion == "Tracking Shot":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: (-int(x_max * (t / duration)), 'center'))
        elif motion == "Pan Right" or motion == "Cinematic Reveal" or motion == "Orbit Reveal":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: (-int(x_max * (1.0 - (t / duration))), 'center'))
        elif motion == "Pan Up" or motion == "Crane Shot" or motion == "Aerial Shot":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: ('center', -int(y_max * (t / duration))))
        elif motion == "Pan Down" or motion == "Drone Shot":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: ('center', -int(y_max * (1.0 - (t / duration)))))
        else:
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t / duration)).set_position('center')
    except Exception:
        clip = clip.set_position('center')
    return clip

# AI Prompt Assistant Module logic (Point 9)
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
    except Exception as e:
        return f"Prompt Assistant Connection Timeout: {e}"
    return "Failed to analyze story."

# ==========================================
# 6. FIXED V40 RENDER SYSTEM CORE (UNTOUCHED)
# ==========================================
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="Zoom Out (v40 Default)", enable_watermark=True, enable_bg_music=True):
    u_id = str(uuid.uuid4())[:8]
    progress_bar = st.progress(0.0)
    status = st.empty()
    
    audio_file = f"a_{u_id}.mp3"
    bg_music_f = f"bg_{u_id}.mp3"
    generated_images = []
    has_bg_music = False
    
    # Dynamic Credit Balance check (Point 3)
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
    
    try:
        progress_bar.progress(0.05)
        status.info("🎙️ Generating Voiceover Track (آڈیو جنریٹ ہو رہی ہے)...")
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        
        save_audio_success = save_audio_safe(story, v_code, rate, pitch, audio_file)
        if not save_audio_success:
            raise Exception("Voice generation failed.")
            
        voice_audio = AudioFileClip(audio_file)
        progress_bar.progress(0.15)
        
        if enable_bg_music:
            status.info("🎵 Downloading Atmospheric Classical Background Track...")
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
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        generated_prompts = []
        
        # v40 RENDER PIPELINE CORE FLOW (Pristine, untouched sequential downloading to files)
        for i, scene in enumerate(sentences):
            progress_bar.progress(0.20 + (i / len(sentences)) * 0.60)
            status.info(f"🎨 منظر {i+1} بن رہا ہے: {scene[:30]}...")
            
            refined_p = get_visual_prompt_v40(scene, style, char_desc, scene_desc)
            generated_prompts.append(refined_p)
            
            if camera_motion in ["Pan Left", "Pan Right", "Pan Up", "Pan Down"]:
                w_target = make_even(w * 1.15)
                h_target = make_even(h * 1.15)
            else:
                w_target = w
                h_target = h
                
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed + i}&nologo=true&negative=double_faces,double_heads,multiple_faces,overlapping_limbs,extra_limbs,extra_hands,extra_fingers,mutated_hands,two_bodies,deformed,blurry,bad_anatomy,clones,twins"
            
            img_path = f"i_{u_id}_{i}.jpg"
            generated_images.append(img_path)
            
            # v40 Write directly to disk first
            img_data = session.get(img_url, timeout=60).content
            with open(img_path, "wb") as f:
                f.write(img_data)
                
            # v40 Force Resize & Format conversion (Sglowina Watermark layered inside PIL)
            try:
                with Image.open(img_path) as img_obj:
                    # Apply camera-motion scaling safely (no black borders)
                    if camera_motion in ["Pan Left", "Pan Right", "Pan Up", "Pan Down"]:
                        img_obj = img_obj.convert("RGB").resize((int(w * 1.15), int(h * 1.15)))
                    else:
                        img_obj = img_obj.convert("RGB").resize((w, h))
                        
                    if active_watermark:
                        draw = ImageDraw.Draw(img_obj)
                        draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                        
                    img_obj.save(img_path, "JPEG")
            except Exception:
                im = Image.new("RGB", (w_target, h_target), color=(30, 41, 59))
                if active_watermark:
                    draw = ImageDraw.Draw(im)
                    draw.text((w_target - 140, h_target - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                im.save(img_path, "JPEG")
                
            # Zoom In Movement
            if camera_motion in ["Pan Left", "Pan Right", "Pan Up", "Pan Down"]:
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24).resize((int(w * 1.15), int(h * 1.15)))
            else:
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24).resize((w, h))
                
            clip = apply_camera_motion_v40(clip, camera_motion, dur_per, w, h)
            clip = fadein(clip, 0.4)
            clips.append(clip)
            
        if not clips:
            fallback_p = f"i_{u_id}_fallback.jpg"
            img_data = generate_high_quality_placeholder(w, h, 1, active_watermark)
            with open(fallback_p, 'wb') as f:
                f.write(img_data)
            generated_images.append(fallback_p)
            clip = ImageClip(fallback_p).set_duration(voice_audio.duration).set_fps(24)
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t / voice_audio.duration)).set_position('center')
            clip = fadein(clip, 0.4)
            clips.append(clip)
            
        progress_bar.progress(0.85)
        status.info("🎞️ Rendering final MP4 movie (v40 High-Stability Export)...")
        
        final_audio = voice_audio
        bg_audio = None
        if has_bg_music and os.path.exists(bg_music_f):
            try:
                bg_audio = AudioFileClip(bg_music_f).volumex(0.10)
                bg_audio = bg_audio.set_duration(voice_audio.duration)
                final_audio = CompositeAudioClip([voice_audio, bg_audio])
            except Exception:
                pass
                
        # v40 final compose concatenation
        final_video = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
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
        status.success("🚀 Video Generated Successfully (ویڈیو بن چکی ہے)!")
        
        # Save project to SQLite (Point 2)
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
# 8. UI NAVIGATION & CONTROL PANEL (Main page Tabs restored)
# ==========================================
tab_auth, tab_chat, tab_movie, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In & Registrations",
    "💬 Electric AI Chat", 
    "🎬 Pro Master Studio", 
    "🎨 Pro Image Studio",
    "👤 Enterprise Center"
])

# Sidebar Settings
st.sidebar.markdown("---")
st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=True)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=True)

# Sglowina Enterprise Center (Credits display)
st.sidebar.markdown("---")
st.sidebar.subheader("👤 Sglowina Enterprise Center")
st.sidebar.write(f"Logged in as: **{st.session_state.logged_in_user}**")
user_info = get_user_data(st.session_state.logged_in_user)
if user_info:
    st.sidebar.write(f"Credits Remaining: **{user_info['credits']}** 🪙")
    st.sidebar.write(f"Plan: **{user_info['plan']}**")

with tab_auth:
    st.write("### 🔑 Sglowina User Access Portal")
    auth_mode = st.radio("Access Action:", ["Sign In / Login", "Create Account / Register"])
    
    if auth_mode == "Sign In / Login":
        login_user = st.text_input("Username:")
        login_pass = st.text_input("Password:", type="password")
        if st.button("Log In to Sglowina 🔓"):
            if authenticate_user(login_user, login_pass):
                st.session_state.logged_in_user = login_user
                st.success(f"Successfully logged in as {login_user}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
    else:
        reg_user = st.text_input("Create Username:")
        reg_email = st.text_input("Your Email:")
        reg_pass = st.text_input("Create Password:", type="password")
        if st.button("Register & Get 50 Credits 🪙"):
            if reg_user and reg_email and reg_pass:
                success, msg = register_saas_user(reg_user, reg_email, reg_pass)
                if success:
                    st.success("Registration successful! Please login.")
                else:
                    st.error(msg)

with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")); st.session_state.msgs.append({"role": "assistant", "content": res})

with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    
    # AI Prompt Assistant Module Layer (Point 9)
    with st.expander("🔮 AI Script & Prompt Assistant Module (نئی اسمارٹ لیئر)", expanded=False):
        raw_story_input = st.text_area("Yahan apni kahani likhein (AI will generate breakdown & prompts):", height=120)
        if st.button("Analyze Story with AI Assistant 🔮"):
            if raw_story_input:
                analysis_output = run_ai_prompt_assistant(raw_story_input)
                st.write(analysis_output)
            else:
                st.warning("Write story first.")

    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    # Character & Scene Memory with Libraries (Point 7, 8)
    char_col1, char_col2 = st.columns([2, 1])
    with char_col1:
        char_desc = st.text_input("Character Memory (کریکٹر کا مستقل حلیہ - مثلاً لباس, عمر, ڈکھیل):", 
                                  placeholder="Example: A 30-year-old brave warrior, short black beard, wearing a traditional dark green turban and grey robe")
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
        scene_desc = st.text_input("Scene Memory (پس منظر کا مستقل حلیہ - مثلاً مٹی کے گھر, اندھیری رات, تیز بارش):", 
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
    with st.expander("🎬 Advanced Cinematic Director Controls (فلمی معیار کی سیٹنگز)", expanded=False):
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

    mc1, mc2, mc3, mc4, mc5, mc6, mc7 = st.columns(7)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch (بھاری پن):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["Zoom Out (v40 Default)", "Zoom In", "Pan Left", "Pan Right", "Pan Up", "Pan Down", "Dolly In", "Dolly Out"])
    with mc7: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        
        pitch_map = {
            "Normal (نارمل)": "+0Hz",
            "Deep (بھاری آواز)": "-15Hz",
            "Very Deep (موٹی آواز)": "-28Hz"
        }
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Sglowina AI is generating your video with voice and motion... Please wait..."):
            v_res = create_cinematic_v40(m_script, mv, rate_val, pitch_val, mr, ms, sd, char_desc, scene_desc, camera_motion, enable_watermark, enable_bg_music)
            
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    
    tab_txt, tab_img = st.tabs(["🎨 Text to Image", "📤 Image Modify & Upload"])
    
    with tab_txt:
        p_i = st.text_area("Describe Image (One per line for batch):", height=150)
        
        char_desc_img = st.text_input("Consistent Character (کریکٹر کا مستقل حلیہ):", 
                                      placeholder="Example: A young girl, blue eyes, brown braided hair, red scarf")
        
        ic1, ic2, ic3 = st.columns(3)
        with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "Cinematic Film", "Anime Art", "Logo Design", "3D Cartoon", "Rustic Village Life", "Historical Epic"])
        with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok", "CinemaScope (21:9)", "Standard Box (4:3)"])
        with ic3: count = st.slider("Quantity:", 1, 10, 1)
        
        if st.button("Generate Titan Visuals 🚀"):
            # Balance check before generation (Deducts 2 credits per image)
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
                            with Image.open(io.BytesIO(img_data)) as im:
                                st.image(im, caption=f"Prompt: {single_p[:30]}...")
                                
                            # Deduct credits
                            deduct_user_credits(st.session_state.logged_in_user, 2)
                            log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
                        else:
                            st.error(f"Image generation failed for prompt: {single_p}")
            else:
                st.error("Deduction failed: Sglowina requires 2 credits per generated image.")

    with tab_img:
        uploaded_file = st.file_uploader("Upload Image to Modify:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Original Image", use_container_width=True)
            
        modify_prompt = st.text_input("Modification Instructions (تبدیلی کے احکامات):", placeholder="Example: Make the background dark green, add cinematic volumetric light")
        i_style_mod = st.selectbox("Modification Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
        
        if st.button("Modify & Re-render Image 🎨"):
            if uploaded_file and modify_prompt:
                u_db = get_user_data(st.session_state.logged_in_user)
                if u_db and u_db['credits'] >= 5:
                    with st.spinner("Modifying image..."):
                        img_name = translate_ur_to_en(modify_prompt)
                        img_data = fetch_img_failover(img_name, 1024, 1024, random.randint(1,999999))
                        if img_data:
                            with Image.open(io.BytesIO(img_data)) as im:
                                st.image(im, caption="Modified Masterpiece")
                            # Deduct credits (5 credits for image modification)
                            deduct_user_credits(st.session_state.logged_in_user, 5)
                            log_credit_usage(u_db['id'], "Image Modification", 5, u_db['credits'] - 5)
                        else:
                            st.error("Modification failed.")
                else:
                    st.error("Deduction failed: Sglowina requires 5 credits to modify images.")
            else:
                st.warning("Please upload an image and write instructions first.")

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
            
            # Account Settings
            st.markdown("---")
            st.subheader("⚙️ Account Settings")
            st.write("Mock integration: Password management is locked in this session.")
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
                    st.write(f"Script: `{proj['story']}`")
                    st.write("Saved Prompts for this video:")
                    st.code(proj['prompt'], language="text")
                    st.markdown("---")
        else:
            st.warning("Please login first.")
                
    with ent_tab_billing:
        st.write("### 💳 Subscription Plans & Credit Packages")
        col_plan1, col_plan2 = st.columns(2)
        with col_plan1:
            st.write("#### 📦 Subscription Plans")
            st.info("Free Plan: 50 Credits/Month, Watermark enforced")
            st.success("Starter Plan ($19): 500 Credits/Month, No Watermark")
            st.warning("Premium Plan ($49): 1500 Credits/Month, Priority processing")
            st.error("Enterprise Plan ($199): Unlimited Credits, dedicated support")
        with col_plan2:
            st.write("#### 🪙 Credit Packages")
            st.write("100 Credits Package ($5)")
            st.write("500 Credits Package ($20)")
            st.write("1000 Credits Package ($35)")
        st.write("Payment Gateway is ready. Stripe/PayPal API configuration locked.")
                
    with ent_tab_admin:
        st.write("#### 🔒 Secured Admin Control Settings")
        if u_db and u_db['role'] == 'Admin':
            st.success("Access Granted: Administrator Mode Activated")
            
            # Fetch SaaS Stats (Point 5)
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(credits) FROM users")
            total_credits_allocated = cursor.fetchone()[0]
            
            st.write("### 👥 System Metrics Dashboard")
            saas_col1, saas_col2, saas_col3 = st.columns(3)
            with saas_col1:
                st.metric("Total Users Count", total_users)
            with saas_col2:
                st.metric("Total Generated Projects", total_projects)
            with saas_col3:
                st.metric("Total Allocated Credits", total_credits_allocated)
                
            cursor.execute("SELECT * FROM users")
            all_users = cursor.fetchall()
            
            st.write("### 👥 User Database Management")
            for u in all_users:
                st.write(f"👤 **{u['username']}** | Role: {u['role']} | Plan: {u['plan']} | Credits: {u['credits']} 🪙 | Status: {u['status']}")
                
            st.markdown("---")
            manage_user = st.selectbox("Select User to Adjust:", [u['username'] for u in all_users])
            new_plan = st.selectbox("Change Subscription Plan:", ["Free", "Starter", "Premium", "Enterprise"])
            new_role = st.selectbox("Change User Role:", ["User", "Admin"])
            new_status = st.selectbox("Change Account Status:", ["Active", "Banned"])
            new_credits = st.number_input("Adjust Credits Balance:", min_value=0, max_value=10000, value=500)
            
            if st.button("Apply Admin Settings"):
                cursor.execute("UPDATE users SET credits = ?, plan = ?, role = ?, status = ? WHERE username = ?", (new_credits, new_plan, new_role, new_status, manage_user))
                conn.commit()
                st.success(f"Successfully updated settings for {manage_user}!")
            conn.close()
        else:
            st.error("Access Denied: Only database-defined Administrators can access this control panel.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.5 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
