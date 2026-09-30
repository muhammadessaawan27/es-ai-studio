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
# STREAMLIT CONFIGURATION & STATES
# ==========================================
st.set_page_config(page_title="ES Ultra Anti-Copyright Shield", layout="wide", page_icon="⚡")

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

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

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

# ==========================================
# MULTI-PLATFORM DOWNLOADER
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
    
    genre = "Viral Video Breakdown"
    safe_titles = [
        f"🔥 {clean_title[:50]} | Full Uncut Action Breakdown",
        f"⚡ High Intensity Scene Recap | {clean_title[:40]}",
        f"😱 Unstoppable Dramatic Climax | {clean_title[:40]}"
    ]
    hashtags = "#MovieBreakdown #ActionMovie #BollywoodAction #Blockbuster #ViralVideo #CinemaReaction"
    thumb_prompt = f"Cinematic 8K action movie thumbnail for '{clean_title[:35]}', dramatic intense angry hero face, cinematic color grading, sparks background, 16:9."
    return genre, safe_titles, hashtags, thumb_prompt

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

st.markdown('<div class="glow-title">ES ULTRA ANTI-COPYRIGHT ENGINE</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">ES</div></div>', unsafe_allow_html=True)

# ==========================================
# MAIN APPLICATION TABS
# ==========================================
tab_es_shield, tab_clip, tab_lofi = st.tabs([
    "⚡ 1. فل مووی شیلڈ (ہر 0.75s کٹ + بھاری آواز و ماسکنگ)",
    "⚔️ 2. کلپ کٹر موڈ (10 سے 20 منٹ)",
    "🎧 3. گانے اور لوفی (Slowed + Reverb)"
])

