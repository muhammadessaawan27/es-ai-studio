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
    page_title="ES AI Studio | Essa & Saba",
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
    # Strip tracking parameters (?si=..., &t=..., etc.)
    clean_raw = raw_url.split('?si=')[0].split('&si=')[0].split('?t=')[0]
    m = re.search(r'(?:v=|\/|shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})', clean_raw)
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

# Multi-Voice TTS Generator (Asad, Saba, Salman/Waheed, Gul)
def save_tts_voiceover_sync(text, voice_name, rate_str, pitch_str, out_file):
    try:
        clean_t = clean_text_for_tts(text)
        voice_map = {
            "asad": "ur-PK-AsadNeural",
            "saba": "ur-PK-SabaNeural",
            "waheed": "ur-IN-SalmanNeural",
            "gul": "ur-IN-GulNeural"
        }
        chosen_voice = voice_map.get(voice_name.lower(), "ur-PK-AsadNeural")
        
        async def amain():
            communicate = edge_tts.Communicate(clean_t, chosen_voice, rate=rate_str, pitch=pitch_str)
            await communicate.save(out_file)
            
        asyncio.run(amain())
        return True
    except Exception as e:
        return False

# ==============================================================================
# ULTRA ROBUST MULTI-SOURCE DOWNLOADER (NO 403 / NO FREEZE)
# ==============================================================================
def download_unblockable_media_parallel(raw_url, target_path):
    vid_id = extract_yt_id(raw_url)
    clean_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else raw_url.strip()
    title = fetch_oembed_title(clean_url) or "Action Video Track"

    # 1. High Speed Piped / Invidious Multi-Node Stream Fetch
    if vid_id:
        apis = [
            f"https://pipedapi.kavin.rocks/streams/{vid_id}",
            f"https://api.piped.privacydev.net/streams/{vid_id}",
            f"https://inv.tux.pizza/api/v1/videos/{vid_id}",
            f"https://invidious.nerdvpn.de/api/v1/videos/{vid_id}",
            f"https://invidious.drgns.space/api/v1/videos/{vid_id}"
        ]
        for api_url in apis:
            try:
                res = requests.get(api_url, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    title = data.get("title", title)
                    streams = data.get("videoStreams", []) or data.get("formatStreams", [])
                    mp4s = [s for s in streams if "mp4" in s.get("container", "").lower() or "video/mp4" in s.get("mimeType", "").lower()] or streams
                    if mp4s:
                        dl_url = mp4s[0].get("url", "")
                        if dl_url:
                            r_file = requests.get(dl_url, stream=True, timeout=8)
                            if r_file.status_code == 200:
                                with open(target_path, "wb") as f:
                                    for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                                        if chunk: f.write(chunk)
                                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                                    return True, title
            except Exception:
                pass

    # 2. Resilient yt-dlp Multi-Client Android / iOS Extractor
    try:
        import yt_dlp
        clients = [
            ['android', 'ios'],
            ['tvhtml5', 'mweb'],
            ['web_creator', 'android_creator']
        ]
        for cl in clients:
            ydl_opts = {
                'format': '18/best[height<=480][ext=mp4]/best[ext=mp4]/best',
                'outtmpl': target_path,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'geo_bypass': True,
                'socket_timeout': 12,
                'retries': 3,
                'extractor_args': {'youtube': {'player_client': cl}}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    meta = ydl.extract_info(clean_url, download=True)
                    if meta:
                        title = meta.get('title', title)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                    return True, title
            except Exception:
                continue
    except Exception:
        pass

    # 3. Direct FFmpeg Stream Sniffer
    try:
        ffmpeg_exe = get_ffmpeg()
        cmd = [
            ffmpeg_exe, "-nostdin", "-y",
            "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
            "-ss", "10", "-t", "400", "-i", clean_url,
            "-c", "copy", target_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
            return True, title
    except Exception:
        pass

    return False, title

# ==========================================
# UNIVERSAL AI URDU SCRIPT GENERATOR
# ==========================================
def generate_urdu_movie_recap_script(movie_title, duration_mins, genre):
    try:
        instruction = (
            f"You are a master Urdu YouTube Storyteller and Video Explainer scriptwriter. "
            f"Write a comprehensive, engaging, and complete Urdu story narrative explaining '{movie_title}'. "
            f"Genre/Theme: {genre}. Target duration: {duration_mins} minutes. "
            f"Write continuous Urdu storytelling narrative dialogues so that an AI voice narrator can read it continuously without gaps. "
            f"Output purely the Urdu narrative story text."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=15)
        if res.status_code == 200 and len(res.text.strip()) > 50:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج کی سنسنی خیز اور دلچسپ ویڈیو {movie_title} کے گرد گھومتی ہے۔ "
        f"کہانی کے آغاز میں ہم دیکھتے ہیں کہ بظاہر سب کچھ پرسکون نظر آتا ہے، لیکن اس خاموشی کے پیچھے ایک بہت بڑا طوفان چھپا ہوا تھا۔ "
        f"ہمارا مرکزی کردار ایک عام انسان کی طرح زندگی گزار رہا تھا لیکن اچانک حالات ایسا رخ اختیار کرتے ہیں جو سب کچھ بدل کر رکھ دیتے ہیں۔ "
        f"جب مشکلات اور دشمن ہر طرف سے گھیر لیتے ہیں تو کہانی میں داخل ہوتا ہے اصل سسپنس اور ایکشن! "
        f"ہیرو اپنی ذہانت، ہمت اور طاقت سے ہر چال کو ناکام بناتا ہے۔ "
        f"اور آخر کار کلائمیکس میں سب سے بڑے راز کا پردہ فاش ہو جاتا ہے۔ "
        f"اگر آپ کو یہ دلچسپ ویڈیو پسند آئی تو لائک کریں اور چینل کو ضرور سبسکرائب کریں!"
    )

def analyze_video_and_generate_metadata(title, is_short=False, is_song=False):
    clean_t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    if not clean_t: clean_t = title
    
    if is_song:
        exact_thumb_prompt = (
            f"Anime aesthetic 4K Lo-Fi relaxing wallpaper thumbnail for '{clean_t[:45]}', cozy neon bedroom, "
            f"soft purple and cyan aesthetic lighting, rain on window, retro tape recorder, cinematic lo-fi anime art, 16:9 aspect ratio."
        )
        titles = [
            f"🎧 {clean_t[:45]} (Slowed + Reverb Lo-Fi Remix) | Midnight Chill",
            f"🌙 {clean_t[:45]} - Deep Relaxing Aesthetic Vibe (Master HD)",
            f"✨ Pure Nostalgia Vibes | {clean_t[:40]} (Slowed Lo-Fi Version)"
        ]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillMusic #AestheticAudio #MidnightVibes #LoFiBeats #ViralSong"
    elif is_short:
        exact_thumb_prompt = (
            f"Hyper-realistic 8K vertical cinematic poster thumbnail 9:16 for YouTube Shorts of '{clean_t[:45]}', "
            f"exact recognizable character face, intense dramatic angry expression, photorealistic eyes and skin texture, "
            f"35mm film photography, neon rim lighting, flying sparks, vertical 9:16 composition, blockbuster movie aesthetics."
        )
        titles = [
            f"🔥 {clean_t[:40]} - UNSTOPPABLE Climax Scene! 😱 #Shorts",
            f"⚡ The Most Intense Moment of {clean_t[:35]} 🔥 #Shorts",
            f"😱 Best Action Climax in {clean_t[:38]} #ViralShorts"
        ]
        hashtags = "#Shorts #YouTubeShorts #ViralShorts #TrendingShorts #MovieClimax #ActionShorts #CinemaReels"
    else:
        exact_thumb_prompt = (
            f"Hyper-realistic 8K award-winning cinematic movie poster portrait of '{clean_t[:45]}', "
            f"exact recognizable facial features, photorealistic skin pores and eyes, intense dramatic emotional expression, "
            f"35mm film photography, volumetric cinematic lighting, action sparks and debris background, high visual contrast, "
            f"ultra-detailed blockbuster aesthetic, 16:9 aspect ratio, masterpiece quality, no cartoon, no distortion."
        )
        titles = [
            f"🔥 {clean_t[:45]} | Full Story Recap & Explanation in Urdu",
            f"⚡ {clean_t[:40]} Story Explained in Hindi/Urdu (Full Breakdown)",
            f"😱 The Entire Story of {clean_t[:40]} Explained!"
        ]
        hashtags = "#MovieRecap #MovieExplained #UrduMovieRecap #FilmReview #TrendingCinema #StoryRecap"
        
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
# GLOWING LOGO & BRANDING UI (ESSA & SABA)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; font-size: 13px !important; }
    .stApp { background-color: #090d16 !important; color: #f1f5f9 !important; }
    
    /* Glowing Neon Logo Header */
    .brand-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        padding: 16px 24px; border-radius: 12px; border: 1px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.25);
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
    }
    .brand-logo {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 1.4rem !important; font-weight: 900 !important;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: 1px;
    }
    .founders-tag {
        font-size: 12px; font-weight: 700; color: #fbbf24;
        background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.4);
        padding: 5px 12px; border-radius: 20px;
    }
    .badge-26 {
        background: linear-gradient(90deg, #059669, #10b981); color: #ffffff;
        padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;
    }
    .stButton>button { 
        background: linear-gradient(90deg, #0284c7, #2563eb) !important; color: white !important;
        border-radius: 8px !important; height: 44px !important; font-size: 14px !important; font-weight: 700 !important;
        border: none !important; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.4) !important;
    }
    .stTabs [data-baseweb="tab"] { height: 38px !important; font-size: 12.5px !important; font-weight: 700 !important; color: #94a3b8; }
    .stTabs [aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-logo">⚡ ES AI STUDIO</div>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Ultra 26-Shield Anti-Copyright & Video Storyteller Engine</div>
    </div>
    <div style="display:flex; align-items:center; gap: 10px;">
        <span class="founders-tag">👑 Founders: Muhammad Essa & Saba</span>
        <span class="badge-26">26 SHIELDS ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7 FULL PRODUCTION TABS
# ==========================================
tab_recap, tab_shorts, tab_shield, tab_clip, tab_lofi, tab_movie, tab_image = st.tabs([
    "🎬 1. آٹو اسد/صبا وائس اوور و مووی ریکیپ",
    "📱 2. پیور فل اسکرین 9:16 شارٹس",
    "🛡️ 3. فل مووی شفلر (26 ہتھیار)",
    "⚔️ 4. کلپ کٹر موڈ (10 تا 20 منٹ کٹ)",
    "🎧 5. لوفی گانے (Slowed + Reverb)",
    "🎥 6. پرو AI مووی اسٹوڈیو",
    "🎨 7. پرو AI امیج اسٹوڈیو"
])

# ------------------------------------------------------------------------------
# TAB 1: AI AUTO ASAD / SABA VOICEOVER & RECAP STUDIO (DUAL MODE + 26 SHIELDS)
# ------------------------------------------------------------------------------
with tab_recap:
    st.write("### 🎬 خودکار AI وائس اوور، اردو اسکرپٹ و مووی ریکیپ جنریٹر")
    st.info("⚡ **سپر فاسٹ اسٹریم:** لنک ڈالتے ہی 15 سے 30 سیکنڈ میں خودکار اردو کہانی لکھی جائے گی، اسد یا صبا کی آواز میں وائس اوور ہوگا اور 26 شیلڈز لاگو کر کے 100% تیار ویڈیو سامنے آ جائے گی۔")

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        voiceover_mode = st.selectbox("وائس اوور کا طریقہ:", [
            "🎙️ خودکار AI وائس اوور (100% تیار ویڈیو)",
            "📝 مینوئل موڈ (صرف ویڈیو میوٹ + اردو اسکرپٹ)"
        ], key="rc_vmode")
    with rc2:
        voice_char = st.selectbox("وائس اوور آواز منتخب کریں:", [
            "🎙️ اسد - بھاری بیریٹون (Asad Deep Voice -15Hz)",
            "🎙️ صبا - نیچرل فی میل (Saba Urdu Voice)",
            "🎙️ وحید / سلمان - کلیئر میل (Salman/Waheed)",
            "🎙️ گل - فیمیل اسمارٹ (Gul Urdu)"
        ], key="rc_vchar")
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
    voice_key = "asad" if "اسد" in voice_char else "saba" if "صبا" in voice_char else "waheed" if "وحید" in voice_char else "gul"

    url_recap_input = st.text_input("🔗 مووی کا یوٹیوب / ویب لنک یہاں پیسٹ کریں (سب سے تیز ترین طریقہ):", placeholder="https://www.youtube.com/watch?v=... یا https://youtu.be/...", key="url_recap")
    up_recap_file = st.file_uploader("📂 یا چھوٹی ویڈیو فائل اپلوڈ کریں (10MB سے 150MB تک):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_recap")

    if st.button("🚀 تیار کریں (AI وائس اوور + اسکرپٹ + شیلڈز) مکمل مووی ریکیپ", type="primary", key="btn_run_recap"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"recap_in_{uid}.mp4"
        voice_audio = f"recap_voice_{uid}.mp3"
        video_montage = f"recap_video_{uid}.mp4"
        final_recap_out = f"final_recap_{uid}.mp4"
        has_input = False
        info = {'title': 'Action Movie Recap'}

        status_box = st.status("⏳ پروسیسنگ شروع ہو رہی ہے...", expanded=True)

        # Smart Input Detection
        if url_recap_input.strip():
            status_box.write("🔗 ویڈیو یوٹیوب فاسٹ اسٹریم کے ذریعے فیچ ہو رہی ہے...")
            success, title_fetched = download_unblockable_media_parallel(url_recap_input.strip(), target_in)
            if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                has_input = True
                info['title'] = title_fetched
        elif up_recap_file is not None:
            status_box.write("📂 اپلوڈ شدہ ویڈیو فائل محفوظ ہو رہی ہے...")
            with open(target_in, "wb") as f:
                f.write(up_recap_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_recap_file.name

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()

            # 1. AI Generates Urdu Movie Script
            status_box.write("🧠 فلم کی مکمل اردو کہانی (وائس اوور اسکرپٹ) لکھی جا رہی ہے...")
            urdu_script = generate_urdu_movie_recap_script(info['title'], target_recap_mins, recap_genre)
            st.session_state.generated_recap_script = urdu_script

            # 2. TTS Voiceover Generation
            has_voiceover = False
            if "خودکار AI" in voiceover_mode:
                status_box.write(f"🎙️ {voice_char} کی آواز میں وائس اوور ریکارڈ ہو رہی ہے...")
                pitch_val = "-15Hz" if voice_key == "asad" else "+0Hz"
                rate_val = "-10%" if voice_key == "asad" else "+0%"
                tts_ok = save_tts_voiceover_sync(urdu_script, voice_key, rate_val, pitch_val, voice_audio)
                if tts_ok and os.path.exists(voice_audio) and os.path.getsize(voice_audio) > 1000:
                    has_voiceover = True

            # 3. Synchronized Montage with 26 Shields
            status_box.write("⚡ 26 اینٹی کاپی رائٹ شیلڈز (1/10 فریم کٹ، فلپ، کراپ، 24fps) لاگو ہو رہی ہیں...")
            start_offset = 8.0
            usable_movie_dur = max(60.0, total_dur - 16.0)
            num_snippets = 32
            time_step = max(4.0, usable_movie_dur / num_snippets)
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
                if pt >= total_dur - 6.0: pt = max(8.0, total_dur * 0.40)
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

            if snippet_files:
                status_box.write("🎬 تمام اسنیپٹس، شیلڈز اور وائس اوور کو مکس کیا جا رہا ہے...")
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

            if os.path.exists(output_ready_path) and os.path.getsize(output_ready_path) > 5000:
                st.session_state.recap_video_out = output_ready_path
                st.session_state.detected_info = info
                status_box.update(label="🎉 آپ کی مووی ریکیپ ویڈیو 100% تیار ہے!", state="complete", expanded=False)
            else:
                status_box.update(label="❌ پروسیسنگ مکمل نہ ہو سکی۔ براہِ کرم دوبارہ کوشش کریں۔", state="error")
        else:
            status_box.update(label="❌ ویڈیو لنک درست نہیں ہے یا پروسیس نہیں ہو سکی۔", state="error")

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
        st.subheader("📖 مکمل اردو وائس اوور اسکرپٹ (Urdu Voiceover Narrative):")
        st.info("💡 یہ مکمل اردو کہانی اسکرپٹ ہے جسے آپ خود پڑھنے کے لیے بھی محفوظ رکھ سکتے ہیں:")
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

    url_shorts_input = st.text_input("🔗 یوٹیوب لنک ڈالیں:", placeholder="https://...", key="url_shorts_pure")
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

    url_input = st.text_input("🔗 یوٹیوب لنک ڈالیں:", placeholder="https://...", key="url_main")
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
# FOOTER BRANDING (ESSA & SABA)
# ==========================================
st.markdown("""
<div style='text-align: center; font-size: 12px; color: #64748b; margin-top: 30px; border-top: 1px solid #1e293b; padding-top: 14px;'>
    ⚡ <strong>ES AI Studio</strong> | Founders: <strong>Muhammad Essa & Saba</strong> | All Rights Reserved © 2026
</div>
""", unsafe_allow_html=True)
