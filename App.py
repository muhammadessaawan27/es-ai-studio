import os
import subprocess
import requests
import json
import streamlit as st
import imageio_ffmpeg
import yt_dlp

st.set_page_config(page_title="ES Ultimate AI Studio", page_icon="⚡", layout="wide")

st.title("⚡ ES الٹرا اینٹی کاپی رائٹ اسٹوڈیو (ڈائریکٹ لنک انجن)")
st.write("یوٹیوب، فیس بک یا کسی بھی ویڈیو/گانے کا لنک ڈالیں اور کاپی رائٹ فری ماسٹر فائل حاصل کریں۔")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False
if "current_title" not in st.session_state:
    st.session_state.current_title = "Action Blockbuster"

tab1, tab2, tab3 = st.tabs([
    "🎬 1. فل مووی موڈ (بذریعہ لنک)",
    "⚔️ 2. کلپ کٹر موڈ (بذریعہ لنک)",
    "🎧 3. گانے اور لوفی (بذریعہ لنک)"
])

input_video = "input_master_video.mp4"
output_video = "output_bypass_video.mp4"

# Multi-Strategy Media Downloader (Bypasses Datacenter IP Blocks)
def universal_media_fetch(url, target_path=input_video):
    if os.path.exists(target_path):
        os.remove(target_path)
        
    # Strategy 1: Multi-Client yt-dlp with TV & Mobile Extractor
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'android', 'ios', 'mweb']
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(target_path) and os.path.getsize(target_path) > 50000:
            return True
    except Exception:
        pass

    # Strategy 2: Direct Stream Request (for Direct MP4 / Cloud CDN links)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 50000:
            return True
    except Exception:
        pass

    return False

def build_video_filter(mode="canvas"):
    if mode == "canvas":
        base_vf = "[0:v]scale=1920:1080,boxblur=20:5[bg];[0:v]hflip,scale=1600:900,eq=contrast=1.07:saturation=1.14:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    else:
        base_vf = "hflip,crop=iw*0.94:ih*0.94,eq=contrast=1.08:saturation=1.15:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4"
    return base_vf

def generate_metadata_pack(movie_name):
    safe_titles = [
        f"🔥 The Unstoppable Power | {movie_name} Best Scenes Explained",
        f"⚡ When Legend Returns! | Top Climax Moment | {movie_name} Special Cut",
        f"😱 Unbelievable Twist & Action! | {movie_name} Hindi/Urdu"
    ]
    hashtags = f"#{movie_name.replace(' ', '')} #MovieRecap #ActionMovies #ViralVideo #HindiCinema #MovieReview #CinemaLovers"
    thumb_prompt = (
        f"Hyper-realistic 8K cinematic movie thumbnail for '{movie_name}', "
        f"intense dramatic lighting, hero character in dynamic action pose, cinematic explosion and golden neon rim light, "
        f"extreme facial expression, depth of field, blockbuster movie poster style, ultra detailed, 16:9 aspect ratio."
    )
    return safe_titles, hashtags, thumb_prompt

# =========================================================
# 🎬 TAB 1: FULL MOVIE MODE (LINK BASED)
# =========================================================
with tab1:
    st.subheader("پوری مووی کو لنک کے ذریعے اینٹی کاپی رائٹ بنائیں")
    
    col_a, col_b = st.columns(2)
    with col_a:
        style_choice = st.selectbox("حفاظتی اسٹائل:", ["🛡️ کینوس بلر فریم (سب سے زیادہ محفوظ)", "⚡ فل اسکرین الٹرا اینٹی ہیش"], key="s_t1")
    with col_b:
        movie_name_input = st.text_input("فلم کا نام درج کریں (ٹائٹل و تھمب نیل کے لیے):", value="Movie Highlight", key="m_name_t1")

    url_input_1 = st.text_input("🔗 یوٹیوب یا مووی کا لنک یہاں پیسٹ کریں:", placeholder="https://youtu.be/...", key="url_t1")
    
    if st.button("🚀 فلم پروسیس کریں اور اینٹی کاپی رائٹ لگائیں", type="primary", key="run_t1"):
        if url_input_1:
            with st.spinner("سرور لنک سے ویڈیو ڈاؤنلوڈ کر کے 7 لیئر فلٹرز لگا رہا ہے..."):
                success = universal_media_fetch(url_input_1, input_video)
                if success and os.path.exists(input_video):
                    filter_mode = "canvas" if "کینوس" in style_choice else "standard"
                    vf_str = build_video_filter(filter_mode)
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
                    st.session_state.current_title = movie_name_input
                    st.session_state.process_ready = True
                else:
                    st.error("❌ لنک سے ویڈیو حاصل نہیں ہو سکی۔ براہ کرم لنک چیک کریں۔")

