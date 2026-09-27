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
# STREAMLIT CONFIG & GLOBALS
# ==========================================
st.set_page_config(page_title="Sglowina AI - MUSE Autonomous Studio V3.5", layout="wide", page_icon="🤖")

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI is an advanced generative AI cinematic video, live vision & image production platform, "
    "proudly developed by Muhammad Essa Awan & Saba Wahid."
)

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []

render_semaphore = threading.Semaphore(value=2)
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
# 🤖 MUSE AUTONOMOUS LIVE COMPANION ENGINE (Full Hands-Free WebRTC + Vision + Speech)
# ==========================================
def render_muse_autonomous_companion():
    muse_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            .muse-wrapper {
                background: radial-gradient(circle at center, #1e1b4b 0%, #090d16 100%);
                border-radius: 24px;
                padding: 25px;
                color: #ffffff;
                font-family: 'Segoe UI', Roboto, sans-serif;
                box-shadow: 0 15px 50px rgba(0,0,0,0.8);
                border: 2px solid #3b82f6;
            }
            .muse-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                padding-bottom: 12px;
            }
            .muse-title {
                font-size: 24px;
                font-weight: 900;
                background: linear-gradient(45deg, #00d4ff, #ff007a);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .muse-stage {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                justify-content: center;
                align-items: center;
            }
            .cam-card {
                flex: 1;
                min-width: 300px;
                max-width: 440px;
                height: 330px;
                background: #000000;
                border-radius: 18px;
                overflow: hidden;
                position: relative;
                border: 2px solid #00d4ff;
                box-shadow: 0 0 25px rgba(0, 212, 255, 0.3);
            }
            #museCam {
                width: 100%;
                height: 100%;
                object-fit: cover;
                transform: scaleX(-1);
            }
            .avatar-card {
                flex: 1;
                min-width: 300px;
                max-width: 440px;
                height: 330px;
                background: linear-gradient(135deg, #181824, #0b0f19);
                border-radius: 18px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                border: 2px solid #ff007a;
                box-shadow: 0 0 25px rgba(255, 0, 122, 0.3);
            }
            
            /* MUSE Character */
            .character-body {
                width: 160px;
                height: 160px;
                background: radial-gradient(circle, #ff007a, #7928ca, #00d4ff);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 0 45px #ff007a;
                animation: idleFloat 3s infinite ease-in-out alternate;
            }
            .character-face {
                width: 130px;
                height: 130px;
                background: #fff8f0;
                border-radius: 50%;
                position: relative;
            }
            .eyes-box {
                display: flex;
                justify-content: space-around;
                width: 70px;
                position: absolute;
                top: 42px;
                left: 30px;
            }
            .eye {
                width: 14px;
                height: 18px;
                background: #0f172a;
                border-radius: 50%;
                animation: eyeBlink 3.5s infinite;
            }
            .mouth {
                width: 26px;
                height: 13px;
                background: #e11d48;
                border-radius: 0 0 13px 13px;
                position: absolute;
                bottom: 30px;
                left: 52px;
                transition: all 0.15s ease;
            }

            /* Live Speaking Animation */
            .speaking .mouth {
                animation: mouthMove 0.25s infinite alternate;
            }
            .speaking .character-body {
                box-shadow: 0 0 70px #00d4ff, 0 0 40px #ff007a;
            }
            
            .hud-status {
                margin-top: 18px;
                padding: 14px 20px;
                background: #1e293b;
                border-radius: 12px;
                text-align: center;
                font-size: 16px;
                color: #38bdf8;
                font-weight: bold;
                border: 1px solid #334155;
            }
            .btn-row {
                display: flex;
                justify-content: center;
                gap: 15px;
                margin-top: 18px;
            }
            .muse-btn {
                background: linear-gradient(45deg, #2563eb, #00d4ff);
                color: #ffffff;
                border: none;
                padding: 14px 30px;
                font-size: 16px;
                font-weight: 900;
                border-radius: 14px;
                cursor: pointer;
                box-shadow: 0 0 20px rgba(37,99,235,0.4);
                transition: 0.3s ease;
            }
            .muse-btn:hover {
                transform: scale(1.04);
            }
            .active-btn {
                background: linear-gradient(45deg, #e11d48, #ff007a) !important;
                box-shadow: 0 0 30px rgba(225,29,72,0.6) !important;
            }

            @keyframes idleFloat {
                0% { transform: translateY(0px) scale(1); }
                100% { transform: translateY(-10px) scale(1.03); }
            }
            @keyframes eyeBlink {
                0%, 90%, 100% { transform: scaleY(1); }
                95% { transform: scaleY(0.1); }
            }
            @keyframes mouthMove {
                0% { height: 6px; border-radius: 0 0 6px 6px; }
                100% { height: 30px; border-radius: 14px; transform: scaleX(1.25); }
            }
        </style>
    </head>
    <body>
        <div class="muse-wrapper">
            <div class="muse-header">
                <div class="muse-title">🤖 MUSE AUTONOMOUS AI COMPANION</div>
                <div id="liveBadge" style="background:#ef4444; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:12px;">STANDBY</div>
            </div>

            <div class="muse-stage">
                <!-- Live Continuous Video View -->
                <div class="cam-card">
                    <div style="position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.7); padding:4px 10px; border-radius:8px; font-size:12px;">📷 Live Camera View</div>
                    <video id="museCam" autoplay playsinline></video>
                </div>

                <!-- Live Animated Mascot -->
                <div class="avatar-card" id="avatarBox">
                    <div style="position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.7); padding:4px 10px; border-radius:8px; font-size:12px;">🧠 MUSE Brain (Live Talking)</div>
                    <div class="character-body">
                        <div class="character-face">
                            <div class="eyes-box">
                                <div class="eye"></div>
                                <div class="eye"></div>
                            </div>
                            <div class="mouth"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="hud-status" id="museStatus">
                🎙️ شروع کرنے کے لیے نیچے <b>"Activate MUSE Hands-Free"</b> کا بٹن دبائیں۔ اس کے بعد کسی بٹن کو دبانے کی ضرورت نہیں ہوگی، صرف بولیں!
            </div>

            <div class="btn-row">
                <button class="muse-btn" id="toggleMuseBtn" onclick="toggleMuseSystem()">🚀 Activate MUSE Hands-Free (لائیو ایجنٹ آن کریں)</button>
            </div>
        </div>

        <canvas id="visionBuffer" style="display:none;"></canvas>

        <script>
            let isRunning = false;
            let videoElement = document.getElementById('museCam');
            let statusDisplay = document.getElementById('museStatus');
            let avatarBox = document.getElementById('avatarBox');
            let liveBadge = document.getElementById('liveBadge');
            let toggleBtn = document.getElementById('toggleMuseBtn');
            let recognition = null;

            async function toggleMuseSystem() {
                if (!isRunning) {
                    try {
                        statusDisplay.innerText = "⏳ کیمرہ اور مائیک لائیو کنیکٹ ہو رہے ہیں...";
                        
                        // 1. Live Continuous Camera
                        const stream = await navigator.mediaDevices.getUserMedia({
                            video: { facingMode: "environment", width: 640, height: 480 },
                            audio: false
                        });
                        videoElement.srcObject = stream;
                        
                        // 2. Start Continuous Hands-Free Speech Recognition
                        startHandsFreeListening();
                        
                        isRunning = true;
                        liveBadge.innerText = "🟢 LIVE & LISTENING";
                        liveBadge.style.background = "#10b981";
                        toggleBtn.innerText = "🛑 Stop MUSE Companion";
                        toggleBtn.classList.add("active-btn");
                        
                        speakUrduOutLoud("السلام علیکم! میں آپ کا میوز ایجنٹ ہوں۔ کیمرہ اور مائیک آن ہے، آپ جو پوچھنا چاہیں بولیں!");
                    } catch (e) {
                        statusDisplay.innerText = "❌ کیمرہ یا مائیک کی پرمیشن الاؤ کریں: " + e.message;
                    }
                } else {
                    stopMuseSystem();
                }
            }

            function stopMuseSystem() {
                isRunning = false;
                if (videoElement.srcObject) {
                    videoElement.srcObject.getTracks().forEach(track => track.stop());
                }
                if (recognition) {
                    recognition.stop();
                }
                liveBadge.innerText = "STANDBY";
                liveBadge.style.background = "#ef4444";
                toggleBtn.innerText = "🚀 Activate MUSE Hands-Free (لائیو ایجنٹ آن کریں)";
                toggleBtn.classList.remove("active-btn");
                statusDisplay.innerText = "🔴 سسٹم بند کر دیا گیا ہے۔";
            }

            function startHandsFreeListening() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    statusDisplay.innerText = "براؤزر میں مائیک سپورٹ دستیاب نہیں ہے۔ Google Chrome استعمال کریں۔";
                    return;
                }

                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.lang = 'ur-PK';

                recognition.onresult = async function(event) {
                    let lastResultIndex = event.results.length - 1;
                    let spokenText = event.results[lastResultIndex][0].transcript;
                    
                    statusDisplay.innerText = "👂 آپ نے کہا: " + spokenText;
                    
                    // Automatically inspect camera frame and answer!
                    await processVisionAndReply(spokenText);
                };

                recognition.onerror = function(event) {
                    if (isRunning) {
                        try { recognition.start(); } catch(e) {}
                    }
                };

                recognition.onend = function() {
                    if (isRunning) {
                        try { recognition.start(); } catch(e) {}
                    }
                };

                recognition.start();
                statusDisplay.innerText = "🟢 MUSE لائیو سن رہا ہے۔ بغیر بٹن دبائے صرف بولیں!";
            }

            async function processVisionAndReply(userPrompt) {
                statusDisplay.innerText = "🧠 MUSE کیمرے سے دیکھ کر تجزیہ کر رہا ہے...";
                setMouthTalking(true);

                let canvas = document.getElementById('visionBuffer');
                canvas.width = videoElement.videoWidth || 640;
                canvas.height = videoElement.videoHeight || 480;
                let ctx = canvas.getContext('2d');
                ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                let base64Img = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];

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
                                            text: "You are the MUSE autonomous AI multimodal companion in a real-time live vision session. Look at this camera frame and answer the user's voice prompt directly in fluent, natural Urdu (اردو). Explain the objects, vehicles, tractors, people, or surroundings in front of the lens clearly in 2 concise sentences: " + userPrompt 
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
                    statusDisplay.innerText = "🗣️ MUSE: " + reply;
                    speakUrduOutLoud(reply);
                } catch (err) {
                    speakUrduOutLoud("معاف کیجئے گا، میں کیمرے کا منظر دیکھنے کی دوبارہ کوشش کر رہا ہوں۔");
                }
            }

            function speakUrduOutLoud(text) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utter = new SpeechSynthesisUtterance(text);
                    utter.lang = 'ur-PK';
                    utter.rate = 1.0;
                    utter.pitch = 1.1;

                    utter.onstart = function() { setMouthTalking(true); };
                    utter.onend = function() { setMouthTalking(false); };
                    utter.onerror = function() { setMouthTalking(false); };

                    window.speechSynthesis.speak(utter);
                } else {
                    setMouthTalking(false);
                }
            }

            function setMouthTalking(state) {
                if (state) {
                    avatarBox.classList.add('speaking');
                } else {
                    avatarBox.classList.remove('speaking');
                }
            }
        </script>
    </body>
    </html>
    """
    st.components.v1.html(muse_html, height=620)

# ==========================================
# MASTER VIDEO & STUDIO ENGINES
# ==========================================
def translate_ur_to_en_enhanced(text):
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote('Translate to 8k video prompt: ' + text)}?model=openai"
        res = session.get(url, timeout=12)
        if res.status_code == 200: return res.text.strip()
    except Exception: pass
    return text

def parallel_download_flux_images(urls, paths, w, h):
    def download_single(url, path):
        try:
            res = session.get(url, timeout=35)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(path, "wb") as f: f.write(res.content)
                return True
        except Exception: pass
        try:
            im = Image.new("RGB", (w, h), color=(15, 23, 42))
            im.save(path, "JPEG")
            return True
        except Exception: return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

def apply_camera_motion_v40(img_path, duration, w, h):
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

def create_cinematic_v40(story, voice_gen, ratio):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    progress_bar = st.progress(0.0)
    temporary_audio_tracks = []
    generated_images = []
    
    try:
        status.info("🎙️ Processing Dialogue Voiceovers...")
        progress_bar.progress(0.15)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 4]
        if not sentences: sentences = [story]
        
        for idx, scene in enumerate(sentences):
            v_code_scene = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
            sub_audio_path = f"a_{u_id}_{idx}.mp3"
            save_audio_safe(scene, v_code_scene, "+0%", "+0Hz", sub_audio_path)
            temporary_audio_tracks.append(sub_audio_path)
            
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        
        flux_prompt_urls = []
        img_paths = []
        for i, scene in enumerate(sentences):
            english_scene = translate_ur_to_en_enhanced(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(english_scene)}?width={w}&height={h}&nologo=true&model=flux"
            flux_prompt_urls.append(img_url)
            img_path = f"i_{u_id}_{i}.jpg"
            img_paths.append(img_path)
            generated_images.append(img_path)
            
        progress_bar.progress(0.45)
        status.info("🎨 Rendering High-Definition Frames...")
        parallel_download_flux_images(flux_prompt_urls, img_paths, w, h)
        
        clips = []
        for i, scene in enumerate(sentences):
            img_path = img_paths[i]
            sub_audio_path = temporary_audio_tracks[i]
            dur_scene = 4.0
            scene_voice_clip = None
            if os.path.exists(sub_audio_path):
                try:
                    scene_voice_clip = AudioFileClip(sub_audio_path)
                    dur_scene = scene_voice_clip.duration
                except Exception: pass
            clip = apply_camera_motion_v40(img_path, dur_scene, w, h)
            if scene_voice_clip and clip:
                clip = clip.set_audio(scene_voice_clip)
            clips.append(clip)
            
        progress_bar.progress(0.85)
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
        margin-top: 10px; margin-bottom: 5px; letter-spacing: 2px;
    }
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 12px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none; 
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI - MUSE LIVE STUDIO</div>', unsafe_allow_html=True)

tab_muse, tab_movie, tab_image, tab_chat, tab_auth = st.tabs([
    "🤖 MUSE Autonomous Agent (ہینڈز فری)",
    "🎬 Pro Movie Studio", 
    "🎨 Pro Image Studio",
    "💬 Electric AI Chat",
    "🔑 User Accounts & Auth"
])

# -----------------
# TAB 1: MUSE AUTONOMOUS AGENT
# -----------------
with tab_muse:
    st.write("### 🤖 MUSE Autonomous Live Companion")
    st.info("💡 **طریقہ استعمال:** نیچے 'Activate MUSE Hands-Free' کا بٹن دبائیں۔ اس کے بعد کسی بٹن کو دبانے کی ضرورت نہیں ہوگی، کیمرہ اور مائیک خودکار لائیو رہیں گے اور آپ جو بولیں گے AI دیکھ کر اسپیکر سے جواب دے گا!")
    render_muse_autonomous_companion()

# -----------------
# TAB 2: PRO MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production Studio")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=120, placeholder="مثال: ایک سرخ ٹریکٹر کھیت میں تیزی سے ہل چلا رہا ہے...")
    mc1, mc2 = st.columns(2)
    with mc1: mv = st.selectbox("AI Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mr = st.selectbox("Video Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    
    if st.button("Generate Master Movie 🚀"):
        if m_script.strip():
            with st.spinner("🎬 Generating cinematic video..."):
                v_res = create_cinematic_v40(m_script, mv, mr)
            if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
                st.video(v_res)
                st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# -----------------
# TAB 3: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image:", height=100)
    if st.button("Generate Visual 🚀"):
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1024&height=1024&seed={random.randint(1,999999)}&model=flux&nologo=true"
        res_img = session.get(img_url, timeout=30)
        if res_img.status_code == 200:
            with Image.open(io.BytesIO(res_img.content)) as im: st.image(im, caption=p_i[:40])

# -----------------
# TAB 4: CHAT
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
# TAB 5: AUTH
# -----------------
with tab_auth:
    st.write("### 🔑 Sglowina User Authentication")
    u_name = st.text_input("Username", value="demo_user")
    st.success(f"Active Session: {u_name} 🟢")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 20px;'>Sglowina AI MUSE V3.5 | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
