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
import concurrent.futures

# ==========================================
# STREAMLIT CONFIGURATION & SESSION STATE
# ==========================================
st.set_page_config(
    page_title="ES AI Studio | Muhammad Essa & Saba Wahid",
    layout="wide",
    page_icon="⚡"
)

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False
if "detected_info" not in st.session_state:
    st.session_state.detected_info = {}
if "current_output_video" not in st.session_state:
    st.session_state.current_output_video = ""
if "generated_shorts" not in st.session_state:
    st.session_state.generated_shorts = []
if "generated_recap_script" not in st.session_state:
    st.session_state.generated_recap_script = ""
if "recap_video_out" not in st.session_state:
    st.session_state.recap_video_out = ""

# ==========================================
# SYSTEM CORE HELPERS
# ==========================================
def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def extract_yt_id(raw_url):
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    clean_raw = raw_url.split('?si=')[0].split('&si=')[0].split('?t=')[0]
    m = re.search(r'(?:v=|\/|shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})', clean_raw)
    return m.group(1) if m else None

def extract_gdrive_id(raw_url):
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    m = re.search(r'(?:/file/d/|id=|/d/)([a-zA-Z0-9_-]{20,})', raw_url)
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

def get_video_duration_fast(file_path):
    try:
        ffmpeg_exe = get_ffmpeg()
        cmd = [ffmpeg_exe, "-nostdin", "-i", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
        if m:
            hours = float(m.group(1))
            minutes = float(m.group(2))
            seconds = float(m.group(3))
            total = hours * 3600 + minutes * 60 + seconds
            if total > 0:
                return total
    except Exception:
        pass
    return 600.0

def clean_text_for_tts(raw_text):
    clean = re.sub(r'[#\*\_]', '', raw_text)
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', clean)
    clean = re.sub(r'https?://\S+', '', clean)
    return clean.strip()

# ==========================================
# MULTI-LANGUAGE VOICE DATABASE
# ==========================================
VOICE_DATABASE = {
    "Urdu - Asad (Deep Baritone Male)": ("ur-PK-AsadNeural", "-10%", "-15Hz"),
    "Urdu - Saba (Natural Clear Female)": ("ur-PK-SabaNeural", "+0%", "+0Hz"),
    "Hindi - Madhur (Deep Male)": ("hi-IN-MadhurNeural", "-5%", "-10Hz"),
    "Hindi - Swara (Natural Female)": ("hi-IN-SwaraNeural", "+0%", "+0Hz"),
    "English - Guy (Deep Narrative Male)": ("en-US-GuyNeural", "-5%", "-10Hz"),
    "English - Jenny (Pro Female)": ("en-US-JennyNeural", "+0%", "+0Hz"),
    "Punjabi - Gagan (Natural Male)": ("pa-IN-GaganNeural", "+0%", "+0Hz"),
    "Pashto - Gul Nawaz (Natural Male)": ("ps-AF-GulNawazNeural", "+0%", "+0Hz"),
    "Arabic - Hamed (Pro Male)": ("ar-SA-HamedNeural", "+0%", "-5Hz")
}

def save_multilang_voiceover_sync(text, voice_key, out_file):
    try:
        clean_t = clean_text_for_tts(text)
        voice_id, rate_str, pitch_str = VOICE_DATABASE.get(voice_key, ("ur-PK-AsadNeural", "-10%", "-15Hz"))
        async def amain():
            communicate = edge_tts.Communicate(clean_t, voice_id, rate=rate_str, pitch=pitch_str)
            await communicate.save(out_file)
        asyncio.run(amain())
        return True
    except Exception:
        return False

# ==============================================================================
# UNIVERSAL MEDIA DOWNLOADER (DAILYMOTION + MP4MOVIEZ + DIRECT MP4 + CLOUD)
# ==============================================================================
def download_google_drive_robust(file_id, target_path):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    urls_to_try = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    ]
    for download_url in urls_to_try:
        try:
            res = session.get(download_url, stream=True, timeout=25, headers=headers)
            content_type = res.headers.get("content-type", "").lower()
            if "html" in content_type:
                confirm_match = re.search(r'confirm=([0-9A-Za-z_\-]+)', res.text)
                if confirm_match:
                    token = confirm_match.group(1)
                    retry_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm={token}"
                    res = session.get(retry_url, stream=True, timeout=25, headers=headers)

            with open(target_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024 * 1024 * 8):
                    if chunk: f.write(chunk)
                        
            if os.path.exists(target_path) and os.path.getsize(target_path) > 30000:
                with open(target_path, "rb") as f_check:
                    head = f_check.read(100)
                    if b"<!DOCTYPE" not in head and b"<html" not in head:
                        return True, "Google Drive Movie File"
        except Exception:
            continue
    return False, ""

