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
        if st.button("🚀 پوری فلم کو کاپی رائٹ فری بنائیں", type="primary", key="t1_run"):
            with st.spinner("7 سیکیورٹی فلٹرز لاگو ہو رہے ہیں، براہ کرم انتظار کریں..."):
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
    st.subheader("مووی سے 10 منٹ کا مخصوص ایکشن سین کاٹیں")
    
    c1, c2 = st.columns(2)
    with c1:
        scene_type = st.selectbox("سین کا آغاز:", ["⚔️ ایکشن و فائٹ (منٹ 30)", "👻 ہارر / سسپنس (منٹ 45)", "🏔️ ایڈونچر (منٹ 15)", "⏱️ کسٹم منٹ"])
    with c2:
        clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10)
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    
    source_type_2 = st.radio("ویڈیو کا ذریعہ:", ["📁 فائل اپلوڈ کریں", "🔗 ڈائریکٹ ویڈیو لنک"], key="src_t2")
    
    if source_type_2 == "📁 فائل اپلوڈ کریں":
        file_2 = st.file_uploader("ویڈیو منتخب کریں:", type=["mp4", "mkv", "mov", "webm"], key="f_t2")
        if file_2 is not None:
            with open(input_video, "wb") as f:
                f.write(file_2.read())
            st.success("✅ فائل لوڈ ہو گئی!")
    else:
        url_2 = st.text_input("ڈائریکٹ MP4 لنک درج کریں:", key="u_t2")
        if url_2 and st.button("📥 ڈاؤنلوڈ کریں", key="btn_u_t2"):
            with st.spinner("ویڈیو لوڈ ہو رہی ہے..."):
                try:
                    download_direct_url(url_2)
                    st.success("✅ ویڈیو تیار ہے!")
                except Exception as e:
                    st.error(f"خرابی: {str(e)}")

    if os.path.exists(input_video):
        if st.button("🚀 کلپ کاٹیں اور اینٹی کاپی رائٹ لگائیں", type="primary", key="t2_run"):
            with st.spinner("کلپ کٹ کر کے فلٹرز لگائے جا رہے ہیں..."):
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
    
    song_file = st.file_uploader("گانا یا ویڈیو فائل منتخب کریں:", type=["mp4", "mp3", "wav"], key="s_f")
    if song_file is not None:
        with open("temp_song.mp4", "wb") as f:
            f.write(song_file.read())
        if st.button("🚀 لوفی ٹریک بنائیں"):
            sample_rate = int(44100 * slow_val)
            af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g={bass_val}:f=110"
            cmd_song = ["ffmpeg", "-y", "-i", "temp_song.mp4", "-af", af_filter, "-c:v", "copy", "-c:a", "aac", output_video]
            subprocess.run(cmd_song)
            st.session_state.process_ready = True

# Download Section
if st.session_state.process_ready and os.path.exists(output_video):
    st.divider()
    st.success("🎉 ویڈیو مکمل تیار ہے! نیچے بٹن سے ڈاؤنلوڈ کریں:")
    st.video(output_video)
    with open(output_video, "rb") as f:
        st.download_button(
            label="📥 تیار شدہ ویڈیو ڈاؤنلوڈ کریں",
            data=f,
            file_name="es_protected_media.mp4",
            mime="video/mp4",
            use_container_width=True
    )
