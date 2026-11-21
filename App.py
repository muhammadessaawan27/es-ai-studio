import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina AI Cinematic Master VFX", page_icon="🎥", layout="wide")

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

def download_master_quality(url, output_path):
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
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

def find_cinematic_timestamp(video_path, target_dur):
    total_dur, _ = get_video_info(video_path)
    if total_dur <= target_dur + 5:
        return 0.0
    best_start = round(total_dur * 0.35, 2)
    if best_start + target_dur > total_dur:
        best_start = 0.0
    return best_start

def extract_thumbnail_frame(video_path, thumb_out_path):
    run_ffmpeg(["-ss", "00:00:02", "-i", video_path, "-vframes", "1", thumb_out_path])

def master_vfx_auto_director(raw_path, out_path, target_dur, audio_action, custom_audio_path, work_dir):
    """
    AI Auto-Director VFX Engine: 
    Implements Purple Energy Tone, Bloom/Glow, 4K Upscaling, Unsharp Mask, and Speed Control.
    """
    total_dur, has_audio = get_video_info(raw_path)
    start_sec = find_cinematic_timestamp(raw_path, target_dur)
    active_dur = min(float(target_dur), total_dur - start_sec)

    # 4K UHD Resolution setup
    tw, th = 2160, 3840

    # ==========================================
    # THE MASTER VFX COMPLEX FILTER
    # ==========================================
    # 1. Scale & Crop to True 4K
    # 2. Cinematic Color Grading (Contrast, Saturation)
    # 3. Purple Energy Cinematic Style (colorbalance)
    # 4. Detail Enhancement (unsharp mask)
    # 5. Split for Bloom/Glow effect
    # 6. Screen Blend (Glow + Original)
    # 7. Speed Ramping (Micro Speed Shift for anti-copyright and motion flow)
    
    vfx_filter = (
        f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
        f"crop={tw}:{th}:(iw-{tw})/2:(ih-{th})/2,"
        "eq=contrast=1.18:brightness=0.01:saturation=1.35:gamma=0.92,"
        "colorbalance=rs=0.05:gs=0.0:bs=0.12:rm=0.02:gm=0.0:bm=0.08," # Purple/Magenta Magic Tone
        "unsharp=9:9:1.5:5:5:0.0[base];"
        "[base]split[vmain][vblur];"
        "[vblur]boxblur=20:10,eq=brightness=0.1[vbloom];"
        "[vmain][vbloom]blend=all_mode=screen:all_opacity=0.15[vbloomed];" # Glow / Light Emission
        "[vbloomed]setpts=1.03*PTS[vout]" # Speed Ramping Control
    )

    cmd = [
        "-ss", f"{start_sec:.2f}",
        "-i", raw_path,
        "-t", f"{active_dur:.2f}",
        "-filter_complex", vfx_filter,
        "-map", "[vout]"
    ]

    # Sound Design & Audio Sync
    if audio_action == "Use Custom Copyright-Free Music / Voiceover" and custom_audio_path and os.path.exists(custom_audio_path):
        cmd += ["-stream_loop", "-1", "-i", custom_audio_path, "-map", "1:a", "-c:a", "aac", "-b:a", "320k", "-shortest"]
    elif audio_action == "Keep Original Audio (Crystal Clear)" and has_audio:
        cmd += ["-map", "0:a", "-c:a", "aac", "-b:a", "320k"]
    else:
        cmd += ["-an"]

    # Final Rendering & Export (CRF 14 Master Preset)
    cmd += [
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14",
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

# ==========================
# Streamlit UI (Pure Professional English)
# ==========================
st.title("🎥 AI Cinematic Auto-Director & Master VFX Engine")
st.markdown("Transform ordinary, low-impact footage into a visually powerful, polished, cinematic action sequence inspired by premium anime-action edits. Includes **4K Upscaling, Purple Energy Grading, Bloom Glow, and Advanced Tracking Effects.**")

input_method = st.radio("Choose Input Method:", ["Upload Video File", "Paste YouTube / Movie Link"], horizontal=True)

up_file = None
yt_url = ""

if input_method == "Upload Video File":
    up_file = st.file_uploader("📥 Upload Your Raw Footage (MP4, MKV):", type=["mp4", "mov", "mkv"])
else:
    yt_url = st.text_input("🔗 Paste YouTube Video Link (URL):", placeholder="https://www.youtube.com/watch?v=...")

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Cinematic Sequence Duration (Seconds):", 15, 60, 30, 5)
with c2:
    audio_choice = st.selectbox("🎵 Professional Sound Design:", [
        "Keep Original Audio (Crystal Clear 320kbps)",
        "Use Custom Copyright-Free Music / Voiceover",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice.startswith("Use Custom"):
    custom_aud = st.file_uploader("🎶 Upload Epic Background Music (MP3):", type=["mp3", "wav"])

if st.button("🚀 Initialize Master VFX Engine & Render", use_container_width=True):
    if input_method == "Upload Video File" and not up_file:
        st.error("Please upload a video file first.")
    elif input_method == "Paste YouTube / Movie Link" and not yt_url.strip():
        st.error("Please paste a valid YouTube video link.")
    elif audio_choice.startswith("Use Custom") and not custom_aud:
        st.error("Please upload your custom music file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        raw_p = os.path.join(work_dir, f"raw_input.mp4")
        out_p = f"Master_Cinematic_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File":
                stat.info("📥 Ingesting raw footage into VFX pipeline...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue())
                prog.progress(0.20)
            else:
                stat.info("🌐 Extracting master-quality stream from server...")
                dl_res = download_master_quality(yt_url.strip(), raw_p)
                if dl_res is not True:
                    raise RuntimeError(f"Download failed: {dl_res}")
                prog.progress(0.35)

            aud_p = None
            if custom_aud:
                aud_ext = os.path.splitext(custom_aud.name)[1] or ".mp3"
                aud_p = os.path.join(work_dir, f"aud{aud_ext}")
                with open(aud_p, "wb") as f:
                    f.write(custom_aud.getvalue())

            stat.info("🤖 AI Auto-Director: Applying Purple Energy Glow, 4K Upscale, & Dynamic Speed Ramping...")
            prog.progress(0.60)

            actual_dur = master_vfx_auto_director(raw_p, out_p, target_duration, audio_choice, aud_p, work_dir)
            prog.progress(0.90)

            extract_thumbnail_frame(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Master VFX Rendering Complete! Your cinematic sequence is ready.")

            col_v1, col_v2 = st.columns([1.2, 0.8])
            with col_v1:
                st.video(out_p)
                with open(out_p, "rb") as f_out:
                    st.download_button(
                        "📥 Download 4K Master Sequence (MP4)",
                        f_out.read(),
                        file_name=out_p,
                        mime="video/mp4",
                        use_container_width=True
                    )
            with col_v2:
                if os.path.exists(thumb_p):
                    st.image(thumb_p, caption="Extracted Cinematic Frame")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Keyframe (JPG)",
                            f_th.read(),
                            file_name=f"Keyframe_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )

            # AI Generated Meta
            st.markdown("---")
            st.markdown("### 🔥 Auto-Generated Cinematic Metadata")
            
            viral_title = "⚡ Ultimate Supernatural Anime Action | 4K Cinematic Masterpiece"
            viral_desc = (
                "Watch this visually powerful, polished cinematic action sequence enhanced with advanced AI Director tools. "
                "Featuring purple energy styling, cinematic bloom, and 4K UHD upscaling.\n\n"
                "#Cinematic #AnimeEdit #4K #VFX #ActionShorts #Supernatural #Masterpiece #SglowinaAI"
            )
            viral_tags = "cinematic edit, anime action, vfx supervisor, 4k upscale, purple energy, glow effect, auto director, viral shorts"

            st.text_input("📌 Suggested Title:", value=viral_title)
            st.text_area("📝 Suggested Description:", value=viral_desc, height=100)
            st.text_input("🏷️ Suggested Tags:", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Render Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
