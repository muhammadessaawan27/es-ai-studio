import os
import subprocess
import streamlit as st
import yt_dlp

st.set_page_config(page_title="ES Ultimate AI Studio", page_icon="🛡️", layout="wide")

st.title("🛡️ ES الٹرا اینٹی کاپی رائٹ اسٹوڈیو")
st.write("یوٹیوب اور میٹا کے خودکار Content ID کو بائی پاس کرنے والا ملٹی لیئر ویڈیو انجن۔")

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False

tab1, tab2, tab3 = st.tabs([
    "🎬 1. فل مووی اینٹی کاپی رائٹ موڈ",
    "⚔️ 2. مووی ہائی لائٹ / کٹ موڈ",
    "🎧 3. گانے اور لوفی (Slowed + Reverb)"
])

input_video = "input_master_video.mp4"
output_video = "output_bypass_video.mp4"

# Helper function to download with yt-dlp
def fetch_video(url):
    if os.path.exists(input_video):
        os.remove(input_video)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': input_video,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# Advanced 7-Layer Anti-Copyright Video Filter
def get_anti_copyright_filter(mode="canvas"):
    if mode == "canvas":
        # Picture-in-picture with blurred background canvas (Most Powerful against Visual AI)
        vf = "[0:v]scale=1920:1080,boxblur=20:5[bg];[0:v]hflip,scale=1600:900,eq=contrast=1.07:saturation=1.14:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    else:
        # Standard Multi-Layer Filter
        vf = "hflip,crop=iw*0.95:ih*0.95,eq=contrast=1.08:saturation=1.15:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4"
    return vf

# =========================================================
# 🎬 TAB 1: FULL MOVIE BYPASS MODE
# =========================================================
with tab1:
    st.subheader("پوری مووی کو مکمل اینٹی کاپی رائٹ فلٹرز میں پروسیس کریں")
    st.info("💡 یہ موڈ پوری فلم کے ہر فریم اور صوتی لہر پر 7 حفاظتی فلٹرز لگاتا ہے۔")
    
    style_choice = st.selectbox(
        "حفاظتی اسٹائل منتخب کریں:",
        [
            "🛡️ کینوس بلر فریم (سب سے زیادہ محفوظ - ریکمنڈڈ)",
            "⚡ فل اسکرین الٹرا اینٹی ہیش فلٹر"
        ]
    )
    
    movie_url_tab1 = st.text_input("فلم کا لنک درج کریں (YouTube / Drive / Direct MP4):", key="t1_url")
    
    if st.button("📥 لنک سے فلم حاصل کریں", key="t1_fetch"):
        if movie_url_tab1:
            with st.spinner("سرور مووی حاصل کر رہا ہے..."):
                try:
                    fetch_video(movie_url_tab1)
                    if os.path.exists(input_video):
                        st.success("✅ مووی کامیابی سے لوڈ ہو گئی!")
                except Exception as e:
                    st.error(f"❌ خرابی: {str(e)}")

    if os.path.exists(input_video):
        if st.button("🚀 پوری فلم کو کاپی رائٹ فری بنائیں (Start Full Movie Process)", type="primary", key="t1_run"):
            with st.spinner("تمام 7 سیکیورٹی فلٹرز لاگو ہو رہے ہیں، براہ کرم انتظار کریں..."):
                filter_mode = "canvas" if "کینوس" in style_choice else "standard"
                vf = get_anti_copyright_filter(filter_mode)
                af = "atempo=1.04,asetrate=44100*1.02,bass=g=2:f=100"
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", input_video,
                    "-filter_complex" if filter_mode == "canvas" else "-vf", vf,
                    "-af", af,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "192k",
                    output_video
                ]
                subprocess.run(cmd)
                st.session_state.process_ready = True

# =========================================================
# ⚔️ TAB 2: HIGHLIGHT / CLIP CUTTER MODE
# =========================================================
with tab2:
    st.subheader("مووی سے 10 منٹ کا مخصوص ایکشن/ایڈونچر سین کاٹیں")
    
    c1, c2 = st.columns(2)
    with c1:
        scene_type = st.selectbox("سین کا آغاز:", ["⚔️ ایکشن و فائٹ (منٹ 30)", "👻 ہارر / سسپنس (منٹ 45)", "🏔️ ایڈونچر (منٹ 15)", "⏱️ کسٹم منٹ"])
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10)
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    
    movie_url_tab2 = st.text_input("فلم کا لنک درج کریں:", key="t2_url")
    if st.button("📥 لنک سے ویڈیو لوڈ کریں", key="t2_fetch"):
        if movie_url_tab2:
            with st.spinner("ویڈیو لوڈ ہو رہی ہے..."):
                try:
                    fetch_video(movie_url_tab2)
                    st.success("✅ مووی تیار ہے!")
                except Exception as e:
                    st.error(f"خرابی: {str(e)}")

    if os.path.exists(input_video):
        if st.button("🚀 کلپ کاٹیں اور اینٹی کاپی رائٹ لگائیں", type="primary", key="t2_run"):
            with st.spinner("مخصوص منٹ سے کلپ کٹ کیا جا رہا ہے..."):
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "hflip,crop=iw*0.95:ih*0.95,eq=contrast=1.08:saturation=1.15,noise=alls=2:allf=t+u,vignette=PI/4"
                af = "atempo=1.04,asetrate=44100*1.02"
                
                cmd = [
                    "ffmpeg", "-y",
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
    
    song_file = st.file_uploader("گانا یا ویڈیو سلیکٹ کریں:", type=["mp4", "mp3", "wav"])
    if song_file is not None:
        with open("temp_song.mp4", "wb") as f:
            f.write(song_file.read())
        if st.button("🚀 لوفی ٹریک بنائیں"):
            sample_rate = int(44100 * slow_val)
            af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
            cmd_song = ["ffmpeg", "-y", "-i", "temp_song.mp4", "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_video]
            subprocess.run(cmd_song)
            st.session_state.process_ready = True

# Persistent Download Section
if st.session_state.process_ready and os.path.exists(output_video):
    st.divider()
    st.success("🎉 ویڈیو پروسیسنگ مکمل! نیچے سے ڈاؤنلوڈ کریں:")
    st.video(output_video)
    with open(output_video, "rb") as f:
        st.download_button(
            label="📥 یہاں کلک کر کے تیار شدہ ویڈیو ڈاؤنلوڈ کریں (Download Now)",
            data=f,
            file_name="es_protected_media.mp4",
            mime="video/mp4",
            use_container_width=True
                )