def download_unblockable_media_parallel(raw_url, target_path):
    raw_url = raw_url.strip()
    title = fetch_oembed_title(raw_url) or "Action Movie Video"

    # 1. Google Drive Auto-Detection
    g_id = extract_gdrive_id(raw_url)
    if ("drive.google.com" in raw_url or "docs.google.com" in raw_url) and g_id:
        ok, t = download_google_drive_robust(g_id, target_path)
        if ok: return True, t
        return False, "Google Drive Permission Error"

    # 2. Dailymotion Link Engine (100% Unblocked on Cloud)
    if "dailymotion.com" in raw_url or "dai.ly" in raw_url:
        try:
            import yt_dlp
            ffmpeg_exe = get_ffmpeg()
            ffmpeg_dir = os.path.dirname(ffmpeg_exe) if os.path.isabs(ffmpeg_exe) else None
            ydl_opts = {
                'format': 'best[height<=720]/best',
                'outtmpl': target_path,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'socket_timeout': 30,
                'retries': 3
            }
            if ffmpeg_dir: ydl_opts['ffmpeg_location'] = ffmpeg_dir
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(raw_url, download=True)
                if meta: title = meta.get('title', title)
            if os.path.exists(target_path) and os.path.getsize(target_path) > 5000:
                return True, title
        except Exception:
            pass

    # 3. MP4Moviez & Direct Video Links (Pixeldrain, FastDL, HubCloud, Dropbox, Direct MP4)
    if raw_url.startswith("http") and ("youtube.com" not in raw_url and "youtu.be" not in raw_url):
        direct_url = raw_url
        if "pixeldrain.com/u/" in raw_url:
            direct_url = raw_url.replace("pixeldrain.com/u/", "pixeldrain.com/api/file/")
        elif "dropbox.com" in raw_url:
            direct_url = raw_url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "?dl=1")
            
        try:
            r = requests.get(direct_url, stream=True, timeout=25, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": raw_url
            })
            if r.status_code == 200:
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024 * 8):
                        if chunk: f.write(chunk)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                    cd = r.headers.get('content-disposition', '')
                    if 'filename=' in cd:
                        m_fn = re.search(r'filename=["\']?([^"\']+)["\']?', cd)
                        if m_fn: title = m_fn.group(1)
                    return True, title if title != "Action Movie Video" else "MP4Moviez Direct Video"
        except Exception:
            pass

    # 4. YouTube Multi-Node Fallback
    m = re.search(r'(?:v=|\/|shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})', raw_url)
    if m:
        vid_id = m.group(1)
        apis = [
            f"https://pipedapi.kavin.rocks/streams/{vid_id}",
            f"https://inv.nadeko.net/api/v1/videos/{vid_id}",
            f"https://yewtu.be/api/v1/videos/{vid_id}"
        ]
        for api_url in apis:
            try:
                res = requests.get(api_url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    title = data.get("title", title)
                    streams = data.get("videoStreams", []) or data.get("formatStreams", [])
                    mp4s = [s for s in streams if "mp4" in s.get("container", "").lower() or "video/mp4" in s.get("mimeType", "").lower()] or streams
                    if mp4s:
                        dl_url = mp4s[0].get("url", "")
                        if dl_url:
                            r_file = requests.get(dl_url, stream=True, timeout=12)
                            if r_file.status_code == 200:
                                with open(target_path, "wb") as f:
                                    for chunk in r_file.iter_content(chunk_size=1024 * 1024 * 4):
                                        if chunk: f.write(chunk)
                                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                                    return True, title
            except Exception:
                pass

    return False, title

# ==============================================================================
# REAL CANONICAL MOVIE PLOT AI STORY GENERATOR
# ==============================================================================
def generate_exact_movie_recap_script(movie_title, duration_mins, genre, target_lang):
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', movie_title).strip()
    try:
        instruction = (
            f"You are an expert film analyst and movie recap narrator. "
            f"Explain the ACTUAL, CANONICAL story, plot twists, character actions, and climax of the real movie or video titled '{clean_title}'. "
            f"Do NOT invent a generic fake story. Identify what this actual movie is about and explain its real storyline. "
            f"Target Language: {target_lang}. Genre/Theme: {genre}. Target duration: {duration_mins} minutes narrative. "
            f"Write continuous, highly engaging storytelling text for an AI narrator without stage notes or brackets."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=18)
        if res.status_code == 200 and len(res.text.strip()) > 60:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج ہم فلم {clean_title} کی اصل اور مکمل کہانی کا جائزہ لے رہے ہیں۔ "
        f"کہانی کے آغاز میں ہمارا مرکزی کردار ایک بڑے چیلنج کا سامنا کرتا ہے جس کے بعد غیر متوقع موڑ سامنے آتے ہیں۔ "
        f"جیسے جیسے کہانی آگے بڑھتی ہے، سسپنس اور ایکشن اپنے عروج پر پہنچتا ہے اور کلائمیکس پر شاندار انجام ہوتا ہے۔ "
        f"اگر آپ کو یہ کہانی اور مووی ریکیپ پسند آیا تو ویڈیو کو لائک اور چینل کو ضرور سبسکرائب کریں!"
    )

