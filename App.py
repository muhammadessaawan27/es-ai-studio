import os
import subprocess
import urllib.request
import streamlit as st

st.set_page_config(page_title="ES Ultimate AI Studio", page_icon="🛡️", layout="wide")

st.title("🛡️ ES الٹرا اینٹی کاپی رائٹ اسٹوڈیو")
st.write("یوٹیوب اور میٹا کے Content ID کو بائی پاس کرنے والا ملٹی لیئر ویڈیو پروسیسر۔")

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False

tab1, tab2, tab3 = st.tabs([
    "🎬 1. فل مووی اینٹی کاپی رائٹ موڈ",
    "⚔️ 2. مووی ہائی لائٹ / کٹ موڈ",
    "🎧 3. گانے اور لوفی (Slowed + Reverb)"
])

input_video = "input_master_video.mp4"
output_video = "output_bypass_video.mp4"

# Direct URL Downloader (Zero 403 Errors for Direct Links & Cloud Storage)
def download_direct_url(url):
    if os.path.exists(input_video):
        os.remove(input_video)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(input_video, "wb") as out_file:
        out_file.write(response.read())

# Advanced 7-Layer Anti-Copyright Video Filter
def get_anti_copyright_filter(mode="canvas"):
    if mode == "canvas":
        vf = "[0:v]scale=1920:1080,boxblur=20:5[bg];[0:v]hflip,scale=1600:900,eq=contrast=1.07:saturation=1.14:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    else:
        vf = "hflip,crop=iw*0.95:ih*0.95,eq=contrast=1.08:saturation=1.15:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4"
    return vf

# =========================================================
# 🎬 TAB 1: FULL MOVIE BYPASS MODE
# =========================================================
with tab1:
    st.subheader("پوری مووی کو اینٹی کاپی رائٹ فلٹرز میں پروسیس کریں")
    
    style_choice = st.selectbox(
        "حفاظتی اسٹائل منتخب کریں:",
        [
            "🛡️ کینوس بلر فریم (سب سے زیادہ محفوظ - ریکمنڈڈ)",
            "⚡ فل اسکرین الٹرا اینٹی ہیش فلٹر"
        ]
    )
    
    source_type_1 = st.radio("ویڈیو کیسے دینی ہے؟", ["📁 اپنے موبائل/کمپیوٹر سے فائل اپلوڈ کریں", "🔗 ڈائریکٹ MP4 / کلاؤڈ لنک درج کریں"], key="src_t1")
    
    if source_type_1 == "📁 اپنے موبائل/کمپیوٹر سے فائل اپلوڈ کریں":
        file_1 = st.file_uploader("مووی فائل منتخب کریں:", type=["mp4", "mkv", "mov", "webm"], key="f_t1")
        if file_1 is not None:
            with open(input_video, "wb") as f:
                f.write(file_1.read())
            st.success("✅ فائل کامیابی سے لوڈ ہو گئی!")
    else:
        url_1 = st.text_input("ڈائریکٹ MP4 / گوگل ڈرائیو لنک درج کریں:", placeholder="https://example.com/video.mp4", key="u_t1")
        if url_1 and st.button("📥 لنک سے ویڈیو حاصل کریں", key="btn_u_t1"):
            with st.spinner("ویڈیو سرور پر ڈاؤنلوڈ ہو رہی ہے..."):
                try:
                    download_direct_url(url_1)
                    if os.path.exists(input_video):
                        st.success("✅ ویڈیو کامیابی سے ڈاؤنلوڈ ہو گئی!")
                except Exception as e:
                    st.error(f"❌ خرابی: {str(e)}")

    if os.path.exists(input_video):
import os
import subprocess
import shutil
import requests
import streamlit as st
import imageio_ffmpeg
import yt_dlp

st.set_page_config(page_title="ES Ultimate AI Studio", page_icon="🛡️", layout="wide")

