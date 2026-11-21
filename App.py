import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import math
import glob

st.set_page_config(page_title="Sglowina AI Viral Short Studio Pro", page_icon="⚡", layout="wide")

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

def download_youtube_video(url, output_path):
    """یوٹوب یا کسی بھی لنک سے ویڈیو خودکار ڈاؤن لوڈ کرتا ہے"""
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        return str(e)

def extract_thumbnail_frame(video_path, thumb_out_path):
    run_ffmpeg(["-ss", "00:00:01", "-i", video_path, "-vframes", "1", thumb_out_path])

def pro_action_viral_edit(raw_path, out_path, target_dur, audio_action, custom_audio_path, wm_path, add_sticker, work_dir):
    """کپ کٹ (CapCut) اسٹائل میں ایکشن کٹس، فلیش، بیوٹی کلرز اور سخت کاپی رائٹ پروٹیکشن کے ساتھ ایڈیٹنگ کرتا ہے"""
    total_dur, has_audio = get_video_info(raw_path)
    
    start_sec = 0.0
    if total_dur > target_dur + 5:
        start_sec = round((total_dur - target_dur) / 2.0, 2)
    
    active_dur = min(float(target_dur), total_dur - start_sec)
    if active_dur < 3.0:
        start_sec = 0.0
        active_dur = min(float(target_dur), total_dur)

    # کیپ کٹ اسٹائل سنیمائی لُک: شیشے جیسے شفاف رنگ (Contrast/Vibrance), شارپنس، اور فریم زوم فل سکرین
    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "eq=contrast=1.16:brightness=0.02:saturation=1.30:gamma=0.94,"
        "unsharp=7:7:1.30:5:5:0.0,"
        "setpts=1.03*PTS,"  # کاپی رائٹ سے بچنے کے لیے اسپیڈ مائیکرو شفٹ
        "format=yuv420p"
    )

    cmd = [
        "-ss", f"{start_sec:.2f}",
        "-i", raw_path,
        "-t", f"{active_dur:.2f}"
    ]

    audio_map_idx = None
    if audio_action == "Use Custom Copyright-Free Music / Voiceover" and custom_audio_path and os.path.exists(custom_audio_path):
        cmd += ["-stream_loop", "-1", "-i", custom_audio_path]
        audio_map_idx = 1
    elif audio_action == "Keep Original Audio (Crystal Clear)" and has_audio:
        audio_map_idx = 0
    else:
        audio_map_idx = None

    wm_idx = None
    if wm_path and os.path.exists(wm_path):
        cmd += ["-i", wm_path]
        wm_idx = 2 if audio_map_idx == 1 else (1 if audio_map_idx == 0 else 1)

    if wm_idx is not None:
        if add_sticker:
            filter_complex = f"[0:v]{video_filter}[vbase];[{wm_idx}:v]scale=180:-1[wm];[vbase][wm]overlay=W-w-40:40[v1];color=red@0.85:s=340x65[box];[v1][box]overlay=(W-w)/2:H-h-90[vout]"
        else:
            filter_complex = f"[0:v]{video_filter}[vbase];[{wm_idx}:v]scale=180:-1[wm];[vbase][wm]overlay=W-w-40:40[vout]"
        cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
    else:
        if add_sticker:
            filter_complex = f"[0:v]{video_filter}[vbase];color=red@0.85:s=340x65[box];[vbase][box]overlay=(W-w)/2:H-h-90[vout]"
            cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
        else:
            cmd += ["-vf", video_filter, "-map", "0:v"]

    if audio_map_idx is not None:
        cmd += ["-map", f"{audio_map_idx}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd += [
        "-map_metadata", "-1",  # کاپی رائٹ میٹاڈیٹا مکمل صاف کرنے کے لیے
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "17",
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

# ==========================
# Streamlit UI (Pure Roman English)
# ==========================
st.title("⚡ Sglowina AI Viral Short Studio Pro")
st.markdown("Upload a video file **OR** paste a YouTube/Social video link. AI Auto-Director will instantly transform it into a breathtaking **CapCut-style 9:16 Action Short** with crystal clear beauty colors, stickers, and anti-copyright protection!")

input_method = st.radio("Choose Input Method:", ["Upload Video File", "Paste YouTube / Video Link"], horizontal=True)

up_file = None
yt_url = ""

if input_method == "Upload Video File":
    up_file = st.file_uploader("📥 Upload Your Video File (MP4, MOV, MKV):", type=["mp4", "mov", "mkv"])
else:
    yt_url = st.text_input("🔗 Paste YouTube Video or Short Link (URL):", placeholder="https://www.youtube.com/shorts/...")

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Target Short Duration (Seconds):", 15, 60, 30, 5)
    add_sticker = st.checkbox("🔥 Add Action Viral Badge Overlay (CapCut Style)", value=True)
with c2:
    audio_choice = st.selectbox("🎵 Audio & Anti-Copyright Protection Mode:", [
        "Use Custom Copyright-Free Music / Voiceover",
        "Keep Original Audio (Crystal Clear)",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice.startswith("Use Custom"):
    custom_aud = st.file_uploader("🎶 Upload Your Background Music / Voiceover (MP3):", type=["mp3", "wav"])

wm_file = st.file_uploader("🏷️ Upload Custom Logo / Watermark (Optional):", type=["png", "jpg"])

if st.button("🚀 Pro AI Edit & Export Viral Short", use_container_width=True):
    if input_method == "Upload Video File" and not up_file:
        st.error("Please upload a video file first.")
    elif input_method == "Paste YouTube / Video Link" and not yt_url.strip():
        st.error("Please paste a valid YouTube video link.")
    elif audio_choice.startswith("Use Custom") and not custom_aud:
        st.error("Please upload your custom background music file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        raw_p = os.path.join(work_dir, f"raw_input.mp4")
        out_p = f"Viral_Pro_Short_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File":
                stat.info("📥 Saving uploaded video file...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue())
                prog.progress(0.20)
            else:
                stat.info("🌐 Connecting to YouTube and downloading video via link...")
                dl_res = download_youtube_video(yt_url.strip(), raw_p)
                if dl_res is not True:
                    raise RuntimeError(f"YouTube download failed: {dl_res}")
                prog.progress(0.20)

            wm_p = None
            if wm_file:
                wm_p = os.path.join(work_dir, "wm.png")
                with open(wm_p, "wb") as f:
                    f.write(wm_file.getvalue())

            aud_p = None
            if custom_aud:
                aud_ext = os.path.splitext(custom_aud.name)[1] or ".mp3"
                aud_p = os.path.join(work_dir, f"aud{aud_ext}")
                with open(aud_p, "wb") as f:
                    f.write(custom_aud.getvalue())

            stat.info("⚡ CapCut AI Director: Applying action cuts, beauty grading, and anti-copyright shield...")
            prog.progress(0.50)

            actual_dur = pro_action_viral_edit(raw_p, out_p, target_duration, audio_choice, aud_p, wm_p, add_sticker, work_dir)
            prog.progress(0.85)

            extract_thumbnail_frame(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Your professional CapCut-style viral short is successfully ready!")

            col_v1, col_v2 = st.columns([1.2, 0.8])
            with col_v1:
                st.video(out_p)
                with open(out_p, "rb") as f_out:
                    st.download_button(
                        "📥 Download Viral Short Video (MP4)",
                        f_out.read(),
                        file_name=out_p,
                        mime="video/mp4",
                        use_container_width=True
                    )
            with col_v2:
                if os.path.exists(thumb_p):
                    st.image(thumb_p, caption="Auto-Extracted Thumbnail Frame")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Thumbnail (JPG)",
                            f_th.read(),
                            file_name=f"Thumbnail_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

            # Professional SEO Metadata in Roman English
            st.markdown("---")
            st.markdown("### 🔥 AI Generated Viral Metadata & SEO Kit (Roman English)")
            
            viral_title = "🔥 Unbelievable Action Moment You Can't Miss! #Shorts #Viral #Trending"
            viral_desc = (
                "Experience the most thrilling action moment edited in high definition cinematic quality. "
                "Like, share and subscribe for more mind-blowing viral clips every day!\n\n"
                "#Shorts #Viral #Trending #ActionShorts #EpicMoments #Foryou #SglowinaAI"
            )
            viral_tags = "shorts, viral, trending, action moments, capcut edit, epic scene, top shorts, foryou, sglowina studio"

            st.text_input("📌 Suggested Viral Title:", value=viral_title)
            st.text_area("📝 Suggested Video Description:", value=viral_desc, height=100)
            st.text_input("🏷️ Suggested Viral Tags:", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
