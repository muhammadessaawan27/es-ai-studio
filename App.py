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

# ==========================================
# STREAMLIT COMPACT CONFIGURATION
# ==========================================
st.set_page_config(page_title="ES Ultra 10X Anti-Copyright Turbo Studio", layout="wide", page_icon="⚡")

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

def extract_yt_id(raw_url):
    raw_url = raw_url.strip()
    m = re.search(r'(?:v=|\/|shorts\/)([0-9A-Za-z_-]{11})', raw_url)
    return m.group(1) if m else None

def fetch_oembed_title(clean_url):
    try:
        req_url = f"https://noembed.com/embed?url={urllib.parse.quote(clean_url)}"
        res = requests.get(req_url, timeout=4)
        if res.status_code == 200:
            return res.json().get("title", "")
    except Exception:
        pass
    return ""

# ==========================================
# UNBLOCKABLE MULTI-ENGINE DOWNLOAD ROUTER
# ==========================================
def download_unblockable_media(raw_url, target_path):
    vid_id = extract_yt_id(raw_url)
    clean_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else raw_url.strip()
    title = fetch_oembed_title(clean_url) or "Action Movie Scene"
    
    # 1. Invidious Dedicated European Proxy Nodes
    if vid_id:
        invidious_nodes = [
            "https://inv.tux.pizza",
            "https://invidious.nerdvpn.de",
            "https://invidious.privacydev.net",
            "https://invidious.drgns.space",
            "https://invidious.projectsegfau.lt"
        ]
        for node in invidious_nodes:
            try:
                api_url = f"{node}/api/v1/videos/{vid_id}"
                res = requests.get(api_url, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    title = data.get("title", title)
                    streams = data.get("formatStreams", [])
                    mp4s = [s for s in streams if "mp4" in s.get("container", "").lower() or "video/mp4" in s.get("type", "").lower()] or streams
                    if mp4s:
                        dl_url = mp4s[-1]["url"]
                        if dl_url.startswith("/"): dl_url = node + dl_url
                        r_file = requests.get(dl_url, stream=True, timeout=12)
                        if r_file.status_code == 200:
                            with open(target_path, "wb") as f:
                                for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                                    if chunk: f.write(chunk)
                            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                                return True, title
            except Exception:
                continue

    # 2. Piped High-Speed Stream Router
    if vid_id:
        piped_nodes = [
            "https://pipedapi.kavin.rocks",
            "https://api.piped.privacydev.net",
            "https://piped-api.lunar.icu"
        ]
        for node in piped_nodes:
            try:
                api_url = f"{node}/streams/{vid_id}"
                res = requests.get(api_url, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    title = data.get("title", title)
                    video_streams = data.get("videoStreams", [])
                    combined = [s for s in video_streams if not s.get("videoOnly") and "mp4" in s.get("format", "").lower()] or [s for s in video_streams if not s.get("videoOnly")]
                    if combined:
                        dl_url = combined[0]["url"]
                        r_file = requests.get(dl_url, stream=True, timeout=12)
                        if r_file.status_code == 200:
                            with open(target_path, "wb") as f:
                                for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                                    if chunk: f.write(chunk)
                            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                                return True, title
            except Exception:
                continue

    # 3. Native Fast Client Fallback
    try:
        import yt_dlp
        ydl_opts = {
            'format': '18/best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'socket_timeout': 8,
            'extractor_args': {'youtube': {'player_client': ['ios', 'android_creator', 'tvhtml5']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            if meta:
                title = meta.get('title', title)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
            return True, title
    except Exception:
        pass

    return False, title

# ==========================================
# AI DEEP VIDEO ANALYSIS & THUMBNAIL ENGINE
# ==========================================
def analyze_video_with_ai(title):
    try:
        query = (
            f"Analyze video title: '{title}'.\n"
            f"Provide:\n"
            f"1. Category/Genre\n"
            f"2. 3 Viral High-CTR Clickbait Titles with emojis\n"
            f"3. 8 Trending Hashtags\n"
            f"4. 8K Photorealistic Thumbnail Prompt for Midjourney/Flux/Bing with intense lighting & hero close-up."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(query)}?model=openai"
        res = requests.get(url, timeout=8)
        if res.status_code == 200 and len(res.text.strip()) > 30:
            return res.text.strip()
    except Exception:
        pass
        
    clean_t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip() or title
    return (
        f"**🎯 کیٹگری:** ایکشن و ڈراماٹک بلاک بسٹر سین\n\n"
        f"**🔥 وائرل ٹائٹلز:**\n"
        f"1. 😱 {clean_t[:45]} | سب سے خطرناک اور ان کٹ سین!\n"
        f"2. ⚡ فل ایچ ڈی ایکشن کلائمیکس | {clean_t[:40]}\n"
        f"3. 🔥 ہائی وولٹیج مووی سین: {clean_t[:40]}\n\n"
        f"**🏷️ وائرل ہیش ٹیگز:**\n"
        f"`#ViralVideo #ActionMovie #Blockbuster #MovieRecap #TrendingNow #CinemaReaction`\n\n"
        f"**🎨 AI تھمب نیل پرامپٹ (Midjourney / Flux / Bing):**\n"
        f"```text\nHyper-realistic 8K cinematic movie thumbnail for '{clean_t[:35]}', intense angry hero face close-up, sparks background, dramatic lighting, ultra-high contrast, 16:9.\n```"
    )

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
    <div class="compact-title">⚡ ES ULTRA 10X ANTI-COPYRIGHT TURBO STUDIO</div>
    <div class="badge">10-SHIELD FULL ENGINE ACTIVE</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_shield, tab_clip, tab_lofi = st.tabs([
    "🛡️ 1. فل مووی فاسٹ شیلڈ (تمام 10 اینٹی کاپی رائٹ ہتھیار)",
    "⚔️ 2. کلپ کٹر موڈ (10 تا 20 منٹ)",
    "🎧 3. لوفی گانے (Slowed + Reverb)"
])

# -----------------
# TAB 1: FAST FULL SHIELD (ALL 10 ANTI-COPYRIGHT WEAPONS)
# -----------------
with tab_shield:
    c1, c2 = st.columns([1, 1])
    with c1:
        shield_mode = st.selectbox("اینٹی کاپی رائٹ شیلڈ لیول:", [
            "🛡️ 0.75s مائیکرو کٹ + ہائپر کینوس + 1.8° ٹِلٹ + کلر اسکریبل (100% کلیم فری)",
            "⚡ 0.75s فاسٹ کٹ + زوم + اینٹی ہیش لیٹرباکس"
        ])
    with c2:
        audio_mode = st.selectbox("آواز کی موٹائی و گڑبڑ شیلڈ:", [
            "🔊 بھاری موٹی آواز (Deep Baritone) + ایکوسٹک ماسکنگ لہریں",
            "🎵 میڈیم پچ شفٹ (Medium Pitch)"
        ])
        
    url_input = st.text_input("🔗 یوٹیوب یا ویڈیو کا لنک پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="url_main")
    up_file = st.file_uploader("📂 یا موبائل / کمپیوٹر سے فائل منتخب کریں (2GB تک سپورٹڈ):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")
    
    if st.button("🚀 10 اینٹی کاپی رائٹ شیلڈز لگائیں (سپر فاسٹ ٹربو پروسیسنگ)", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"in_vid_{uid}.mp4"
        target_out = f"es_turbo_{uid}.mp4"
        info = {'title': 'Action Scene Video'}
        has_input = False
        
        if url_input.strip():
            with st.spinner("🔗 لنک بائی پاس ہو رہا ہے اور ایچ ڈی ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media(url_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
                else:
                    st.error("❌ لنک ڈاؤنلوڈ نہیں ہو سکا۔ برائے مہربانی ڈائریکٹ فائل اپلوڈر استعمال کریں۔")
        elif up_file is not None:
            with st.spinner("📂 ویڈیو محفوظ ہو رہی ہے..."):
                with open(target_in, "wb") as f:
                    up_file.seek(0)
                    while True:
                        chunk = up_file.read(1024 * 1024 * 16)
                        if not chunk: break
                        f.write(chunk)
                if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                    has_input = True
                    info['title'] = up_file.name

        if has_input and os.path.exists(target_in):
            t_start = time.time()
            with st.spinner("⚡ تمام 10 اینٹی کاپی رائٹ شیلڈز لائیو لگ رہی ہیں..."):
                ffmpeg_exe = get_ffmpeg()
                
                # 1. 0.75s Sub-Cut + 2. Zero-CPU Blur + 3. 1.8 Deg Tilt + 4. H-Flip + 5. Color/Contrast + 6. Letterbox
                if "ہائپر کینوس" in shield_mode:
                    vf_str = (
                        "[0:v]scale=160:90,scale=1280:720[bg];"
                        "[0:v]select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                        "hflip,crop=iw*0.82:ih*0.82,scale=980:552,"
                        "eq=contrast=1.18:saturation=1.24:brightness=0.02[fg];"
                        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                        "drawbox=y=0:h=36:color=black@0.75:t=fill,"
                        "drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                    )
                else:
                    vf_str = (
                        "select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,"
                        "hflip,crop=iw*0.80:ih*0.80,scale=1280:720,"
                        "eq=contrast=1.18:saturation=1.24:brightness=0.02,"
                        "drawbox=y=0:h=36:color=black@0.75:t=fill,"
                        "drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                    )
                
                # 7. Deep Pitch + 8. Acoustic Echo/Reverb + 9. Harmonic Frequency Masking
                if "بھاری موٹی آواز" in audio_mode:
                    af_str = (
                        "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,"
                        "bass=g=7:f=100,treble=g=-4:f=3000,aecho=0.8:0.5:15:0.2"
                    )
                else:
                    af_str = "volume=0.75,asetrate=44100*0.94,aresample=44100:async=1,atempo=1.0638,bass=g=4:f=110"
                
                # 10. Metadata Clean + Keyframe Scramble + Multi-Thread Fast Pipeline
                cmd = [
                    ffmpeg_exe, "-y", "-i", target_in,
                    "-map_metadata", "-1",
                    "-filter_complex" if "ہائپر کینوس" in shield_mode else "-vf", vf_str,
                    "-af", af_str,
                    "-r", "24",
                    "-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode",
                    "-threads", "0", "-crf", "27",
                    "-g", "48", "-keyint_min", "24",
                    "-b:v", "850k", "-maxrate", "1100k", "-bufsize", "2000k",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                ]
                
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                dur = round(time.time() - t_start, 1)
                
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    st.success(f"⚡ ویڈیو صرف **{dur} سیکنڈ** میں تیار ہو گئی!")
                    try: os.remove(target_in)
                    except Exception: pass
                else:
                    st.error("❌ ویڈیو پروسیسنگ مکمل نہ ہو سکی۔")
        elif not has_input and not url_input.strip() and up_file is None:
            st.error("❌ برائے مہربانی یوٹیوب لنک ڈالیں یا فائل اپلوڈ کریں۔")

# -----------------
# TAB 2: CLIP CUTTER
# -----------------
with tab_clip:
    c1, c2 = st.columns(2)
    with c1: scene_type = st.selectbox("سین کا آغاز:", ["⚔️ منٹ 30", "👻 منٹ 45", "🏔️ منٹ 15", "⏱️ کسٹم"], key="s_t2")
    with c2: clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    clip_url = st.text_input("🔗 یوٹیوب لنک:", placeholder="https://...", key="clip_url")
    upload_opt2 = st.file_uploader("📂 یا فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t2")

    if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="run_t2"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"clip_in_{uid}.mp4"
        target_out = f"clip_out_{uid}.mp4"
        info = {'title': 'Clip Highlight'}
        has_input = False
        
        if clip_url.strip():
            with st.spinner("ویڈیو لنک سے ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media(clip_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
        elif upload_opt2 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt2.read())
            has_input = True
            info['title'] = upload_opt2.name
            
        if has_input and os.path.exists(target_in):
            with st.spinner("کلپ کٹ کر کے فاسٹ شیلڈ لگائی جا رہی ہے..."):
                ffmpeg_exe = get_ffmpeg()
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "select='mod(n\\,18)<16',setpts=N/(24*TB),rotate=1.8*PI/180:ow=iw:oh=ih:c=black,hflip,crop=iw*0.80:ih*0.80,scale=1280:720,eq=contrast=1.18:saturation=1.24:brightness=0.02,drawbox=y=0:h=36:color=black@0.75:t=fill,drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                af = "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,bass=g=7:f=100,treble=g=-4:f=3000,aecho=0.8:0.5:15:0.2"
                
                cmd = [
                    ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                    "-i", target_in, "-map_metadata", "-1", "-vf", vf, "-af", af,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "0", "-crf", "27",
                    "-b:v", "850k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "96k", "-shortest", target_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    try: os.remove(target_in)
                    except Exception: pass
        else:
            st.error("❌ درست لنک دیں یا ویڈیو فائل اپلوڈ کریں۔")

# -----------------
# TAB 3: LO-FI & SONGS
# -----------------
with tab_lofi:
    col_s1, col_s2 = st.columns(2)
    with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
    with col_s2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
        
    song_url = st.text_input("🔗 گانے کا لنک:", placeholder="https://...", key="song_url")
    upload_opt3 = st.file_uploader("📂 یا آڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
    
    if st.button("🚀 فاسٹ لوفی بنائیں", type="primary", key="run_t3"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"song_in_{uid}.mp4"
        target_out = f"song_out_{uid}.mp4"
        has_input = False
        info = {'title': 'Lo-Fi Chill Track'}
        
        if song_url.strip():
            with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                success, title_fetched = download_unblockable_media(song_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
        elif upload_opt3 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt3.read())
            has_input = True
            info['title'] = upload_opt3.name
            
        if has_input and os.path.exists(target_in):
            with st.spinner("لوفی گانا تیار ہو رہا ہے..."):
                ffmpeg_exe = get_ffmpeg()
                sample_rate = int(44100 * slow_val)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g=6:f=110"
                cmd_song = [
                    ffmpeg_exe, "-y", "-i", target_in,
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
                    try: os.remove(target_in)
                    except Exception: pass
        else:
            st.error("❌ گانے کا درست لنک دیں یا فائل اپلوڈ کریں۔")

# ==========================================
# OUTPUT & AI METADATA / THUMBNAIL DASHBOARD
# ==========================================
active_out = st.session_state.current_output_video
if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
    st.divider()
    st.write("#### 🎬 پروسیس شدہ اینٹی کاپی رائٹ ویڈیو:")
    
    video_bytes = open(active_out, 'rb').read()
    st.video(video_bytes)
    
    st.download_button(
        label="📥 محفوظ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
        data=video_bytes,
        file_name=f"es_protected_{os.path.basename(active_out)}",
        mime="video/mp4",
        use_container_width=True
    )

    st.markdown("---")
    st.write("#### 🧠 AI تجزیہ، وائرل ٹائٹلز اور نیا تھمب نیل پرامپٹ:")
    with st.spinner("AI مواد تیار کر رہا ہے..."):
        ai_response = analyze_video_with_ai(st.session_state.detected_info.get('title', 'Video'))
        st.markdown(ai_response)

st.markdown("<p style='text-align: center; font-size: 11px; color: #64748b; margin-top: 20px;'>ES Ultra Anti-Copyright Turbo Studio | Developers: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
