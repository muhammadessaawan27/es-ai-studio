import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import math
import glob

st.set_page_config(page_title="Sglowina AI Viral Short Studio", page_icon="⚡", layout="wide")

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

def extract_thumbnail_frame(video_path, thumb_out_path):
    """ویڈیو کے درمیان سے یا پہلے سیکنڈ سے ایک شاندار تھمب نیل فریم نکالتا ہے"""
    run_ffmpeg(["-ss", "00:00:01", "-i", video_path, "-vframes", "1", thumb_out_path])

def ai_lightning_fast_edit(raw_path, out_path, target_dur, audio_action, custom_audio_path, wm_path, add_sticker, work_dir):
    """سپر فاسٹ الٹرا آپٹمائزڈ ایڈیٹنگ انجن جو چند سیکنڈ میں بیوٹی کلرز اور فل سکرین شارٹ تیار کرتا ہے"""
    total_dur, has_audio = get_video_info(raw_path)
    
    start_sec = 0.0
    if total_dur > target_dur + 5:
        start_sec = round((total_dur - target_dur) / 2.0, 2)
    
    active_dur = min(float(target_dur), total_dur - start_sec)
    if active_dur < 3.0:
        start_sec = 0.0
        active_dur = min(float(target_dur), total_dur)

    # بیوٹی کیمرے جیسے کلرز، شیشے جیسی شفافیت اور پکسل شفٹ کافیسٹ پائپ لائن
    # ultrafast preset کی وجہ سے اب 24MB کی ویڈیو چند سیکنڈ میں رینڈر ہوگی
    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "eq=contrast=1.14:brightness=0.03:saturation=1.28:gamma=0.95,"
        "unsharp=5:5:1.15:3:3:0.0,"
        "setpts=1.02*PTS,"
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

    # اگر یوزر نے ایڈونچر/وائرل بیج (Sticker Overlay) سلیکٹ کیا ہو
    if wm_idx is not None:
        if add_sticker:
            filter_complex = f"[0:v]{video_filter}[vbase];[{wm_idx}:v]scale=180:-1[wm];[vbase][wm]overlay=W-w-40:40[v1];color=red@0.8:s=320x60[box];[v1][box]overlay=(W-w)/2:H-h-80[vout]"
        else:
            filter_complex = f"[0:v]{video_filter}[vbase];[{wm_idx}:v]scale=180:-1[wm];[vbase][wm]overlay=W-w-40:40[vout]"
        cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
    else:
        if add_sticker:
            filter_complex = f"[0:v]{video_filter}[vbase];color=red@0.8:s=320x60[box];[vbase][box]overlay=(W-w)/2:H-h-80[vout]"
            cmd += ["-filter_complex", filter_complex, "-map", "[vout]"]
        else:
            cmd += ["-vf", video_filter, "-map", "0:v"]

    if audio_map_idx is not None:
        cmd += ["-map", f"{audio_map_idx}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    # ultrafast preset سے پروسیسنگ سپیڈ 10 گنا تیز ہو جائے گی
    cmd += [
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

# ==========================
# Streamlit UI (Pure Roman English)
# ==========================
st.title("⚡ Sglowina AI Viral Short Studio")
st.markdown("Upload any long or short video. AI Auto-Director will instantly convert it into a stunning **Full-Screen 9:16 Viral Masterpiece** with glass-like beauty colors, anti-copyright shield, and lightning-fast speed!")

up_file = st.file_uploader("📥 Upload Your Video File (MP4, MOV, MKV):", type=["mp4", "mov", "mkv"])

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Target Short Duration (Seconds):", 15, 60, 30, 5)
    add_sticker = st.checkbox("🔥 Add Trending Action Badge Overlay (Sticker Effect)", value=True)
with c2:
    audio_choice = st.selectbox("🎵 Audio & Copyright Protection Mode:", [
        "Use Custom Copyright-Free Music / Voiceover",
        "Keep Original Audio (Crystal Clear)",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice.startswith("Use Custom"):
    custom_aud = st.file_uploader("🎶 Upload Your Background Music / Voiceover (MP3):", type=["mp3", "wav"])

wm_file = st.file_uploader("🏷️ Upload Custom Logo / Watermark (Optional):", type=["png", "jpg"])

if st.button("🚀 Lightning Fast AI Edit & Export", use_container_width=True):
    if not up_file:
        st.error("Please upload a video file first.")
    elif audio_choice.startswith("Use Custom") and not custom_aud:
        st.error("Please upload your custom music/audio file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        ext = os.path.splitext(up_file.name)[1] or ".mp4"
        raw_p = os.path.join(work_dir, f"raw{ext}")
        out_p = f"Viral_Short_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")

        with open(raw_p, "wb") as f:
            f.write(up_file.getvalue())

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

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            stat.info("⚡ Super-Fast AI Engine: Processing video frames and optimizing colors...")
            prog.progress(0.30)

            actual_dur = ai_lightning_fast_edit(raw_p, out_p, target_duration, audio_choice, aud_p, wm_p, add_sticker, work_dir)
            prog.progress(0.80)

            # Extract automatic thumbnail frame
            extract_thumbnail_frame(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Your viral short video and thumbnail are successfully ready!")

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
                    st.image(thumb_p, caption="Auto-Extracted Viral Thumbnail Frame")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Thumbnail (JPG)",
                            f_th.read(),
                            file_name=f"Thumbnail_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

            # Professional Auto-Generated Viral Metadata (Roman English)
            st.markdown("---")
            st.markdown("### 🔥 AI Generated Viral Metadata & SEO Kit")
            
            viral_title = "🔥 Ultimate Action & Mind Blowing Moments! #Shorts #Viral #Trending"
            viral_desc = (
                "Watch this incredible viral moment captured in stunning high-definition quality. "
                "Don't forget to like, share, and subscribe for more amazing daily content!\n\n"
                "#Shorts #Viral #Trending #Action #Foryou #Masterpiece #SglowinaAI"
            )
            viral_tags = "shorts, viral, trending, action shorts, masterpiece, sglowina ai, epic moments, top viral, foryoupage"

            st.text_input("📌 Suggested Viral Title (Copy):", value=viral_title)
            st.text_area("📝 Suggested Video Description (Copy):", value=viral_desc, height=100)
            st.text_input("🏷️ Suggested Viral Tags (Copy):", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