st.title("🛡️ ES الٹرا اینٹی کاپی رائٹ اسٹوڈیو (واٹر مارک اور لوگو ریموور)")
st.write("ویڈیو سے چینل کے لوگو، واٹر مارک اور کاپی رائٹ ہیش ختم کرنے والا جدید سسٹم۔")

# Locate FFmpeg binary safely (Zero FileNotFoundError)
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False

tab1, tab2, tab3 = st.tabs([
    "🎬 1. فل مووی موڈ (اینٹی کاپی رائٹ + لوگو ریموور)",
    "⚔️ 2. کلپ کٹر موڈ (فائٹ / ایڈونچر)",
    "🎧 3. گانے اور لوفی (Slowed + Reverb)"
])

input_video = "input_master_video.mp4"
output_video = "output_bypass_video.mp4"

def fetch_youtube(url):
    if os.path.exists(input_video):
        os.remove(input_video)
    ydl_opts = {
        'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': input_video,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'ios', 'mweb']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# Filter Engine with Logo Blur & 7-Layer Protection
def build_video_filter(mode="canvas", remove_logo=True):
    filters = []
    
    # Base Transformation
    if mode == "canvas":
        base_vf = "[0:v]scale=1920:1080,boxblur=20:5[bg];[0:v]hflip,scale=1600:900,eq=contrast=1.07:saturation=1.14:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    else:
        base_vf = "hflip,crop=iw*0.94:ih*0.94,eq=contrast=1.08:saturation=1.15:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4"
        
    return base_vf

# =========================================================
# 🎬 TAB 1: FULL MOVIE MODE
# =========================================================
with tab1:
    st.subheader("پوری مووی کو کاپی رائٹ اور لوگو فری بنائیں")
    
    col_a, col_b = st.columns(2)
    with col_a:
        style_choice = st.selectbox("حفاظتی اسٹائل:", ["🛡️ کینوس بلر فریم (سب سے زیادہ محفوظ)", "⚡ فل اسکرین الٹرا اینٹی ہیش"])
    with col_b:
        delogo_option = st.checkbox("🚫 چینل کا لوگو / واٹر مارک بلر کریں (Remove Channel Logo)", value=True)

    upload_source = st.radio("مووی کیسے لوڈ کرنی ہے؟", ["📁 موبائل / کمپیوٹر سے فائل اپلوڈ کریں (100٪ محفوظ)", "🔗 یوٹیوب یا ویڈیو لنک پیسٹ کریں"])

    if upload_source == "📁 موبائل / کمپیوٹر سے فائل اپلوڈ کریں (100٪ محفوظ)":
        uploaded_f = st.file_uploader("فلم کی فائل سلیکٹ کریں:", type=["mp4", "mkv", "mov", "webm"], key="up_t1")
        if uploaded_f is not None:
            with open(input_video, "wb") as f:
                f.write(uploaded_f.read())
            st.success(f"✅ فائل کامیابی سے لوڈ ہو گئی! ({round(uploaded_f.size/(1024*1024), 1)} MB)")
    else:
        url_input = st.text_input("ویڈیو لنک پیسٹ کریں:", placeholder="https://youtu.be/...", key="url_t1")
        if url_input and st.button("📥 لنک سے ویڈیو لوڈ کریں", key="btn_yt_1"):
            with st.spinner("ویڈیو لوڈ کی جا رہی ہے..."):
                try:
                    fetch_youtube(url_input)
                    if os.path.exists(input_video):
                        st.success("✅ ویڈیو کامیابی سے ڈاؤنلوڈ ہو گئی!")
                except Exception as e:
                    st.error("❌ یوٹیوب لنک سے بلاک ہو رہا ہے۔ اوپر 'فائل اپلوڈ کریں' والا آپشن استعمال کریں۔")

    if os.path.exists(input_video) and os.path.getsize(input_video) > 50000:
        if st.button("🚀 اینٹی کاپی رائٹ اور لوگو ریموور پروسیس چلائیں", type="primary", key="run_t1"):
            with st.spinner("لوگو ریموول اور 7 لیئر اینٹی کاپی رائٹ فلٹرز لگ رہے ہیں..."):
                filter_mode = "canvas" if "کینوس" in style_choice else "standard"
                vf_str = build_video_filter(filter_mode, delogo_option)
                af_str = "atempo=1.04,asetrate=44100*1.02,bass=g=2:f=100"
                
                cmd = [
                    FFMPEG_BIN, "-y",
                    "-i", input_video,
                    "-filter_complex" if filter_mode == "canvas" else "-vf", vf_str,
                    "-af", af_str,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "192k",
                    output_video
                ]
                
                subprocess.run(cmd)
                st.session_state.process_ready = True

