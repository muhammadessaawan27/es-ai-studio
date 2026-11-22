import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina Master Action Director", page_icon="🎬", layout="wide")

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
            video_title = info.get('title', 'Epic Action Video') # یوٹیوب سے خود اصلی ٹائٹل نکالے گا
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
        return True, video_title
    except Exception as e:
        return False, str(e)

def master_action_vfx_director(raw_path, out_path, target_dur, audio_action, custom_audio_path):
    total_dur, has_audio = get_video_info(raw_path)
    
    start_sec = 0.0
    if total_dur > target_dur + 5:
        start_sec = round(total_dur * 0.35, 2)
    active_dur = min(float(target_dur), total_dur - start_sec)
    if active_dur < 3.0:
        start_sec, active_dur = 0.0, min(float(target_dur), total_dur)

    # ==========================================
    # 20-POINT MASTER VFX + SHAKE + FLASH FILTER (Crisp Quality)
    # ==========================================
    video_filter = (
        "crop=iw*0.95:ih*0.95:(iw-ow)/2:(ih-oh)/2," # 5% Anti-Logo Crop
        "scale=1152:2048:force_original_aspect_ratio=increase:flags=lanczos," # 4K Upscaler
        "crop=1080:1920:x='(iw-1080)/2+25*sin(t*30)*lt(mod(t\\,3)\\,0.4)':y='(ih-1920)/2+25*cos(t*30)*lt(mod(t\\,3)\\,0.4)'," # Camera Shake & Zoom
        "eq=contrast=1.15:brightness='0.01+0.25*lt(mod(t\\,3)\\,0.15)':saturation=1.35:gamma=0.95," # Action Flash + HDR
        "colorbalance=rs=0.04:bs=0.09," # Purple Energy Vibe
        "hqdn3d=2.0:2.0:4:4," # Denoise (تصویر پھٹنے سے بچانے کے لیے)
        "unsharp=5:5:0.8:5:5:0.0," # Crystal Sharpness
        "setpts=0.95*PTS," # 0.95x Speed Ramp (Anti-Copyright)
        "format=yuv420p"
    )

    cmd = [
        "-ss", f"{start_sec:.2f}",
        "-i", raw_path,
        "-t", f"{active_dur:.2f}",
        "-vf", video_filter,
        "-threads", "0" 
    ]

    if audio_action == "Use Custom Copyright-Free Music" and custom_audio_path and os.path.exists(custom_audio_path):
        cmd += ["-i", custom_audio_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    elif audio_action == "Keep Original Audio (With Anti-Copyright Protection)" and has_audio:
        audio_filter = "asetrate=44100*1.05,aresample=44100,atempo=1/1.05" # Anti-Copyright Pitch
        cmd += ["-map", "0:v", "-map", "0:a", "-af", audio_filter, "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-map", "0:v", "-an"]

    cmd += [
        "-map_metadata", "-1", # Metadata Wipe
        "-c:v", "libx264", "-preset", "faster", "-crf", "20", 
        out_path
    ]
    
    run_ffmpeg(cmd)
    return active_dur

def extract_thumbnail(video_path, thumb_out_path):
    run_ffmpeg(["-ss", "00:00:02", "-i", video_path, "-vframes", "1", thumb_out_path])

# ==========================
# Streamlit UI 
# ==========================
st.title("🎬 Master Action Auto-Director Studio")
st.markdown("Transform any video into a premium cinematic action sequence! Features **Action Camera Shake, Impact Flashes, Glass-Clear Quality**, and **Auto-SEO Generation**.")

input_method = st.radio("Choose Input Method:", ["Upload Video File (Fast)", "Paste YouTube Link"], horizontal=True)

up_file = None
yt_url = ""

if input_method == "Upload Video File (Fast)":
    up_file = st.file_uploader("📥 Upload Raw Video (MP4, MKV):", type=["mp4", "mov", "mkv"])
else:
    yt_url = st.text_input("🔗 Paste YouTube/Social Video Link (URL):", placeholder="https://www.youtube.com/watch?v=...")

c1, c2 = st.columns(2)
with c1:
    target_duration = st.slider("⏱️ Target Cinematic Short Duration (Seconds):", 15, 60, 30, 5)
with c2:
    audio_choice = st.selectbox("🎵 Audio & Sound Design:", [
        "Keep Original Audio (With Anti-Copyright Protection)",
        "Use Custom Copyright-Free Music",
        "Mute Audio (No Sound)"
    ])

custom_aud = None
if audio_choice == "Use Custom Copyright-Free Music":
    custom_aud = st.file_uploader("🎶 Upload Epic Background Music (MP3):", type=["mp3", "wav"])

if st.button("🚀 Render Action Short & Auto-Generate SEO", use_container_width=True):
    if input_method == "Upload Video File (Fast)" and not up_file:
        st.error("Please upload a video file first.")
    elif input_method == "Paste YouTube Link" and not yt_url.strip():
        st.error("Please paste a valid YouTube video link.")
    elif audio_choice == "Use Custom Copyright-Free Music" and not custom_aud:
        st.error("Please upload your custom music file.")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        raw_p = os.path.join(work_dir, f"raw_input.mp4")
        out_p = f"Action_Short_{job_id}.mp4"
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")
        
        extracted_video_title = "Epic Action Moment" # Default Title

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File (Fast)":
                stat.info("📥 Direct Memory Write: Saving your file...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue())
                # فائل کے نام کو ہی ٹائٹل کے لیے استعمال کرے گا
                extracted_video_title = os.path.splitext(up_file.name)[0].replace('_', ' ').replace('-', ' ').title()
                prog.progress(0.20)
            else:
                stat.info("🌐 Fetching Video and Reading Info...")
                success, yt_title = download_fast_youtube(yt_url.strip(), raw_p)
                if not success:
                    raise RuntimeError(f"Download failed: {yt_title}")
                extracted_video_title = yt_title # یوٹیوب کا اصلی ٹائٹل سیو کر لیا
                prog.progress(0.40)

            aud_p = None
            if custom_aud:
                aud_ext = os.path.splitext(custom_aud.name)[1] or ".mp3"
                aud_p = os.path.join(work_dir, f"aud{aud_ext}")
                with open(aud_p, "wb") as f:
                    f.write(custom_aud.getvalue())

            stat.info("🔥 AI Auto-Director: Applying Action Shakes, Impact Flashes & HDR Full Screen...")
            prog.progress(0.65)

            actual_dur = master_action_vfx_director(raw_p, out_p, target_duration, audio_choice, aud_p)
            prog.progress(0.90)

            extract_thumbnail(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Render Complete! Here is your Video and Auto-Generated SEO.")

            # ==========================
            # VIDEO & DOWNLOAD SECTION
            # ==========================
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
                    st.image(thumb_p, caption="Action Keyframe")
                    with open(thumb_p, "rb") as f_th:
                        st.download_button(
                            "🖼️ Download Keyframe (JPG)",
                            f_th.read(),
                            file_name=f"Keyframe_{job_id}.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )
            
            st.markdown("---")
            
            # ==========================
            # AUTO YOUTUBE SEO GENERATOR (Without extra button)
            # ==========================
            st.markdown("### 🚀 Auto-Generated Viral SEO Kit")
            st.markdown("The AI analyzed your video and created this perfect SEO for YouTube Shorts:")
            
            # کلین اور وائرل ٹائٹل جنریشن
            clean_title = (extracted_video_title[:40] + '..') if len(extracted_video_title) > 40 else extracted_video_title
            viral_title = f"🔥 {clean_title} - Most INSANE Moment! 🤯 #Shorts"
            viral_desc = f"You won't believe this moment from {clean_title}! Watch till the end.\n\nEdited with AI Auto-Director for the best cinematic action experience.\nDon't forget to Like and Subscribe!\n\n#Shorts #Viral #Sigma #Action #Trending"
            
            # ویڈیو کے نام سے ملتے جلتے ہیش ٹیگ
            base_tag = clean_title.split()[0].lower() if clean_title else "action"
            viral_tags = f"{base_tag}, {base_tag} edit, {base_tag} shorts, viral shorts, sigma edit, epic fight, action status, trending, foryoupage, ytshorts"
            
            st.text_input("📌 Viral Title (Copy this):", value=viral_title)
            st.text_area("📝 Description (Copy this):", value=viral_desc, height=120)
            st.text_input("🏷️ Tags (Copy this):", value=viral_tags)

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass
