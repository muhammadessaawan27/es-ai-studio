import sys
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
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import threading
import sqlite3
import hashlib
import json

try:
    import nest_asyncio
    nest_asyncio.apply()
except:
    pass

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except Exception as e:
    MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"})

st.set_page_config(page_title="Sglowina AI - Enterprise Studio", layout="wide", page_icon="🎬")

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

def hash_password(password):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(password, hashed):
    salt = b"sglowina_saas_salt_1234"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == hashed

def get_db():
    conn = sqlite3.connect("sglowina_v2.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, plan TEXT DEFAULT 'Free', credits INTEGER DEFAULT 50
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS local_payments (
        id TEXT PRIMARY KEY, username TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Pending'
    )""")
    # Founders Admin Setup: Muhammad Essa Awan & Saba Wahid
    h_admin = hash_password("786")
    for adm in ["muhammad_essa_awan", "saba_wahid"]:
        c.execute("INSERT OR IGNORE INTO users (username, password_hash, plan, credits) VALUES (?, ?, 'Enterprise', 5000)", (adm, h_admin))
    conn.commit()
    conn.close()

init_db()

# Safe Missing Functions
def burn_subtitles_to_image(img_path, subtitle_text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            w, h = im.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            bar_height = int(h * 0.14)
            draw.rectangle([(0, h - bar_height), (w, h)], fill=(0, 0, 0, 160))
            clean_sub = subtitle_text[:90]
            try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.04))
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
            draw.rectangle([(int(w * 0.1), int(h * 0.1)), (int(w * 0.9), int(h * 0.22))], fill=(37, 99, 235, 200))
            draw.text((w // 2, int(h * 0.16)), overlay_text, font=font, fill=(255, 255, 255, 255), anchor="mm")
            Image.alpha_composite(im, overlay).convert("RGB").save(img_path, "PNG")
    except: pass

def translate_ur_to_en(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            return "".join([s[0] for s in res.json()[0] if s[0]]).strip()
    except: pass
    return text

def apply_camera_motion_v40(img_path, motion, duration, w, h):
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
        else:
            animated = clip.set_position('center')
        return CompositeVideoClip([animated], size=(w, h)).set_duration(duration)
    except:
        return ImageClip(img_path).set_duration(duration)

def save_audio_safe(text, voice, rate, pitch, filename):
    async def amain():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(amain())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except: return False

def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, camera_motion="AI Hollywood Director (Auto)"):
    if not MOVIEPY_AVAILABLE: return "MoviePy library missing."
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
        
        clips, temp_files = [], []
        try:
            for i, scene in enumerate(sentences):
                status.info(f"🎬 منظر {i+1} از {total_scenes}: آواز اور ویژول سنکرونائزیشن...")
                progress_bar.progress((i / total_scenes) * 0.8)
                
                sub_audio = f"a_{u_id}_{i}.mp3"
                if not save_audio_safe(scene, voice_gen, rate, pitch, sub_audio): continue
                temp_files.append(sub_audio)
                a_clip = AudioFileClip(sub_audio)
                dur = a_clip.duration
                
                trans = translate_ur_to_en(scene)
                p_text = f"{trans}, visual style: {style}, highly detailed cinematic frame, 8k, sharp focus"
                img_p = f"img_{u_id}_{i}.png"
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_text[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
                
                try:
                    res = session.get(img_url, timeout=25)
                    if res.status_code == 200:
                        with open(img_p, "wb") as f: f.write(res.content)
                except:
                    Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_p, "PNG")
                temp_files.append(img_p)
                
                c_motion = "Pan Left" if i % 2 == 0 else "Pan Right"
                clip = apply_camera_motion_v40(img_p, c_motion, dur, w, h)
                clip = clip.set_audio(a_clip.volumex(1.2))
                clips.append(clip)

            progress_bar.progress(0.85)
            status.info("🎞️ ویڈیو تیار ہو رہی ہے...")
            final_video = concatenate_videoclips(clips, method="compose")
            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
            
            final_video.close()
            for c in clips: c.close()
            for f in temp_files:
                try: os.remove(f)
                except: pass
                
            progress_bar.progress(1.0)
            status.success("🚀 ویڈیو کامیابی سے تیار ہو گئی!")
            return out_name
        except Exception as e:
            return f"Error: {e}"

# Dashboard UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;800&display=swap');
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 1.4rem !important; font-weight: 700 !important; color: #1e3a8a !important; text-align: center; }
    .stButton>button { background: linear-gradient(90deg, #2563eb, #1d4ed8) !important; color: white !important; font-size: 18px !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='glow-title'>🎬 Sglowina AI - Enterprise Studio</h1>", unsafe_allow_html=True)

tab_movie, tab_image, tab_billing = st.tabs(["🎬 Pro Movie Studio", "🎨 Pro Image Studio", "👤 Founders & Billing"])

with tab_movie:
    st.write("### 🎥 Movie Generator")
    m_script = st.text_area("کہانی درج کریں (Urdu / English):", height=140, placeholder="ایک خوبصورت مہم جوئی کی کہانی...")
    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز:", ["ur-PK-AsadNeural", "ur-PK-UzmaNeural", "en-US-GuyNeural", "en-US-JennyNeural"])
    with c2: mr = st.selectbox("سائز:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("اسٹائل:", ["Realistic HD", "Cinematic Hollywood", "3D Cartoon", "Anime Art"])
    with c4: sd = st.number_input("سیڈ (Character Seed):", value=786)

    if st.button("Generate Master Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے اسکرپٹ لکھو!")
        else:
            with st.spinner("ویڈیو رینڈر ہو رہی ہے..."):
                v_res = create_cinematic_v40(m_script, mv, "+0%", "+0Hz", mr, ms, int(sd))
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

with tab_image:
    st.write("### 🎨 Visual Studio")
    p_i = st.text_area("تصویر کی تفصیل لکھیں:", height=100)
    if st.button("Generate Image 🚀"):
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i)}?width=1280&height=720&nologo=true&model=flux"
        r = session.get(img_url)
        if r.status_code == 200: st.image(r.content)

with tab_billing:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders:** Muhammad Essa Awan & Saba Wahid")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