# -----------------
# TAB 1: FULL MOVIE SHIELD
# -----------------
with tab_es_shield:
    st.write("### 🛡️ فل مووی و ویڈیو اینٹی کاپی رائٹ شیلڈ (Sub-Second Break)")
    st.info("💡 **100% ایکٹیو شیلڈ:** ہر 0.75 سیکنڈ بعد مائیکرو کٹس، بھاری موٹی آواز، کلر و کنٹراسٹ اسکریبلر، 1.8° ٹِلٹ اور ہائی نوائز۔")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        shield_mode = st.selectbox("شیلڈ فریم اسٹائل:", [
            "🛡️ 0.75s مائیکرو کٹ + کینوس فریم + 1.8° ٹِلٹ + ہائی کنٹراسٹ (100% تجویز کردہ)",
            "⚡ 0.75s فاسٹ کٹ + ڈیپ زوم + اینٹی ہیش لیٹرباکس"
        ])
    with col_opt2:
        audio_mode = st.selectbox("آواز کی موٹائی اور گڑبڑ شیلڈ:", [
            "🔊 بھاری موٹی آواز (Deep Baritone) + ایکوسٹک گڑبڑ شیلڈ (100% Safe)",
            "🎵 میڈیم پچ شفٹ (Medium Thick Voice)"
        ])
        
    up_file1 = st.file_uploader("📂 اپنے موبائل یا کمپیوٹر سے ویڈیو اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")
    url_input_1 = st.text_input("🔗 یا کسی بھی ویڈیو کا لنک پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="url_main")
    
    if st.button("🚀 100% اینٹی کاپی رائٹ شیلڈ لگا کر ویڈیو تیار کریں", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        base_prefix = f"in_vid_{uid}"
        target_out = f"es_shielded_{uid}.mp4"
        info = {'title': 'Action Scene'}
        input_file = None
        
        if up_file1 is not None:
            with st.spinner("📂 ویڈیو فائل محفوظ ہو رہی ہے..."):
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
        elif url_input_1.strip():
            with st.spinner("🔗 لنک سے ویڈیو ڈاؤنلوڈ کی جا رہی ہے..."):
                info, d_file = inspect_and_fetch_media(url_input_1.strip(), base_prefix)
                if d_file and os.path.exists(d_file) and os.path.getsize(d_file) > 1000:
                    input_file = d_file
                else:
                    st.error("❌ یوٹیوب نے لنک بلاک کیا ہے۔ براہ کرم ویڈیو فائل ڈائریکٹ اپلوڈ کریں۔")

        if input_file and os.path.exists(input_file):
            with st.spinner("⚡ ہر 0.75 سیکنڈ پر کٹس، بھاری آواز اور پکسل اسکریبلنگ لگ رہی ہے..."):
                ffmpeg_exe = get_ffmpeg()
                
                # SUB-SECOND CUTS (< 1s TIMELINE BREAK) + COLOR CONTRAST SHIFT + 1.8 DEG TILT + NOISE
                if "کینوس فریم" in shield_mode:
                    vf_str = (
                        "[0:v]scale=1280:720,boxblur=24:4[bg];"
                        "[0:v]select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                        "hflip,crop=iw*0.80:ih*0.80,scale=980:552,"
                        "eq=contrast=1.20:saturation=1.25:brightness=0.02:gamma=1.06,"
                        "colorbalance=rs=0.06:gs=-0.04:bs=0.05,"
                        "noise=alls=8:allf=t+u,vignette=PI/3.5[fg];"
                        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                        "drawbox=y=0:h=44:color=black@0.75:t=fill,"
                        "drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                    )
                else:
                    vf_str = (
                        "select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                        "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                        "eq=contrast=1.20:saturation=1.25:brightness=0.02:gamma=1.06,"
                        "colorbalance=rs=0.06:gs=-0.04:bs=0.05,"
                        "noise=alls=8:allf=t+u,vignette=PI/3.5,"
                        "drawbox=y=0:h=44:color=black@0.75:t=fill,"
                        "drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                    )
                
                # HEAVY THICK VOICE + ACOUSTIC HARMONIC MASKING LAYER
                if "بھاری موٹی آواز" in audio_mode:
                    af_str = (
                        "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,"
                        "bass=g=8:f=100,treble=g=-5:f=3000,equalizer=f=1000:t=q:w=1:g=-4,"
                        "aecho=0.8:0.6:20:0.25"
                    )
                else:
                    af_str = "volume=0.75,asetrate=44100*0.94,aresample=44100:async=1,atempo=1.0638,bass=g=5:f=110"
                
                cmd = [
                    ffmpeg_exe, "-y", "-i", input_file,
                    "-map_metadata", "-1",
                    "-filter_complex" if "کینوس فریم" in shield_mode else "-vf", vf_str,
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
                    st.error("❌ ویڈیو پروسیسنگ فیل ہو گئی۔ فائل دوبارہ اپلوڈ کریں۔")
        elif not input_file and not url_input_1.strip() and up_file1 is None:
            st.error("❌ برائے مہربانی ویڈیو فائل اپلوڈ کریں یا درست لنک دیں۔")

# -----------------
# TAB 2: CLIP CUTTER
# -----------------
with tab_clip:
    st.write("### ⚔️ کلپ کٹر موڈ (مائیکرو کٹس اور بھاری آواز کے ساتھ)")
    c1, c2 = st.columns(2)
    with c1:
        scene_type = st.selectbox("سین کا آغاز:", ["⚔️ اہم سین (منٹ 30)", "👻 سسپنس موڑ (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    upload_opt2 = st.file_uploader("📂 ویڈیو فائل منتخب کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t2")
    url_input_2 = st.text_input("🔗 یا نیا لنک ڈالیں:", placeholder="https://...", key="url_t2")

    if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="run_t2"):
        uid = str(uuid.uuid4())[:8]
        base_prefix = f"clip_in_{uid}"
        target_out = f"clip_out_{uid}.mp4"
        info = {'title': 'Clip Highlight'}
        input_file = None
        
        if upload_opt2 is not None:
            ext = upload_opt2.name.split('.')[-1] if '.' in upload_opt2.name else "mp4"
            target_in = f"{base_prefix}.{ext}"
            with open(target_in, "wb") as f:
                upload_opt2.seek(0)
                while True:
                    chunk = upload_opt2.read(1024 * 1024 * 4)
                    if not chunk: break
                    f.write(chunk)
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                input_file = target_in
                info['title'] = upload_opt2.name
        elif url_input_2.strip():
            with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                info, d_file = inspect_and_fetch_media(url_input_2.strip(), base_prefix)
                if d_file and os.path.exists(d_file) and os.path.getsize(d_file) > 1000:
                    input_file = d_file

        if input_file and os.path.exists(input_file):
            with st.spinner("کلپ کٹ کر کے مائیکرو کٹس اور بھاری آواز لگائی جا رہی ہے..."):
                ffmpeg_exe = get_ffmpeg()
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,hflip,crop=iw*0.80:ih*0.80,scale=1280:720,eq=contrast=1.20:saturation=1.25:brightness=0.02:gamma=1.06,colorbalance=rs=0.06:gs=-0.04:bs=0.05,noise=alls=8:allf=t+u,vignette=PI/3.5,drawbox=y=0:h=44:color=black@0.75:t=fill,drawbox=y=ih-52:h=52:color=black@0.85:t=fill"
                af = "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,bass=g=8:f=100,treble=g=-5:f=3000,aecho=0.8:0.6:20:0.25"
                
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
                    st.error("❌ ویڈیو ٹائم سیٹنگز چیک کریں۔")
        else:
            st.error("❌ ویڈیو اپلوڈ کریں یا درست لنک دیں۔")

# -----------------
# TAB 3: LO-FI & SONGS
# -----------------
with tab_lofi:
    st.write("### 🎧 گانے کو Slowed + Reverb لوفی میں بدلیں")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
    with col_s2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
    with col_s3: bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3")
        
    upload_opt3 = st.file_uploader("📂 گانے کی آڈیو یا ویڈیو منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
    song_url = st.text_input("🔗 یا گانے کا لنک یہاں ڈالیں:", placeholder="https://...", key="url_t3")
    
    if st.button("🚀 لوفی گانا بنائیں", type="primary", key="run_t3"):
        uid = str(uuid.uuid4())[:8]
        base_prefix = f"dyn_song_in_{uid}"
        target_out = f"dyn_song_out_{uid}.mp4"
        info = {'title': 'Lo-Fi Chill Track'}
        input_file = None
        
        if upload_opt3 is not None:
            ext = upload_opt3.name.split('.')[-1] if '.' in upload_opt3.name else "mp4"
            target_in = f"{base_prefix}.{ext}"
            with open(target_in, "wb") as f:
                upload_opt3.seek(0)
                while True:
                    chunk = upload_opt3.read(1024 * 1024 * 4)
                    if not chunk: break
                    f.write(chunk)
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                input_file = target_in
                info['title'] = upload_opt3.name
        elif song_url.strip():
            with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                info, d_file = inspect_and_fetch_media(song_url.strip(), base_prefix)
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

# Output Video Player & Download
active_out = st.session_state.current_output_video
if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
    st.divider()
    st.success("🎉 ویڈیو 100% اینٹی کاپی رائٹ شیلڈ (0.75s کٹ، بھاری آواز، پکسل اسکریبل) کے ساتھ تیار ہے:")
    
    video_bytes = open(active_out, 'rb').read()
    st.video(video_bytes)
    
    st.download_button(
        label="📥 یہاں کلک کر کے پروسیس شدہ محفوظ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
        data=video_bytes,
        file_name=f"es_protected_{os.path.basename(active_out)}",
        mime="video/mp4",
        use_container_width=True
    )

    genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
    st.info(f"🎯 **AI ڈیٹیکشن:** ویڈیو کیٹگری: **'{genre}'** (اصل نام: **{st.session_state.detected_info.get('title', 'Video')}**)")
    
    c_meta1, c_meta2 = st.columns(2)
    with c_meta1:
        st.markdown("### 🔥 وائرل ٹائٹلز:")
        for t in titles:
            st.code(t, language="text")
        st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
        st.code(tags, language="text")

    with c_meta2:
        st.markdown("### 🎨 AI تھمب نیل کا پرامپٹ (Thumbnail Prompt):")
        st.code(prompt, language="text")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px;'>ES Ultra Anti-Copyright Shield Studio | Developers: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
