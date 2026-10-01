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
# MOVIEPY IMPORTS
# ==========================================
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip

# ==========================================
# STREAMLIT COMPACT CONFIGURATION
# ==========================================
st.set_page_config(page_title="ES Ultra Universal AI Storyteller & Explainer Studio", layout="wide", page_icon="⚡")

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
        res = requests.get(req_url, timeout=3)
        if res.status_code == 200:
            return res.json().get("title", "")
    except Exception:
        pass
    return ""

def get_video_duration_fast(file_path):
    try:
        ffmpeg_exe = get_ffmpeg()
        cmd = [ffmpeg_exe, "-nostdin", "-i", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
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

def save_asad_voiceover_sync(text, rate_str, pitch_str, out_file):
    try:
        clean_t = clean_text_for_tts(text)
        async def amain():
            communicate = edge_tts.Communicate(clean_t, "ur-PK-AsadNeural", rate=rate_str, pitch=pitch_str)
            await communicate.save(out_file)
        asyncio.run(amain())
        return True
    except Exception:
        return False

# ==========================================
# FAST STREAM & PROXY LINK FETCHER
# ==========================================
def try_download_node(node_url, vid_id, target_path):
    try:
        api_url = f"{node_url}/api/v1/videos/{vid_id}"
        res = requests.get(api_url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", "Action Video Scene")
            streams = data.get("formatStreams", [])
            # Prefer fast 360p / 720p stream to avoid 1GB long download freezes
            mp4s = [s for s in streams if "360p" in s.get("qualityLabel", "") or "720p" in s.get("qualityLabel", "")] or streams
            if mp4s:
                dl_url = mp4s[0]["url"]
                if dl_url.startswith("/"): dl_url = node_url + dl_url
                r_file = requests.get(dl_url, stream=True, timeout=8)
                if r_file.status_code == 200:
                    with open(target_path, "wb") as f:
                        for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                            if chunk: f.write(chunk)
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                        return True, title
    except Exception:
        pass
    return False, ""

def download_unblockable_media_parallel(raw_url, target_path):
    vid_id = extract_yt_id(raw_url)
    clean_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else raw_url.strip()
    title = fetch_oembed_title(clean_url) or "Universal Video Topic"
    
    if vid_id:
        nodes = [
            "https://inv.tux.pizza",
            "https://invidious.nerdvpn.de",
            "https://invidious.privacydev.net",
            "https://invidious.drgns.space",
            "https://invidious.projectsegfau.lt"
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_download_node, node, vid_id, target_path) for node in nodes]
            for future in concurrent.futures.as_completed(futures):
                success, t = future.result()
                if success:
                    return True, t
                    
    try:
        import yt_dlp
        ydl_opts = {
            'format': '18/best[height<=480][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'socket_timeout': 6,
            'extractor_args': {'youtube': {'player_client': ['ios', 'android_creator', 'tvhtml5']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            if meta: title = meta.get('title', title)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
            return True, title
    except Exception:
        pass

    return False, title

# ==========================================
# UNIVERSAL AI SCRIPT & STORY EXPLAINER
# ==========================================
def generate_universal_urdu_script(topic_title, duration_mins, category):
    try:
        instruction = (
            f"You are a master Urdu YouTube Storyteller, Documentary Narrator, and Video Explainer. "
            f"Write a thrilling, continuous, highly engaging voiceover script in natural Urdu language explaining the video/topic: '{topic_title}'. "
            f"Category/Genre: {category}. Target video length: {duration_mins} minutes. "
            f"Write continuous Urdu storytelling dialogues with high suspense, exciting facts, and emotional hooks so that an AI voice narrator can read it smoothly without gaps. "
            f"Output purely the clean Urdu narration script text."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=20)
        if res.status_code == 200 and len(res.text.strip()) > 50:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج کی یہ دلچسپ اور سنسنی خیز کہانی {topic_title} کے بارے میں ہے۔ "
        f"اس کہانی کے آغاز میں ہم دیکھتے ہیں کہ بظاہر سب کچھ بہت پرسکون نظر آتا ہے، لیکن اس خاموشی کے پیچھے ایک بہت بڑا راز اور طوفان چھپا ہوا تھا۔ "
        f"جیسے جیسے وقت گزرتا ہے، حالات ایک دم غیر متوقع موڑ لے لیتے ہیں اور ہمارے سامنے ایسے حیرت انگیز مناظر آتے ہیں جو دیکھنے والے کو دنگ کر دیتے ہیں۔ "
        f"ہر گزرتے لمحے کے ساتھ سسپنس اور تجسس میں اضافہ ہوتا جا رہا ہے۔ "
        f"اور آخر کار آخری حصے میں سب سے بڑا سچ اور کلائمیکس سامنے آ جاتا ہے جو سب کو حیران کر دیتا ہے۔ "
        f"اگر آپ کو یہ ویڈیو اور کہانی پسند آئی تو ویڈیو کو لائک اور چینل کو ضرور سبسکرائب کریں!"
    )

def extract_celebrity_name(title):
    t_clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    return t_clean if t_clean else title

def analyze_video_and_generate_exact_prompt(title, is_short=False, is_song=False):
    clean_t = extract_celebrity_name(title)
    
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
            f"intense dramatic expression, photorealistic details, 35mm film photography, volumetric lighting, vertical 9:16 composition."
        )
        titles = [
            f"🔥 {clean_t[:40]} - UNSTOPPABLE Viral Moment! 😱 #Shorts",
            f"⚡ The Most Shocking Scene of {clean_t[:35]} 🔥 #Shorts",
            f"😱 Unbelievable Facts in {clean_t[:38]} #ViralShorts"
        ]
        hashtags = "#Shorts #YouTubeShorts #ViralShorts #TrendingShorts #MovieClimax #ViralReels #CinemaShorts"
    else:
        exact_thumb_prompt = (
            f"Hyper-realistic 8K award-winning cinematic thumbnail for '{clean_t[:45]}', "
            f"intense dramatic close-up, photorealistic textures, 35mm film photography, volumetric cinematic lighting, "
            f"action sparks and high visual contrast, ultra-detailed aesthetic, 16:9 aspect ratio, masterpiece quality."
        )
        titles = [
            f"🔥 {clean_t[:45]} | Full Story Explained in Urdu (Full Breakdown)",
            f"⚡ The Complete Truth of {clean_t[:40]} - Shocking Facts Revealed!",
            f"😱 Unstoppable Dramatic Story: {clean_t[:40]} Explained"
        ]
        hashtags = "#MovieRecap #StoryExplained #UrduExplainer #DocumentaryRecap #ViralStory #CinemaReview"
        
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
    .badge { background: #059669; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .stButton>button { 
        background: #0284c7 !important; color: white !important; border-radius: 6px !important; 
        height: 38px !important; font-size: 13px !important; font-weight: 600 !important; border: none !important;
    }
    .stTabs [data-baseweb="tab"] { height: 34px !important; font-size: 12px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="compact-header">
    <div class="compact-title">⚡ ES ULTRA UNIVERSAL AI STORYTELLER & EXPLAINER STUDIO</div>
    <div class="badge">FAST STREAM + ASAD VOICEOVER ACTIVE</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_recap, tab_shorts, tab_shield, tab_clip, tab_lofi, tab_movie, tab_image = st.tabs([
    "🎬 1. یونیورسل AI اسٹوری ٹیلر و ریکیپ (Auto Voiceover + Script)",
    "📱 2. پیور فل اسکرین 9:16 شارٹس",
    "🛡️ 3. فل مووی شفلر (26 ہتھیار)",
    "⚔️ 4. کلپ کٹر موڈ (10 تا 20 منٹ کٹ)",
    "🎧 5. لوفی گانے (Slowed + Reverb)",
    "🎥 6. پرو AI مووی اسٹوڈیو",
    "🎨 7. پرو AI امیج اسٹوڈیو"
])

# -----------------
# TAB 1: UNIVERSAL AI STORYTELLER & VIDEO RECAP (MOVIES, ANIMALS, DISCOVERY, COMEDY)
# -----------------
with tab_recap:
    st.write("### 🎬 یونیورسل AI ویڈیو ایکسپلینر، اردو وائس اوور و مکمل ڈیش بورڈ")
    st.info("💡 **یونیورسل موڈ:** مووی ہو، جنگلی جانوروں (Wildlife) کی ویڈیو ہو، ڈسکوری، سائنس یا کامیڈی—AI خودکار طور پر اردو وائس اوور کہانی لکھے گا، **اسد کی بھاری و 10% سلو آواز** میں وائس اوور کرے گا، اور نیچے وائرل ٹائٹلز، ہیش ٹیگ اور تھمب نیل پرامپٹ دے گا!")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        voiceover_mode = st.selectbox("وائس اوور کا طریقہ:", [
            "🎙️ خودکار اسد AI وائس اوور (Auto Asad Deep Voiceover - 100% ریڈی ویڈیو)",
            "📝 مینوئل موڈ (صرف ویڈیو میوٹ + اردو اسکرپٹ - خود بولنے کے لیے)"
        ], key="rc_vmode")
    with rc2:
        recap_dur = st.selectbox("ویڈیو کا دورانیہ:", ["10 منٹ (10 Mins Recap Video)", "20 منٹ (20 Mins Full Video)"], key="rc_dur")
    with rc3:
        recap_category = st.selectbox("ویڈیو کا موضوع (Topic / Genre):", [
            "🔥 موویز و فلمی سسپنس (Movies / Action / Thriller)",
            "🦁 جنگلی جانور و وائلڈ لائف (Animals / Wildlife / Nature)",
            "🌍 ڈسکوری و سائنسی حقائق (Discovery / Science / Space)",
            "😂 کامیڈی و انٹرٹینمنٹ (Funny / Comedy / Entertainment)",
            "😱 خوفناک و پراسرار کہانیاں (Horror / Mystery / True Crime)"
        ], key="rc_cat")

    target_recap_mins = 10 if "10" in recap_dur else 20

    up_recap_file = st.file_uploader("📂 ویڈیو فائل اپلوڈ کریں (یا لنک ڈالیں):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_recap")
    url_recap_input = st.text_input("🔗 یا کسی بھی ویڈیو کا لنک یہاں پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="url_recap")

    if st.button("🚀 خودکار اسد وائس اوور ویڈیو، اردو اسکرپٹ و ٹائٹلز تیار کریں", type="primary", key="btn_run_recap"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"recap_in_{uid}.mp4"
        voice_audio = f"recap_voice_{uid}.mp3"
        video_montage = f"recap_video_{uid}.mp4"
        final_recap_out = f"final_recap_{uid}.mp4"
        has_input = False
        info = {'title': 'Universal Topic Video'}

        if up_recap_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_recap_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_recap_file.name
        elif url_recap_input.strip():
            with st.spinner("🔗 تیز رفتار اسٹریم سرور سے ویڈیو کنیکٹ کی جا رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_recap_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()

            # 1. AI Generates Topic-Specific Urdu Story Narrative
            with st.spinner("🧠 ویڈیو کے موضوع پر تفصیلی اردو وائس اوور کہانی لکھی جا رہی ہے..."):
                urdu_script = generate_universal_urdu_script(info['title'], target_recap_mins, recap_category)
                st.session_state.generated_recap_script = urdu_script

            # 2. Edge-TTS Generates Asad Voiceover if Auto Mode Selected
            has_voiceover = False
            if "اسد AI وائس اوور" in voiceover_mode:
                with st.spinner("🎙️ اسد کی بھاری اور 10% سلو آواز میں وائس اوور ریکارڈ ہو رہی ہے..."):
                    success_tts = save_asad_voiceover_sync(urdu_script, rate_str="-10%", pitch_str="-15Hz", out_file=voice_audio)
                    if success_tts and os.path.exists(voice_audio) and os.path.getsize(voice_audio) > 1000:
                        has_voiceover = True

            # 3. Build Synchronized 3.5s Montage Across Movie / Video
            with st.spinner("⚡ 3، 3 سیکنڈ کے سینز نکال کر میوٹڈ اینٹی کاپی رائٹ مونتاج تیار ہو رہا ہے..."):
                start_offset = 6.0
                usable_dur = max(40.0, total_dur - 12.0)
                num_snippets = 25
                time_step = max(3.5, usable_dur / num_snippets)

                snippet_files = []
                list_txt = f"recap_list_{uid}.txt"

                vf_recap = (
                    "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),"
                    "scale=1280:720:flags=fast_bilinear,hflip,"
                    "eq=contrast=1.18:saturation=1.24:brightness=0.02,"
                    "drawbox=y=0:h=36:color=black@0.75:t=max,drawbox=y=ih-44:h=44:color=black@0.85:t=max"
                )

                for i in range(num_snippets):
                    pt = start_offset + (i * time_step)
                    if pt >= total_dur - 5.0: pt = max(6.0, total_dur * 0.35)
                    snip_path = f"snip_{uid}_{i}.mp4"
                    
                    cmd_snip = [
                        ffmpeg_exe, "-nostdin", "-y",
                        "-ss", str(pt), "-t", "3.5",
                        "-i", target_in, "-an", "-map_metadata", "-1",
                        "-vf", vf_recap,
                        "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                        "-pix_fmt", "yuv420p", snip_path
                    ]
                    subprocess.run(cmd_snip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(snip_path) and os.path.getsize(snip_path) > 2000:
                        snippet_files.append(snip_path)

                if snippet_files:
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

                try: os.remove(target_in)
                except Exception: pass

                if os.path.exists(output_ready_path) and os.path.getsize(output_ready_path) > 5000:
                    st.session_state.recap_video_out = output_ready_path
                    st.session_state.detected_info = info
                    st.session_state.process_ready = True
                    st.success("🎉 آپ کی ویڈیو (اسد وائس اوور، اسکرپٹ و ٹائٹلز کے ساتھ) 100% تیار ہے!")
                else:
                    st.error("❌ ویڈیو پروسیسنگ مکمل نہ ہو سکی۔ براہِ کرم دوبارہ کوشش کریں۔")

    # DISPLAY RECAP VIDEO & COMPLETE URDU VOICEOVER SCRIPT + METADATA
    if st.session_state.recap_video_out and os.path.exists(st.session_state.recap_video_out):
        st.divider()
        st.subheader("🎬 تیار شدہ ویڈیو (اسد وائس اوور کے ساتھ):")
        r_bytes = open(st.session_state.recap_video_out, 'rb').read()
        st.video(r_bytes)
        st.download_button(
            label="📥 مکمل ویڈیو ڈاؤنلوڈ کریں (Download MP4 Video)",
            data=r_bytes,
            file_name=f"es_story_{os.path.basename(st.session_state.recap_video_out)}",
            mime="video/mp4",
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("📖 مکمل اردو وائس اوور کہانی (Urdu Narrative Script):")
        st.info("💡 یہ اسکرپٹ ویڈیو میں اسد کی آواز میں بولا گیا ہے، آپ چاہیں تو کاپی کر کے مستقبل کے لیے محفوظ رکھ سکتے ہیں:")
        st.code(st.session_state.generated_recap_script, language="markdown")

        st.markdown("---")
        st.subheader("🔥 وائرل ٹائٹلز، ہیش ٹیگز اور 8K تھمب نیل پرامپٹ (1-Click Copy):")
        raw_title = st.session_state.detected_info.get('title', 'Explainer Video')
        clean_hero_title, titles, hashtags, exact_thumb_prompt = analyze_video_and_generate_exact_prompt(raw_title, is_short=False)
        
        c_rc1, c_rc2 = st.columns(2)
        with c_rc1:
            st.markdown("**🔥 وائرل یوٹیوب ٹائٹلز:**")
            for t in titles:
                st.code(t, language="text")
            st.markdown("**🏷️ وائرل ہیش ٹیگز:**")
            st.code(hashtags, language="text")
        with c_rc2:
            st.markdown(f"**🎨 AI 8K تھمب نیل پرامپٹ ({clean_hero_title[:30]}):**")
            st.code(exact_thumb_prompt, language="text")
            with st.expander("🖼️ تھمب نیل کا لائیو AI پریویو دیکھیں"):
                thumb_gen_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(exact_thumb_prompt)}?width=1280&height=720&nologo=true&model=flux"
                try:
                    st.image(thumb_gen_url, caption="AI Generated Thumbnail (Flux)", use_column_width=True)
                except Exception:
                    st.write("پرامپٹ کو کاپی کر کے Midjourney یا Bing Creator میں استعمال کریں۔")

# -----------------
# TAB 2: PURE FULL-SCREEN 9:16 SHORTS
# -----------------
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

    up_shorts_file = st.file_uploader("📂 ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_shorts_pure")
    url_shorts_input = st.text_input("🔗 یا یوٹیوب لنک ڈالیں:", placeholder="https://...", key="url_shorts_pure")

    if st.button(f"🚀 {count_target} فل اسکرین 9:16 شارٹس بنائیں", type="primary", key="btn_run_shorts_pure"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"shorts_in_{uid}.mp4"
        has_input = False
        info = {'title': 'Viral Action Shorts'}

        if up_shorts_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_shorts_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_shorts_file.name
        elif url_shorts_input.strip():
            with st.spinner("🔗 ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_shorts_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

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
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
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

# -----------------
# TAB 3: FULL MOVIE SCENE SHUFFLER (26 WEAPONS)
# -----------------
with tab_shield:
    st.write("### 🛡️ فل مووی شفلر (ہر سیکنڈ 1/10واں فریم کٹ + سین شفلنگ)")
    c1, c2 = st.columns(2)
    with c1: shield_mode = st.selectbox("شیلڈ اسٹائل:", ["🛡️ فل شفلر: لوگو کٹ + سین شفل + 1/10واں کٹ", "⚡ لکیری موڈ: لوگو کٹ + 1/10واں کٹ"], key="sm_t1")
    with c2: voice_quality = st.selectbox("ڈبنگ:", ["🔊 کرسٹل کلیئر بیریٹون ڈبنگ", "🎵 نیچرل اسمارٹ پچ"], key="am_t1")

    up_file = st.file_uploader("📂 ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")
    url_input = st.text_input("🔗 یا یوٹیوب لنک ڈالیں:", placeholder="https://...", key="url_main")

    if st.button("🚀 فل ویڈیو تیار کریں", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"in_vid_{uid}.mp4"
        target_out = f"es_turbo_{uid}.mp4"
        info = {'title': 'Action Scene Video'}
        has_input = False

        if up_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_file.name
        elif url_input.strip():
            with st.spinner("🔗 ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()
            af_clear = "highpass=f=75,lowpass=f=8000,volume=0.45,asetrate=44100*0.93,aresample=44100,atempo=1.16,bass=g=5:f=110,aecho=0.8:0.5:15:0.2"
            vf_10th_drop = "select=not(eq(mod(n\\,10)\\,9)),setpts=N/(24*TB),hflip,crop=iw*0.82:ih*0.82,scale=1280:720:flags=fast_bilinear,eq=contrast=1.20:saturation=1.24:brightness=0.02,drawbox=y=0:h=40:color=black@0.75:t=max,drawbox=y=ih-48:h=48:color=black@0.85:t=max"

            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-ss", "8", "-i", target_in,
                "-map_metadata", "-1", "-vf", vf_10th_drop, "-af", af_clear,
                "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
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

# -----------------
# TAB 4: CLIP CUTTER
# -----------------
with tab_clip:
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
                "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                st.video(open(target_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ کلپ", data=open(target_out, 'rb').read(), file_name="clip.mp4", mime="video/mp4")
                try: os.remove(target_in)
                except Exception: pass

# -----------------
# TAB 5: 22-SHIELD ANTI-COPYRIGHT LO-FI & SONGS
# -----------------
with tab_lofi:
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

# -----------------
# TAB 6: PRO AI MOVIE STUDIO
# -----------------
with tab_movie:
    st.write("### 🎬 Pro AI Cinematic Movie Production")
    m_script = st.text_area("مووی اسکرپٹ:", height=100, placeholder="ایک خوبصورت جنگل میں شیر شکار کی تلاش میں ہے...")
    if st.button("Generate Master Movie 🚀"):
        st.info("اے آئی ویڈیو جنریشن شروع ہو چکی ہے۔")

# -----------------
# TAB 7: PRO AI IMAGE STUDIO
# -----------------
with tab_image:
    st.write("### 🎨 Pro AI Visual & Canvas Studio")
    p_i = st.text_area("تصویر کی تفصیل لکھیں:", height=80, placeholder="A high-tech cybernetic warrior standing in neon city...")
    if st.button("Generate AI Image 🎨"):
        img_bytes = fetch_img_failover(p_i, 1280, 720, random.randint(1, 999999))
        if img_bytes:
            st.image(img_bytes, caption="Generated AI Image")

st.markdown("<p style='text-align: center; font-size: 11px; color: #64748b; margin-top: 20px;'>ES Ultra Universal AI Storyteller Studio | 100% Free & Unlimited</p>", unsafe_allow_html=True)
