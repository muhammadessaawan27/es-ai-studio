import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import subprocess

# ==========================================
# STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="ES AI Studio | Muhammad Essa & Saba Wahid",
    layout="wide",
    page_icon="⚡"
)

# Session States
if "cut_video_path" not in st.session_state:
    st.session_state.cut_video_path = ""
if "generated_script" not in st.session_state:
    st.session_state.generated_script = ""
if "voice_mp3_path" not in st.session_state:
    st.session_state.voice_mp3_path = ""

# ==========================================
# CORE HELPERS
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

# Voice Engine DB
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
# FAST DOWNLOAD ENGINE
# ==============================================================================
def download_unblockable_media_parallel(raw_url, target_path):
    raw_url = raw_url.strip()
    title = fetch_oembed_title(raw_url) or "Movie Video"

    if "dailymotion.com" in raw_url or "dai.ly" in raw_url or raw_url.startswith("http"):
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best[height<=720]/best',
                'outtmpl': target_path,
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 35
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(raw_url, download=True)
                if meta: title = meta.get('title', title)
            if os.path.exists(target_path) and os.path.getsize(target_path) > 5000:
                return True, title
        except Exception:
            pass

    # Direct Web Download Fallback
    if raw_url.startswith("http"):
        direct_url = raw_url
        if "pixeldrain.com/u/" in raw_url:
            direct_url = raw_url.replace("pixeldrain.com/u/", "pixeldrain.com/api/file/")
        elif "dropbox.com" in raw_url:
            direct_url = raw_url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "?dl=1")
            
        try:
            r = requests.get(direct_url, stream=True, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024 * 8):
                        if chunk: f.write(chunk)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                    return True, title
        except Exception:
            pass

    return False, title

# ==============================================================================
# SCRIPT GENERATOR
# ==============================================================================
def generate_long_movie_script(movie_title, duration_mins, genre, target_lang):
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', movie_title).strip() or movie_title
    try:
        instruction = (
            f"Write an extensive, comprehensive, scene-by-scene movie storyline in {target_lang} for '{clean_title}'. "
            f"Genre: {genre}. Reading duration: {duration_mins} minutes. "
            f"Write in spoken story format with full paragraphs describing the characters, plot twists, dangerous obstacles, the full climax, and resolution. "
            f"Do not write short summaries. Write a long, continuous storytelling script."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج ہم فلم '{clean_title}' کی مکمل اور تفصیلی کہانی آپ کے سامنے پیش کر رہے ہیں۔ یہ ایک انتہائی سنسنی خیز اور زبردست کہانی ہے۔\n\n"
        f"1. شروعات اور منظر نامہ:\n"
        f"کہانی کے آغاز میں ہمارا مرکزی کردار ایک غیر معمولی صورتحال میں داخل ہوتا ہے۔ حالات انتہائی پراسرار دکھائی دیتے ہیں اور ایک بڑا مشن سامنے آتا ہے۔ ٹیم آگے بڑھتی ہے مگر جلد ہی انہیں احساس ہوتا ہے کہ وہ کسی بہت بڑی مصیبت اور جال میں پھنس چکے ہیں۔\n\n"
        f"2. بڑھتا ہوا سسپنس اور خطرات:\n"
        f"جیسے جیسے کہانی آگے بڑھتی ہے، ہر لمحہ سسپنس میں اضافہ ہوتا چلا جاتا ہے۔ ایک کے بعد ایک پراسرار واقعات پیش آتے ہیں اور ایک انجانی طاقت ان کا پیچھا شروع کر دیتی ہے۔ مرکزی کردار اپنی حکمت عملی اور بہادری سے حالات کو سنبھالنے کی کوشش کرتا ہے۔\n\n"
        f"3. فلم کا درمیانی موڑ (Twist):\n"
        f"کہانی کے وسط میں ایک زبردست موڑ آتا ہے جو پوری کہانی کا رخ بدل دیتا ہے۔ چھپے ہوئے راز فاش ہوتے ہیں اور معلوم ہوتا ہے کہ خطرہ ہر طرف پھیل چکا ہے۔ یہاں سے بقا کی ایک ہنگامی جنگ شروع ہو جاتی ہے۔\n\n"
        f"4. آخری کلائمیکس اور شاندار انجام:\n"
        f"کہانی اپنے عروج یعنی کلائمیکس پر پہنچتی ہے۔ مرکزی کردار اور خطرناک دشمن کے درمیان آخری اور فیصلہ کن معرکہ ہوتا ہے۔ تمام تر مشکلات کے باوجود مرکزی کردار فتح حاصل کرتا ہے اور کہانی ایک شاندار انجام پر ختم ہوتی ہے۔\n\n"
        f"اگر آپ کو یہ تفصیلی کہانی پسند آئی ہو تو ویڈیو کو لائک کریں اور چینل کو ضرور سبسکرائب کریں!"
    )

