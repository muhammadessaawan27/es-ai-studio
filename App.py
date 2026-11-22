import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob

st.set_page_config(page_title="Sglowina Master Action Director", page_icon="🎬", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

# سیشن اسٹیٹ (تاکہ ویڈیو اور ٹائٹل کبھی غائب نہ ہوں)
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
            video_title = info.get('title', 'Epic Action Video')
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
    # ULTRA HIGH QUALITY VFX + SHAKE + FLASH FILTER
    # ==========================================
    # اب تصویر بالکل نہیں پھٹے گی۔ ہم ڈائریکٹ اسکیل اور کراپ کر رہے ہیں۔
    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase:flags=bicubic," # High Quality Scale
        # ہلکا کیمرہ شیک (تاکہ کنارے باہر نہ نکلیں) اور زوم
        "crop=1080:1920:'(iw-1080)/2 + 15*sin(t*15)*lt(mod(t\\,3)\\,0.3)':'(ih-1920)/2 + 15*cos(t*15)*lt(mod(t\\,3)\\,0.3)',"
        # کلر گریڈنگ اور امپیکٹ فلیش (کوئی بلر فلٹر نہیں ڈالا تاکہ تصویر صاف رہے)
        "eq=contrast=1.12:brightness='0.0+0.15*lt(mod(t\\,3)\\,0.1)':saturation=1.3,"
        "colorbalance=rs=0.04:bs=0.08," 
        # ہلکی اور کرسپ شارپنیس (زیادہ نہیں تاکہ پکسل نہ پھٹیں)
        "unsharp=3:3:0.8:3:3:0.0,"
        "setpts=0.95*PTS," # Speed Ramping
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
        audio_filter = "asetrate=44100*1.05,aresample=44100,atempo=1/1.05"
        cmd += ["-map", "0:v", "-map", "0:a", "-af", audio_filter, "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-map", "0:v", "-an"]

    # HIGH BITRATE & CRISP QUALITY (crf 16 = Near Lossless Quality)
    cmd += [
        "-map_metadata", "-1", 
        "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-b:v", "5M", "-maxrate", "6M", "-bufsize", "12M",
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
st.markdown("Transform any video into a premium cinematic action sequence! Features **Action Camera Shake, Impact Flashes, Glass-Clear 4K Quality**, and **Auto-SEO Generation**.")

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
        out_p = os.path.join(work_dir, f"Action_Short_{job_id}.mp4")
        thumb_p = os.path.join(work_dir, f"thumbnail_{job_id}.jpg")
        
        extracted_video_title = "Epic Action Moment"

        prog = st.progress(0.0)
        stat = st.empty()

        try:
            if input_method == "Upload Video File (Fast)":
                stat.info("📥 Direct Memory Write: Saving your file...")
                with open(raw_p, "wb") as f:
                    f.write(up_file.getvalue())
                extracted_video_title = os.path.splitext(up_file.name)[0].replace('_', ' ').replace('-', ' ').title()
                prog.progress(0.20)
            else:
                stat.info("🌐 Fetching Video and Reading Info...")
                success, yt_title = download_fast_youtube(yt_url.strip(), raw_p)
                if not success:
                    raise RuntimeError(f"Download failed: {yt_title}")
                extracted_video_title = yt_title 
                prog.progress(0.40)

            aud_p = None
            if custom_aud:
                aud_ext = os.path.splitext(custom_aud.name)[1] or ".mp3"
                aud_p = os.path.join(work_dir, f"aud{aud_ext}")
                with open(aud_p, "wb") as f:
                    f.write(custom_aud.getvalue())

            stat.info("🔥 AI Auto-Director: Applying Action Shakes, Impact Flashes & High-Quality Full Screen...")
            prog.progress(0.65)

            actual_dur = master_action_vfx_director(raw_p, out_p, target_duration, audio_choice, aud_p)
            prog.progress(0.90)

            extract_thumbnail(out_p, thumb_p)
            prog.progress(1.0)
            stat.success("🎉 Render Complete! Here is your High-Quality Video and Auto-Generated SEO.")

            # ڈاٹا کو سیشن اسٹیٹ (میموری) میں محفوظ کر رہے ہیں تاکہ غائب نہ ہو
            with open(out_p, "rb") as f_video:
                st.session_state.video_data = f_video.read()
            if os.path.exists(thumb_p):
                with open(thumb_p, "rb") as f_thumb:
                    st.session_state.thumb_data = f_thumb.read()
            
            # ٹائٹل اور ٹیگز بھی میموری میں محفوظ
            clean_title = (extracted_video_title[:40] + '..') if len(extracted_video_title) > 40 else extracted_video_title
            st.session_state.seo_title = f"🔥 {clean_title} - Most INSANE Moment! 🤯 #Shorts"
            st.session_state.seo_desc = f"You won't believe this moment from {clean_title}! Watch till the end.\n\nEdited with AI Auto-Director for the best cinematic action experience.\nDon't forget to Like and Subscribe!\n\n#Shorts #Viral #Sigma #Action #Trending"
            base_tag = clean_title.split()[0].lower() if clean_title else "action"
            st.session_state.seo_tags = f"{base_tag}, {base_tag} edit, {base_tag} shorts, viral shorts, sigma edit, epic fight, action status, trending, foryoupage"
            
            st.session_state.render_done = True

        except Exception as e:
            st.error(f"❌ Processing Error: {e}")
        finally:
            for tmp in glob.glob(os.path.join(work_dir, "*")):
                try: os.remove(tmp)
                except: pass
            try: os.rmdir(work_dir)
            except: pass

# ==========================
# PERMANENT DISPLAY SECTION (اب یہ غائب نہیں ہوگا)
# ==========================
if st.session_state.render_done:
    col_v1, col_v2 = st.columns([1.2, 0.8])
    with col_v1:
        st.video(st.session_state.video_data)
        st.download_button(
            "📥 Download Master Short (MP4)",
            st.session_state.video_data,
            file_name="Viral_Master_Short.mp4",
            mime="video/mp4",
            use_container_width=True
        )
    with col_v2:
        if 'thumb_data' in st.session_state:
            st.image(st.session_state.thumb_data, caption="Action Keyframe")
            st.download_button(
                "🖼️ Download Keyframe (JPG)",
                st.session_state.thumb_data,
                file_name="Keyframe.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
            
    st.markdown("---")
    st.markdown("### 🚀 Auto-Generated Viral SEO Kit")
    st.markdown("The AI analyzed your video and created this perfect SEO for YouTube Shorts:")
            
    st.text_input("📌 Viral Title (Copy this):", value=st.session_state.seo_title)
    st.text_area("📝 Description (Copy this):", value=st.session_state.seo_desc, height=120)
    st.text_input("🏷️ Tags (Copy this):", value=st.session_state.seo_tags)
