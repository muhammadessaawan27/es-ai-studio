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
# MOVIEPY CINEMATIC IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# BROWSER SESSION & GLOBAL CONSTANTS
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

st.set_page_config(page_title="Sglowina AI - Vision & Studio V2.5", layout="wide", page_icon="🎬")

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []
if "avatar_speaking" not in st.session_state:
    st.session_state.avatar_speaking = False
if "last_vision_reply" not in st.session_state:
    st.session_state.last_vision_reply = "السلام علیکم! میں آپ کا AI ساتھی ہوں۔ اپنے کیمرے سے مجھے کچھ دکھائیں، میں دیکھ کر بتاؤں گا!"

st.sidebar.subheader("🎬 Video & Avatar Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)
avatar_voice = st.sidebar.selectbox("Avatar Voice:", ["Urdu Female (Uzma)", "Urdu Male (Asad)"])

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

# Speech Generator
def save_audio_safe(text, voice, rate, pitch, filename):
    try:
        async def amain():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(filename)
        asyncio.run(amain())
        return True
    except Exception:
        return False

# Multimodal AI Vision Analyzer
def analyze_image_with_ai_vision(image_bytes, user_question=""):
    try:
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        prompt_instruction = (
            "You are an intelligent vision AI companion. Look at this camera image and describe what you see in fluent, natural Urdu (اردو). "
            "Identify objects (like tractors, vehicles, gadgets), people, colors, animals, or actions clearly. "
        )
        if user_question.strip():
            prompt_instruction += f"Answer this specific question asked by the user: '{user_question}'"
        else:
            prompt_instruction += "Give a friendly 2-3 sentence overview of what is in front of the camera."

        url = "https://text.pollinations.ai/openai"
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_instruction},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }
            ],
            "model": "openai"
        }
        res = session.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    
    # Text backup if vision fails
    return "میں نے کیمرے میں منظر دیکھ لیا ہے۔ یہ ایک دلچسپ ماحول ہے!"

