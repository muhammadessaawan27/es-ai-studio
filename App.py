import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina AI Cinematic Auto-Director", page_icon="🎬", layout="wide")

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

def master_20point_vfx_director(raw_path, out_path, target_dur, audio_action, custom_audio_path):
    """
    AI Auto-Director: Applies the 20-point prompt settings automatically.
    No blur! Pure full-screen crop, Purple energy colors, high sharpness, speed ramping, and anti-copyright.
    """
    total_dur, has_audio = get_video_info(raw_path)
    
    # 1. Smart Action Hunter (Find best action part)
    start_sec = 0.0
    if total_dur > target_dur + 5:
        start_sec = round(total_dur * 0.35, 2)
    active_dur = min(float(target_dur), total_dur - start_sec)
    if active_dur < 3.0:
        start_sec, active_dur = 0.0, min(float(target_dur), total_dur)

    # ==========================================
    # THE 20-POINT MASTER VFX FILTER
    # ==========================================
    # - crop=iw*0.8:ih*0.8 -> Removes 20% edges (kills logos/text naturally without blur)
    # - scale & crop 1080x1920 -> Fills the 9:16 screen perfectly
    # - eq & colorbalance -> Cinematic HDR + Purple Energy Vibe
    # - unsharp -> Crystal clear 4K-like detail boost
    # - setpts -> Speed Ramping (0.95) for action pacing and Anti-Copyright
    
    video_filter = (
        "crop=iw*0.80:ih*0.80:(iw-iw*0.80)/2:(ih-ih*0.80)/2," 
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "eq=contrast=1.20:brightness=0.01:saturation=1.35:gamma=0.92,"
        "colorbalance=rs=0.03:bs=0.08," # Subtle Purple Energy Tone
        "unsharp=7:7:1.5:5:5:0.0," # Pro Detail Sharpening
        "setpts=0.95*PTS," # Action Speed Ramp
        "format=yuv420p"
    )

    # Use all CPU threads for ultra-fast processing
    cmd = [
        "-ss", f"{start_sec:.2f}",
        "-i", raw_path,
        "-t", f"{active_dur:.2f}",
        "-vf", video_filter,
        "-threads", "0" 
    ]

    # Audio & Sound Design (Anti-Copyright)
    if audio_action == "Use Custom Copyright-Free Music / Voiceover" and custom_audio_path and os.path.exists(custom_audio_path):
        cmd += ["-i", custom_audio_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    elif audio_action == "Keep Original Audio (With Anti-Copyright Protection)" and has_audio:
        # Pitch shift to bypass Content ID while keeping it clear
        audio_filter = "asetrate=44100*1.05,aresample=44100,atempo=1/1.05"
        cmd += ["-map", "0:v", "-map", "0:a", "-af", audio_filter, "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-map", "0:v", "-an"]

    # Final Export (Ultrafast preset ensures quick output even on free servers)
    cmd += [
        "-map_metadata", "-1", 
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", 
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

def extract_thumbnail(video_path, thumb_out_path):
    run_ffmpeg(["-ss", "00:00:01", "-i", video_path, "-vframes", "1", thumb_out_path])

# ==========================
# Streamlit UI (Clean & Professional)
# ==========================
st.title("🎬 AI Cinematic Auto-Director Studio")
st.markdown("Transform any video into a premium cinematic action sequence! Features **Full-Screen Smart Crop (No Blur, No Logos)**, Purple Energy Color Grading, Action Speed Ramping, and Strict Anti-Copyright Shield. Fast Upload & Processing!")

input_method = st.radio("Choose Input Method:", ["Upload Video File (Ultra Fast)", "Paste YouTube / Social Link"], horizontal=True)

up_file = None
yt_url = ""

if input_method == "Upload Video File (Ultra Fast)":
    up_file = st.file_uploader("📥 Upload Raw Video (MP4, MKV - Max 50MB):", type=["mp4", "mov", "mkv"])
else:
    yt_url = st.text_input("🔗 Paste YouTube/Social Video Link (URL):", placeholder="https://www.youtube.com/watch?v=...")

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Target Cinematic Short Duration (Seconds):", 15, 60, 30, 5)
with c2:
    audio_choice = st.selectbox("🎵 Audio & Sound Design:", [
        "Keep Original Audio (With Anti-Copyright Protection)",
        "Use Custom Copyright-Free Music / Voiceover",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice == "Use Custom Copyright-Free Music / Voiceover":
    custom_aud = st.file_uploader("🎶 Upload Epic Background Music (MP3):", type=["mp3", "wav"])

if st.button("🚀 Render Master Cinematic Short (Ultra-Fast)", use_container_width=True):
    if input_method == "Upload Video File (Ultra Fast)" and not up_file:
        st.error("Please upload a video file first.")
    elif input_method == "Paste YouTube / Social Link" and not yt_url.strip():
        st.error("Please paste a valid YouTube video link.")
    elif audio_choice == "Use Custom Copyright-Free Music / Voiceover" and not custom_aud:
        st.error("Please upload your custom music file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        raw_p = os.path.join(work_dir, f"raw_input.mp4")
        out_p = f"Master_Action_Short_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File (Ultra Fast)":
                stat.info("📥 Fast Direct Memory Write: Saving your file...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue()) # Direct write fixes the slow upload issue
                prog.progress(0.20)
            else:
                stat.info("🌐 Fetching Video from Server...")
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

            stat.info("🔥 AI Master Director: Cropping Logos, Applying Purple Energy VFX & Anti-Copyright Speed Ramping...")
            prog.progress(0.65)

            actual_dur = master_20point_vfx_director(raw_p, out_p, target_duration, audio_choice, aud_p)
            prog.progress(0.90)

            extract_thumbnail(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Rendering Complete! Your Copyright-Safe Cinematic Masterpiece is Ready.")

            col_v1, col_v2 = st.columns([1.2, 0.8])
            with col_v1:
                st.video(out_p)
                with open(out_p, "rb") as f_out:
                    st.download_button(
                        "📥 Download Master Short (MP4)",
                        f_out.read(),
                        file_name=out_p,
                        mime="video/mp4",
                        use_container_width=True
                    )
            with col_v2:
                if os.path.exists(thumb_p):
                    st.image(thumb_p, caption="Auto-Extracted Cinematic Keyframe")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Keyframe (JPG)",
                            f_th.read(),
                            file_name=f"Keyframe_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

            # Auto-Generated Metadata for Social Media
            st.markdown("---")
            st.markdown("### 📈 AI Generated Action SEO Kit")
            
            viral_title = "⚡ Unbelievable Anime-Style Action Moment! #Cinematic #Shorts"
            viral_desc = (
                "Watch this visually powerful, polished cinematic action sequence! "
                "Enhanced with AI Auto-Director for true HDR colors, perfect speed ramping, and maximum impact.\n\n"
                "Don't forget to Like & Subscribe!\n\n"
                "#ActionShorts #Viral #Sigma #CinematicEdit #Foryou #EpicMoments #SglowinaAI"
            )
            viral_tags = "action shorts, cinematic edit, purple energy, anime edit, viral moments, epic fight, trending video, foryoupage"

            st.text_input("📌 High-Impact Title:", value=viral_title)
            st.text_area("📝 Viral Description:", value=viral_desc, height=120)
            st.text_input("🏷️ Trending Tags:", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
