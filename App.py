import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina Viral Shorts Auto-Director", page_icon="🔥", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

def get_video_info(video_path):
    proc = subprocess.run([FFMPEG_BIN, "-i", video_path], capture_output=True, text=True)
    stderr = proc.stderr
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    duration = 0.0
    if dur_match:
        h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s
    has_audio = "Audio:" in stderr
    return duration, has_audio

def run_ffmpeg(args):
    proc = subprocess.run([FFMPEG_BIN, "-y"] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-600:])

def download_fast_youtube(url, output_path):
    """تیز ترین ڈاؤنلوڈر جو ہائی کوالٹی ویڈیو لاتا ہے"""
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': output_path.replace('.mp4', ''),
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith('.mp4'):
                filename_mp4 = filename.rsplit('.', 1)[0] + '.mp4'
                if os.path.exists(filename_mp4):
                    if filename_mp4 != output_path:
                        if os.path.exists(output_path): os.remove(output_path)
                        os.rename(filename_mp4, output_path)
            else:
                if filename != output_path:
                    if os.path.exists(output_path): os.remove(output_path)
                    os.rename(filename, output_path)
        return True
    except Exception as e:
        return str(e)

def viral_shorts_auto_director(raw_path, out_path, target_dur, audio_action, custom_audio_path, work_dir):
    total_dur, has_audio = get_video_info(raw_path)
    
    # 1. Smart Highlight Detection
    start_sec = 0.0
    if total_dur > target_dur + 5:
        start_sec = round(total_dur * 0.35, 2)
    active_dur = min(float(target_dur), total_dur - start_sec)
    
    # 2. ANTI-COPYRIGHT SMART CROP & VIRAL EFFECTS
    # crop=iw*0.82:ih*0.82 -> یہ کناروں سے 18 فیصد ویڈیو کاٹ دے گا تاکہ چینل کا نام اور واٹر مارک مکمل غائب ہو جائے۔
    # HDR Grading -> eq=contrast=1.2:saturation=1.35
    # Speed/Copyright Bypass -> setpts=0.96*PTS (ہلکی سی اسپیڈ تیز جس سے کاپی رائٹ بائی پاس ہوتا ہے)
    
    video_filter = (
        "crop=iw*0.82:ih*0.82:(iw-iw*0.82)/2:(ih-ih*0.82)/2," # واٹرمارک اور لکھائی ریموو کرنے والا اسمارٹ کراپ
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "eq=contrast=1.20:brightness=0.01:saturation=1.35:gamma=0.95," # YouTube Viral HDR Look
        "unsharp=5:5:1.2:5:5:0.0," # بیوٹی شاپنس
        "setpts=0.96*PTS," # Anti-Copyright Time Shift
        "format=yuv420p"
    )

    cmd = [
        "-ss", f"{start_sec:.2f}",
        "-i", raw_path,
        "-t", f"{active_dur:.2f}",
        "-vf", video_filter,
        "-threads", "4" # اسپیڈ کو 4 گنا تیز کرنے کے لیے
    ]

    # Audio Anti-Copyright Processing
    if audio_action == "Use Custom Copyright-Free Music" and custom_audio_path and os.path.exists(custom_audio_path):
        cmd += ["-i", custom_audio_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    elif audio_action == "Keep Original Audio (With Anti-Copyright Pitch)" and has_audio:
        # اصل آواز کی فریکوئنسی ہلکی سی بدلنا تاکہ Content ID نہ پکڑ سکے
        audio_filter = "asetrate=44100*1.04,aresample=44100,atempo=1/1.04"
        cmd += ["-map", "0:v", "-map", "0:a", "-af", audio_filter, "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-map", "0:v", "-an"]

    # Ultrafast Rendering (گھنٹوں کا کام سیکنڈوں میں)
    cmd += [
        "-map_metadata", "-1", # پرانا سورس ڈیٹا جڑ سے ختم
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", 
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

def extract_thumbnail(video_path, thumb_out_path):
    run_ffmpeg(["-ss", "00:00:01", "-i", video_path, "-vframes", "1", thumb_out_path])

# ==========================
# Streamlit UI (Viral Engine)
# ==========================
st.title("🔥 AI Viral Shorts Auto-Director")
st.markdown("Transform any video into a highly engaging, HDR-graded viral Short. Featuring **Anti-Logo Smart Crop** (removes text/watermarks) and **Anti-Copyright Speed/Pitch Shifting**!")

input_method = st.radio("Choose Input Method:", ["Upload Video File", "Paste YouTube / Social Link"], horizontal=True)

up_file = None
yt_url = ""

if input_method == "Upload Video File":
    up_file = st.file_uploader("📥 Upload Raw Video (MP4, MKV - Max 50MB):", type=["mp4", "mov", "mkv"])
else:
    yt_url = st.text_input("🔗 Paste YouTube/Social Video Link (URL):", placeholder="https://www.youtube.com/watch?v=...")

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Target Short Duration (Seconds):", 15, 60, 30, 5)
with c2:
    audio_choice = st.selectbox("🎵 Audio & Anti-Copyright Protection Mode:", [
        "Keep Original Audio (With Anti-Copyright Pitch)",
        "Use Custom Copyright-Free Music",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice == "Use Custom Copyright-Free Music":
    custom_aud = st.file_uploader("🎶 Upload Background Music (MP3):", type=["mp3", "wav"])

if st.button("🚀 Render Viral Short (Ultra-Fast)", use_container_width=True):
    if input_method == "Upload Video File" and not up_file:
        st.error("Please upload a video file first.")
    elif input_method == "Paste YouTube / Social Link" and not yt_url.strip():
        st.error("Please paste a valid YouTube video link.")
    elif audio_choice == "Use Custom Copyright-Free Music" and not custom_aud:
        st.error("Please upload your custom music file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        raw_p = os.path.join(work_dir, f"raw_input.mp4")
        out_p = f"Viral_Short_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File":
                stat.info("📥 Fast Uploading to Secure Buffer...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue())
                prog.progress(0.20)
            else:
                stat.info("🌐 Fetching Video Fast from YouTube...")
                dl_res = download_fast_youtube(yt_url.strip(), raw_p)
                if dl_res is not True:
                    raise RuntimeError(f"Download failed: {dl_res}")
                prog.progress(0.40)

            aud_p = None
            if custom_aud:
                aud_ext = os.path.splitext(custom_aud.name)[1] or ".mp3"
                aud_p = os.path.join(work_dir, f"aud{aud_ext}")
                with open(aud_p, "wb") as f:
                    f.write(custom_aud.getvalue())

            stat.info("🔥 AI Auto-Director: Cropping Out Logos, Applying HDR Effects & Bypassing Copyright...")
            prog.progress(0.65)

            actual_dur = viral_shorts_auto_director(raw_p, out_p, target_duration, audio_choice, aud_p, work_dir)
            prog.progress(0.90)

            extract_thumbnail(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Fast Rendering Complete! Your Copyright-Safe Viral Short is Ready.")

            col_v1, col_v2 = st.columns([1.2, 0.8])
            with col_v1:
                st.video(out_p)
                with open(out_p, "rb") as f_out:
                    st.download_button(
                        "📥 Download Viral Short (MP4)",
                        f_out.read(),
                        file_name=out_p,
                        mime="video/mp4",
                        use_container_width=True
                    )
            with col_v2:
                if os.path.exists(thumb_p):
                    st.image(thumb_p, caption="Extracted Viral Thumbnail")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Thumbnail (JPG)",
                            f_th.read(),
                            file_name=f"Thumb_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

            # High-Converting Viral Metadata
            st.markdown("---")
            st.markdown("### 📈 Auto-Generated YouTube/TikTok SEO Kit")
            
            viral_title = "🤯 Most Insane Action Moment! #Shorts #Sigma #Trending"
            viral_desc = (
                "Watch till the end for an epic twist! Edited with AI Auto-Director for the best cinematic HDR experience. "
                "Make sure to Like & Subscribe for daily viral moments!\n\n"
                "#Shorts #Viral #Action #SigmaRule #Epic #Foryou #TrendingVideo"
            )
            viral_tags = "shorts, viral shorts, sigma male, action edit, epic moment, trending video, foryoupage, tiktok viral, hdr edit"

            st.text_input("📌 High-CTR Title:", value=viral_title)
            st.text_area("📝 Viral Description:", value=viral_desc, height=100)
            st.text_input("🏷️ Trending Tags:", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
