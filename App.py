import os
import subprocess
import streamlit as st

st.set_page_config(page_title="ES AI Fast Studio", page_icon="⚡", layout="wide")

st.title("⚡ ES الٹرا فاسٹ اسٹوڈیو (لنک ڈاؤنلوڈر اور کلپر)")

if "movie_ready" not in st.session_state:
    st.session_state.movie_ready = False

tab1, tab2 = st.tabs(["🎬 1. مووی ہائی لائٹ کٹر (بذریعہ لنک یا فائل)", "🎧 2. گانے اور لوفی (Slowed + Reverb)"])

# =========================================================
# 🎬 TAB 1: MOVIE CUTTER
# =========================================================
with tab1:
    st.subheader("بڑی مووی سے 10 منٹ کا کلپ کاٹیں")
    
    col1, col2 = st.columns(2)
    with col1:
        scene_type = st.selectbox(
            "سین کی قسم منتخب کریں:",
            [
                "⚔️ فائٹ اور ایکشن سین (Fight / Action)",
                "👻 خوفناک / سسپنس سین (Horror / Suspense)",
                "🏔️ ایڈونچر اور کلائمیکس (Adventure / Climax)",
                "⏱️ کسٹم ٹائم (اپنی مرضی کے منٹ سے)"
            ]
        )
    with col2:
        clip_duration = st.slider("کلپ کا دورانیہ (منٹ میں):", min_value=1, max_value=20, value=10)

    start_minute = 0
    if "فائٹ" in scene_type:
        start_minute = 30
    elif "خوفناک" in scene_type:
        start_minute = 45
    elif "ایڈونچر" in scene_type:
        start_minute = 15
    else:
        start_minute = st.number_input("مووی کس منٹ سے کاٹنا شروع کرے؟", min_value=0, max_value=300, value=10)

    st.divider()
    upload_choice = st.radio("ویڈیو کیسے دینی ہے؟", ["🔗 لنک پیسٹ کریں (سب سے تیز ترین - ریکمنڈڈ)", "📁 موبائل/کمپیوٹر سے فائل اپلوڈ کریں"])

    input_movie = "input_movie.mp4"
    output_clip = "movie_highlight_final.mp4"
    file_ready_to_cut = False

    if upload_choice == "🔗 لنک پیسٹ کریں (سب سے تیز ترین - ریکمنڈڈ)":
        video_url = st.text_input("ویڈیو / مووی کا لنک یہاں پیسٹ کریں (YouTube, Drive, or Direct Link):", placeholder="https://...")
        if video_url:
            if st.button("📥 لنک سے ویڈیو لوڈ کریں (Fetch Video)"):
                with st.spinner("سرور تیز ترین اسپیڈ سے ویڈیو ڈاؤنلوڈ کر رہا ہے..."):
                    if os.path.exists(input_movie):
                        os.remove(input_movie)
                    # Use yt-dlp to download directly on server in seconds
                    cmd_dl = ["yt-dlp", "-f", "best[ext=mp4]/best", "-o", input_movie, video_url]
                    res = subprocess.run(cmd_dl)
                    if os.path.exists(input_movie):
                        st.success("✅ مووی سرور پر لوڈ ہو چکی ہے! اب نیچے کٹ کرنے کا بٹن دبائیں۔")
                        file_ready_to_cut = True
                    else:
                        st.error("❌ لنک سے ویڈیو ڈاؤنلوڈ نہیں ہو سکی۔ براہ کرم درست لنک دیں۔")

    else:
        movie_file = st.file_uploader("فلم سلیکٹ کریں:", type=["mp4", "mkv", "mov", "webm"])
        if movie_file is not None:
            with open(input_movie, "wb") as f:
                f.write(movie_file.read())
            st.success("✅ فائل لوڈ ہو گئی!")
            file_ready_to_cut = True

    # Cut Button
    if os.path.exists(input_movie):
        if st.button("🚀 10 منٹ کا کلپ کاٹیں اور اینٹی کاپی رائٹ لگائیں", type="primary"):
            with st.spinner("ویڈیو کٹ کر کے اینٹی کاپی رائٹ فلٹر لگایا جا رہا ہے..."):
                start_seconds = start_minute * 60
                duration_seconds = clip_duration * 60
                
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_seconds),
                    "-t", str(duration_seconds),
                    "-i", input_movie,
                    "-vf", "hflip,eq=contrast=1.06:saturation=1.12",
                    "-af", "atempo=1.03,asetrate=44100*1.02",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    output_clip
                ]
                subprocess.run(cmd)
                st.session_state.movie_ready = True

        if st.session_state.movie_ready and os.path.exists(output_clip):
            st.divider()
            st.success("🎉 کلپ تیار ہے! نیچے سے ڈاؤنلوڈ کریں:")
            st.video(output_clip)
            with open(output_clip, "rb") as f:
                st.download_button(
                    label="📥 کلک کریں اور کلپ ڈاؤنلوڈ کریں (Download MP4)",
                    data=f,
                    file_name="movie_highlight_clip.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

# =========================================================
# 🎧 TAB 2: SLOWED + REVERB
# =========================================================
with tab2:
    st.subheader("گانے کو وائرل Slowed + Reverb اور لوفی بنائیں")
    
    slow_factor = st.slider("سلو اسپیڈ اور بھاری آواز:", min_value=0.80, max_value=0.96, value=0.88, step=0.01)
    reverb_level = st.slider("ریورب و گونج:", min_value=20, max_value=80, value=50, step=5)
    bass_level = st.slider("بیس بوسٹ:", min_value=0, max_value=12, value=6)

    song_file = st.file_uploader("گانا یا چھوٹی ویڈیو اپلوڈ کریں:", type=["mp4", "mp3", "wav"])
    if song_file is not None:
        input_song = "input_song_media.mp4"
        output_song = "slowed_reverb_final.mp4"
        with open(input_song, "wb") as f:
            f.write(song_file.read())
            
        if st.button("🚀 Slowed + Reverb بنائیں", type="primary"):
            with st.spinner("لوفی ماسٹرنگ جاری ہے..."):
                sample_rate = int(44100 * slow_factor)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_level}:0.4,bass=g={bass_level}:f=110"
                cmd_song = ["ffmpeg", "-y", "-i", input_song, "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_song]
                subprocess.run(cmd_song)
                
                if os.path.exists(output_song):
                    st.success("🎉 تیار ہے!")
                    st.video(output_song)
                    with open(output_song, "rb") as f:
                        st.download_button("📥 ڈاؤنلوڈ کریں", f, file_name="slowed_reverb.mp4", mime="video/mp4", use_container_width=True)