# Render Live Animated HTML5 Avatar
def render_live_avatar(is_speaking=False):
    speaking_class = "speaking" if is_speaking else "idle"
    avatar_html = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 15px;">
        <style>
            .avatar-container {{
                width: 170px;
                height: 170px;
                position: relative;
                background: linear-gradient(135deg, #ff007a, #7928ca, #00d4ff);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 0 35px rgba(255, 0, 122, 0.45);
                animation: floatAvatar 3s ease-in-out infinite alternate;
            }}
            .avatar-face {{
                width: 140px;
                height: 140px;
                background: #fff8f0;
                border-radius: 50%;
                position: relative;
                box-shadow: inset 0 -5px 12px rgba(0,0,0,0.1);
            }}
            .avatar-eyes {{
                display: flex;
                justify-content: space-around;
                width: 75px;
                position: absolute;
                top: 45px;
                left: 32px;
            }}
            .eye {{
                width: 14px;
                height: 18px;
                background: #1e293b;
                border-radius: 50%;
                animation: blinkEye 3.5s infinite;
            }}
            .avatar-mouth {{
                width: 28px;
                height: 14px;
                background: #e11d48;
                border-radius: 0 0 14px 14px;
                position: absolute;
                bottom: 35px;
                left: 56px;
                transition: all 0.2s ease;
            }}
            .avatar-blush {{
                position: absolute;
                width: 18px;
                height: 10px;
                background: #fda4af;
                border-radius: 50%;
                top: 58px;
            }}
            .blush-left {{ left: 16px; }}
            .blush-right {{ right: 16px; }}

            /* Speaking Mouth Animation */
            .speaking .avatar-mouth {{
                animation: speakMouth 0.35s infinite alternate;
            }}
            .speaking .avatar-container {{
                box-shadow: 0 0 55px #00d4ff, 0 0 30px #ff007a;
            }}

            @keyframes floatAvatar {{
                0% {{ transform: translateY(0px) scale(1); }}
                100% {{ transform: translateY(-8px) scale(1.02); }}
            }}
            @keyframes blinkEye {{
                0%, 90%, 100% {{ transform: scaleY(1); }}
                95% {{ transform: scaleY(0.1); }}
            }}
            @keyframes speakMouth {{
                0% {{ height: 8px; border-radius: 0 0 8px 8px; }}
                100% {{ height: 26px; border-radius: 12px; transform: scaleX(1.15); }}
            }}
        </style>

        <div class="avatar-container {speaking_class}">
            <div class="avatar-face">
                <div class="avatar-blush blush-left"></div>
                <div class="avatar-blush blush-right"></div>
                <div class="avatar-eyes">
                    <div class="eye"></div>
                    <div class="eye"></div>
                </div>
                <div class="avatar-mouth"></div>
            </div>
        </div>
    </div>
    """
    st.components.v1.html(avatar_html, height=210)

def translate_ur_to_en_enhanced(text):
    try:
        instruction = "Translate this Urdu scene into a descriptive English visual prompt for video generation with 8k details."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' Urdu: ' + text)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return text

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined_text = (scene_text_en + " " + scene_text_ur).lower()
    spiritual_keywords = ["prophet", "sahaba", "saint", "angel", "god", "allah", "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ"]
    if any(k in combined_text for k in spiritual_keywords):
        return True, "Cinematic spiritual scenery, volumetric divine golden light rays from heavens, sacred mountains, no human faces."
    return False, scene_text_en

def generate_enhanced_cinematic_prompt(urdu_scene, char_memory, scene_memory, character_heritage, enable_islamic_filter, raw_male_url, raw_female_url):
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote('Write detailed Flux prompt: ' + urdu_scene)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            return res.text.strip()
    except Exception:
        pass
    return f"Cinematic scene: {urdu_scene}, 8k photorealistic"

def apply_color_lut_harmony(img_path, style_preset):
    try:
        if not os.path.exists(img_path): return
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "JPEG")
    except Exception:
        pass

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
            bg.paste(fg, ((target_w - new_w) // 2, (target_h - new_h) // 2))
            bg.save(img_path, "JPEG")
    except Exception:
        pass

def parallel_download_flux_images(urls, paths, w, h):
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
            im = Image.new("RGB", (w, h), color=(15, 23, 42))
            im.save(path, "JPEG")
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

def apply_camera_motion_v40(img_path, motion, duration, w, h):
    try:
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            im = Image.new("RGB", (w, h), color=(15, 23, 42))
            im.save(img_path, "JPEG")
        scale_factor = 1.25
        base_clip = ImageClip(img_path).set_duration(duration).set_fps(24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = base_clip.resize((cw, ch))
        animated_clip = clip.resize(lambda t: 1.15 - 0.15 * (t / duration)).set_position('center')
        return CompositeVideoClip([animated_clip], size=(w, h)).set_duration(duration)
    except Exception:
        return ImageClip(img_path).set_duration(duration).resize((w, h))

def apply_clip_transition(clip, transition, duration):
    try:
        if clip is not None:
            return clip.fadein(0.3).fadeout(0.3)
    except Exception:
        pass
    return clip

# Master Video Generator
def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="AI Hollywood Director (Auto)", transition_style="Cross Dissolve (Fade)", enable_watermark=True, enable_bg_music=True, uploaded_male_img=None, uploaded_female_img=None, enable_islamic_filter=True, character_heritage="Automatic", gen_mode="Cinematic Photo Zoom & Pan (100% Free & Unlimited)", pollinations_key="", video_model="wan-fast", advanced_params=None):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
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
            
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)
        
        flux_prompt_urls = []
        img_paths = []
        
        for i, scene in enumerate(sentences):
            english_scene = translate_ur_to_en_enhanced(scene)
            refined_p = f"Cinematic photorealistic 8k video scene: {english_scene}"
            generated_prompts.append(refined_p)
            
            # Real AI Video Mode
            if "Real AI Video" in gen_mode:
                status.info(f"🎥 Rendering Moving Video Frame {i+1}...")
                aspect_param = "16:9" if "16:9" in ratio else "9:16"
                vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(refined_p[:300])}?model={video_model}&aspectRatio={aspect_param}&duration=4"
                if pollinations_key.strip(): vid_url += f"&key={pollinations_key.strip()}"
                vid_path = f"v_{u_id}_{i}.mp4"
                try:
                    res_vid = session.get(vid_url, timeout=75)
                    if res_vid.status_code == 200 and len(res_vid.content) > 50000:
                        with open(vid_path, "wb") as f_vid:
                            f_vid.write(res_vid.content)
                        sub_audio_p = temporary_audio_tracks[i]
                        dur_sc = AudioFileClip(sub_audio_p).duration if os.path.exists(sub_audio_p) else 4.0
                        clip = VideoFileClip(vid_path).resize((w, h)).set_duration(dur_sc)
                        if os.path.exists(sub_audio_p):
                            clip = clip.set_audio(AudioFileClip(sub_audio_p))
                        clips.append(clip)
                        generated_images.append(vid_path)
                        continue
                except Exception:
                    pass
            
            w_target, h_target = make_even(w * 1.25), make_even(h * 1.25)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p)}?width={w_target}&height={h_target}&seed={seed}&nologo=true&model=flux"
            flux_prompt_urls.append(img_url)
            img_path = f"i_{u_id}_{i}.jpg"
            img_paths.append(img_path)
            generated_images.append(img_path)
            
        progress_bar.progress(0.40)
        parallel_download_flux_images(flux_prompt_urls, img_paths, w, h)
        
        for i, scene in enumerate(sentences):
            if len(clips) > i: continue
            img_path = img_paths[i]
            sub_audio_path = temporary_audio_tracks[i]
            apply_blurred_background_padding(img_path, make_even(w * 1.25), make_even(h * 1.25))
            
            dur_scene = 4.0
            scene_voice_clip = None
            if os.path.exists(sub_audio_path):
                try:
                    scene_voice_clip = AudioFileClip(sub_audio_path)
                    dur_scene = scene_voice_clip.duration
                except Exception: pass
                
            clip = apply_camera_motion_v40(img_path, camera_motion, dur_scene, w, h)
            if scene_voice_clip and clip:
                clip = clip.set_audio(scene_voice_clip)
            clips.append(clip)
            
        progress_bar.progress(0.80)
        final_video = concatenate_videoclips(clips, method="compose").resize((w, h))
        out_name = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        final_video.close()
        
        for sub_voice in temporary_audio_tracks:
            if os.path.exists(sub_voice): os.remove(sub_voice)
        for file_p in generated_images:
            if os.path.exists(file_p): os.remove(file_p)
            
        progress_bar.progress(1.0)
        status.success("🚀 Video Generated Successfully!")
        deduct_user_credits(st.session_state.logged_in_user, 15)
        log_credit_usage(user_id, "Video Generation", 15, user_credits - 15)
        return out_name
    except Exception as e:
        progress_bar.empty()
        return f"Error Details: {e}"
    finally:
        gc.collect()

# ==========================================
# UI STYLING & NAVIGATION
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700;900&display=swap');
    
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    .glow-title { 
        font-size: 2.2rem; font-weight: 900; text-align: center; font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-top: 15px; margin-bottom: 5px; letter-spacing: 2px;
    }
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 12px !important; 
        height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; 
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI</div>', unsafe_allow_html=True)

tab_auth, tab_avatar_vision, tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🔑 Sign In & Registrations",
    "👁️ Live Vision & Talking Avatar",
    "🎬 Pro Master Studio", 
    "🎨 Pro Image Studio",
    "💬 Electric AI Chat", 
    "👤 Enterprise Center"
])

# -----------------
# TAB 1: AUTH
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
                else: st.error("Invalid credentials.")
    else:
        with st.form("reg_form"):
            new_u = st.text_input("Choose Username")
            new_e = st.text_input("Email Address")
            new_p = st.text_input("Password", type="password")
            if st.form_submit_button("Register Account 🎯"):
                if new_u and new_e and new_p:
                    success, msg = register_saas_user(new_u, new_e, new_p)
                    if success: st.success(f"Account for '{new_u}' registered! Please sign in. 🟢")
                    else: st.error(msg)

# -----------------
# TAB 2: LIVE VISION & TALKING AVATAR COMPANION
# -----------------
with tab_avatar_vision:
    st.write("### 👁️ Live AI Camera Vision & Animated Companion")
    st.info("موبائل یا کمپیوٹر کا کیمرہ آن کریں، سامنے جو بھی چیز دکھائیں گے، اوتار اسے دیکھ کر خودکار طریقے سے اردو میں بول کر بتائے گا!")
    
    col_av1, col_av2 = st.columns([1.2, 2])
    
    with col_av1:
        st.write("#### 🤖 Live Talking Mascot")
        render_live_avatar(is_speaking=st.session_state.avatar_speaking)
        st.markdown(f"**AI بول رہا ہے:**\n\n> *\"{st.session_state.last_vision_reply}\"*")
        
    with col_av2:
        st.write("#### 📸 Point Camera & Ask")
        cam_pic = st.camera_input("کیمرے سے تصویر لیں (Take Snapshot):")
        custom_question = st.text_input("اس چیز کے بارے میں کچھ پوچھنا چاہتے ہیں؟ (Optional):", placeholder="مثال: دیکھو اور بتاؤ یہ کون سا ٹریکٹر/پودا ہے؟")
        
        if cam_pic is not None:
            if st.button("Look & Tell Me (دیکھو اور بتاؤ) 🚀"):
                with st.spinner("🤖 اوتار کیمرے سے دیکھ رہا ہے اور جواب تیار کر رہا ہے..."):
                    img_bytes = cam_pic.getvalue()
                    vision_ans = analyze_image_with_ai_vision(img_bytes, custom_question)
                    st.session_state.last_vision_reply = vision_ans
                    st.session_state.avatar_speaking = True
                    
                    # Generate speech audio
                    v_actor = "ur-PK-UzmaNeural" if "Uzma" in avatar_voice else "ur-PK-AsadNeural"
                    temp_speech_file = f"vision_speech_{uuid.uuid4().hex[:6]}.mp3"
                    if save_audio_safe(vision_ans, v_actor, "+0%", "+0Hz", temp_speech_file):
                        st.audio(temp_speech_file, format="audio/mp3", autoplay=True)
                    st.rerun()

# -----------------
# TAB 3: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    gen_mode = st.selectbox("Select Generator Engine:", ["Real AI Video Motion (Beta - Pollinations Video API)", "Cinematic Photo Zoom & Pan (100% Free & Unlimited)"])
    pollinations_key = st.text_input("Enter Pollinations API Key (Optional - Leave blank for Free):", type="password") if "Real AI Video" in gen_mode else ""
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150, placeholder="مثال: ایک سرخ ٹریکٹر کھیت میں تیزی سے ہل چلا رہا ہے...")
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc3: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
    with mc4: sd = st.number_input("Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        with st.spinner("🎬 Generating cinematic video..."):
            v_res = create_cinematic_v40(
                story=m_script, voice_gen=mv, rate="+0%", pitch="+0Hz", ratio=mr, style=ms, seed=sd,
                gen_mode=gen_mode, pollinations_key=pollinations_key
            )
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: st.error(v_res)

# -----------------
# TAB 4: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    if st.button("Generate Visual 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        if u_db and u_db['credits'] >= 2:
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1024&height=1024&seed={random.randint(1,999999)}&model=flux&nologo=true"
            res_img = session.get(img_url, timeout=30)
            if res_img.status_code == 200:
                with Image.open(io.BytesIO(res_img.content)) as im: st.image(im, caption=p_i[:40])
                deduct_user_credits(st.session_state.logged_in_user, 2)
        else: st.error("Insufficient credits.")

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
        res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true", timeout=15).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# -----------------
# TAB 6: ENTERPRISE CENTER
# -----------------
with tab_enterprise:
    st.write("### 👤 Enterprise Center")
    u_db = get_user_data(st.session_state.logged_in_user)
    if u_db:
        st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 20px;'>Sglowina AI V2.5 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
