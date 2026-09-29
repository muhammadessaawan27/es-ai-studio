import os
import subprocess
import requests
import streamlit as st

st.set_page_config(page_title="ES Ultimate AI Studio", page_icon="⚡", layout="wide")

st.title("⚡ ES الٹرا اسمارٹ اینٹی کاپی رائٹ اسٹوڈیو")
st.write("ویڈیو کیٹگری کی خودکار پہچان، 7 لیئر اینٹی کاپی رائٹ فلٹرز اور وائرل میٹا ڈیٹا پیک۔")

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False
if "detected_info" not in st.session_state:
    st.session_state.detected_info = {}

tab1, tab2, tab3 = st.tabs([
    "🎬 1. فل ویڈیو / مووی موڈ",
    "⚔️ 2. کلپ کٹر موڈ (10 منٹ کٹ)",
    "🎧 3. گانے اور لوفی (Slowed + Reverb)"
])

input_video = "input_master_video.mp4"
output_video = "output_bypass_video.mp4"

# Safe FFmpeg Locator
def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def inspect_and_fetch_media(url, target_path=input_video):
    if os.path.exists(target_path):
        os.remove(target_path)
    
    info_dict = {'title': 'Special Video', 'categories': ['Entertainment']}
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {'player_client': ['tv_embedded', 'android', 'ios', 'mweb']}
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            info_dict['title'] = meta.get('title', 'Viral Video')
            info_dict['categories'] = meta.get('categories', ['Entertainment'])
    except Exception:
        info_dict['title'] = "Custom Video Highlight"
        try:
            with requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception:
            pass

    return info_dict

def generate_smart_metadata(info):
    title = info.get('title', 'Video')
    t_lower = title.lower()
    
    if any(k in t_lower for k in ['kapil', 'comedy', 'funny', 'laugh', 'joke', 'hasna', 'standup', 'prank']):
        genre = "Comedy"
        safe_titles = [
            f"😂 Non-Stop Laugh Attack! | {title[:40]}... Best Funny Moments",
            f"🤣 Kapil Sharma Comedy Special | Uncut Hilarious Scenes",
            f"🔥 When Laughter Goes Wild! | {title[:45]}"
        ]
        hashtags = "#KapilSharmaShow #ComedyShow #FunnyVideo #StandupComedy #HindiComedy #LaughOutLoud #ViralComedy"
        thumb_prompt = f"Ultra realistic 8K YouTube thumbnail for comedy show '{title[:30]}', comedian laughing loudly on a bright modern comedy stage, 16:9."
    elif any(k in t_lower for k in ['song', 'music', 'lofi', 'slowed', 'reverb', 'audio', 'gaana']):
        genre = "Music"
        safe_titles = [
            f"🎧 Deep Emotional Vibes | {title[:40]} (Slowed + Reverb Lo-Fi)",
            f"🌙 Midnight Lo-Fi Chill | {title[:40]} | Relax & Chill",
            f"✨ Pure Nostalgia Vibes | {title[:40]} (4K Master)"
        ]
        hashtags = "#SlowedAndReverb #LofiRemix #ChillVibes #BollywoodLofi #MidnightVibes #AestheticAudio"
        thumb_prompt = f"Anime aesthetic Lo-Fi 4K wallpaper thumbnail for song '{title[:30]}', neon city lights in background, cozy bedroom, 16:9."
    else:
        genre = "Action / Movie"
        safe_titles = [
            f"🔥 The Real Climax Scene | {title[:40]}... Explained in Urdu/Hindi",
            f"⚡ Unstoppable Hero Returns! | {title[:45]} Special Cut",
            f"😱 Unbelievable Twist! You Won't Believe What Happened in {title[:35]}"
        ]
        hashtags = "#MovieRecap #CinemaLovers #ActionMovie #Blockbuster #HindiCinema #ViralMovieClip"
        thumb_prompt = f"Hyper-realistic 8K cinematic movie thumbnail for '{title[:30]}', hero in action pose, cinematic explosion, 16:9."
        
    return genre, safe_titles, hashtags, thumb_prompt

# =========================================================
# 🎬 TAB 1: FULL MOVIE / SHOW MODE
# =========================================================
with tab1:
    st.subheader("پوری ویڈیو / شو کو اینٹی کاپی رائٹ فلٹرز میں پروسیس کریں")
    style_choice = st.selectbox("حفاظتی اسٹائل:", ["🛡️ کینوس بلر فریم (سب سے زیادہ محفوظ)", "⚡ فل اسکرین الٹرا اینٹی ہیش"], key="s_t1")
    url_input_1 = st.text_input("🔗 ویڈیو کا لنک درج کریں (جیسے کپل شرما شو یا مووی):", placeholder="https://youtu.be/...", key="url_t1")
    
    if st.button("🚀 پروسیسنگ شروع کریں", type="primary", key="run_t1"):
        if url_input_1:
            with st.spinner("ویڈیو اسکین، کٹ اور فلٹرز لگ رہے ہیں..."):
                info = inspect_and_fetch_media(url_input_1, input_video)
                if os.path.exists(input_video) and os.path.getsize(input_video) > 50000:
                    ffmpeg_exe = get_ffmpeg()
                    vf_str = "[0:v]scale=1920:1080,boxblur=20:5[bg];[0:v]hflip,scale=1600:900,eq=contrast=1.07:saturation=1.14:brightness=0.01,noise=alls=2:allf=t+u,vignette=PI/4[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" if "کینوس" in style_choice else "hflip,crop=iw*0.94:ih*0.94,eq=contrast=1.08:saturation=1.15,noise=alls=2:allf=t+u,vignette=PI/4"
                    af_str = "atempo=1.04,asetrate=44100*1.02,bass=g=2:f=100"
                    
                    cmd = [ffmpeg_exe, "-y", "-i", input_video, "-filter_complex" if "کینوس" in style_choice else "-vf", vf_str, "-af", af_str, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "192k", output_video]
                    subprocess.run(cmd)
                    st.session_state.detected_info = info
                    st.session_state.process_ready = True
                else:
                    st.error("❌ ویڈیو ڈاؤنلوڈ نہیں ہو سکی۔")

