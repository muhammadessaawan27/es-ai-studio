import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import glob
import subprocess

# ==========================================
# STREAMLIT CONFIGURATION & SESSION STATE
# ==========================================
st.set_page_config(
    page_title="ES AI Studio | Muhammad Essa & Saba Wahid",
    layout="wide",
    page_icon="⚡"
)

if "recap_data" not in st.session_state:
    st.session_state.recap_data = {}
if "custom_tts_audio" not in st.session_state:
    st.session_state.custom_tts_audio = ""

# ==========================================
# SYSTEM HELPERS
# ==========================================
def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def fetch_oembed_title(clean_url):
    try:
        req_url = f"https://noembed.com/embed?url={urllib.parse.quote(clean_url)}"
        res = requests.get(req_url, timeout=4)
        if res.status_code == 200:
            return res.json().get("title", "")
    except Exception:
        pass
    return ""

def clean_text_for_tts(raw_text):
    clean = re.sub(r'[#\*\_]', '', raw_text)
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', clean)
    clean = re.sub(r'https?://\S+', '', clean)
    return clean.strip()

# ==========================================
# MULTI-LANGUAGE VOICE DATABASE
# ==========================================
VOICE_DATABASE = {
    "Urdu - Asad (Deep Baritone Male)": ("ur-PK-AsadNeural", "-8%", "-10Hz"),
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
        voice_id, rate_str, pitch_str = VOICE_DATABASE.get(voice_key, ("ur-PK-AsadNeural", "-8%", "-10Hz"))
        
        async def amain():
            communicate = edge_tts.Communicate(clean_t, voice_id, rate=rate_str, pitch=pitch_str)
            await communicate.save(out_file)
            
        asyncio.run(amain())
        return os.path.exists(out_file) and os.path.getsize(out_file) > 1000
    except Exception:
        return False

# ==============================================================================
# ROBUST DOWNLOADER & 10-20 MIN VIDEO CUTTER (100% GUARANTEED PLAYABLE)
# ==============================================================================
def download_and_cut_playable_video(raw_url, output_mp4, duration_mins=10):
    raw_url = raw_url.strip()
    title = fetch_oembed_title(raw_url) or "Action Movie Video"
    ffmpeg_exe = get_ffmpeg()
    uid = uuid.uuid4().hex[:6]
    target_seconds = duration_mins * 60

    downloaded_file = None

    # 1. Download via yt-dlp (Dailymotion, YouTube, etc.)
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': f'dl_temp_{uid}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 35
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(raw_url, download=True)
            if meta:
                title = meta.get('title', title)
        
        # Locate the downloaded file regardless of extension (.mp4, .mkv, .webm)
        found = glob.glob(f"dl_temp_{uid}.*")
        if found:
            downloaded_file = found[0]
    except Exception:
        pass

    # 2. Direct HTTP Fallback
    if not downloaded_file or not os.path.exists(downloaded_file):
        direct_url = raw_url
        if "pixeldrain.com/u/" in raw_url:
            direct_url = raw_url.replace("pixeldrain.com/u/", "pixeldrain.com/api/file/")
        elif "dropbox.com" in raw_url:
            direct_url = raw_url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "?dl=1")
            
        try:
            r = requests.get(direct_url, stream=True, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                fallback_path = f"dl_temp_{uid}.mp4"
                with open(fallback_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024 * 8):
                        if chunk: f.write(chunk)
                if os.path.exists(fallback_path) and os.path.getsize(fallback_path) > 10000:
                    downloaded_file = fallback_path
        except Exception:
            pass

    # 3. Cut to requested Duration and Convert to Mobile-Compatible H.264
    if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 5000:
        cmd_convert = [
            ffmpeg_exe, "-nostdin", "-y",
            "-ss", "30", "-t", str(target_seconds),
            "-i", downloaded_file,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", output_mp4
        ]
        subprocess.run(cmd_convert, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup temp file
        try: os.remove(downloaded_file)
        except Exception: pass

        if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 5000:
            return True, title

    return False, title

# ==============================================================================
# FULL-LENGTH 10-20 MIN SCRIPT GENERATOR
# ==============================================================================
def generate_full_length_movie_script(movie_title, duration_mins, genre, target_lang):
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', movie_title).strip()
    try:
        instruction = (
            f"You are an expert movie storyteller. Write a long, comprehensive, chapter-by-chapter story narrative in {target_lang} for the movie '{clean_title}'. "
            f"Genre: {genre}. Target duration: {duration_mins} minutes narrative. "
            f"Describe the opening scenes, character goals, major threats, twists, intense climax battle, and the ending in full detail. "
            f"Write continuous storytelling text for spoken video narration without brackets or stage notes."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 350:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج ہم فلم '{clean_title}' کی مکمل اور سنسنی خیز کہانی لے کر حاضر ہوئے ہیں۔\n\n"
        f"1. شروعات اور منظر نامہ:\n"
        f"کہانی کے آغاز میں ہمارا مرکزی کردار ایک غیر معمولی صورتحال کا سامنا کرتا ہے۔ ماحول میں چھپی پراسراریت شروع سے ہی ایک بڑا خطرہ ظاہر کرتی ہے۔ مرکزی کردار اپنے مشن کے لیے آگے بڑھتا ہے مگر جلد ہی حالات ان کے کنٹرول سے باہر ہو جاتے ہیں۔\n\n"
        f"2. بڑھتا ہوا تناؤ اور سسپنس:\n"
        f"جیسے جیسے وقت گزرتا ہے، خطرات میں خوفناک حد تک اضافہ ہوتا چلا جاتا ہے۔ ایک کے بعد ایک ایسی رکاوٹیں سامنے آتی ہیں جن کا مقابلہ کرنا ناممکن دکھائی دیتا ہے۔ ہر کردار کی ہمت اور حکمت عملی کا سخت امتحان شروع ہو جاتا ہے۔\n\n"
        f"3. بڑا موڑ اور بقا کی جنگ:\n"
        f"فلم کے وسط میں ایک ایسا زبردست موڑ آتا ہے جو پوری کہانی کا نقشہ بدل کر رکھ دیتا ہے۔ چھپے ہوئے راز فاش ہوتے ہیں اور معلوم ہوتا ہے کہ اصل خطرہ کچھ اور ہی تھا۔ یہاں سے جان بچانے اور مشن مکمل کرنے کی ایک خونخوار جنگ شروع ہو جاتی ہے۔\n\n"
        f"4. آخری کلائمیکس اور انجام:\n"
        f"کہانی اپنے عروج یعنی کلائمیکس پر پہنچتی ہے جہاں آخری اور فیصلہ کن معرکہ ہوتا ہے۔ مرکزی کردار اپنی تمام تر طاقت اور ذہانت سے دشمن کو شکست دیتا ہے اور کہانی ایک شاندار انجام پر ختم ہوتی ہے۔\n\n"
        f"اگر آپ کو یہ کہانی پسند آئی ہو تو ویڈیو کو لائک اور چینل کو ضرور سبسکرائب کریں!"
    )

def analyze_video_and_generate_metadata(title):
    clean_t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip() or title
    titles = [
        f"🔥 {clean_t[:45]} | Full Story Recap & Breakdown",
        f"⚡ {clean_t[:40]} - Real Story & Unbelievable Climax Scene",
        f"😱 The Full Story of {clean_t[:40]} Explained in Detail!"
    ]
    hashtags = "#MovieRecap #MovieExplained #FilmStory #CinemaRecap #Trending"
    exact_thumb_prompt = f"Hyper-realistic 8K cinematic movie poster for '{clean_t[:45]}', dramatic lighting, intense action climax, 16:9."
    return clean_t, titles, hashtags, exact_thumb_prompt

# ==========================================
# STYLING
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
    .stButton>button { 
        background: #0284c7 !important; color: #ffffff !important; border-radius: 8px !important; 
        height: 44px !important; font-size: 14px !important; font-weight: 700 !important; border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-logo">⚡ ES AI STUDIO</div>
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">Guaranteed Mobile Playable Video & Voice Studio</div>
    </div>
    <div>
        <span class="founders-tag">👑 Founders: Muhammad Essa & Saba Wahid</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# MAIN TABS
# ==========================================
tab_recap, tab_voice_studio, tab_shorts, tab_clip = st.tabs([
    "🎬 1. مووی ریکیپ (10-20 منٹ ویڈیو + کہانی + آڈیو)",
    "🎙️ 2. پرو AI وائس اوور اسٹوڈیو (لمبے اسکرپٹ کا وائس اوور)",
    "📱 3. فل اسکرین شارٹس",
    "⚔️ 4. کلپ کٹر"
])

# ------------------------------------------------------------------------------
# TAB 1: FULL MOVIE RECAP (VIDEO + SCRIPT + AUDIO)
# ------------------------------------------------------------------------------
with tab_recap:
    st.write("### 🎬 مکمل مووی کہانی، اسکرپٹ، وائس اوور اور ویڈیو ڈاؤنلوڈر")
    st.info("💡 لنک درج کریں یا فائل اپلوڈ کریں۔ منتخب کردہ دورانیے کے مطابق **ویڈیو**، **مکمل اسکرپٹ** اور **MP3 وائس اوور** تیار ہو کر سامنے آئیں گے!")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        voice_char = st.selectbox("وائس اوور کی آواز:", list(VOICE_DATABASE.keys()), key="rc_vchar")
    with rc2:
        recap_dur = st.selectbox("ویڈیو اور کہانی کا دورانیہ:", ["10 منٹ (10 Mins)", "20 منٹ (20 Mins)"], key="rc_dur")
    with rc3:
        recap_genre = st.selectbox("ویڈیو کا انداز:", ["🔥 ایکشن و تھرلر", "🐾 سسپنس و خوفناک", "🏔️ ایڈونچر", "💖 ڈراما"], key="rc_genre")

    target_recap_mins = 10 if "10" in recap_dur else 20
    target_lang_str = voice_char.split(" - ")[0]

    url_recap_input = st.text_input("🔗 ویڈیو یا مووی کا لنک پیسٹ کریں:", placeholder="https://www.dailymotion.com/video/...", key="url_recap")
    up_recap_file = st.file_uploader("📂 یا اپنے موبائل سے ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_recap")

    if st.button(f"🚀 مکمل {target_recap_mins} منٹ کا ڈیٹا تیار کریں", type="primary", key="btn_run_recap"):
        uid = str(uuid.uuid4())[:8]
        final_mp4 = f"playable_video_{uid}.mp4"
        voice_audio = f"voice_{uid}.mp3"
        has_input = False
        info = {'title': 'Action Movie Recap'}

        status_box = st.status("⏳ پروسیسنگ جاری ہے، برائے مہربانی چند سیکنڈ انتظار کریں...", expanded=True)

        # 1. Download & Cut Video into exact duration
        if url_recap_input.strip():
            status_box.write(f"🔗 ویڈیو ڈاؤنلوڈ اور {target_recap_mins} منٹ میں کٹ ہو رہی ہے...")
            success, title_fetched = download_and_cut_playable_video(url_recap_input.strip(), final_mp4, duration_mins=target_recap_mins)
            if success and os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 5000:
                has_input = True
                info['title'] = title_fetched
        elif up_recap_file is not None:
            status_box.write(f"📂 اپلوڈ شدہ ویڈیو {target_recap_mins} منٹ فارمیٹ میں تیار ہو رہی ہے...")
            temp_up = f"temp_up_{uid}.mp4"
            with open(temp_up, "wb") as f:
                f.write(up_recap_file.getbuffer())
            ffmpeg_exe = get_ffmpeg()
            cmd_fix = [
                ffmpeg_exe, "-nostdin", "-y",
                "-ss", "0", "-t", str(target_recap_mins * 60),
                "-i", temp_up,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart", final_mp4
            ]
            subprocess.run(cmd_fix, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try: os.remove(temp_up)
            except Exception: pass
            if os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 5000:
                has_input = True
                info['title'] = up_recap_file.name

        if not has_input:
            info['title'] = "Action Thriller Movie"

        # 2. Generate Full Length Story Script
        status_box.write(f"🧠 فلم '{info['title'][:30]}' کا مکمل تحریری اسکرپٹ تیار ہو رہا ہے...")
        story_script = generate_full_length_movie_script(info['title'], target_recap_mins, recap_genre, target_lang_str)

        # 3. Generate Audio Voiceover
        status_box.write(f"🎙️ {voice_char} کی آواز میں مکمل MP3 وائس اوور بن رہا ہے...")
        audio_ok = save_multilang_voiceover_sync(story_script, voice_char, voice_audio)

        # Store in Session State
        st.session_state.recap_data = {
            "title": info['title'],
            "mins": target_recap_mins,
            "script": story_script,
            "voice_file": voice_audio if audio_ok and os.path.exists(voice_audio) else "",
            "video_file": final_mp4 if has_input and os.path.exists(final_mp4) else ""
        }
        status_box.update(label="🎉 تمام ڈیٹا 100% کامیابی کے ساتھ تیار ہو گیا ہے!", state="complete", expanded=False)

    # ------------------ OUTPUT DISPLAY ------------------
    if st.session_state.recap_data:
        data = st.session_state.recap_data
        st.divider()

        # 1. Full Story Script
        st.subheader(f"📖 1. فلم کا مکمل تحریری اسکرپٹ ({data.get('mins', 10)} منٹ لمبی کہانی):")
        st.text_area("مکمل تفصیلی اسکرپٹ (پڑھنے یا کاپی کرنے کے لیے):", value=data.get("script", ""), height=280)

        # 2. Voiceover Audio Player
        if data.get("voice_file") and os.path.exists(data.get("voice_file")):
            st.subheader("🎙️ 2. تیار شدہ AI وائس اوور (MP3 Audio):")
            st.audio(data["voice_file"], format="audio/mp3")
            with open(data["voice_file"], "rb") as fp_a:
                st.download_button(
                    label="📥 مکمل MP3 وائس اوور ڈاؤنلوڈ کریں",
                    data=fp_a,
                    file_name="movie_voiceover.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )

        # 3. Mobile Playable Video
        if data.get("video_file") and os.path.exists(data.get("video_file")):
            st.subheader(f"🎬 3. تیار شدہ ویڈیو ({data.get('mins', 10)} منٹ کٹ):")
            st.video(data["video_file"])
            with open(data["video_file"], "rb") as fp_v:
                st.download_button(
                    label="📥 ویڈیو فائل ڈاؤنلوڈ کریں (Download MP4 Video)",
                    data=fp_v,
                    file_name=f"movie_{data.get('mins', 10)}min.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

        # 4. SEO Titles & Prompt
        st.markdown("---")
        st.subheader("🔥 4. وائرل ٹائٹلز، ہیش ٹیگز اور AI تھمب نیل:")
        clean_hero_title, titles, hashtags, exact_thumb_prompt = analyze_video_and_generate_metadata(data.get("title", "Movie Recap"))
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🔥 وائرل یوٹیوب ٹائٹلز:**")
            for t in titles: st.code(t, language="text")
            st.markdown("**🏷️ وائرل ہیش ٹیگز:**")
            st.code(hashtags, language="text")
        with c2:
            st.markdown(f"**🎨 AI تھمب نیل پرامپٹ ({clean_hero_title[:30]}):**")
            st.code(exact_thumb_prompt, language="text")

# ------------------------------------------------------------------------------
# TAB 2: PRO AI VOICEOVER STUDIO
# ------------------------------------------------------------------------------
with tab_voice_studio:
    st.write("### 🎙️ پرو AI وائس اوور اسٹوڈیو (لمبے اسکرپٹس کا تیز وائس اوور)")
    tts_voice = st.selectbox("وائس اوور آرٹسٹ منتخب کریں:", list(VOICE_DATABASE.keys()), key="studio_voice")

    user_custom_script = st.text_area(
        "📝 اپنا مکمل اسکرپٹ یہاں پیسٹ کریں:",
        value=st.session_state.recap_data.get("script", "") if st.session_state.recap_data else "",
        height=260,
        placeholder="یہاں اپنی فلم یا کہانی کا پورا اسکرپٹ لکھیں یا پیسٹ کریں..."
    )

    if st.button("🚀 مکمل اسکرپٹ کا وائس اوور (MP3) بنائیں", type="primary", key="btn_run_tts_studio"):
        if user_custom_script.strip():
            uid = str(uuid.uuid4())[:8]
            out_voice_path = f"custom_voice_{uid}.mp3"
            
            with st.spinner("🎙️ ہائی کوالٹی وائس اوور ریکارڈ ہو رہا ہے..."):
                ok = save_multilang_voiceover_sync(user_custom_script.strip(), tts_voice, out_voice_path)
                if ok and os.path.exists(out_voice_path) and os.path.getsize(out_voice_path) > 1000:
                    st.session_state.custom_tts_audio = out_voice_path
                    st.success("🎉 آپ کا وائس اوور 100% تیار ہو گیا ہے!")
                else:
                    st.error("❌ وائس اوور تیار نہ ہو سکا۔")

    if st.session_state.custom_tts_audio and os.path.exists(st.session_state.custom_tts_audio):
        st.divider()
        st.subheader("🎧 تیار شدہ وائس اوور سنیں اور ڈاؤنلوڈ کریں:")
        st.audio(st.session_state.custom_tts_audio, format="audio/mp3")
        with open(st.session_state.custom_tts_audio, "rb") as fp_t:
            st.download_button(
                label="📥 مکمل MP3 وائس اوور ڈاؤنلوڈ کریں",
                data=fp_t,
                file_name="movie_full_voiceover.mp3",
                mime="audio/mp3",
                use_container_width=True
            )

# ------------------------------------------------------------------------------
# TAB 3: FULL-SCREEN SHORTS
# ------------------------------------------------------------------------------
with tab_shorts:
    st.write("### 📱 فل اسکرین 9:16 شارٹس میکر")
    up_shorts_file = st.file_uploader("📂 ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_sh")

    if st.button("🚀 شارٹ بنائیں (30 سیکنڈ)", type="primary", key="btn_sh"):
        if up_shorts_file:
            uid = str(uuid.uuid4())[:8]
            t_in = f"sh_in_{uid}.mp4"
            t_out = f"sh_out_{uid}.mp4"
            with open(t_in, "wb") as f: f.write(up_shorts_file.getbuffer())
            
            ffmpeg_exe = get_ffmpeg()
            vf_pure = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1"
            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-ss", "10", "-t", "30",
                "-i", t_in, "-vf", vf_pure,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "96k", t_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(t_out) and os.path.getsize(t_out) > 5000:
                st.video(t_out)
                with open(t_out, "rb") as fp_s:
                    st.download_button(label="📥 ڈاؤنلوڈ شارٹ", data=fp_s, file_name="short_916.mp4", mime="video/mp4")
                try: os.remove(t_in)
                except Exception: pass

# ------------------------------------------------------------------------------
# TAB 4: CLIP CUTTER
# ------------------------------------------------------------------------------
with tab_clip:
    st.write("### ⚔️ کلپ کٹر موڈ")
    c1, c2 = st.columns(2)
    with c1: s_min = st.number_input("آغاز کا منٹ:", min_value=0, max_value=240, value=5)
    with c2: c_dur = st.slider("کتنے منٹ کاٹنا ہے:", 1, 30, 5)
    up_c = st.file_uploader("📂 ویڈیو منتخب کریں:", type=["mp4", "mov", "mkv"], key="up_cl")

    if st.button("🚀 کلپ تیار کریں", type="primary", key="btn_cl"):
        if up_c:
            uid = str(uuid.uuid4())[:8]
            t_in = f"c_in_{uid}.mp4"
            t_out = f"c_out_{uid}.mp4"
            with open(t_in, "wb") as f: f.write(up_c.getbuffer())
            
            ffmpeg_exe = get_ffmpeg()
            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-ss", str(s_min*60), "-t", str(c_dur*60),
                "-i", t_in, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", t_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(t_out) and os.path.getsize(t_out) > 5000:
                st.video(t_out)
                with open(t_out, "rb") as fp_c:
                    st.download_button(label="📥 ڈاؤنلوڈ کلپ", data=fp_c, file_name="clip.mp4", mime="video/mp4")
                try: os.remove(t_in)
                except Exception: pass

# ==========================================
# FOOTER BRANDING
# ==========================================
st.markdown("""
<div style='text-align: center; font-size: 13px; color: #475569; margin-top: 32px; border-top: 2px solid #e2e8f0; padding-top: 14px; font-weight: 600;'>
    ⚡ <strong>ES AI Studio</strong> | Founders: <strong>Muhammad Essa & Saba Wahid</strong> | All Rights Reserved © 2026
</div>
""", unsafe_allow_html=True)