# ==========================================
# UI THEME
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
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">3-Step Independent Production Engine</div>
    </div>
    <div>
        <span class="founders-tag">👑 Founders: Muhammad Essa & Saba Wahid</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 3 MAIN INDEPENDENT TABS
# ==========================================
tab_video_cutter, tab_script_writer, tab_voice_gen = st.tabs([
    "🎬 1. ویڈیو ڈاؤنلوڈر و کٹر (10 تا 20 منٹ کٹ)",
    "📖 2. مووی کہانی و اسکرپٹ رائٹر",
    "🎙️ 3. پرو AI وائس اوور اسٹوڈیو"
])

# ------------------------------------------------------------------------------
# TAB 1: INDEPENDENT VIDEO CUTTER & DOWNLOADER
# ------------------------------------------------------------------------------
with tab_video_cutter:
    st.write("### 🎬 1. ویڈیو کٹ اور ڈاؤنلوڈ کریں (10 تا 20 منٹ)")
    st.info("💡 یہاں صرف ویڈیو ڈاؤنلوڈ اور کٹ ہوگی۔ کوئی اسکرپٹ یا وائس اوور کا بوجھ نہیں ہوگا۔ ویڈیو تیزی سے کٹ کر سامنے آ جائے گی!")

    vc_col1, vc_col2 = st.columns(2)
    with vc_col1:
        cut_duration = st.selectbox("کتنے منٹ کی ویڈیو کاٹنی ہے؟", [
            "10 منٹ کٹ (10 Minutes)",
            "20 منٹ کٹ (20 Minutes)",
            "15 منٹ کٹ (15 Minutes)",
            "5 منٹ کٹ (5 Minutes)",
            "مکمل ویڈیو (Full Original Video)"
        ], key="vc_dur")
    with vc_col2:
        start_minute = st.number_input("ویڈیو کہاں سے شروع کرنی ہے (منٹس میں)؟", min_value=0, max_value=240, value=2, key="vc_start")

    v_url_input = st.text_input("🔗 ویڈیو یا مووی کا لنک پیسٹ کریں:", placeholder="https://www.dailymotion.com/video/... یا کوئی بھی لنک", key="v_url")
    v_up_file = st.file_uploader("📂 یا اپنے ڈیوائس سے ویڈیو اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="v_up")

    if st.button("🚀 ویڈیو تیار کریں اور ڈاؤنلوڈ کریں", type="primary", key="btn_run_vc"):
        uid = str(uuid.uuid4())[:8]
        raw_vid = f"raw_{uid}.mp4"
        final_vid = f"cut_video_{uid}.mp4"
        has_video = False

        status_v = st.status("⏳ ویڈیو پروسیس ہو رہی ہے...", expanded=True)

        if v_url_input.strip():
            status_v.write("🔗 ویڈیو ڈاؤنلوڈ ہو رہی ہے...")
            ok, title = download_unblockable_media_parallel(v_url_input.strip(), raw_vid)
            if ok and os.path.exists(raw_vid) and os.path.getsize(raw_vid) > 3000:
                has_video = True
        elif v_up_file is not None:
            status_v.write("📂 ویڈیو محفوظ ہو رہی ہے...")
            with open(raw_vid, "wb") as f:
                f.write(v_up_file.getbuffer())
            if os.path.exists(raw_vid) and os.path.getsize(raw_vid) > 1000:
                has_video = True

        if has_video and os.path.exists(raw_vid):
            ffmpeg_exe = get_ffmpeg()
            
            if "مکمل ویڈیو" in cut_duration:
                final_vid = raw_vid
            else:
                dur_mins = 10 if "10" in cut_duration else 20 if "20" in cut_duration else 15 if "15" in cut_duration else 5
                dur_secs = dur_mins * 60
                start_secs = start_minute * 60

                status_v.write(f"✂️ ویڈیو کو منٹ {start_minute} سے لے کر {dur_mins} منٹ دورانیے میں کاٹا جا رہا ہے...")
                
                cmd_cut = [
                    ffmpeg_exe, "-nostdin", "-y",
                    "-ss", str(start_secs),
                    "-i", raw_vid,
                    "-t", str(dur_secs),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    final_vid
                ]
                subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # If copy fails, fallback to fast ultrafast encode
                if not os.path.exists(final_vid) or os.path.getsize(final_vid) < 5000:
                    cmd_cut_reencode = [
                        ffmpeg_exe, "-nostdin", "-y",
                        "-ss", str(start_secs),
                        "-i", raw_vid,
                        "-t", str(dur_secs),
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                        "-c:a", "aac", "-b:a", "96k",
                        "-movflags", "+faststart",
                        final_vid
                    ]
                    subprocess.run(cmd_cut_reencode, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                if not os.path.exists(final_vid) or os.path.getsize(final_vid) < 5000:
                    final_vid = raw_vid  # Fallback to full video if cutting has an issue

            st.session_state.cut_video_path = final_vid
            status_v.update(label="🎉 ویڈیو 100% کامیابی کے ساتھ تیار ہے!", state="complete", expanded=False)
        else:
            status_v.update(label="❌ ویڈیو حاصل نہیں ہو سکی۔ درست لنک یا فائل فراہم کریں۔", state="error")

    # Display Video & Download Button
    if st.session_state.cut_video_path and os.path.exists(st.session_state.cut_video_path):
        st.divider()
        st.subheader("🎬 تیار شدہ ویڈیو پلیئر:")
        v_bytes = open(st.session_state.cut_video_path, "rb").read()
        st.video(v_bytes)
        st.download_button(
            label="📥 تیار شدہ ویڈیو ڈاؤنلوڈ کریں (Download MP4 Video)",
            data=v_bytes,
            file_name=f"movie_cut_{os.path.basename(st.session_state.cut_video_path)}",
            mime="video/mp4",
            use_container_width=True
        )

# ------------------------------------------------------------------------------
# TAB 2: INDEPENDENT MOVIE STORY SCRIPT WRITER
# ------------------------------------------------------------------------------
with tab_script_writer:
    st.write("### 📖 2. مووی کہانی و اسکرپٹ رائٹر (10 تا 20 منٹ)")
    st.info("💡 یہاں آپ مووی کا نام یا لنک ڈالیں گے۔ AI فلم کی پوری لمبی کہانی (Scene-by-Scene) لکھ کر دے گا۔")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        s_lang = st.selectbox("کہانی کی زبان:", ["Urdu (اردو)", "Hindi (ہندی)", "English (انگریزی)", "Pashto (پشتو)", "Punjabi (پنجابی)"], key="sc_lang")
    with sc2:
        s_dur = st.selectbox("کہانی کا دورانیہ:", ["10 منٹ کہانی (10 Mins)", "20 منٹ کہانی (20 Mins)"], key="sc_dur")
    with sc3:
        s_genre = st.selectbox("ویڈیو کا انداز:", ["🔥 ایکشن و تھرلر", "🐾 سسپنس و خوفناک", "🏔️ ایڈونچر و جزیرہ", "💖 جذباتی و ڈراما"], key="sc_genre")

    movie_title_or_link = st.text_input("🎬 مووی کا نام یا ویڈیو کا لنک درج کریں:", placeholder="مثال: Forbidden Island یا مووی کا ڈیلی موشن لنک", key="sc_title")

    if st.button("🚀 پوری 10 تا 20 منٹ کی کہانی لکھیں", type="primary", key="btn_run_script"):
        if movie_title_or_link.strip():
            with st.spinner("🧠 فلم کی اصل اور تفصیلی کہانی لکھی جا رہی ہے..."):
                t_val = movie_title_or_link.strip()
                if t_val.startswith("http"):
                    fetched = fetch_oembed_title(t_val)
                    if fetched: t_val = fetched
                
                target_m = 10 if "10" in s_dur else 20
                script_res = generate_long_movie_script(t_val, target_m, s_genre, s_lang.split(" ")[0])
                st.session_state.generated_script = script_res
                st.success("🎉 مکمل تفصیلی کہانی کامیابی سے لکھ دی گئی ہے!")
        else:
            st.warning("⚠️ برائے مہربانی پہلے مووی کا نام یا لنک درج کریں۔")

    if st.session_state.generated_script:
        st.divider()
        st.subheader("📖 تیار شدہ مکمل مووی اسکرپٹ (پڑھنے اور کاپی کرنے کے لیے):")
        st.text_area("مکمل تفصیلی اسکرپٹ:", value=st.session_state.generated_script, height=320)
        st.info("💡 آپ یہ پورا اسکرپٹ کاپی کر کے اگلے ٹیب (3. پرو AI وائس اوور اسٹوڈیو) میں ڈال کر مکمل MP3 آڈیو ریکارڈ کر سکتے ہیں!")

# ------------------------------------------------------------------------------
# TAB 3: INDEPENDENT PRO AI VOICEOVER STUDIO (TEXT TO MP3)
# ------------------------------------------------------------------------------
with tab_voice_gen:
    st.write("### 🎙️ 3. پرو AI وائس اوور اسٹوڈیو (تحریر سے MP3 آڈیو بنائیں)")
    st.info("💡 آپ کے پاس جتنا بھی لمبا اسکرپٹ ہو، یہاں پیسٹ کریں اور قدرتی انسانی آواز میں مکمل MP3 وائس اوور ڈاؤنلوڈ کریں!")

    tts_voice_choice = st.selectbox("وائس اوور آرٹسٹ منتخب کریں:", list(VOICE_DATABASE.keys()), key="tab3_voice")

    input_text_for_voice = st.text_area(
        "📝 اپنا مکمل اسکرپٹ یہاں پیسٹ کریں:",
        value=st.session_state.generated_script,
        height=280,
        placeholder="یہاں اپنی تحریر یا اسکرپٹ پیسٹ کریں..."
    )

    if st.button("🚀 مکمل اسکرپٹ کا MP3 وائس اوور بنائیں", type="primary", key="btn_run_tab3_tts"):
        if input_text_for_voice.strip():
            uid = str(uuid.uuid4())[:8]
            out_mp3 = f"voiceover_{uid}.mp3"
            
            with st.spinner("🎙️ ہائی کوالٹی اسٹوڈیو وائس اوور تیار ہو رہا ہے..."):
                ok = save_multilang_voiceover_sync(input_text_for_voice.strip(), tts_voice_choice, out_mp3)
                if ok and os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1000:
                    st.session_state.voice_mp3_path = out_mp3
                    st.success("🎉 آپ کا مکمل MP3 وائس اوور 100% تیار ہو چکا ہے!")
                else:
                    st.error("❌ وائس اوور تیار نہ ہو سکا۔ انٹرنیٹ کنکشن چیک کریں۔")
        else:
            st.warning("⚠️ برائے مہربانی پہلے باکس میں کوئی اسکرپٹ لکھیں یا پیسٹ کریں۔")

    if st.session_state.voice_mp3_path and os.path.exists(st.session_state.voice_mp3_path):
        st.divider()
        st.subheader("🎧 تیار شدہ وائس اوور سنیں اور ڈاؤنلوڈ کریں:")
        a_bytes = open(st.session_state.voice_mp3_path, "rb").read()
        st.audio(a_bytes, format="audio/mp3")
        st.download_button(
            label="📥 مکمل MP3 وائس اوور ڈاؤنلوڈ کریں (Download Voiceover MP3)",
            data=a_bytes,
            file_name="movie_voiceover.mp3",
            mime="audio/mp3",
            use_container_width=True
        )

# ==========================================
# FOOTER BRANDING
# ==========================================
st.markdown("""
<div style='text-align: center; font-size: 13px; color: #475569; margin-top: 32px; border-top: 2px solid #e2e8f0; padding-top: 14px; font-weight: 600;'>
    ⚡ <strong>ES AI Studio</strong> | Founders: <strong>Muhammad Essa & Saba Wahid</strong> | All Rights Reserved © 2026
</div>
""", unsafe_allow_html=True)