# =========================================================
# ⚔️ TAB 2: CLIP CUTTER MODE
# =========================================================
with tab2:
    st.subheader("ویڈیو یا شو سے 10 منٹ کا کلپ کاٹیں")
    c1, c2 = st.columns(2)
    with c1:
        scene_type = st.selectbox("سین کا آغاز:", ["⚔️ اہم سین / کامیڈی پیک (منٹ 30)", "👻 سسپنس (منٹ 45)", "🏔️ آغاز (منٹ 15)", "⏱️ کسٹم منٹ"], key="s_t2")
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    url_input_2 = st.text_input("🔗 ویڈیو کا لنک درج کریں:", placeholder="https://youtu.be/...", key="url_t2")

    if st.button("🚀 کلپ کاٹیں اور اینٹی کاپی رائٹ لگائیں", type="primary", key="run_t2"):
        if url_input_2:
            with st.spinner("ویڈیو اسکین اور کلپ کٹ ہو رہا ہے..."):
                info = inspect_and_fetch_media(url_input_2, input_video)
                if os.path.exists(input_video) and os.path.getsize(input_video) > 50000:
                    ffmpeg_exe = get_ffmpeg()
                    start_sec = start_min * 60
                    dur_sec = clip_len * 60
                    vf = "hflip,crop=iw*0.94:ih*0.94,eq=contrast=1.08:saturation=1.15,noise=alls=2:allf=t+u,vignette=PI/4"
                    af = "atempo=1.04,asetrate=44100*1.02"
                    
                    cmd = [ffmpeg_exe, "-y", "-ss", str(start_sec), "-t", str(dur_sec), "-i", input_video, "-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", output_video]
                    subprocess.run(cmd)
                    st.session_state.detected_info = info
                    st.session_state.process_ready = True
                else:
                    st.error("❌ لنک سے کلپ لوڈ نہیں ہو سکا۔")

# =========================================================
# 🎧 TAB 3: SLOWED + REVERB
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
        
    song_url = st.text_input("🔗 گانے کا لنک یہاں پیسٹ کریں:", placeholder="https://youtu.be/...", key="url_t3")
    
    if st.button("🚀 گانے کو Slowed + Reverb بنائیں", type="primary", key="run_t3"):
        if song_url:
            with st.spinner("گانا ماسٹر ہو رہا ہے..."):
                temp_audio_in = "temp_song.mp4"
                info = inspect_and_fetch_media(song_url, temp_audio_in)
                if os.path.exists(temp_audio_in) and os.path.getsize(temp_audio_in) > 50000:
                    ffmpeg_exe = get_ffmpeg()
                    sample_rate = int(44100 * slow_val)
                    af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
                    cmd_song = [ffmpeg_exe, "-y", "-i", temp_audio_in, "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_video]
                    subprocess.run(cmd_song)
                    st.session_state.detected_info = info
                    st.session_state.process_ready = True
                else:
                    st.error("❌ گانے کا لنک لوڈ نہیں ہو سکا۔")

# =========================================================
# 📦 OUTPUT + DOWNLOAD + METADATA
# =========================================================
if st.session_state.process_ready and os.path.exists(output_video):
    st.divider()
    st.success("🎉 ویڈیو مکمل تیار ہے! نیچے سے ڈاؤنلوڈ کریں:")
    
    st.video(output_video)
    with open(output_video, "rb") as f:
        st.download_button(
            label="📥 یہاں کلک کریں اور ویڈیو ڈاؤنلوڈ کریں (Download MP4)",
            data=f,
            file_name="es_protected_master.mp4",
            mime="video/mp4",
            use_container_width=True
        )

    genre, titles, tags, prompt = generate_smart_metadata(st.session_state.detected_info)
    st.info(f"🎯 **AI نے پہچانا:** یہ ویڈیو **'{genre}'** کیٹگری کی ہے۔")
    
    c_meta1, c_meta2 = st.columns(2)
    with c_meta1:
        st.markdown(f"### 😂 محفوظ وائرل ٹائٹلز ({genre}):")
        for i, t in enumerate(titles, 1):
            st.code(t, language="text")
        st.markdown("### 🏷️ وائرل ہیش ٹیگز:")
        st.code(tags, language="text")

    with c_meta2:
        st.markdown("### 🎨 AI تھمب نیل پرامپٹ (Thumbnail Prompt):")
        st.info("💡 اسے Midjourney یا Bing Creator میں ڈال کر نیا تھمب نیل بنائیں۔")
        st.code(prompt, language="text")
