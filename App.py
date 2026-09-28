import os
import subprocess
import streamlit as st

# Page Setup
st.set_page_config(page_title="ES Studio - Fast Action Clipper & Slowed Reverb", layout="wide")

st.title("⚡ ES الٹرا فاسٹ اسٹوڈیو: فلم کلپر اور لوفی ریورب انجن")

# Create Two Separate Tabs
tab1, tab2 = st.tabs(["🎬 1. فلم کلپر اور ہائی لائٹس (Action / Horror / Adventure)", "🎧 2. گانے اور لوفی (Slowed + Reverb Engine)"])

# ==========================================
# 🎬 TAB 1: MOVIE HIGHLIGHT CUTTER & ANTI-COPYRIGHT
# ==========================================
with tab1:
    st.subheader("مووی میں سے فائٹ، ہارر یا ایڈونچر سین کاٹیں")
    
    col1, col2 = st.columns(2)
    with col1:
        scene_type = st.selectbox(
            "سین کی قسم منتخب کریں:",
            [
                "⚔️ فائٹ اور ایکشن سینز (Fight / Action)",
                "👻 خوفناک اور ہارر مناظر (Horror / Suspense)",
                "🏔️ ایڈونچر اور کلائمیکس (Adventure / Climax)",
                "⏱️ مینوئل اسٹارٹ ٹائم (Manual Time Cut)"
            ]
        )
    with col2:
        clip_duration = st.slider("کلپ کا دورانیہ (منٹ میں):", min_value=1, max_value=20, value=10)
        
    start_minute = 0
    if "فائٹ" in scene_type:
        start_minute = 35  # Common fight block interval
    elif "خوفناک" in scene_type:
        start_minute = 50  # Horror peak interval
    elif "ایڈونچر" in scene_type:
        start_minute = 20  # Adventure start interval
    else:
        start_minute = st.number_input("ویڈیو کس منٹ سے کاٹنا شروع کرے؟ (Start Minute)", min_value=0, max_value=300, value=15)

    movie_file = st.file_uploader("فلم یا لمبی ویڈیو اپلوڈ کریں:", type=["mp4", "mkv", "mov", "webm"], key="movie_uploader")

    if movie_file is not None:
        input_movie = "input_movie.mp4"
        output_clip = "highlight_clip.mp4"
        
        with open(input_movie, "wb") as f:
            f.write(movie_file.read())
            
        st.success("✅ مووی فائل لوڈ ہو گئی!")
        
        if st.button("⚡ فوری 10 منٹ کا کلپ نکالیں (Fast Cut)"):
            with st.spinner("سیکنڈوں میں کلپ کٹ اور اینٹی کاپی رائٹ فلٹر لگایا جا رہا ہے..."):
                start_seconds = start_minute * 60
                duration_seconds = clip_duration * 60
                
                # Ultra fast seek + Flip + Pitch shift for Anti-Copyright
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_seconds),
                    "-t", str(duration_seconds),
                    "-i", input_movie,
                    "-vf", "hflip,eq=contrast=1.05:saturation=1.1",
                    "-af", "atempo=1.04,asetrate=44100*1.02",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    output_clip
                ]
                
                subprocess.run(cmd)
                
                if os.path.exists(output_clip):
                    st.success("🎉 کلپ کامیابی سے تیار ہے!")
                    st.video(output_clip)
                    with open(output_clip, "rb") as f:
                        st.download_button("📥 تیار شدہ کلپ ڈاؤنلوڈ کریں", f, file_name="movie_highlight_clip.mp4", mime="video/mp4")

# ==========================================
# 🎧 TAB 2: SLOWED + REVERB MASTERING
# ==========================================
with tab2:
    st.subheader("گانے کو وائرل Slowed + Reverb اور بھاری آواز میں تبدیل کریں")
    
    col_a, col_b = st.columns(2)
    with col_a:
        slow_factor = st.slider("سلو اسپیڈ اور ڈیپ آواز (Slow Speed):", min_value=0.80, max_value=0.96, value=0.88, step=0.01)
        reverb_level = st.slider("ریورب و گونج (Reverb / Echo):", min_value=20, max_value=80, value=50, step=5)
    with col_b:
        bass_level = st.slider("بیس بوسٹ (Heavy Bass Boost):", min_value=0, max_value=12, value=6)
        video_size = st.selectbox("ویڈیو آؤٹ پٹ فارمیٹ:", ["16:9 لینڈ اسکیپ (YouTube)", "9:16 موبائل ریلز (Shorts/TikTok)"])

    song_file = st.file_uploader("گانا یا چھوٹی ویڈیو اپلوڈ کریں:", type=["mp4", "mkv", "mp3", "wav"], key="song_uploader")

    if song_file is not None:
        input_song = "input_song_media.mp4"
        output_song = "slowed_reverb_final.mp4"
        
        with open(input_song, "wb") as f:
            f.write(song_file.read())
            
        st.success("✅ فائل کامیابی سے لوڈ ہو گئی!")
        
        if st.button("🚀 Slowed + Reverb تیار کریں"):
            with st.spinner("لوفی ریورب اور آڈیو ماسٹرنگ جاری ہے..."):
                sample_rate = int(44100 * slow_factor)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_level}:0.4,bass=g={bass_level}:f=110"
                
                vf_filter = "eq=contrast=1.06:saturation=1.15"
                if "9:16" in video_size:
                    vf_filter += ",scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
                else:
                    vf_filter += ",scale=1920:1080:force_original_aspect_ratio=decrease"
                    
                cmd_song = [
                    "ffmpeg", "-y",
                    "-i", input_song,
                    "-vf", vf_filter,
                    "-af", af_filter,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "320k",
                    output_song
                ]
                
                subprocess.run(cmd_song)
                
                if os.path.exists(output_song):
                    st.success("🎉 آپ کا Slowed + Reverb تیار ہے!")
                    st.video(output_song)
                    with open(output_song, "rb") as f:
                        st.download_button("📥 Slowed + Reverb ویڈیو ڈاؤنلوڈ کریں", f, file_name="slowed_reverb_master.mp4", mime="video/mp4")
