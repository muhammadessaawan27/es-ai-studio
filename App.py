import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import glob
import json

# ==========================================
# 1. INITIALIZATION & STYLING
# ==========================================
st.set_page_config(page_title="Sglowina AI Cinematic Studio", page_icon="🎬", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

# Maintain session state to prevent UI refreshes from losing video data
if 'render_result' not in st.session_state:
    st.session_state.render_result = None

# ==========================================
# 2. CORE ENGINES (FFMPEG PIPELINE)
# ==========================================

def get_video_metadata(path):
    """Gathers real metadata for SEO and processing decisions."""
    cmd = [FFMPEG_BIN, "-i", path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr
    
    # Extract resolution
    res_match = re.search(r", (\d{3,4})x(\d{3,4})", stderr)
    width, height = (int(res_match.group(1)), int(res_match.group(2))) if res_match else (1280, 720)
    
    # Extract Duration
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    duration = 0.0
    if dur_match:
        h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s
        
    return {"width": width, "height": height, "duration": duration, "raw_info": stderr}

def build_cinematic_filter(preset, intensity, output_res):
    """Constructs the visual engine based on user selection."""
    w, h = output_res.split('x')
    
    # Base Correction (Normalization & Sharpening)
    filters = [
        f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={w}:{h}:(iw-ow)/2:(ih-oh)/2",
        "hqdn3d=1.5:1.5:3:3" # Noise Reduction
    ]
    
    # Preset Logic
    if preset == "Purple Energy Cinematic":
        filters.append("eq=contrast=1.25:saturation=1.5:brightness=0.02:gamma=0.9")
        filters.append("colorbalance=rs=0.1:bs=0.2:rm=0.05:bm=0.15") # Shift to Purple/Magenta
        filters.append("unsharp=5:5:1.0:5:5:0.0")
    elif preset == "Ultra Vibrant":
        filters.append("eq=contrast=1.2:saturation=1.7:brightness=0.01")
        filters.append("unsharp=3:3:0.8:3:3:0.0")
    elif preset == "HDR-Look Cinematic":
        filters.append("tonemap=hable:desat=2")
        filters.append("eq=contrast=1.3:saturation=1.4:gamma=0.8")
    elif preset == "Dark Action Cinematic":
        filters.append("eq=contrast=1.4:saturation=1.1:brightness=-0.05:gamma=0.7")
        filters.append("colorbalance=bs=0.05:gs=-0.05")
    elif preset == "Anime Action":
        filters.append("eq=contrast=1.2:saturation=1.8")
        filters.append("unsharp=7:7:1.2:7:7:0.0")
    
    # Intensity-based Effects
    if intensity in ["Medium", "High"]:
        # Action Shake (Subtle math-based)
        shake_val = 20 if intensity == "High" else 10
        filters.append(f"crop={w}:{h}:(iw-ow)/2+{shake_val}*sin(t*10)*lt(mod(t,2),0.5):(ih-oh)/2+{shake_val}*cos(t*10)*lt(mod(t,2),0.5)")
        # Impact Flash (Every 3 seconds)
        filters.append("eq=brightness='0.0+0.15*lt(mod(t,3),0.1)':contrast='1.0+0.1*lt(mod(t,3),0.1)'")

    return ",".join(filters)

# ==========================================
# 3. UI SECTIONS
# ==========================================

st.title("🎬 Sglowina AI Cinematic Studio")
st.info("Professional Cinematic Auto-Director | 4K HDR Pipeline | Action VFX")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Director Controls")
output_quality = st.sidebar.selectbox("Target Resolution", 
    ["1080x1920 (TikTok/Reels)", "1440x2560 (2K Vertical)", "2160x3840 (4K Ultra HD)", "720x1280 (Standard HD)"], index=0)

intensity = st.sidebar.select_slider("Cinematic Intensity", options=["Low", "Medium", "High", "Auto"], value="Auto")

# --- INPUT SECTION ---
tab1, tab2 = st.tabs(["📥 Upload Video", "🔗 YouTube Link"])

video_path = None
raw_filename = "Cinematic_Edit"

with tab1:
    up_file = st.file_uploader("Choose a video file...", type=["mp4", "mov", "mkv"])
    if up_file:
        video_path = f"temp_{uuid.uuid4().hex}.mp4"
        with open(video_path, "wb") as f:
            f.write(up_file.read())
        raw_filename = up_file.name

with tab2:
    yt_url = st.text_input("Paste YouTube URL")
    if yt_url:
        st.warning("Note: High-res YouTube downloads may be limited by cloud bandwidth.")
        # Simplified download logic for demonstration
        if st.button("Fetch YouTube Video"):
            with st.spinner("Downloading..."):
                video_path = f"temp_yt_{uuid.uuid4().hex}.mp4"
                try:
                    import yt_dlp
                    ydl_opts = {'format': 'bestvideo[height<=1080]+bestaudio/best', 'outtmpl': video_path}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(yt_url, download=True)
                        raw_filename = info.get('title', 'YouTube Video')
                    st.success("Download Complete!")
                except Exception as e:
                    st.error(f"Download Failed: {e}")

# --- ENHANCEMENT OPTIONS ---
if video_path:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎨 Visual Style")
        preset = st.selectbox("Cinematic Preset", [
            "Natural Cinematic", "Ultra Vibrant", "HDR-Look Cinematic", 
            "Dark Action Cinematic", "Purple Energy Cinematic", "Anime Action", "Ultra Sharp"
        ])
        fps_opt = st.selectbox("Output FPS", [24, 30, 60], index=1)
        
    with c2:
        st.subheader("🎵 Audio Engine")
        audio_choice = st.selectbox("Audio Source", ["Keep Original Audio", "Upload Custom Music", "Mute Audio"])
        
        mix_audio = False
        custom_music = None
        if audio_choice == "Upload Custom Music":
            custom_music = st.file_uploader("Upload MP3/WAV", type=["mp3", "wav"])
            mix_audio = st.checkbox("Mix with Original Audio?", value=False)
        
        orig_vol = st.slider("Original Volume", 0.0, 2.0, 1.0)
        mus_vol = st.slider("Music Volume", 0.0, 2.0, 1.0)

    # --- RENDER BUTTON ---
    if st.button("🚀 RENDER CINEMATIC MASTERPIECE", use_container_width=True):
        job_id = str(uuid.uuid4())[:8]
        output_file = f"Sglowina_{job_id}.mp4"
        
        try:
            meta = get_video_metadata(video_path)
            
            # 1. Build Filtergraph
            v_filter = build_cinematic_filter(preset, intensity, output_quality)
            
            # 2. Build Audio Filter
            a_filter = []
            if audio_choice == "Keep Original Audio":
                a_filter = [f"volume={orig_vol},afade=t=in:st=0:d=1,afade=t=out:st={st.session_state.get('dur', 15)-1}:d=1"]
            elif audio_choice == "Mute Audio":
                a_filter = None
            
            # 3. Construct FFmpeg Command
            cmd = [FFMPEG_BIN, "-y", "-i", video_path]
            
            # If custom music
            if custom_music:
                m_path = f"music_{job_id}.mp3"
                with open(m_path, "wb") as f: f.write(custom_music.read())
                cmd += ["-i", m_path]
                
                if mix_audio:
                    cmd += ["-filter_complex", f"[0:a]volume={orig_vol}[a0];[1:a]volume={mus_vol}[a1];[a0][a1]amix=inputs=2:duration=first"]
                else:
                    cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
            
            cmd += ["-vf", v_filter, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-threads", "1"]
            
            # Handle Duration (Dynamic Selection logic)
            target_dur = 30 # Default
            cmd += ["-t", str(target_dur)]
            
            cmd.append(output_file)
            
            with st.spinner("AI Director is processing... This may take a minute."):
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    st.error(f"Render Error: {process.stderr[-500:]}")
                else:
                    # Success
                    st.session_state.render_result = output_file
                    
                    # Generate SEO
                    keywords = re.findall(r'\w+', raw_filename)
                    main_kw = keywords[0] if keywords else "Action"
                    st.session_state.seo_title = f"🔥 {main_kw.upper()} - Insane Cinematic Edit 🤯 #Shorts #Viral"
                    st.session_state.seo_tags = f"#{main_kw} #Cinematic #8K #Edit #Sigma #Action"
                    
        except Exception as e:
            st.error(f"System Error: {e}")

# ==========================================
# 4. DOWNLOAD & PREVIEW
# ==========================================

if st.session_state.render_result:
    res_path = st.session_state.render_result
    if os.path.exists(res_path):
        st.success("✅ Render Complete!")
        
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.video(res_path)
            with open(res_path, "rb") as vid:
                st.download_button("📥 DOWNLOAD CINEMATIC VIDEO", vid, file_name=res_path, use_container_width=True)
        
        with c2:
            st.subheader("🚀 Viral SEO Kit")
            st.text_input("Suggested Title", value=st.session_state.seo_title)
            st.text_area("Hashtags & Description", value=st.session_state.seo_tags, height=150)
            
            st.info("💡 Pro Tip: Upload with 'High Quality Uploads' enabled on Social Media.")

# --- CLEANUP ---
# (Usually handled by background task, but in Streamlit we clean old temp files)
for f in glob.glob("temp_*"):
    try:
        # Check if file is older than 1 hour to prevent deleting active jobs
        if os.path.getmtime(f) < (os.path.time() - 3600):
            os.remove(f)
    except: pass
