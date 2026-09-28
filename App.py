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
# 1. MOVIEPY UNIVERSAL COMPATIBILITY ENGINE
# ==========================================
try:
    import moviepy.editor as mp
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    import moviepy as mp
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

def safe_duration(clip, dur):
    if hasattr(clip, "set_duration"):
        return clip.set_duration(dur)
    elif hasattr(clip, "with_duration"):
        return clip.with_duration(dur)
    clip.duration = dur
    return clip

def safe_fps(clip, fps):
    if hasattr(clip, "set_fps"):
        return clip.set_fps(fps)
    elif hasattr(clip, "with_fps"):
        return clip.with_fps(fps)
    clip.fps = fps
    return clip

def safe_position(clip, pos):
    if hasattr(clip, "set_position"):
        return clip.set_position(pos)
    elif hasattr(clip, "with_position"):
        return clip.with_position(pos)
    return clip

def safe_audio(clip, audio):
    if hasattr(clip, "set_audio"):
        return clip.set_audio(audio)
    elif hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    clip.audio = audio
    return clip

def safe_resize(clip, size_or_func):
    if hasattr(clip, "resize"):
        return clip.resize(size_or_func)
    elif hasattr(clip, "resized"):
        return clip.resized(size_or_func)
    return clip

def safe_volume(audio_clip, factor):
    if hasattr(audio_clip, "volumex"):
        return audio_clip.volumex(factor)
    elif hasattr(audio_clip, "multiply_volume"):
        return audio_clip.multiply_volume(factor)
    return audio_clip

def safe_fadein(clip, duration):
    if hasattr(clip, "fadein"):
        return clip.fadein(duration)
    elif hasattr(clip, "with_effects"):
        try:
            from moviepy.video.fx import FadeIn
            return clip.with_effects([FadeIn(duration)])
        except Exception:
            pass
    return clip

def safe_fadeout(clip, duration):
    if hasattr(clip, "fadeout"):
        return clip.fadeout(duration)
    elif hasattr(clip, "with_effects"):
        try:
            from moviepy.video.fx import FadeOut
            return clip.with_effects([FadeOut(duration)])
        except Exception:
            pass
    return clip

# ==========================================
# 2. SESSION & BROWSER STABILITY HEADERS
# ==========================================
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
session = requests.Session()
session.headers.update(headers_browser)

SGLOWINA_BIO = (
    "Sglowina AI V5.0 is an enterprise-grade AI production platform, proudly developed by "
    "Muhammad Essa Awan & Saba Wahid."
)

st.set_page_config(page_title="Sglowina AI - SaaS Enterprise V5.0", layout="wide", page_icon="🎬")

if "enable_watermark" not in st.session_state:
    st.session_state.enable_watermark = True
if "enable_bg_music" not in st.session_state:
    st.session_state.enable_bg_music = True
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = "demo_user"
if "msgs" not in st.session_state:
    st.session_state.msgs = []

st.sidebar.subheader("🎬 Global Studio Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=st.session_state.enable_watermark)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Audio", value=st.session_state.enable_bg_music)

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

def burn_viral_subtitles(img_path, caption_text, is_vertical=True):
    try:
        if not os.path.exists(img_path) or not caption_text.strip():
            return
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            txt_layer = Image.new("RGBA", im.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            font_size = max(26, int(im.width / (20 if is_vertical else 30)))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            words = caption_text.strip().split()
            lines = []
            curr_line = []
            max_words_per_line = 5 if is_vertical else 9
            
            for w in words:
                curr_line.append(w)
                if len(curr_line) >= max_words_per_line:
                    lines.append(" ".join(curr_line))
                    curr_line = []
            if curr_line:
                lines.append(" ".join(curr_line))
                
            full_text = "\n".join(lines)
            bbox = draw.multiline_textbbox((0, 0), full_text, font=font, align="center")
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            x = (im.width - text_w) // 2
            y = int(im.height * 0.72) if is_vertical else (im.height - text_h - 50)
            
            pad = 18
            draw.rounded_rectangle(
                [(x - pad, y - pad), (x + text_w + pad, y + text_h + pad)],
                radius=14,
                fill=(0, 0, 0, 180),
                outline=(245, 158, 11, 220),
                width=2
            )
            
            draw.multiline_text((x, y), full_text, font=font, fill=(255, 255, 255, 255), align="center")
            combined = Image.alpha_composite(im, txt_layer).convert("RGB")
            combined.save(img_path, "JPEG")
    except Exception:
        pass

# ==========================================
# 3. DATABASE & PERSISTENCE LAYER
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
    for adm, mail in [("essasaba", "essasaba@sglowina.ai"), ("essa_awan", "essa@sglowina.ai")]:
        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = ?", (adm,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (adm, mail, h_admin, "Enterprise", 5000, "Admin", "2026-07-21"))
        else:
            cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = ?", (h_admin, adm))
                       
    h_saba = hash_password("1234")
    cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'saba_wahid'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, password_hash, plan, credits, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ("saba_wahid", "saba@sglowina.ai", h_saba, "Enterprise", 5000, "Admin", "2026-07-21"))
    else:
        cursor.execute("UPDATE users SET password_hash = ?, plan = 'Enterprise', role = 'Admin' WHERE LOWER(username) = ?", (h_saba,))
                       
    conn.commit()
    conn.close()

init_db_v21()

# ==========================================
# 4. AUTH & USAGE HELPERS
# ==========================================
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

def translate_ur_to_en_enhanced(text):
    try:
        instruction = "Translate this Urdu story scene into an English visual prompt for AI video. Output ONLY the visual prompt."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction + ' ' + text)}?model=openai"
        res = session.get(url, timeout=12)
        if res.status_code == 200 and len(res.text) > 5:
            return res.text.strip()
    except Exception:
        pass
    return text

def apply_islamic_safety_filter(scene_text_en, scene_text_ur):
    combined_text = (scene_text_en + " " + scene_text_ur).lower()
    spiritual_keywords = [
        "prophet", "sahaba", "saint", "angel", "god", "allah", "messenger", "nooh", "musa", "isa", "ibrahim", "yousuf", "muhammad", 
        "نبی", "رسول", "صحابہ", "ولی", "اللہ", "فرشتہ", "جنت", "جہنم", "قبر", "غوث", "قطب", "امام"
    ]
    if any(k in combined_text for k in spiritual_keywords):
        safe_prompt = (
            "Cinematic spiritual scenery, divine volumetric glowing white and golden spiritual light emanating from the heavens, "
            "sacred light beam, peaceful glowing ancient background, majestic natural mountains. STRICTLY NO human faces, NO human figures."
        )
        return True, safe_prompt
    return False, scene_text_en

def generate_faceless_script(niche, topic, language):
    try:
        instruction = (
            f"You are a viral YouTube Shorts and TikTok content creator. Generate a 4-scene viral short video script about '{topic}' in the niche '{niche}'.\n"
            f"Language: {language}.\n"
            "Format your output strictly with 4 lines separated by newlines. Each line must be a single powerful narration sentence."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = session.get(url, timeout=15)
        if res.status_code == 200 and len(res.text) > 10:
            lines = [l.strip() for l in res.text.strip().split("\n") if len(l.strip()) > 5]
            if len(lines) >= 3:
                return lines[:4]
    except Exception:
        pass
    if language == "Urdu":
        return [
            f"کیا آپ جانتے ہیں کہ {topic} کے پیچھے کیا راز چھپا ہے؟",
            "تاریخ کے اوراق پلٹیں تو اس کے ایسے حیران کن حقائق ملتے ہیں جو ہوش اڑا دیتے ہیں۔",
            "اس کے بارے میں جاننے کے بعد لوگ حیران رہ گئے۔",
            "مزید ایسی پراسرار معلومات کے لیے ہمارے ساتھ جڑے رہیں۔"
        ]
    return [
        f"Did you know the incredible hidden truth behind {topic}?",
        "When we look into history, the shocking facts leave everyone speechless.",
        "Experts could hardly believe what they discovered.",
        "Follow for more mind-blowing daily facts!"
    ]

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
            res = session.get(url, timeout=35)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
        except Exception:
            pass
        try:
            im = Image.new("RGB", (1280, 720), color=(15, 23, 42))
            im.save(path, "JPEG")
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_single, urls[i], paths[i]) for i in range(len(urls))]
        concurrent.futures.wait(futures)