# =========================================================
# ⚔️ TAB 2: CLIP CUTTER MODE (LINK BASED)
# =========================================================
with tab2:
    st.subheader("مووی کے لنک سے 10 منٹ کا ایکشن سین کاٹیں")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        scene_type = st.selectbox("سین کا انتخاب:", ["⚔️ ایکشن و فائٹ (منٹ 30)", "👻 ہارر و خوفناک (منٹ 45)", "🏔️ ایڈونچر (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
    with c3:
        movie_name_cut = st.text_input("ویڈیو کا نام درج کریں:", value="Action Hero", key="m_name_t2")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    url_input_2 = st.text_input("🔗 یوٹیوب یا ویڈیو کا لنک درج کریں:", placeholder="https://youtu.be/...", key="url_t2")

    if st.button("🚀 کلپ کاٹیں اور محفوظ ویڈیو بنائیں", type="primary", key="run_t2"):
        if url_input_2:
            with st.spinner("ویڈیو لائیو کٹ اور اینٹی کاپی رائٹ ہو رہی ہے..."):
                success = universal_media_fetch(url_input_2, input_video)
                if success and os.path.exists(input_video):
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
                    st.session_state.current_title = movie_name_cut
                    st.session_state.process_ready = True
                else:
                    st.error("❌ ویڈیو لنک لوڈ نہیں ہو سکا۔")

# =========================================================
# 🎧 TAB 3: SLOWED + REVERB (LINK BASED)
# =========================================================
with tab3:
    st.subheader("گانے کا لنک ڈالیں اور وائرل Slowed + Reverb بنائیں")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
    with col_s2:
        reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
    with col_s3:
        bass_val = st.slider("بیس بوسٹ:", 0, 12, 6, key="bass_t3")
        
    song_url = st.text_input("🔗 یوٹیوب یا گانے کا لنک یہاں پیسٹ کریں:", placeholder="https://youtu.be/...", key="url_t3")
    
    if st.button("🚀 گانے کو Slowed + Reverb بنائیں", type="primary", key="run_t3"):
        if song_url:
            with st.spinner("گانا ڈاؤنلوڈ ہو کر لوفی ریورب میں ماسٹر ہو رہا ہے..."):
                temp_audio_in = "temp_song.mp4"
                success = universal_media_fetch(song_url, temp_audio_in)
                if success and os.path.exists(temp_audio_in):
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [FFMPEG_BIN, "-y", "-i", temp_audio_in, "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_video]
                    subprocess.run(cmd_song)
                    st.session_state.current_title = "Lofi Viral Song"
                    st.session_state.process_ready = True
                else:
                    st.error("❌ گانے کا لنک لوڈ نہیں ہو سکا۔")

# =========================================================
# 📦 OUTPUT + DOWNLOAD + METADATA GENERATOR PACK
# =========================================================
if st.session_state.process_ready and os.path.exists(output_video):
    st.divider()
    st.success("🎉 آپ کی ویڈیو تیار ہے! نیچے سے ڈاؤنلوڈ کریں:")
    
    st.video(output_video)
    with open(output_video, "rb") as f:
        st.download_button(
            label="📥 تیار شدہ ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
            data=f,
            file_name="es_protected_media.mp4",
            mime="video/mp4",
            use_container_width=True
        )

    st.subheader("📋 اینٹی کاپی رائٹ ٹائٹل، ہیش ٹیگز اور تھمب نیل پرامپٹ")
    titles, tags, prompt = generate_metadata_pack(st.session_state.current_title)
    
    c_meta1, c_meta2 = st.columns(2)
    with c_meta1:
        st.markdown("### 🔥 محفوظ وائرل ٹائٹلز:")
        for i, t in enumerate(titles, 1):
            st.code(t, language="text")
            
        st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
        st.code(tags, language="text")

    with c_meta2:
        st.markdown("### 🎨 AI تھمب نیل پرامپٹ:")
        st.info("💡 اسے Midjourney یا Bing Image Creator میں ڈال کر نیا تھمب نیل بنائیں۔")
        st.code(prompt, language="text")