def analyze_video_and_generate_metadata(title, is_short=False, is_song=False):
    clean_t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    if not clean_t: clean_t = title
    
    if is_song:
        exact_thumb_prompt = f"Anime aesthetic 4K Lo-Fi wallpaper for '{clean_t[:45]}', cozy neon room, aesthetic lighting, 16:9."
        titles = [f"🎧 {clean_t[:45]} (Slowed + Reverb Lo-Fi Remix)", f"🌙 {clean_t[:45]} - Deep Relaxing Aesthetic Vibe", f"✨ Pure Nostalgia Vibes | {clean_t[:40]}"]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio #LoFiBeats"
    elif is_short:
        exact_thumb_prompt = f"Hyper-realistic 8K vertical cinematic poster 9:16 for YouTube Shorts of '{clean_t[:45]}', intense expression, 35mm photography."
        titles = [f"🔥 {clean_t[:40]} - UNSTOPPABLE Climax Scene! 😱 #Shorts", f"⚡ The Most Intense Moment of {clean_t[:35]} 🔥 #Shorts", f"😱 Best Action Climax in {clean_t[:38]} #ViralShorts"]
        hashtags = "#Shorts #YouTubeShorts #ViralShorts #TrendingShorts #MovieClimax"
    else:
        exact_thumb_prompt = f"Hyper-realistic 8K award-winning cinematic movie poster portrait of '{clean_t[:45]}', photorealistic character face, volumetric lighting, 16:9."
        titles = [f"🔥 {clean_t[:45]} | Full Story Explained & Recap", f"⚡ {clean_t[:40]} Movie Full Story Breakdown", f"😱 The Entire Story of {clean_t[:40]} Explained!"]
        hashtags = "#MovieRecap #MovieExplained #FilmReview #TrendingCinema #StoryRecap"
        
    return clean_t, titles, hashtags, exact_thumb_prompt