def apply_camera_motion_v40(img_path, motion_idx, duration, w, h):
    try:
        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_path, "JPEG")
            
        scale_factor = 1.25
        base_clip = safe_duration(ImageClip(img_path), duration)
        base_clip = safe_fps(base_clip, 24)
        cw, ch = int(w * scale_factor), int(h * scale_factor)
        clip = safe_resize(base_clip, (cw, ch))
        
        if motion_idx % 3 == 0:
            animated_clip = safe_position(safe_resize(clip, lambda t: 1.0 + 0.12 * (t / max(duration, 0.1))), 'center')
        elif motion_idx % 3 == 1:
            animated_clip = safe_position(clip, lambda t: (int((w - cw) * (t / max(duration, 0.1))), 'center'))
        else:
            animated_clip = safe_position(safe_resize(clip, lambda t: 1.12 - 0.12 * (t / max(duration, 0.1))), 'center')

        comp = CompositeVideoClip([animated_clip], size=(w, h))
        return safe_duration(comp, duration)
    except Exception:
        fallback = ImageClip(img_path)
        fallback = safe_duration(fallback, duration)
        return safe_resize(fallback, (w, h))

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
# 5. MASTER UNIVERSAL VIDEO RENDER ENGINE
# ==========================================
def render_master_video_pipeline(scenes_list, voice_code, ratio_choice, enable_subtitles=True, enable_bg=True, is_faceless=False):
    u_id = str(uuid.uuid4())[:8]
    
    global active_renderers
    with render_lock:
        active_renderers += 1
        my_pos = active_renderers
        
    status = st.empty()
    if my_pos > 2:
        status.info(f"⏳ Waiting in Queue... Position #{my_pos - 2}")
        
    with render_semaphore:
        with render_lock:
            active_renderers -= 1
            
        progress_bar = st.progress(0.0)
        bg_music_f = f"bg_{u_id}.mp3"
        generated_images = []
        generated_prompts = []
        temporary_audio_tracks = []
        has_bg_music = False
        
        user_db = get_user_data(st.session_state.logged_in_user)
        if not user_db:
            st.error("Please login to proceed.")
            return "Error"
        
        user_id = user_db["id"]
        if user_db["credits"] < 15:
            st.error("Insufficient credits: Sglowina requires at least 15 coins to render.")
            return "Error"
            
        try:
            progress_bar.progress(0.10)
            status.info("🎙️ Synthesizing Neural Voices (Edge-TTS)...")
            
            for idx, scene in enumerate(scenes_list):
                v_code = voice_code
                if "صبا" in scene.lower() or "saba" in scene.lower():
                    v_code = "ur-PK-UzmaNeural"
                elif "عیسی" in scene.lower() or "essa" in scene.lower():
                    v_code = "ur-PK-AsadNeural"
                    
                sub_audio = f"a_{u_id}_{idx}.mp3"
                save_audio_safe(scene, v_code, "+0%", "+0Hz", sub_audio)
                temporary_audio_tracks.append(sub_audio)
                
            progress_bar.progress(0.25)
            if enable_bg:
                status.info("🎵 Mixing Atmospheric Soundtracks...")
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                try:
                    res_bg = session.get(bg_url, timeout=8)
                    if res_bg.status_code == 200:
                        with open(bg_music_f, 'wb') as f:
                            f.write(res_bg.content)
                        has_bg_music = True
                except Exception:
                    pass
                    
            res_map = {
                "TikTok/Reels (9:16)": (720, 1280),
                "YouTube (16:9)": (1280, 720),
                "Instagram (1:1)": (720, 720)
            }
            w, h = res_map.get(ratio_choice, (720, 1280) if is_faceless else (1280, 720))
            w, h = make_even(w), make_even(h)
            is_vertical = (h > w)
            
            flux_prompt_urls = []
            img_paths = []
            
            for i, scene in enumerate(scenes_list):
                en_prompt = translate_ur_to_en_enhanced(scene)
                generated_prompts.append(en_prompt)
                
                w_t, h_t = make_even(w * 1.2), make_even(h * 1.2)
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(en_prompt + ', 8k cinematic hyperrealistic') }?width={w_t}&height={h_t}&seed={random.randint(1,99999)}&nologo=true&model=flux"
                flux_prompt_urls.append(img_url)
                
                img_p = f"i_{u_id}_{i}.jpg"
                img_paths.append(img_p)
                generated_images.append(img_p)
                
            progress_bar.progress(0.45)
            status.info("🎨 Rendering Photorealistic Cinematic Visuals...")
            parallel_download_flux_images(flux_prompt_urls, img_paths)
            
            progress_bar.progress(0.70)
            status.info("🎞️ Stitching Motion Frames & Viral Subtitles...")
            
            clips = []
            for i, scene in enumerate(scenes_list):
                img_p = img_paths[i]
                sub_audio = temporary_audio_tracks[i]
                
                if enable_subtitles:
                    burn_viral_subtitles(img_p, scene, is_vertical=is_vertical)
                apply_blurred_background_padding(img_p, make_even(w * 1.2), make_even(h * 1.2))
                
                voice_clip = AudioFileClip(sub_audio)
                dur = max(voice_clip.duration, 1.8)
                
                anim_clip = apply_camera_motion_v40(img_p, i, dur, w, h)
                anim_clip = safe_audio(anim_clip, voice_clip)
                anim_clip = safe_fadeout(safe_fadein(anim_clip, 0.25), 0.25)
                clips.append(anim_clip)
                
            progress_bar.progress(0.88)
            status.info("🚀 Assembling Master Render MP4...")
            
            final_video = concatenate_videoclips(clips, method="compose")
            final_video = safe_resize(final_video, (w, h))
            
            if has_bg_music and os.path.exists(bg_music_f):
                try:
                    bg_clip = safe_volume(AudioFileClip(bg_music_f), 0.05)
                    bg_clip = safe_duration(bg_clip, final_video.duration)
                    final_video = safe_audio(final_video, CompositeAudioClip([final_video.audio, bg_clip]))
                except Exception:
                    pass
                    
            out_name = f"Sglowina_{u_id}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
            final_video.close()
            
            for f_tmp in temporary_audio_tracks + generated_images:
                if os.path.exists(f_tmp): os.remove(f_tmp)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            
            progress_bar.progress(1.0)
            status.success("🎉 Video Generated Successfully!")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (id, user_id, project_name, type, file_path, prompt, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (u_id, user_id, f"Video {u_id}", "Video", out_name, " | ".join(generated_prompts), time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            
            deduct_user_credits(st.session_state.logged_in_user, 15)
            log_credit_usage(user_id, "Video Generation", 15, user_db['credits'] - 15)
            return out_name
        except Exception as e:
            for f_tmp in temporary_audio_tracks + generated_images:
                if os.path.exists(f_tmp): os.remove(f_tmp)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            progress_bar.empty()
            return f"Error Details: {e}"
        finally:
            gc.collect()

# ==========================================
# 6. UI STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;900&display=swap');
    
    .stApp { background-color: #ffffff !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    .glow-title { 
        font-size: 2.2rem; font-weight: 900; text-align: center; font-family: 'Orbitron', sans-serif;
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 5px 0; letter-spacing: 2px;
    }
    .logo-container { display: flex; justify-content: center; align-items: center; padding: 5px 0; }
    .circular-s {
        width: 75px; height: 75px; 
        background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff) !important;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 34px; color: #ffffff !important;
        border: 3px solid #ffffff !important; box-shadow: 0 0 25px #ff007a;
    }
    .stButton>button { 
        background: #000000 !important; color: white !important; border-radius: 10px !important; 
        height: 50px; width: 100%; font-size: 18px; font-weight: bold; border: none; 
    }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="glow-title">SGLOWINA AI V5.0</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 7. NAVIGATION TABS
# ==========================================
tab_auth, tab_faceless, tab_movie, tab_companion, tab_chat, tab_image, tab_enterprise = st.tabs([
    "🔑 Sign In",
    "⚡ 1-Click Viral Shorts Factory",
    "🎬 Pro Movie Studio",
    "🧸 Live AR Vision",
    "💬 AI Chat",
    "🎨 HD Image Studio",
    "👤 Enterprise Center"
])

# -----------------
# TAB 1: AUTH
# -----------------
with tab_auth:
    st.write("### 🔑 Secure Authentication")
    auth_mode = st.radio("Choose Action", ["Sign In", "Register New Account"], horizontal=True)
    
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

# -----------------
# TAB 2: 1-CLICK VIRAL SHORTS FACTORY
# -----------------
with tab_faceless:
    st.write("### ⚡ 1-Click Automated Viral Faceless Shorts Generator")
    st.info("💡 صرف عنوان لکھیں، AI خودکار اسکرپٹ، نیورل وائس، 8K امیجز، اور ٹک ٹاک اسٹائل سب ٹائٹلز کے ساتھ پوری شارٹ ویڈیو تیار کرے گا!")
    
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_niche = st.selectbox("Select Niche (موضوع کی کیٹیگری):", [
            "Mysterious & Horror (پراسرار و خوفناک واقعات)",
            "Islamic & Historical (اسلامی و تاریخی کہانیاں)",
            "Mind-blowing Facts (حیرت انگیز سائنسی حقائق)",
            "Motivational & Life Advice (حوصلہ افزا اسباق)",
            "Tech & Future AI (ٹیکنالوجی اور مصنوعی ذہانت)"
        ])
    with fc2:
        f_lang = st.selectbox("Language (زبان):", ["Urdu", "English"])
    with fc3:
        f_voice = st.selectbox("Voice Actor:", [
            "ur-PK-AsadNeural (Urdu Male)", 
            "ur-PK-UzmaNeural (Urdu Female)",
            "en-US-ChristopherNeural (English Male)",
            "en-US-JennyNeural (English Female)"
        ])

    f_topic = st.text_input("Enter Topic / Concept (ویڈیو کا عنوان لکھیں):", placeholder="مثال: بحیرہ برمودا کا خوفناک سچ یا کائنات کے پراسرار سیارے")
    f_subtitles = st.checkbox("Burn TikTok-Style Glowing Subtitles (ویڈیو پر الفاظ لکھے جائیں) 🔤", value=True)
    
    if st.button("Generate 1-Click Viral Short 🚀"):
        if f_topic.strip():
            with st.spinner("⚡ AI is generating viral script, voice, visual frames, and subtitles..."):
                v_code_clean = f_voice.split(" ")[0]
                script_lines = generate_faceless_script(f_niche, f_topic, f_lang)
                v_out = render_master_video_pipeline(
                    scenes_list=script_lines,
                    voice_code=v_code_clean,
                    ratio_choice="TikTok/Reels (9:16)",
                    enable_subtitles=f_subtitles,
                    enable_bg=enable_bg_music,
                    is_faceless=True
                )
                if isinstance(v_out, str) and v_out.endswith(".mp4") and os.path.exists(v_out):
                    st.video(v_out)
                    st.download_button("Download Ready Short (9:16)", open(v_out, 'rb').read(), file_name=v_out)
                else:
                    st.error(v_out)
        else:
            st.warning("Please enter a topic.")

# -----------------
# TAB 3: PRO MOVIE STUDIO (MANUAL SCRIPT)
# -----------------
with tab_movie:
    st.write("### 🎬 Pro Master Studio (Full Manual Script)")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=130, placeholder="مثال: ایک کسان شام کے وقت ٹریکٹر چلا رہا تھا۔ اچانک آسمان پر گرج چمک شروع ہو گئی۔")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1: mv = st.selectbox("Voice:", ["ur-PK-AsadNeural (Male)", "ur-PK-UzmaNeural (Female)"])
    with col_v2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with col_v3: m_sub = st.checkbox("Include Text Overlay", value=True)
    
    if st.button("Generate Custom Movie 🎥"):
        if m_script.strip():
            with st.spinner("🎬 Rendering Custom Film..."):
                sentences = [s.strip() for s in re.split(r'[۔.!]', m_script) if len(s.strip()) > 3]
                if not sentences: sentences = [m_script]
                v_res = render_master_video_pipeline(
                    scenes_list=sentences,
                    voice_code=mv.split(" ")[0],
                    ratio_choice=mr,
                    enable_subtitles=m_sub,
                    enable_bg=enable_bg_music,
                    is_faceless=False
                )
                if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res):
                    st.video(v_res)
                    st.download_button("Download Movie MP4", open(v_res, 'rb').read(), file_name=v_res)
                else:
                    st.error(v_res)
        else:
            st.warning("Please enter a script.")

