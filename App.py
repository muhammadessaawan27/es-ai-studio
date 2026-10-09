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

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
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
    st.session_state.gen_mode = "Real AI Video Motion (Beta - Pollinations Video API)"
if "pollinations_key" not in st.session_state:
    st.session_state.pollinations_key = ""

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

st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V2.0", layout="wide", page_icon="🎬")

if "enable_watermark" not in st.session_state: st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Video & Audio Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=st.session_state.enable_bg_music)
custom_watermark_file = st.sidebar.file_uploader("Upload Custom Watermark Logo (Premium Only):", type=["png", "jpg", "jpeg"])

st.session_state.enable_watermark = enable_watermark
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=1)

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
    conn = sqlite3.connect("sglowina_saas_v21.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_v21():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, plan TEXT DEFAULT 'Free', credits INTEGER DEFAULT 50,
            role TEXT DEFAULT 'User', status TEXT DEFAULT 'Active', created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, user_id INTEGER, project_name TEXT,
            type TEXT, file_path TEXT, prompt TEXT, created_at TEXT, is_favorite INTEGER DEFAULT 0
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS local_payments (id TEXT PRIMARY KEY, username TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Pending', created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
    
    # Founders Admin Credentials: Muhammad Essa Awan & Saba Wahid (Password: 786)
    h_admin = hash_password("786")
    for adm in ["muhammad_essa_awan", "saba_wahid"]:
        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = ?", (adm,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, 'Enterprise', 5000, 'Admin', ?)",
                           (adm, f"{adm}@sglowina.ai", h_admin, time.strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

init_db_v21()

def authenticate_user(username, password):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password_hash FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        row = cursor.fetchone()
        if row: return verify_password(password.strip(), row['password_hash'])
        return False
    except: return False
    finally: conn.close()

def get_user_data(username):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        row = cursor.fetchone()
        if row: return dict(row)
        return None
    except: return None
    finally: conn.close()

def deduct_user_credits(username, amount):
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET credits = MAX(0, credits - ?) WHERE LOWER(username) = LOWER(?)", (amount, username))
        conn.commit()
    except: pass
    finally: conn.close()

# ================= CRASH-PROOF ENHANCEMENT FUNCTIONS =================
def burn_subtitles_to_image(img_path, scene_text):
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
                return "\n".join([re.sub(r'<[^>]*>', '', s).strip() for s in snippets[:3]])
    except: pass
    return ""

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
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            result = res.json()
            return "".join([sentence[0] for sentence in result[0] if sentence[0]]).strip()
    except: pass
    return text

def download_scene_sfx(scene_text, u_id, idx):
    text = scene_text.lower()
    sfx_url = None
    if any(k in text for k in ["rain", "storm", "بارش", "طوفان"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/rain-07.mp3"
    elif any(k in text for k in ["sword", "fight", "تلوار", "جنگ"]):
        sfx_url = "https://www.soundjay.com/mechanical/sounds/cutlery-clink-1.mp3"
    elif any(k in text for k in ["forest", "birds", "جنگل", "پرندے"]):
        sfx_url = "https://www.soundjay.com/nature/sounds/forest-wind-1.mp3"
    if sfx_url:
        fn = f"sfx_{u_id}_{idx}.mp3"
        try:
            r = session.get(sfx_url, timeout=10)
            if r.status_code == 200:
                with open(fn, "wb") as f: f.write(r.content)
                return fn
        except: pass
    return None

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

# ================= EDGE-TTS VOICE (CLEAN ASYNC - NO NEST_ASYNCIO) =================
def save_audio_safe(text, voice, rate, pitch, filename):
    async def _tts_exec():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(_tts_exec())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except:
        return False

# ================= REAL 5-SECOND MOTION VIDEO ENGINE =================
def generate_real_motion_clip(prompt, audio_path, out_clip_path, w, h, seed=786, video_model="wan-fast", api_key=""):
    aspect = "16:9" if w > h else "9:16"
    motion_prompt = f"high cinematic action motion, dynamic movement, lively walking, realistic physics, {prompt}"
    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt[:380])}?model={video_model}&aspectRatio={aspect}&duration=5&seed={seed}"
    if api_key: vid_url += f"&key={api_key}"
    
    temp_raw = out_clip_path.replace(".mp4", "_raw.mp4")
    success = False
    for attempt in range(2):
        try:
            r = session.get(vid_url, timeout=60)
            if r.status_code == 200 and len(r.content) > 40000:
                with open(temp_raw, "wb") as f: f.write(r.content)
                success = True
                break
        except: time.sleep(1)

    if success and os.path.exists(temp_raw):
        try:
            a_clip = AudioFileClip(audio_path)
            target_dur = a_clip.duration
            v_clip = VideoFileClip(temp_raw).resize((w, h))

            if v_clip.duration < target_dur:
                loops = int(np.ceil(target_dur / v_clip.duration))
                v_clip = concatenate_videoclips([v_clip] * loops)

            final_clip = v_clip.subclip(0, target_dur).set_audio(a_clip.volumex(1.2))
            final_clip.write_videofile(out_clip_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
            
            final_clip.close()
            v_clip.close()
            a_clip.close()
            if os.path.exists(temp_raw): os.remove(temp_raw)
            return True
        except: pass
    if os.path.exists(temp_raw): os.remove(temp_raw)
    return False

def generate_dynamic_photo_clip(prompt, audio_path, out_clip_path, w, h, seed, style):
    img_p = out_clip_path.replace(".mp4", ".png")
    img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
    try:
        r = session.get(img_url, timeout=25)
        if r.status_code == 200:
            with open(img_p, "wb") as f: f.write(r.content)
    except:
        Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_p, "PNG")

    scale_factor = 1.15
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_scaled = img_p.replace(".png", "_scaled.png")
    try:
        with Image.open(img_p) as im:
            im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_scaled, "PNG")
    except: temp_scaled = img_p

    try:
        a_clip = AudioFileClip(audio_path)
        dur = a_clip.duration
        clip = ImageClip(temp_scaled).set_duration(dur).set_fps(24)
        animated = clip.set_position(lambda t: (int((w - cw) * (t / dur)), 'center'))
        comp = CompositeVideoClip([animated], size=(w, h)).set_duration(dur).set_audio(a_clip.volumex(1.2))
        comp.write_videofile(out_clip_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
        comp.close()
        a_clip.close()
        clip.close()
    except: pass
    for f in [img_p, temp_scaled]:
        if os.path.exists(f): os.remove(f)

# ================= MASTER MOVIE PIPELINE (REAL MOTION + LOCKED CHARACTER) =================
def create_cinematic_v40(story, voice_gen, rate_val, pitch_val, ratio, style, seed, char_anchor="", enable_watermark=True, enable_bg_music=True, video_model="wan-fast"):
    if not MOVIEPY_AVAILABLE: return "MoviePy missing"
    u_id = str(uuid.uuid4())[:8]

    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()

        sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        total_scenes = len(sentences)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)

        scene_clips = []
        temp_files_to_clean = []

        c_anchor = char_anchor.strip() if char_anchor.strip() else "consistent protagonist character, detailed features, cohesive outfit"

        try:
            for idx, scene in enumerate(sentences):
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: آواز اور 5 سیکنڈ متحرک ویڈیو کی تشکیل...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(scene, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                trans = translate_ur_to_en_enhanced(scene)
                prompt = f"{c_anchor}, {trans}, visual style: {style}, 8k resolution, sharp focus, cinematic motion"

                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                success = generate_real_motion_clip(prompt, sub_audio, clip_mp4, w, h, seed=seed, video_model=video_model)
                if not success or not os.path.exists(clip_mp4):
                    generate_dynamic_photo_clip(prompt, sub_audio, clip_mp4, w, h, seed=seed, style=style)

                if os.path.exists(clip_mp4):
                    scene_clips.append(VideoFileClip(clip_mp4))

            if not scene_clips: raise Exception("No video clips generated.")

            progress_bar.progress(0.85)
            status.info("🎞️ تمام متحرک کلپس کو جوڑا جا رہا ہے اور بیک گراؤنڈ میوزک ڈک کیا جا رہا ہے...")

            final_video = concatenate_videoclips(scene_clips, method="compose")

            if enable_bg_music:
                bg_m = get_cached_bg_music(False, True)
                if bg_m and os.path.exists(bg_m):
                    try:
                        bg_track = AudioFileClip(bg_m).volumex(0.04).set_duration(final_video.duration)
                        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                    except: pass

            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)

            final_video.close()
            for c in scene_clips: c.close()
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass

            progress_bar.progress(1.0)
            status.success("🚀 متحرک سینیمیٹک مووی کامیابی سے تیار ہو گئی!")
            deduct_user_credits(st.session_state.logged_in_user, 15)
            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
            return f"Error: {e}"

# ================= UI & STYLING =================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;800&display=swap');
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 1.3rem !important; font-weight: 700 !important; color: #1e3a8a !important; text-align: center; }
    .dashboard-header { display: flex; justify-content: center; align-items: center; gap: 15px; margin: 15px 0; }
    .circular-s { width: 50px; height: 50px; background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #2563eb; animation: rotateSpins 10s infinite linear; }
    .metallic-s { font-family: 'Orbitron'; font-size: 28px; font-weight: 900; color: #2563eb; }
    @keyframes rotateSpins { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .stButton>button, .stFormSubmitButton>button { background: linear-gradient(90deg, #2563eb, #1d4ed8) !important; color: white !important; font-size: 19px !important; border-radius: 10px !important; }
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

# 1. Sign-In Tab
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
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                                 (u_name.strip().lower(), u_email.strip().lower(), hash_password(p_word), time.strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Account created successfully!")
                except: st.error("Username or email already exists.")
                finally: conn.close()

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

# 3. Pro Movie Studio (All Voice Pitch/Speed + Character Anchor + Full Story)
with tab_movie:
    st.write("### 🎥 Movie Studio (Full Motion & Consistent Characters)")
    m_script = st.text_area("کہانی یا مکمل اسکرپٹ یہاں درج کریں (Urdu / English):", height=150, placeholder="ایک خوبصورت مہم جوئی کی کہانی جو جنگل کے اس پار شروع ہوتی ہے...")
    c_anchor_input = st.text_input("کردار کا فکسڈ اینکر (Consistent Character DNA):", placeholder="مثلاً: A brave young prince wearing green royal robes with sharp eyes")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6, c7 = st.columns(3)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Realistic HD", "3D Cartoon", "Cinematic Hollywood", "Anime Art", "Dark Gothic / Mystery"])
    with c6: video_engine = st.selectbox("ویڈیو موشن ماڈل:", ["wan-fast", "seedance", "veo"])
    with c7: sd = st.number_input("فکسڈ سیڈ (Character Seed):", value=786)

    voice_map = {
        "Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
        "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural",
        "Arabic Egypt Male (Shakir)": "ar-EG-ShakirNeural", "Persian Male (Farid)": "fa-IR-FaridNeural"
    }
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے اسکرپٹ درج کریں!")
        else:
            with st.spinner("🎬 5، 5 سیکنڈ کے متحرک ویڈیو کلپس اور آڈیو تیار ہو رہے ہیں..."):
                v_res = create_cinematic_v40(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    char_anchor=c_anchor_input, enable_bg_music=st.session_state.enable_bg_music,
                    video_model=video_engine
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 4. Pro Image Studio
with tab_image:
    st.write("### 🎨 Visual Studio")
    p_i = st.text_area("تصویر کی تفصیل درج کریں:", height=100)
    canva_overlay_text = st.text_input("Canva Text Overlay:", placeholder="e.g. Movie Poster Title")
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

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
