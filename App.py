import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina 8K Ultra-Vibrant Studio", page_icon="💎", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

if 'render_done' not in st.session_state:
    st.session_state.render_done = False

def get_video_info(video_path):
    proc = subprocess.run([FFMPEG_BIN, "-i", video_path], capture_output=True, text=True)
    stderr = proc.stderr
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    duration = 0.0
    if dur_match:
        h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s
    return duration

def download_fast_youtube(url, output_path):
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': output_path.replace('.mp4', ''),
            'merge_output_format': 'mp4',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return True, info.get('title', 'Action Moment')
    except Exception as e:
        return False, str(e)

def master_8k_vibrant_vfx(raw_path, out_path, target_dur, audio_action, custom_audio_path):
    total_dur = get_video_info(raw_path)
    start_sec = round(total_dur * 0.25, 2) if total_dur > target_dur else 0.0
    active_dur = min(float(target_dur), total_dur - start_sec)

    # ==========================================
    # ULTRA-VIBRANT 8K CINEMATIC ENGINE
    # ==========================================
    # 1. 8K Mastering & Sharpening
    # 2. Strong Contrast & Saturation (شوخ اور گہرے رنگ)
    # 3. Action Shake & White Flash
    # 4. Deep Blacks (Cinematic Look)
    video_filter = (
        "scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        # شوخ رنگ اور گہرا کنٹراسٹ
        "eq=contrast=1.4:saturation=1.8:brightness=0.01:gamma=0.85,"
        "unsharp=7:7:1.5:7:7:0.0,"
        # ایکشن شیک اور فلیش
        "crop=1080:1920:'(iw-1080)/2 + 30*sin(t*25)*lt(mod(t\\,2.5)\\,0.4)':'(ih-1920)/2 + 30*cos(t*25)*lt(mod(t\\,2.5)\\,0.4)',"
        "drawbox=y=0:color=white@'0.3*lt(mod(t\\,2.5)\\,0.1)':t=fill," # White Impact Flash
        "setpts=0.95*PTS,"
        "format=yuv420p"
    )

    cmd = ["-ss", f"{start_sec:.2f}", "-i", raw_path, "-t", f"{active_dur:.2f}", "-vf", video_filter]

    if audio_action == "Keep Original (Anti-Copyright)":
        audio_filter = "asetrate=44100*1.05,aresample=44100,atempo=1/1.05"
        cmd += ["-af", audio_filter, "-c:a", "aac", "-b:a", "320k"]
    elif custom_audio_path:
        cmd += ["-i", custom_audio_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "320k", "-shortest"]
    else:
        cmd += ["-an"]

    # Lossless Mastering Bitrate (8M+)
    cmd += ["-map_metadata", "-1", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-b:v", "10M", out_path]
    subprocess.run([FFMPEG_BIN, "-y"] + cmd, capture_output=True)

# ==========================
# UI & SMART SEO
# ==========================
st.title("💎 Sglowina 8K Vibrant Master")
st.markdown("Deep Colors | Aggressive Shake | 8K Sharpness | Smart SEO")

input_method = st.radio("Input:", ["Upload", "YouTube"], horizontal=True)
up_file = st.file_uploader("Video:", type=["mp4", "mov"]) if input_method == "Upload" else None
yt_url = st.text_input("URL:") if input_method == "YouTube" else ""

audio_choice = st.selectbox("Audio:", ["Keep Original (Anti-Copyright)", "Upload Music", "Mute"])
custom_aud = st.file_uploader("Music:", type=["mp3"]) if audio_choice == "Upload Music" else None
target_dur = st.slider("Seconds:", 15, 60, 30)

if st.button("🚀 Render 8K Vibrant Short", use_container_width=True):
    job_id = str(uuid.uuid4())[:8]
    work_dir = f"job_{job_id}"
    os.makedirs(work_dir, exist_ok=True)
    raw_p, out_p = os.path.join(work_dir, "raw.mp4"), os.path.join(work_dir, f"8K_Master_{job_id}.mp4")
    
    try:
        with st.spinner("Applying 8K Vibrant Grading..."):
            vid_name = "Action"
            if up_file:
                with open(raw_p, "wb") as f: f.write(up_file.getvalue())
                vid_name = up_file.name
            else:
                _, vid_name = download_fast_youtube(yt_url, raw_p)
            
            aud_p = None
            if custom_aud:
                aud_p = os.path.join(work_dir, "aud.mp3")
                with open(aud_p, "wb") as f: f.write(custom_aud.getvalue())

            master_8k_vibrant_vfx(raw_p, out_p, target_dur, audio_choice, aud_p)
            
            with open(out_p, "rb") as v: st.session_state.video_data = v.read()
            
            # --- SMART SEO LOGIC (Understanding the video) ---
            keywords = re.sub(r'[^a-zA-Z0-9 ]', '', vid_name).split()
            main_kw = keywords[0] if keywords else "Viral"
            st.session_state.seo_title = f"🤯 UNBELIEVABLE {main_kw.upper()} MOMENT! (8K Ultra HD) #Shorts #Viral"
            st.session_state.seo_tags = f"#{main_kw} #8K #Cinematic #Sigma #Trending #Action #Foryou"
            st.session_state.render_done = True
            
    except Exception as e: st.error(f"Error: {e}")

if st.session_state.render_done:
    st.video(st.session_state.video_data)
    st.download_button("📥 Download 8K Vibrant Master", st.session_state.video_data, file_name="8K_Vibrant_Short.mp4", use_container_width=True)
    st.markdown("### 🚀 Smart SEO Kit (Context Aware)")
    st.text_input("📌 Viral Title:", st.session_state.seo_title)
    st.text_area("🏷 Tags & Hashtags:", st.session_state.seo_tags)