# -----------------
# TAB 4: LIVE AR COMPANION (MUSE AI) - VISION FIXED
# -----------------
with tab_companion:
    st.write("### 🧸 Live Camera AR Companion")
    viewport_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
            .viewport { width: 100%; max-width: 460px; height: 500px; background: #000; border-radius: 20px; position: relative; overflow: hidden; margin: 0 auto; border: 2px solid #f59e0b; }
            #video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
            .hud { position: absolute; top: 10px; left: 10px; right: 10px; display: flex; justify-content: space-between; z-index: 10; }
            .badge { background: rgba(0,0,0,0.8); color: #10b981; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; border: 1px solid #10b981; }
            .subs { position: absolute; bottom: 65px; left: 10px; right: 10px; background: rgba(15,23,42,0.92); color: #fff; padding: 10px 14px; border-radius: 12px; font-size: 14px; text-align: right; direction: rtl; z-index: 10; min-height: 45px; border: 1px solid #f59e0b; line-height: 1.4; }
            .controls { position: absolute; bottom: 10px; left: 10px; right: 10px; display: flex; gap: 8px; z-index: 20; }
            .btn { flex: 1; background: linear-gradient(45deg, #f59e0b, #ec4899); color: #000; border: none; padding: 10px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 13px; }
            .overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.9); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 30; }
        </style>
    </head>
    <body>
        <div class="viewport">
            <video id="video" autoplay playsinline></video>
            <div class="hud"><div class="badge" id="lbl">READY</div><div style="color:#f59e0b; font-weight:bold; font-size:12px;">🧸 MUSE AI</div></div>
            <div class="subs" id="sub">کیمرہ کھولیں اور بٹن دبائیں، میں دیکھ کر بولوں گا!</div>
            <div class="controls" id="ctrl" style="display:none;">
                <button class="btn" onclick="ask('اردو میں دیکھ کر بتاؤ یہ کیا ہے اور کیسا دکھتا ہے؟')">📸 دیکھ کر بتاؤ (اردو)</button>
                <button class="btn" onclick="ask('Describe what you see in concise English.')">🌐 In English</button>
            </div>
            <div class="overlay" id="startScr">
                <h3 style="color:#fff; margin-bottom:10px;">🧸 MUSE Live Vision</h3>
                <button class="btn" style="padding:12px 24px;" onclick="start()">🚀 کیمرہ شروع کریں</button>
            </div>
        </div>
        <canvas id="cvs" style="display:none;"></canvas>
        <script>
            let v = document.getElementById('video'), s = document.getElementById('startScr'), c = document.getElementById('ctrl'), sub = document.getElementById('sub'), lbl = document.getElementById('lbl');
            async function start() {
                try {
                    s.style.display = 'none'; c.style.display = 'flex';
                    let stm = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 640 }, audio: false });
                    v.srcObject = stm;
                    speak("السلام علیکم! کیمرہ تیار ہے، بٹن دبا کر جو مرضی پوچھیں۔");
                } catch(e){ alert("کیمرہ پرمیشن دیں: " + e.message); }
            }
            async function ask(p) {
                lbl.innerText = "SEEING..."; sub.innerText = "👀 دیکھ رہا ہوں، ایک لمحہ...";
                let cv = document.getElementById('cvs'); cv.width = v.videoWidth || 640; cv.height = v.videoHeight || 480;
                cv.getContext('2d').drawImage(v, 0, 0, cv.width, cv.height);
                let b64 = cv.toDataURL('image/jpeg', 0.8).split(',')[1];
                try {
                    let r = await fetch("https://text.pollinations.ai/openai", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            model: "openai-large", 
                            messages: [{ 
                                role: "user", 
                                content: [
                                    { type: "text", text: "You are looking at this camera snapshot. Describe directly in 2 natural sweet sentences in the requested language: " + p }, 
                                    { type: "image_url", image_url: { url: "data:image/jpeg;base64," + b64 } }
                                ] 
                            }] 
                        })
                    });
                    let data = await r.json();
                    let reply = "";
                    if (data && data.choices && data.choices[0] && data.choices[0].message) {
                        reply = data.choices[0].message.content;
                    } else if (typeof data === "string") {
                        reply = data;
                    } else {
                        reply = "میں نے منظر دیکھ لیا ہے لیکن وضاحت موصول نہیں ہو سکی۔";
                    }
                    reply = reply.replace(/<think>[\\s\\S]*?<\\/think>/g, '').trim();
                    sub.innerText = "🧸: " + reply; 
                    speak(reply);
                } catch(e) { 
                    sub.innerText = "ایرر: دوبارہ کوشش کریں۔"; 
                } finally { 
                    lbl.innerText = "READY"; 
                }
            }
            function speak(t) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utter = new SpeechSynthesisUtterance(t);
                    utter.lang = 'ur-PK';
                    utter.rate = 1.0;
                    window.speechSynthesis.speak(utter);
                }
            }
        </script>
    </body>
    </html>
    """
    st.components.v1.html(viewport_html, height=520)

# -----------------
# TAB 5: AI CHAT
# -----------------
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask anything..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai", timeout=12).text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# -----------------
# TAB 6: PRO IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image:", height=90)
    if st.button("Generate Visual 🚀"):
        u_db = get_user_data(st.session_state.logged_in_user)
        if u_db and u_db['credits'] >= 2:
            img_data = session.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1280&height=720&seed={random.randint(1,99999)}&nologo=true&model=flux", timeout=30).content
            if img_data:
                img_path_temp = f"temp_canvas.jpg"
                with open(img_path_temp, "wb") as f_temp:
                    f_temp.write(img_data)
                with Image.open(img_path_temp) as im:
                    st.image(im, caption=p_i[:35])
                if os.path.exists(img_path_temp): os.remove(img_path_temp)
                deduct_user_credits(st.session_state.logged_in_user, 2)
                log_credit_usage(u_db['id'], "Image Generation", 2, u_db['credits'] - 2)
        else:
            st.error("Insufficient credits (Requires 2 coins).")

# -----------------
# TAB 7: ENTERPRISE CENTER
# -----------------
with tab_enterprise:
    st.write("### 👤 Sglowina Enterprise Administration Center")
    u_db = get_user_data(st.session_state.logged_in_user)
    if u_db:
        st.info(f"User: **{st.session_state.logged_in_user}** | Plan: **{u_db['plan']}** | Available Balance: **{u_db['credits']}** 🪙")
        
        st.write("### 📱 Pakistani Local Payment Gateway")
        bcol1, bcol2 = st.columns(2)
        with bcol1: st.info("💚 **EasyPaisa Account**\n\n* **Name:** Saba Wahid\n* **Number:** 03086834020")
        with bcol2: st.warning("❤️ **JazzCash Account**\n\n* **Name:** Ayisha bi bi\n* **Number:** 03240755475")
            
        with st.form("local_payment_form"):
            p_method = st.selectbox("Payment Method Used:", ["EasyPaisa", "JazzCash"])
            p_trx_id = st.text_input("Enter Transaction ID (TrxID):")
            p_amount = st.number_input("Amount Sent (PKR):", min_value=500.0, value=1000.0, step=100.0)
            if st.form_submit_button("Submit Payment Proof 🚀"):
                if p_trx_id.strip():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO local_payments (id, username, method, trx_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                       (str(uuid.uuid4())[:8], u_db['username'], p_method, p_trx_id.strip(), p_amount, 'Pending', time.strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.success("Payment submitted! Administrator will verify and credit your coins.")
                    except sqlite3.IntegrityError:
                        st.error("This TrxID has already been submitted.")
                    finally:
                        conn.close()
    else:
        st.warning("Please sign in first.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI V5.0 Full Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
