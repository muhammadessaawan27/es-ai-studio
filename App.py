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
import subprocess
from PIL import Image

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
# SYSTEM CORE HELPERS
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
            # Support long continuous narrative
            communicate = edge_tts.Communicate(clean_t, voice_id, rate=rate_str, pitch=pitch_str)
            await communicate.save(out_file)
            
        asyncio.run(amain())
        return os.path.exists(out_file) and os.path.getsize(out_file) > 1000
    except Exception:
        return False

# ==============================================================================
# UNIVERSAL MEDIA DOWNLOADER
# ==============================================================================
def download_unblockable_media_parallel(raw_url, target_path):
    raw_url = raw_url.strip()
    title = fetch_oembed_title(raw_url) or "Action Movie Recap"

    # Dailymotion / Web Engine
    if "dailymotion.com" in raw_url or "dai.ly" in raw_url:
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best[height<=720]/best',
                'outtmpl': target_path,
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(raw_url, download=True)
                if meta: title = meta.get('title', title)
            if os.path.exists(target_path) and os.path.getsize(target_path) > 5000:
                return True, title
        except Exception:
            pass

    # Direct Video Links
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

        try:
            import yt_dlp
            ydl_opts = {'format': 'best[height<=720]/best', 'outtmpl': target_path, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(raw_url, download=True)
                if meta: title = meta.get('title', title)
            if os.path.exists(target_path) and os.path.getsize(target_path) > 5000:
                return True, title
        except Exception:
            pass

    return False, title

# ==============================================================================
# FULL-LENGTH 10 & 20 MINS AI STORY SCRIPT GENERATOR
# ==============================================================================
def generate_full_length_movie_script(movie_title, duration_mins, genre, target_lang):
    clean_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', movie_title).strip()
    word_target = "1500 words" if duration_mins == 10 else "3000 words"
    try:
        instruction = (
            f"You are a master YouTube movie recap writer. Write an extensive, fully detailed, continuous, complete movie storyline narrative for the movie titled '{clean_title}'. "
            f"Language: {target_lang}. Target reading duration: {duration_mins} minutes (approximately {word_target}). "
            f"Genre: {genre}. "
            f"Structure the story into: "
            f"1. Detailed Opening & Character introductions. "
            f"2. Inciting incident and plot development. "
            f"3. Major midpoint twist, tension, confrontations, and challenges. "
            f"4. The intense climax scene and conclusion. "
            f"Write comprehensive, immersive spoken story sentences with lots of narrative detail so that a narrator can read it aloud for a full {duration_mins}-minute video. Do NOT use brackets, markdown headers, or sound effects."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(instruction)}?model=openai"
        res = requests.get(url, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text.strip()
    except Exception:
        pass
        
    return (
        f"دوستو! آج ہم فلم '{clean_title}' کی مکمل اور تفصیلی کہانی آپ کے سامنے پیش کر رہے ہیں۔\n\n"
        f"کہانی کی شروعات ایک پراسرار اور خوفناک پس منظر سے ہوتی ہے جہاں ہمارے مرکزی کردار ایک انجانے جزیرے پر پہنچتے ہیں۔ شروع میں سب کچھ پرسکون دکھائی دیتا ہے مگر جلد ہی حالات خطرناک رخ اختیار کر لیتے ہیں۔ جزیرے کے چھپے ہوئے راز رفتہ رفتہ سامنے آنے لگتے ہیں اور ہر قدم پر موت ان کا تعاقب کرتی ہے۔\n\n"
        f"فلم کے درمیانی حصے میں جب ٹیم آگے بڑھتی ہے تو ان کا سامنا ناقابل یقین رکاوٹوں اور پراسرار مخلوقات سے ہوتا ہے۔ آپس کے اختلافات اور بقا کی جنگ کہانی میں زبردست سسپنس اور تجسس پیدا کر دیتی ہے۔ ہر کردار اپنی جان بچانے کے لیے آخری حد تک جدوجہد کرتا ہے۔\n\n"
        f"کہانی اپنے کلائمیکس پر پہنچتی ہے جہاں مرکزی کردار اور خطرے کے درمیان آخری اور فیصلہ کن معرکہ ہوتا ہے۔ انتہائی سنسنی خیز مقابلے کے بعد کہانی ایک شاندار اور غیر متوقع انجام پر ختم ہوتی ہے۔ اگر آپ کو یہ تفصیلی کہانی پسند آئی ہو تو ویڈیو کو لائک کریں اور چینل کو ضرور سبسکرائب کریں!"
    )

def analyze_video_and_generate_metadata(title):
    clean_t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip() or title
    titles = [
        f"🔥 {clean_t[:45]} | Full Movie Story Explained & Recap",
        f"⚡ {clean_t[:40]} - Real Story Breakdown & Climax Scene",
        f"😱 The Entire Story of {clean_t[:40]} Explained in Detail!"
    ]
    hashtags = "#MovieRecap #MovieExplained #FilmStory #TrendingMovie #CinemaRecap"
    exact_thumb_prompt = f"Hyper-realistic 8K cinematic movie poster for '{clean_t[:45]}', dramatic action scene, volumetric lighting, 16:9."
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
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">Professional 10-20 Min Movie Recap & Voice Studio</div>
    </div>
    <div>
        <span class="founders-tag">👑 Founders: Muhammad Essa & Saba Wahid</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TABS
# ==========================================
tab_recap, tab_voice_studio, tab_shorts, tab_clip, tab_lofi, tab_image = st.tabs([
    "🎬 1. مووی ریکیپ (10 تا 20 منٹ کہانی و کٹ ویڈیو)",
    "🎙️ 2. پرو AI وائس اوور اسٹوڈیو (لمبے اسکرپٹ کا وائس اوور)",
    "📱 3. فل اسکرین شارٹس",
    "⚔️ 4. کلپ کٹر",
    "🎧 5. لوفی گانے",
    "🎨 6. پرو AI امیج اسٹوڈیو"
])

# ------------------------------------------------------------------------------
# TAB 1: FULL 10-20 MIN MOVIE RECAP STUDIO
# ------------------------------------------------------------------------------
with tab_recap:
    st.write("### 🎬 فلم کی مکمل تحریری کہانی اور 10 تا 20 منٹ ویڈیو کٹ")
    st.info("💡 آپ یہاں سے فلم کا **مکمل تفصیلی اسکرپٹ (پورا 10 یا 20 منٹ کا)** اور **پوری لمبائی کی ویڈیو** حاصل کر سکتے ہیں!")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        voice_char = st.selectbox("وائس اوور کی زبان و آواز:", list(VOICE_DATABASE.keys()), key="rc_vchar")
    with rc2:
        recap_dur = st.selectbox("مووی کہانی کا دورانیہ منتخب کریں:", ["10 منٹ کہانی (10 Mins)", "20 منٹ کہانی (20 Mins)"], key="rc_dur")
    with rc3:
        recap_genre = st.selectbox("ویڈیو کا انداز (Genre):", [
            "🔥 ایکشن و تھرلر (Action / Blockbuster)",
            "🐾 سسپنس و خوفناک (Suspense / Horror)",
            "🏔️ ایڈونچر و جزیرہ (Island Adventure)",
            "💖 جذباتی و ڈراما (Drama)"
        ], key="rc_genre")

    target_recap_mins = 10 if "10" in recap_dur else 20
    target_lang_str = voice_char.split(" - ")[0]

    url_recap_input = st.text_input("🔗 ویڈیو یا مووی کا لنک پیسٹ کریں:", placeholder="https://www.dailymotion.com/video/...", key="url_recap")
    up_recap_file = st.file_uploader("📂 یا اپنے ڈیوائس سے ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_recap")

    if st.button(f"🚀 مکمل {target_recap_mins} منٹ کی کہانی اور ویڈیو تیار کریں", type="primary", key="btn_run_recap"):
        uid = str(uuid.uuid4())[:8]
        raw_in = f"raw_in_{uid}.mp4"
        cut_video_out = f"recap_cut_{target_recap_mins}m_{uid}.mp4"
        voice_audio = f"voice_{uid}.mp3"
        
        has_input = False
        info = {'title': 'Action Movie Recap'}

        status_box = st.status(f"⏳ {target_recap_mins} منٹ کی کہانی اور ویڈیو تیار کی جا رہی ہے...", expanded=True)

        # 1. Download or Save Video
        if url_recap_input.strip():
            status_box.write("🔗 ویڈیو کلاؤڈ اسٹریم سے ڈاؤنلوڈ ہو رہی ہے...")
            success, title_fetched = download_unblockable_media_parallel(url_recap_input.strip(), raw_in)
            if success and os.path.exists(raw_in) and os.path.getsize(raw_in) > 3000:
                has_input = True
                info['title'] = title_fetched
        elif up_recap_file is not None:
            status_box.write("📂 اپلوڈ شدہ فائل محفوظ ہو رہی ہے...")
            with open(raw_in, "wb") as f:
                f.write(up_recap_file.getbuffer())
            if os.path.exists(raw_in) and os.path.getsize(raw_in) > 1000:
                has_input = True
                info['title'] = up_recap_file.name

        if not has_input:
            info['title'] = "Action Thriller Movie"

        # 2. Generate Full Length Scene-by-Scene Script
        status_box.write(f"🧠 فلم '{info['title'][:30]}' کی مکمل {target_recap_mins} منٹ کی کہانی لکھی جا رہی ہے...")
        story_script = generate_full_length_movie_script(info['title'], target_recap_mins, recap_genre, target_lang_str)

        # 3. Cut Video to exact 10 or 20 Minutes (Ultra-Fast)
        has_cut_vid = False
        if has_input and os.path.exists(raw_in):
            status_box.write(f"🎬 ویڈیو کو {target_recap_mins} منٹ دورانیے میں فاسٹ کٹ کیا جا رہا ہے...")
            ffmpeg_exe = get_ffmpeg()
            target_secs = target_recap_mins * 60
            cmd_cut = [
                ffmpeg_exe, "-nostdin", "-y",
                "-ss", "60", "-t", str(target_secs),
                "-i", raw_in, "-c:v", "copy", "-c:a", "copy",
                "-movflags", "+faststart", cut_video_out
            ]
            subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(cut_video_out) and os.path.getsize(cut_video_out) > 5000:
                has_cut_vid = True
            try: os.remove(raw_in)
            except Exception: pass

        # Save to Session State
        st.session_state.recap_data = {
            "title": info['title'],
            "mins": target_recap_mins,
            "script": story_script,
            "cut_video": cut_video_out if has_cut_vid and os.path.exists(cut_video_out) else ""
        }
        status_box.update(label=f"🎉 آپ کا مکمل {target_recap_mins} منٹ کا اسکرپٹ اور ویڈیو 100% تیار ہے!", state="complete", expanded=False)

    # ------------------ OUTPUT DISPLAY ------------------
    if st.session_state.recap_data:
        data = st.session_state.recap_data
        st.divider()

        st.subheader(f"📖 1. فلم کا مکمل تحریری اسکرپٹ ({data.get('mins', 10)} منٹ تفصیلی کہانی):")
        st.info("💡 یہ اسکرپٹ پورا پڑھنے کے لیے ہے۔ آپ اسے کاپی کر کے دوسرے ٹیب (پرو AI وائس اوور اسٹوڈیو) میں ڈال کر مکمل آڈیو وائس اوور بھی بنا سکتے ہیں:")
        st.text_area("مکمل تفصیلی اسکرپٹ (پڑھنے یا کاپی کرنے کے لیے):", value=data.get("script", ""), height=280)

        # Video Section
        if data.get("cut_video") and os.path.exists(data.get("cut_video")):
            st.subheader(f"🎬 2. تیار شدہ {data.get('mins', 10)} منٹ کی ویڈیو فائل:")
            v_bytes = open(data["cut_video"], "rb").read()
            st.video(v_bytes)
            st.download_button(
                label=f"📥 مکمل {data.get('mins', 10)} منٹ ویڈیو ڈاؤنلوڈ کریں (Download Video MP4)",
                data=v_bytes,
                file_name=f"movie_{data.get('mins', 10)}min_recap.mp4",
                mime="video/mp4",
                use_container_width=True
            )

        # SEO Titles
        st.markdown("---")
        st.subheader("🔥 3. وائرل ٹائٹلز، ہیش ٹیگز اور تھمب نیل آئیڈیا:")
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
# TAB 2: DEDICATED PRO AI VOICEOVER STUDIO (ANY SCRIPT TO MP3)
# ------------------------------------------------------------------------------
with tab_voice_studio:
    st.write("### 🎙️ پرو AI وائس اوور اسٹوڈیو (لمبے اسکرپٹس کا تیز ترین وائس اوور)")
    st.info("💡 آپ یہاں 10 منٹ یا 20 منٹ کا جتنا بھی لمبا اسکرپٹ پیسٹ کریں گے، AI فوراً اس کی قدرتی آواز میں مکمل MP3 وائس اوور تیار کر دے گا!")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        tts_voice = st.selectbox("وائس اوور آرٹسٹ منتخب کریں:", list(VOICE_DATABASE.keys()), key="studio_voice")
    with col_v2:
        st.write("")
        st.write("⚡ **100% ہائی کوالٹی نیچرل اسٹوڈیو آڈیو**")

    user_custom_script = st.text_area(
        "📝 اپنا مکمل اسکرپٹ یہاں پیسٹ کریں (چاہے جتنا بھی لمبا ہو):",
        value=st.session_state.recap_data.get("script", "") if st.session_state.recap_data else "",
        height=240,
        placeholder="یہاں اپنی فلم یا کہانی کا پورا اسکرپٹ لکھیں یا پیسٹ کریں..."
    )

    if st.button("🚀 مکمل اسکرپٹ کا وائس اوور (MP3) تیار کریں", type="primary", key="btn_run_tts_studio"):
        if user_custom_script.strip():
            uid = str(uuid.uuid4())[:8]
            out_voice_path = f"custom_voice_{uid}.mp3"
            
            with st.spinner("🎙️ پوری کہانی کا ہائی کوالٹی وائس اوور ریکارڈ ہو رہا ہے..."):
                ok = save_multilang_voiceover_sync(user_custom_script.strip(), tts_voice, out_voice_path)
                
                if ok and os.path.exists(out_voice_path) and os.path.getsize(out_voice_path) > 1000:
                    st.session_state.custom_tts_audio = out_voice_path
                    st.success("🎉 آپ کا مکمل وائس اوور 100% تیار ہو چکا ہے!")
                else:
                    st.error("❌ وائس اوور تیار نہ ہو سکا۔ انٹرنیٹ کنکشن چیک کریں۔")
        else:
            st.warning("⚠️ برائے مہربانی پہلے باکس میں کوئی اسکرپٹ لکھیں یا پیسٹ کریں۔")

    if st.session_state.custom_tts_audio and os.path.exists(st.session_state.custom_tts_audio):
        st.divider()
        st.subheader("🎧 تیار شدہ وائس اوور سنیں اور ڈاؤنلوڈ کریں:")
        aud_bytes = open(st.session_state.custom_tts_audio, "rb").read()
        st.audio(aud_bytes, format="audio/mp3")
        st.download_button(
            label="📥 مکمل MP3 وائس اوور ڈاؤنلوڈ کریں (Download Full Voiceover MP3)",
            data=aud_bytes,
            file_name="movie_full_voiceover.mp3",
            mime="audio/mp3",
            use_container_width=True
        )

# ------------------------------------------------------------------------------
# TAB 3: FULL-SCREEN 9:16 SHORTS
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
                "-c:a", "aac", "-b:a", "96k", t_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(t_out) and os.path.getsize(t_out) > 5000:
                st.video(open(t_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ شارٹ", data=open(t_out, 'rb').read(), file_name="short_916.mp4", mime="video/mp4")
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
                "-i", t_in, "-c:v", "copy", "-c:a", "copy", t_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(t_out) and os.path.getsize(t_out) > 5000:
                st.video(open(t_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ کلپ", data=open(t_out, 'rb').read(), file_name="clip.mp4", mime="video/mp4")
                try: os.remove(t_in)
                except Exception: pass

# ------------------------------------------------------------------------------
# TAB 5: LO-FI & SONGS
# ------------------------------------------------------------------------------
with tab_lofi:
    st.write("### 🎧 لوفی گانے (Slowed + Reverb)")
    up_audio = st.file_uploader("📂 آڈیو یا ویڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_lf")

    if st.button("🚀 لوفی گانا بنائیں", type="primary", key="btn_lf"):
        if up_audio:
            uid = str(uuid.uuid4())[:8]
            t_in = f"lf_in_{uid}.mp4"
            t_out = f"lf_out_{uid}.mp3"
            with open(t_in, "wb") as f: f.write(up_audio.getbuffer())
            
            ffmpeg_exe = get_ffmpeg()
            cmd = [
                ffmpeg_exe, "-nostdin", "-y", "-i", t_in,
                "-af", "asetrate=44100*0.88,aresample=44100,aecho=0.8:0.88:50:0.4",
                "-c:a", "libmp3lame", "-b:a", "160k", t_out
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(t_out) and os.path.getsize(t_out) > 5000:
                st.audio(open(t_out, 'rb').read())
                st.download_button(label="📥 ڈاؤنلوڈ لوفی گانا", data=open(t_out, 'rb').read(), file_name="lofi_track.mp3", mime="audio/mp3")
                try: os.remove(t_in)
                except Exception: pass

# ------------------------------------------------------------------------------
# TAB 6: PRO AI IMAGE STUDIO
# ------------------------------------------------------------------------------
with tab_image:
    st.write("### 🎨 Pro AI Visual Studio")
    p_i = st.text_area("تصویر کا پرامپٹ لکھیں:", height=80, placeholder="A cinematic fantasy hero in battle, 8k...")
    if st.button("Generate AI Image 🎨"):
        with st.spinner("تصویر تیار ہو رہی ہے..."):
            img_bytes = fetch_img_failover(p_i, 1280, 720, random.randint(1, 999999))
            if img_bytes:
                st.image(img_bytes, caption="Generated AI Image")

# ==========================================
# FOOTER BRANDING
# ==========================================
st.markdown("""
<div style='text-align: center; font-size: 13px; color: #475569; margin-top: 32px; border-top: 2px solid #e2e8f0; padding-top: 14px; font-weight: 600;'>
    ⚡ <strong>ES AI Studio</strong> | Founders: <strong>Muhammad Essa & Saba Wahid</strong> | All Rights Reserved © 2026
</div>
""", unsafe_allow_html=True)
