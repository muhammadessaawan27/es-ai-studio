import streamlit as st
import subprocess
import os
import re
import uuid
import time
import cv2
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Sglowina 8K AI Master", page_icon="💎", layout="wide")

# فولڈرز
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("rendered")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def analyze_video_context(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return "Medium"
    motion_scores = []
    count = 0
    while count < 100:
        ret, frame = cap.read()
        if not ret: break
        if count % 10 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if count > 0:
                diff = cv2.absdiff(gray, prev_gray)
                motion_scores.append(np.mean(diff))
            prev_gray = gray
        count += 1
    cap.release()
    return "High" if np.mean(motion_scores) > 7 else "Medium"

def render_8k_safe(params):
    p = params
    # 8K کے لیے مخصوص میموری سیف ریزولوشن
    res_map = {
        "720p": "720:1280", "1080p": "1080:1920", 
        "1440p": "1440:2560", "4K": "2160:3840", "8K": "4320:7680"
    }
    target_res = res_map.get(p['res'], "1080:1920")
    
    # فلٹر چین: 8K Lanczos Scaling + Sharpness
    v_filter = f"scale={target_res}:force_original_aspect_ratio=increase:flags=lanczos,crop={target_res}:(iw-ow)/2:(ih-oh)/2"
    
    if p['preset'] == "Purple Energy":
        v_filter += ",eq=contrast=1.3:saturation=1.6,colorbalance=rs=0.1:bs=0.2"
    elif p['preset'] == "Ultra Vibrant":
        v_filter += ",eq=contrast=1.2:saturation=1.8:brightness=0.01"
    
    if p['intensity'] == "High":
        v_filter += f",crop={target_res}:(iw-ow)/2+20*sin(t*10):(ih-oh)/2+20*cos(t*10),eq=brightness='0.1*lt(mod(t,2),0.1)'"

    # FFmpeg 8K Optimized Command
    cmd = ["ffmpeg", "-y", "-i", str(p['video_in'])]
    
    if p['music_in'] and "Music" in p['audio_mode']:
        cmd += ["-i", str(p['music_in'])]
        if p['audio_mode'] == "Mix Original + Music":
            cmd += ["-filter_complex", f"[0:a]volume={p['vol_orig']}[a0];[1:a]volume={p['vol_mus']}[a1];[a0][a1]amix=inputs=2:duration=first"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a", "-shortest"]
    
    # 8K Encoding سیٹنگز جو سرور کو کریش ہونے سے بچاتی ہیں
    cmd += [
        "-vf", v_filter,
        "-c:v", "libx264", 
        "-preset", "ultrafast", # کلاؤڈ ریم بچانے کے لیے سب سے اہم
        "-crf", "18", 
        "-pix_fmt", "yuv420p", # موبائل سپورٹ کے لیے
        "-level", "6.2", # 8K سپورٹ کے لیے
        "-max_muxing_queue_size", "1024",
        "-t", str(p['duration']),
        str(p['video_out'])
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

def main():
    st.title("💎 Sglowina 8K Ultra-AI Studio")
    video_file = st.sidebar.file_uploader("Upload Video", type=["mp4", "mov"])
    
    if video_file:
        res_choice = st.selectbox("Resolution", ["1080p", "1440p", "4K", "8K"], index=0)
        if res_choice == "8K":
            st.warning("⚠️ 8K رینڈرنگ میں 1 سے 2 منٹ لگ سکتے ہیں۔ رینڈر کے بعد ویڈیو براہِ راست یہاں نہیں چلے گی، آپ کو اسے ڈاؤن لوڈ کر کے دیکھنا ہوگا۔")
        
        preset = st.selectbox("Cinematic Style", ["Purple Energy", "Ultra Vibrant", "Dark Action", "Original"])
        duration = st.slider("Duration", 5, 60, 15)
        
        # آڈیو
        a_mode = st.selectbox("Audio", ["Keep Original", "Music Only", "Mix Original + Music"])
        music_file = st.file_uploader("Background Music", type=["mp3"]) if "Music" in a_mode else None

        if st.button("🚀 RENDER 8K MASTERPIECE"):
            job_id = uuid.uuid4().hex[:6]
            raw_p = UPLOAD_DIR / f"raw_{job_id}.mp4"
            out_p = OUTPUT_DIR / f"Sglowina_8K_{job_id}.mp4"
            
            with open(raw_p, "wb") as f: f.write(video_file.getbuffer())
            
            m_path = None
            if music_file:
                m_path = UPLOAD_DIR / f"m_{job_id}.mp3"
                with open(m_path, "wb") as f: f.write(music_file.getbuffer())

            intensity = analyze_video_context(str(raw_p))
            
            params = {
                'video_in': raw_path, 'video_out': out_path, 'music_in': m_path,
                'res': res_choice, 'preset': preset, 'duration': duration,
                'audio_mode': a_mode, 'vol_orig': 0.8, 'vol_mus': 1.0, 'intensity': intensity
            }

            with st.spinner(f"Rendering {res_choice} Cinematic Video..."):
                success, error = render_8k_safe(params)
                if success:
                    st.success("✨ Render Complete!")
                    # 8K کے لیے صرف ڈاؤن لوڈ بٹن (کیونکہ پلیئر سپورٹ نہیں کرتا)
                    with open(out_p, "rb") as f:
                        st.download_button(f"📥 Download {res_choice} Video", f, file_name=f"Sglowina_{res_choice}.mp4", use_container_width=True)
                    
                    if res_choice != "8K": # 1080p اور 4K کا پری ویو دکھائیں
                        st.video(str(out_p))
                else:
                    st.error(f"Error: {error}")

if __name__ == "__main__":
    main()
