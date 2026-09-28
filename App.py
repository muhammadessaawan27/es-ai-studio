import os
import subprocess
import streamlit as st
import yt_dlp

st.set_page_config(page_title="ES Video Clipper Studio", page_icon="⚡", layout="wide")

st.title("⚡ ES الٹرا فاسٹ اسٹوڈیو (ویڈیو کلپر اور آڈیو مکسر)")

if "movie_ready" not in st.session_state:
    st.session_state.movie_ready = False

tab1, tab2 = st.tabs(["🎬 1. مووی ہائی لائٹ کٹر", "🎧 2. گانے اور لوفی (Slowed + Reverb)"])

# =========================================================
# 🎬 TAB 1: MOVIE CUTTER
# =========================================================
with tab1:
    st.subheader("ویڈیو سے کلپ کاٹنے کا سیکشن")
    
    col1, col2 = st.columns(2)
    with col1:
        scene_type = st.selectbox(
            "سین کا آغاز منتخب کریں:",
            [
                "⚔️ فائٹ / ایکشن بلاک (منٹ 30)",
                "👻 سسپنس بلاک (منٹ 45)",
                "🏔️ ایڈونچر بلاک (منٹ 15)",
                "⏱️ کسٹم ٹائم (اپنی مرضی سے)"
            ]
        )
    with col2:
        clip_duration = st.slider("کلپ کا دورانیہ (منٹ):", min_value=1, max_value=20, value=10)

    start_minute = 0
    if "منٹ 30" in scene_type:
        start_minute = 30
    elif "منٹ 45" in scene_type:
        start_minute = 45
    elif "منٹ 15" in scene_type:
        start_minute = 15
    else:
        start_minute = st.number_input("کس منٹ سے کٹ شروع ہو؟", min_value=0, max_value=300, value=10)

    st.divider()
    upload_choice = st.radio("ویڈیو کا ذریعہ:", ["🔗 لنک درج کریں", "📁 فائل اپلوڈ کریں"])

    input_movie = "input_movie.mp4"
    output_clip = "movie_highlight_final.mp4"

    if upload_choice == "🔗 لنک درج کریں":
        video_url = st.text_input("ویڈیو لنک درج کریں:", placeholder="https://...")
        if video_url:
            if st.button("📥 ویڈیو حاصل کریں"):
                with st.spinner("ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                    if os.path.exists(input_movie):
                        os.remove(input_movie)
                    ydl_opts = {
                        'format': 'best[ext=mp4]/best',
                        'outtmpl': input_movie,
                        'quiet': True
                    }
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])
                        if os.path.exists(input_movie):
                            st.success("✅ ویڈیو کامیابی سے حاصل ہو گئی!")
                    except Exception as e:
                        st.error(f"❌ خرابی: {str(e)}")

    else:
        movie_file = st.file_uploader("فائل منتخب کریں:", type=["mp4", "mkv", "mov", "webm"])
        if movie_file is not None:
            with open(input_movie, "wb") as f:
                f.write(movie_file.read())
            st.success("✅ فائل کامیابی سے لوڈ ہو گئی!")

    # Processing Section
    if os.path.exists(input_movie):
        if st.button("🚀 کلپ پروسیس کریں", type="primary"):
            with st.spinner("ویڈیو کٹنگ اور فلٹرز لاگو کیے جا رہے ہیں..."):
                start_seconds = start_minute * 60
                duration_seconds = clip_duration * 60
                
                # Multi-layer video filters: Horizontal flip, crop, color tuning, micro noise
                vf_filters = "hflip,crop=iw*0.96:ih*0.96,eq=contrast=1.07:saturation=1.15:brightness=0.01,noise=alls=2:allf=t+u"
                
                # Audio modifications: Minor tempo & pitch modification
                af_filters = "atempo=1.04,asetrate=44100*1.02"
                
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_seconds),
                    "-t", str(duration_seconds),
                    "-i", input_movie,
                    "-vf", vf_filters,
                    "-af", af_filters,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    output_clip
                ]
                subprocess.run(cmd)
                st.session_state.movie_ready = True

        if st.session_state.movie_ready and os.path.exists(output_clip):
            st.divider()
            st.success("🎉 کلپ تیار ہے!")
            st.video(output_clip)
            with open(output_clip, "rb") as f:
                st.download_button(
                    label="📥 کلپ ڈاؤنلوڈ کریں (MP4)",
                    data=f,
                    file_name="movie_highlight_clip.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

# =========================================================
# 🎧 TAB 2: SLOWED + REVERB
# =========================================================
with tab2:
    st.subheader("آڈیو ماسٹرنگ اور لوفی انجن")
    
    slow_factor = st.slider("اسپیڈ ایڈجسٹمنٹ:", min_value=0.80, max_value=0.96, value=0.88, step=0.01)
    reverb_level = st.slider("ریورب لیول:", min_value=20, max_value=80, value=50, step=5)
    bass_level = st.slider("بیس بوسٹ:", min_value=0, max_value=12, value=6)

    song_file = st.file_uploader("آڈیو/ویڈیو فائل منتخب کریں:", type=["mp4", "mp3", "wav"])
    if song_file is not None:
        input_song = "input_song_media.mp4"
        output_song = "slowed_reverb_final.mp4"
        with open(input_song, "wb") as f:
            f.write(song_file.read())
            
        if st.button("🚀 لوفی ٹریک تیار کریں", type="primary"):
            with st.spinner("ماسٹرنگ جاری ہے..."):
                sample_rate = int(44100 * slow_factor)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_level}:0.4,bass=g={bass_level}:f=110"
                cmd_song = ["ffmpeg", "-y", "-i", input_song, "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_song]
                subprocess.run(cmd_song)
                
                if os.path.exists(output_song):
                    st.success("🎉 پروسیسنگ مکمل!")
                    st.video(output_song)
                    with open(output_song, "rb") as f:
                        st.download_button("📥 ڈاؤنلوڈ کریں", f, file_name="slowed_reverb.mp4", mime="video/mp4", use_container_width=True)