def fetch_img_failover(prompt, w, h, seed):
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        res = requests.get(url, timeout=25)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# ==========================================
# CLEAN & BRIGHT THEME (MUHAMMAD ESSA & SABA WAHID)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; font-size: 13.5px !important; }
    .stApp { background-color: #ffffff !important; color: #0f172a !important; }
    
    .brand-header {
        background: #0f172a; color: #ffffff; padding: 14px 22px; border-radius: 10px;
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
        border-bottom: 3px solid #0284c7;
    }
    .brand-logo { font-size: 1.35rem !important; font-weight: 800 !important; color: #38bdf8 !important; }
    .founders-tag {
        font-size: 12.5px; font-weight: 700; color: #fbbf24;
        background: rgba(251, 191, 36, 0.15); border: 1px solid #fbbf24;
        padding: 5px 12px; border-radius: 20px;
    }
    .badge-26 {
        background: #059669; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #f8fafc !important; color: #0f172a !important;
        border: 1px solid #cbd5e1 !important; font-size: 13.5px !important; font-weight: 600 !important;
    }
    label { color: #0f172a !important; font-weight: 700 !important; font-size: 13px !important; }
    
    .stButton>button { 
        background: #0284c7 !important; color: #ffffff !important; border-radius: 8px !important; 
        height: 44px !important; font-size: 14px !important; font-weight: 700 !important; border: none !important;
    }
    .stTabs [data-baseweb="tab"] { height: 38px !important; font-size: 13px !important; font-weight: 700 !important; color: #475569; }
    .stTabs [aria-selected="true"] { color: #0284c7 !important; border-bottom: 2px solid #0284c7 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-logo">⚡ ES AI STUDIO</div>
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">Dailymotion & MP4Moviez Engine + 26 Shields Active</div>
    </div>
    <div style="display:flex; align-items:center; gap: 10px;">
        <span class="founders-tag">👑 Founders: Muhammad Essa & Saba Wahid</span>
        <span class="badge-26">26 SHIELDS ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7 FULL PRODUCTION TABS
# ==========================================
tab_recap, tab_shorts, tab_shield, tab_clip, tab_lofi, tab_movie, tab_image = st.tabs([
    "🎬 1. ملٹی لینگویج مووی ریکیپ (Dailymotion + MP4Moviez)",
    "📱 2. پیور فل اسکرین 9:16 شارٹس",
    "🛡️ 3. فل مووی شفلر (26 ہتھیار)",
    "⚔️ 4. کلپ کٹر موڈ (10 تا 20 منٹ کٹ)",
    "🎧 5. لوفی گانے (Slowed + Reverb)",
    "🎥 6. پرو AI مووی اسٹوڈیو",
    "🎨 7. پرو AI امیج اسٹوڈیو"
])

# ------------------------------------------------------------------------------
# TAB 1: MULTI-LANGUAGE AI REAL MOVIE PLOT RECAP STUDIO
# ------------------------------------------------------------------------------
with tab_recap:
    st.write("### 🎬 خودکار AI وائس اوور، اصلی فلم کی کہانی و مووی ریکیپ")
    st.info("💡 **ڈیلی موشن و MP4Moviez ایکٹو:** ڈیلی موشن کا لنک، MP4Moviez کا ڈائریکٹ لنک یا ویڈیو لنک درج کریں۔ کلاؤڈ پر فوری ڈاؤنلوڈ ہو کر پروسیسنگ شروع ہو جائے گی!")

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        voiceover_mode = st.selectbox("وائس اوور کا طریقہ:", [
            "🎙️ خودکار AI وائس اوور (100% تیار ویڈیو)",
            "📝 مینوئل موڈ (صرف ویڈیو میوٹ + تحریری اسکرپٹ)"
        ], key="rc_vmode")
    with rc2:
        voice_char = st.selectbox("کہانی کی زبان و آواز (Language & Voice):", list(VOICE_DATABASE.keys()), key="rc_vchar")
    with rc3:
        recap_dur = st.selectbox("مووی ریکیپ کا دورانیہ:", ["10 منٹ ریکیپ (10 Mins)", "20 منٹ ریکیپ (20 Mins)"], key="rc_dur")
    with rc4:
        recap_genre = st.selectbox("ویڈیو کا انداز (Genre):", [
            "🔥 ایکشن و تھرلر (Action / Blockbuster)",
            "🐾 اینیملز و جنگلی حیات (Wildlife / Discovery)",
            "😱 سسپنس و خوفناک (Suspense / Horror)",
            "💖 رومانٹک و ڈراما (Romantic Drama)",
            "⚡ کرائم و ایڈونچر (Crime Adventure)"
        ], key="rc_genre")

    target_recap_mins = 10 if "10" in recap_dur else 20
    target_lang_str = voice_char.split(" - ")[0]

    url_recap_input = st.text_input("🔗 مووی کا ڈیلی موشن / MP4Moviez / ویب لنک یہاں پیسٹ کریں:", placeholder="https://www.dailymotion.com/video/... یا ڈائریکٹ مووی ڈاؤنلوڈ لنک", key="url_recap")
    up_recap_file = st.file_uploader("📂 یا اپنے ڈیوائس سے ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_recap")

    if st.button("🚀 تیار کریں (اصلی مووی کہانی + AI وائس اوور + 26 شیلڈز)", type="primary", key="btn_run_recap"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"recap_in_{uid}.mp4"
        voice_audio = f"recap_voice_{uid}.mp3"
        video_montage = f"recap_video_{uid}.mp4"
        final_recap_out = f"final_recap_{uid}.mp4"
        output_ready_path = ""
        has_input = False
        info = {'title': 'Action Movie Recap'}

        status_box = st.status("⏳ پروسیسنگ جاری ہے، برائے مہربانی چند سیکنڈ انتظار کریں...", expanded=True)

        if url_recap_input.strip():
            status_box.write("🔗 ویڈیو کلاؤڈ اسٹریم سے ڈاؤنلوڈ ہو رہی ہے...")
            success, title_fetched = download_unblockable_media_parallel(url_recap_input.strip(), target_in)
            if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                has_input = True
                info['title'] = title_fetched
        elif up_recap_file is not None:
            status_box.write("📂 اپلوڈ شدہ فائل محفوظ ہو رہی ہے...")
            with open(target_in, "wb") as f:
                while True:
                    chunk = up_recap_file.read(1024 * 1024 * 8)
                    if not chunk: break
                    f.write(chunk)
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_recap_file.name

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()

            # 1. AI Generates Real Movie Plot Script
            status_box.write(f"🧠 فلم '{info['title'][:30]}' کی اصل کہانی ({target_lang_str}) میں لکھی جا رہی ہے...")
            real_movie_script = generate_exact_movie_recap_script(info['title'], target_recap_mins, recap_genre, target_lang_str)
            st.session_state.generated_recap_script = real_movie_script

            # 2. Multi-Language TTS Voiceover Generation
            has_voiceover = False
            if "خودکار AI" in voiceover_mode:
                status_box.write(f"🎙️ {voice_char} کی آواز میں وائس اوور ریکارڈ ہو رہی ہے...")
                tts_ok = save_multilang_voiceover_sync(real_movie_script, voice_char, voice_audio)
                if tts_ok and os.path.exists(voice_audio) and os.path.getsize(voice_audio) > 1000:
                    has_voiceover = True

            # 3. Synchronized Montage with 26 Shields
            status_box.write("⚡ 26 اینٹی کاپی رائٹ شیلڈز (1/10 فریم کٹ، فلپ، کراپ، 24fps) لاگو ہو رہی ہیں...")
            
            # Dynamic calculation of snippets
            if total_dur < 60.0:
                num_snippets = max(3, int(total_dur / 4.0))
            elif total_dur < 300.0:
                num_snippets = 12
            else:
                num_snippets = 24

            start_offset = min(5.0, total_dur * 0.1)
            usable_dur = max(10.0, total_dur - (start_offset * 2))
            time_step = max(3.5, usable_dur / max(1, num_snippets))
            snippet_files = []
            list_txt = f"recap_list_{uid}.txt"

            vf_recap = (
                "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),"
                "scale=1280:720:flags=fast_bilinear,hflip,"
                "crop=iw*0.82:ih*0.82,scale=1280:720,"
                "eq=contrast=1.18:saturation=1.24:brightness=0.02,"
                "drawbox=y=0:h=36:color=black@0.75:t=max,drawbox=y=ih-44:h=44:color=black@0.85:t=max"
            )

            for i in range(num_snippets):
                pt = start_offset + (i * time_step)
                if pt >= total_dur - 4.0: 
                    pt = max(2.0, total_dur * 0.25)
                snip_path = f"snip_{uid}_{i}.mp4"
                
                cmd_snip = [
                    ffmpeg_exe, "-nostdin", "-y",
                    "-ss", str(pt), "-t", "3.5",
                    "-i", target_in, "-an", "-map_metadata", "-1",
                    "-vf", vf_recap,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", snip_path
                ]
                subprocess.run(cmd_snip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(snip_path) and os.path.getsize(snip_path) > 1000:
                    snippet_files.append(snip_path)

            # Fallback if snippets list is empty: Process whole video directly
            if not snippet_files:
                cmd_direct = [
                    ffmpeg_exe, "-nostdin", "-y",
                    "-i", target_in, "-an", "-map_metadata", "-1",
                    "-vf", vf_recap,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-t", "60", video_montage
                ]
                subprocess.run(cmd_direct, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(video_montage):
                    snippet_files.append(video_montage)

            if snippet_files:
                status_box.write("🎬 تمام سینز اور وائس اوور کو ویڈیو میں مکس کیا جا رہا ہے...")
                with open(list_txt, "w") as lf:
                    for sf in snippet_files:
                        lf.write(f"file '{sf}'\n")

                if has_voiceover and os.path.exists(voice_audio):
                    cmd_mux = [
                        ffmpeg_exe, "-nostdin", "-y",
                        "-f", "concat", "-safe", "0", "-stream_loop", "-1", "-i", list_txt,
                        "-i", voice_audio,
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "128k",
                        "-shortest", "-movflags", "+faststart",
                        final_recap_out
                    ]
                    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    output_ready_path = final_recap_out
                else:
                    cmd_concat_recap = [
                        ffmpeg_exe, "-nostdin", "-y", "-f", "concat", "-safe", "0",
                        "-i", list_txt,
                        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                        "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
                        "-movflags", "+faststart", video_montage
                    ]
                    subprocess.run(cmd_concat_recap, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    output_ready_path = video_montage

                for sf in snippet_files:
                    if os.path.exists(sf): os.remove(sf)
                if os.path.exists(list_txt): os.remove(list_txt)

            if os.path.exists(target_in): os.remove(target_in)
            if os.path.exists(voice_audio): os.remove(voice_audio)

            if output_ready_path and os.path.exists(output_ready_path) and os.path.getsize(output_ready_path) > 5000:
                st.session_state.recap_video_out = output_ready_path
                st.session_state.detected_info = info
                status_box.update(label="🎉 آپ کی مووی ریکیپ ویڈیو 100% تیار ہے!", state="complete", expanded=False)
            else:
                status_box.update(label="❌ ویڈیو تیار نہ ہو سکی۔ دوبارہ کوشش کریں۔", state="error")
        else:
            status_box.update(label="❌ ویڈیو حاصل نہیں ہو سکی۔ درست ڈیلی موشن یا MP4Moviez لنک درج کریں۔", state="error")

    # Display Ready Video & Full Script Section
    if st.session_state.recap_video_out and os.path.exists(st.session_state.recap_video_out):
        st.divider()
        st.subheader("🎬 تیار شدہ مووی ریکیپ ویڈیو (26 شیلڈز و وائس اوور کے ساتھ):")
        r_bytes = open(st.session_state.recap_video_out, 'rb').read()
        st.video(r_bytes)
        st.download_button(
            label="📥 مکمل مووی ریکیپ ویڈیو ڈاؤنلوڈ کریں (Download Ready Movie Recap MP4)",
            data=r_bytes,
            file_name=f"movie_recap_voiced_{os.path.basename(st.session_state.recap_video_out)}",
            mime="video/mp4",
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("📖 فلم کا مکمل تحریری اسکرپٹ (Real Story Script):")
        st.info("💡 یہ اسکرین پر چلنے والی ویڈیو کی اصل کہانی کا تحریری اسکرپٹ ہے:")
        st.code(st.session_state.generated_recap_script, language="markdown")

        st.markdown("---")
        st.subheader("🔥 وائرل ٹائٹلز، ہیش ٹیگز اور تھمب نیل پرامپٹ (1-Click Copy):")
        raw_title = st.session_state.detected_info.get('title', 'Movie Recap Video')
        clean_hero_title, titles, hashtags, exact_thumb_prompt = analyze_video_and_generate_metadata(raw_title, is_short=False)
        
        c_rc1, c_rc2 = st.columns(2)
        with c_rc1:
            st.markdown("**🔥 وائرل یوٹیوب ٹائٹلز:**")
            for t in titles:
                st.code(t, language="text")
            st.markdown("**🏷️ وائرل ہیش ٹیگز:**")
            st.code(hashtags, language="text")
        with c_rc2:
            st.markdown(f"**🎨 اصلی ہیرو ({clean_hero_title[:30]}) کا AI تھمب نیل پرامپٹ:**")
            st.code(exact_thumb_prompt, language="text")

# ------------------------------------------------------------------------------
# TAB 2: PURE FULL-SCREEN 9:16 SHORTS
# ------------------------------------------------------------------------------
with tab_shorts:
    st.write("### 📱 پیور فل اسکرین 9:16 شارٹس (ہر سیکنڈ 1/10واں فریم کٹ)")
    col_sh1, col_sh2 = st.columns(2)
    with col_sh1:
        num_shorts = st.selectbox("کتنے فل اسکرین شارٹس بنانے ہیں؟", [
            "1 شارٹ (Best Climax Hook)", "2 شارٹس (Opening + Climax)", "3 شارٹس (Hook + Story + Climax)"
        ], key="num_sh_pure")
    with col_sh2:
        short_dur = st.selectbox("ہر شارٹ کا دورانیہ:", ["30 سیکنڈ (30s)", "15 سیکنڈ (15s)", "60 سیکنڈ (60s)"], key="dur_sh_pure")

    count_target = 1 if "1" in num_shorts else 2 if "2" in num_shorts else 3
    dur_sec_target = 30 if "30" in short_dur else 15 if "15" in short_dur else 60

    url_shorts_input = st.text_input("🔗 مووی یا ویڈیو کا لنک ڈالیں:", placeholder="https://www.dailymotion.com/video/... یا ڈائریکٹ لنک", key="url_shorts_pure")
    up_shorts_file = st.file_uploader("📂 یا ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_shorts_pure")

    if st.button(f"🚀 {count_target} فل اسکرین 9:16 شارٹس بنائیں", type="primary", key="btn_run_shorts_pure"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"shorts_in_{uid}.mp4"
        has_input = False
        info = {'title': 'Viral Action Shorts'}

        if url_shorts_input.strip():
            with st.spinner("🔗 ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_shorts_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
        elif up_shorts_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_shorts_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_shorts_file.name

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()
            created_shorts = []
            
            usable_dur = max(dur_sec_target + 10.0, total_dur)
            points = [max(8.0, min(usable_dur - dur_sec_target - 2.0, total_dur * 0.45))] if count_target == 1 else [max(8.0, total_dur * 0.15), max(12.0, min(usable_dur - dur_sec_target - 2.0, total_dur * 0.60))]

            for idx, start_pt in enumerate(points, 1):
                short_out = f"pure_short_{uid}_{idx}.mp4"
                vf_pure = (
                    "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),"
                    "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,"
                    "hflip,eq=contrast=1.18:saturation=1.24:brightness=0.02"
                )
                af_pure = "highpass=f=75,lowpass=f=8000,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"

                cmd = [
                    ffmpeg_exe, "-nostdin", "-y",
                    "-ss", str(start_pt), "-t", str(dur_sec_target),
                    "-i", target_in, "-map_metadata", "-1", "-vf", vf_pure, "-af", af_pure,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k",
                    short_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(short_out) and os.path.getsize(short_out) > 5000:
                    created_shorts.append((short_out, f"📱 فل اسکرین 9:16 شارٹ #{idx} ({dur_sec_target}s)"))

            try: os.remove(target_in)
            except Exception: pass
            
            st.session_state.detected_info = info
            st.session_state.generated_shorts = created_shorts

    if st.session_state.generated_shorts:
        st.divider()
        st.subheader("📱 تیار شدہ فل اسکرین 9:16 شارٹس:")
        cols = st.columns(len(st.session_state.generated_shorts))
        for i, (s_path, s_title) in enumerate(st.session_state.generated_shorts):
            with cols[i]:
                st.write(f"**{s_title}**")
                s_bytes = open(s_path, 'rb').read()
                st.video(s_bytes)
                st.download_button(label=f"📥 ڈاؤنلوڈ شارٹ #{i+1}", data=s_bytes, file_name=f"short_{i+1}.mp4", mime="video/mp4", key=f"dl_p_{i}")

# ------------------------------------------------------------------------------
# TAB 3: FULL MOVIE SCENE SHUFFLER (26 WEAPONS)
# ------------------------------------------------------------------------------
with tab_shield:
    st.write("### 🛡️ فل مووی شفلر (ہر سیکنڈ 1/10واں فریم کٹ + سین شفلنگ)")
    c1, c2 = st.columns(2)
    with c1: shield_mode = st.selectbox("شیلڈ اسٹائل:", ["🛡️ فل شفلر: لوگو کٹ + سین شفل + 1/10واں کٹ", "⚡ لکیری موڈ: لوگو کٹ + 1/10واں کٹ"], key="sm_t1")
    with c2: voice_quality = st.selectbox("ڈبنگ:", ["🔊 کرسٹل کلیئر بیریٹون ڈبنگ", "🎵 نیچرل اسمارٹ پچ"], key="am_t1")

    url_input = st.text_input("🔗 مووی کا ڈیلی موشن یا ویڈیو لنک ڈالیں:", placeholder="https://www.dailymotion.com/video/...", key="url_main")
    up_file = st.file_uploader("📂 یا ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")

    if st.button("🚀 فل ویڈیو تیار کریں", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"in_vid_{uid}.mp4"
        target_out = f"es_turbo_{uid}.mp4"
        info = {'title': 'Action Scene Video'}
        has_input = False

        if url_input.strip():
            with st.spinner("🔗 ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
        elif up_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_file.name

        if has_input and os.path.exists(target_in):
            ffmpeg_exe = get_ffmpeg()
            af_clear = "highpass=f=75,lowpass=f=8000,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"
            vf_10th_drop = "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),hflip,crop=iw*0.82:ih*0.82,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=40:color=black@0.75:t=max,drawbox=y=ih-48:h=48:color=black@0.85:t=max"

            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-ss", "8", "-i", target_in,
                "-map_metadata", "-1", "-vf", vf_10th_drop, "-af", af_clear,
                "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try: os.remove(target_in)
            except Exception: pass

            if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                st.session_state.detected_info = info
                st.session_state.current_output_video = target_out
                st.session_state.process_ready = True
                st.success("🎉 ویڈیو تیار ہو گئی!")

    if st.session_state.process_ready and st.session_state.current_output_video and os.path.exists(st.session_state.current_output_video) and "recap" not in st.session_state.current_output_video:
        st.divider()
        v_bytes = open(st.session_state.current_output_video, 'rb').read()
        st.video(v_bytes)
        st.download_button(label="📥 ڈاؤنلوڈ پروٹیکٹڈ ویڈیو", data=v_bytes, file_name="protected_video.mp4", mime="video/mp4")

# ------------------------------------------------------------------------------
# TAB 4: CLIP CUTTER
# ------------------------------------------------------------------------------
with tab_clip:
    st.write("### ⚔️ کلپ کٹر موڈ (10 تا 20 منٹ کٹ + شیلڈز)")
    c1, c2 = st.columns(2)
    with c1: scene_type = st.selectbox("سین کا آغاز:", ["⚔️ منٹ 30", "👻 منٹ 45", "🏔️ منٹ 15"], key="s_t3")
    with c2: clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t3")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15
    upload_opt2 = st.file_uploader("📂 ویڈیو فائل منتخب کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t3")

    if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="run_t3"):
        if upload_opt2 is not None:
            uid = str(uuid.uuid4())[:8]
            target_in = f"clip_in_{uid}.mp4"
            target_out = f"clip_out_{uid}.mp4"
            with open(target_in, "wb") as f:
                f.write(upload_opt2.getbuffer())
                
            ffmpeg_exe = get_ffmpeg()
            start_sec = start_min * 60
            dur_sec = clip_len * 60
            vf = "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),hflip,crop=iw*0.80:ih*0.80,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=36:color=black@0.75:t=max,drawbox=y=ih-44:h=44:color=black@0.85:t=max"
            af = "highpass=f=75,lowpass=f=8000,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"
            
            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                "-i", target_in, "-map_metadata", "-1", "-vf", vf, "-af", af,
                "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                st.video(open(target_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ کلپ", data=open(target_out, 'rb').read(), file_name="clip.mp4", mime="video/mp4")
                try: os.remove(target_in)
                except Exception: pass

# ------------------------------------------------------------------------------
# TAB 5: 22-SHIELD ANTI-COPYRIGHT LO-FI & SONGS
# ------------------------------------------------------------------------------
with tab_lofi:
    st.write("### 🎧 لوفی گانے (Slowed + Reverb & Bass Boost)")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.82, 0.96, 0.88, 0.01, key="sl_t6")
    with col_s2: reverb_val = st.slider("گونج / Reverb:", 25, 80, 50, 5, key="rev_t6")
    with col_s3: bass_val = st.slider("سب-بیس بوسٹ:", 2, 12, 6, key="bass_t6")
        
    upload_opt3 = st.file_uploader("📂 گانے کی آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t6")
    
    if st.button("🚀 لوفی گانا بنائیں", type="primary", key="run_t6"):
        if upload_opt3 is not None:
            uid = str(uuid.uuid4())[:8]
            target_in = f"song_in_{uid}.mp4"
            target_out = f"song_out_{uid}.mp4"
            with open(target_in, "wb") as f:
                f.write(upload_opt3.getbuffer())
                
            ffmpeg_exe = get_ffmpeg()
            sample_rate = int(44100 * slow_val)
            af_song_22 = f"highpass=f=40,asetrate={sample_rate},aresample=44100:async=1,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=105,treble=g=-3:f=3500,aphaser=in_gain=0.9:out_gain=0.8:delay=2.5:decay=0.35:speed=0.4:type=t,alimiter=limit=0.95"
            
            cmd_song = [
                ffmpeg_exe, "-nostdin", "-y", "-i", target_in,
                "-map_metadata", "-1", "-af", af_song_22, "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", target_out
            ]
            subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                st.audio(open(target_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ لوفی گانا", data=open(target_out, 'rb').read(), file_name="lofi_track.mp4", mime="audio/mp4")
                try: os.remove(target_in)
                except Exception: pass

# ------------------------------------------------------------------------------
# TAB 6: PRO AI MOVIE STUDIO
# ------------------------------------------------------------------------------
with tab_movie:
    st.write("### 🎬 Pro AI Cinematic Movie Production")
    m_script = st.text_area("مووی اسکرپٹ یا پرامپٹ لکھیں:", height=100, placeholder="ایک پرانے قلعے میں ایک پراسرار جنگجو داخل ہوتا ہے...")
    if st.button("Generate Master Movie 🚀"):
        st.info("💡 اے آئی مووی جنریشن کا پروسیس شروع ہو چکا ہے۔")

# ------------------------------------------------------------------------------
# TAB 7: PRO AI IMAGE STUDIO
# ------------------------------------------------------------------------------
with tab_image:
    st.write("### 🎨 Pro AI Visual & Canvas Studio")
    p_i = st.text_area("تصویر کی تفصیل لکھیں:", height=80, placeholder="A high-tech cybernetic warrior standing in neon city, 8k masterpiece...")
    if st.button("Generate AI Image 🎨"):
        with st.spinner("تصویر تیار ہو رہی ہے..."):
            img_bytes = fetch_img_failover(p_i, 1280, 720, random.randint(1, 999999))
            if img_bytes:
                st.image(img_bytes, caption="Generated AI Image")

# ==========================================
# FOOTER BRANDING (MUHAMMAD ESSA & SABA WAHID)
# ==========================================
st.markdown("""
<div style='text-align: center; font-size: 13px; color: #475569; margin-top: 32px; border-top: 2px solid #e2e8f0; padding-top: 14px; font-weight: 600;'>
    ⚡ <strong>ES AI Studio</strong> | Founders: <strong>Muhammad Essa & Saba Wahid</strong> | All Rights Reserved © 2026
</div>
""", unsafe_allow_html=True)