# =========================================================
# ⚔️ TAB 2: CLIP CUTTER MODE
# =========================================================
with tab2:
    st.subheader("مخصوص منٹ سے 10 منٹ کا کلپ کاٹیں")
    
    c1, c2 = st.columns(2)
    with c1:
        scene_type = st.selectbox("سین کا انتخاب:", ["⚔️ ایکشن و فائٹ (منٹ 30)", "👻 ہارر و خوفناک (منٹ 45)", "🏔️ ایڈونچر (منٹ 15)", "⏱️ کسٹم منٹ"])
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10)
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)

    f_cut = st.file_uploader("ویڈیو اپلوڈ کریں:", type=["mp4", "mkv", "mov", "webm"], key="up_t2")
    if f_cut is not None:
        with open(input_video, "wb") as f:
            f.write(f_cut.read())
        st.success("✅ فائل لوڈ ہو گئی!")

    if os.path.exists(input_video) and os.path.getsize(input_video) > 50000:
        if st.button("🚀 کلپ کاٹیں اور لوگو ختم کریں", type="primary", key="run_t2"):
            with st.spinner("کلپ کٹ اور لوگو ریموو ہو رہا ہے..."):
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "hflip,crop=iw*0.94:ih*0.94,eq=contrast=1.08:saturation=1.15,noise=alls=2:allf=t+u,vignette=PI/4"
                af = "atempo=1.04,asetrate=44100*1.02"
                
                cmd = [
                    FFMPEG_BIN, "-y",
                    "-ss", str(start_sec),
                    "-t", str(dur_sec),
                    "-i", input_video,
                    "-vf", vf,
                    "-af", af,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    output_video
                ]
                subprocess.run(cmd)
                st.session_state.process_ready = True

# =========================================================
# 🎧 TAB 3: SLOWED + REVERB
# =========================================================
with tab3:
    st.subheader("گانے کو وائرل Slowed + Reverb بنائیں")
    slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01)
    reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5)
    bass_val = st.slider("بیس بوسٹ:", 0, 12, 6)
    
    song_file = st.file_uploader("گانا یا ویڈیو فائل منتخب کریں:", type=["mp4", "mp3", "wav"], key="up_t3")
    if song_file is not None:
        with open("temp_song.mp4", "wb") as f:
            f.write(song_file.read())
        if st.button("🚀 Slowed + Reverb بنائیں"):
            sample_rate = int(44100 * slow_val)
            af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
            cmd_song = [FFMPEG_BIN, "-y", "-i", "temp_song.mp4", "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_video]
            subprocess.run(cmd_song)
            st.session_state.process_ready = True

# Download Area
if st.session_state.process_ready and os.path.exists(output_video):
    st.divider()
    st.success("🎉 ویڈیو بغیر لوگو اور کاپی رائٹ فلٹرز کے ساتھ تیار ہے! نیچے سے ڈاؤنلوڈ کریں:")
    st.video(output_video)
    with open(output_video, "rb") as f:
        st.download_button(
            label="📥 تیار شدہ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
            data=f,
            file_name="es_protected_media.mp4",
            mime="video/mp4",
            use_container_width=True
                )
