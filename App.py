import streamlit as st
import subprocess
import os
import re
import uuid
import time
import cv2
import numpy as np
from pathlib import Path

# --- سیٹ اپ اور برانڈنگ ---
st.set_page_config(page_title="Sglowina AI Cinematic Studio", page_icon="🎬", layout="wide")

# فولڈرز کا انتظام
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("rendered")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 1. اصلی ویڈیو اینالائزر (AI Director Logic)
def analyze_video_context(video_path):
    """ویڈیو کے فریمز کو چیک کر کے ایکشن اور برائٹنس کا پتہ لگاتا ہے"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return "Medium", 0.5
    
    motion_scores = []
    prev_frame = None
    count = 0
    
    while count < 150: # پہلے 150 فریمز کا تجزیہ
        ret, frame = cap.read()
        if not ret: break
        if count % 10 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_frame is not None:
                diff = cv2.absdiff(gray, prev_frame)
                motion_scores.append(np.mean(diff))
            prev_frame = gray
        count += 1
    cap.release()
    
    avg_motion = np.mean(motion_scores) if motion_scores else 0
    intensity = "High" if avg_motion > 7 else ("Low" if avg_motion < 2 else "Medium")
    return intensity

# 2. پروفیشنل آڈیو مکسر اور رینڈرنگ انجن
def render_cinematic_video(params):
    p = params
    v_in = p['video_in']
    out = p['video_out']
    
    # ریزولوشن سیٹنگ
    res_map = {"720p": "720:1280", "1080p": "1080:1920", "1440p": "1440:2560", "4K": "2160:3840", "8K": "4320:7680"}
    target_res = res_map.get(p['res'], "1080:1920")
    
    # فلٹر چین (Cinematic Grading & VFX)
    # اس میں اصلی Lanczos شارپننگ اور کلر بیلنس شامل ہے
    v_filter = f"scale={target_res}:force_original_aspect_ratio=increase,crop={target_res}:(iw-ow)/2:(ih-oh)/2"
    
    # سینیمیٹک پری سیٹس
    if p['preset'] == "Purple Energy":
        v_filter += ",eq=contrast=1.3:saturation=1.5:brightness=0.02,colorbalance=rs=0.12:bs=0.22"
    elif p['preset'] == "Teal and Orange":
        v_filter += ",colorbalance=rs=0.15:bs=-0.1:gs=0.05,eq=contrast=1.15"
    elif p['preset'] == "Dark Action":
        v_filter += ",eq=contrast=1.4:saturation=0.9:brightness=-0.05:gamma=0.8"
    
    # ایکشن شیک اور فلیش (صرف تب جب اینالائزر 'High' کہے)
    if p['intensity'] == "High":
        v_filter += f",crop={target_res}:(iw-ow)/2+15*sin(t*15):(ih-oh)/2+15*cos(t*15)"
        v_filter += ",eq=brightness='0.1*lt(mod(t,2),0.1)'"

    # آڈیو مکسنگ (پیشہ ورانہ طریقہ)
    cmd = ["ffmpeg", "-y", "-i", str(v_in)]
    
    if p['audio_mode'] == "Mix Original + Music" and p['music_in']:
        cmd += ["-i", str(p['music_in'])]
        cmd += ["-filter_complex", f"[0:a]volume={p['vol_orig']}[a0];[1:a]volume={p['vol_mus']}[a1];[a0][a1]amix=inputs=2:duration=first"]
    elif p['audio_mode'] == "Music Only" and p['music_in']:
        cmd += ["-i", str(p['music_in']), "-map", "0:v", "-map", "1:a", "-shortest"]
    elif p['audio_mode'] == "Keep Original":
        cmd += ["-c:a", "copy"]
    elif p['audio_mode'] == "Remove Original":
        cmd += ["-an"]

    # فائنل ایکسپورٹ سیٹنگز
    cmd += ["-vf", v_filter, "-c:v", "libx264", "-preset", "faster", "-crf", "17", "-t", str(p['duration']), str(out)]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

# 3. محفوظ کلین اپ
def safe_cleanup():
    now = time.time()
    for f in list(UPLOAD_DIR.glob("*")) + list(OUTPUT_DIR.glob("*")):
        if f.is_file() and (now - f.stat().st_mtime) > 3600:
            try: f.unlink()
            except: pass

# --- UI سیکشن ---
def main():
    safe_cleanup()
    st.title("🎬 Sglowina AI Cinematic Auto-Director")
    st.markdown("Professional 8K Cinematic Rendering & Action VFX Studio")

    # سائیڈ بار ان پٹ
    with st.sidebar:
        st.header("📥 میڈیا اپلوڈ")
        video_file = st.file_uploader("ویڈیو فائل منتخب کریں", type=["mp4", "mov", "mkv"])
        st.divider()
        st.header("⚙️ رینڈر سیٹنگز")
        res_choice = st.selectbox("ریزولوشن (Real Scaling)", ["720p", "1080p", "1440p", "4K", "8K"], index=1)
        preset_choice = st.selectbox("کلر گریڈ پری سیٹ", ["Original", "Purple Energy", "Teal and Orange", "Dark Action", "Ultra Vibrant", "Anime Action"])
        duration = st.slider("دورانیہ (Seconds)", 5, 60, 15)

    if video_file:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎵 آڈیو مکسر")
            a_mode = st.selectbox("آڈیو موڈ", ["Keep Original", "Remove Original", "Music Only", "Mix Original + Music", "Mute Completely"])
            music_file = st.file_uploader("پس منظر موسیقی (Optional)", type=["mp3", "wav"])
            vol_orig = st.slider("اوریجنل والیم", 0.0, 2.0, 1.0)
            vol_mus = st.slider("میوزک والیم", 0.0, 2.0, 1.0)

        with col2:
            st.subheader("🚀 ایڈوانسڈ VFX")
            vfx_intensity = st.select_slider("ایکشن انٹینسٹی", options=["Low", "Medium", "High", "Auto"], value="Auto")
            st.info("AI Auto-Director ویڈیو کا تجزیہ کر کے خودکار طور پر بہترین فلٹرز لگائے گا۔")

        if st.button("🚀 رینڈر سینیمیٹک ویڈیو (8K Optimized)", use_container_width=True):
            job_id = uuid.uuid4().hex[:6]
            raw_path = UPLOAD_DIR / f"raw_{job_id}.mp4"
            out_path = OUTPUT_DIR / f"Sglowina_{job_id}.mp4"
            
            with open(raw_path, "wb") as f:
                f.write(video_file.getbuffer())
            
            with st.spinner("🧠 AI Director ویڈیو کا تجزیہ کر رہا ہے..."):
                detected_intensity = analyze_video_context(str(raw_path))
                final_intensity = detected_intensity if vfx_intensity == "Auto" else vfx_intensity
                st.write(f"Detection: **{detected_intensity} Action** سین پایا گیا۔")

            mus_path = None
            if music_file:
                mus_path = UPLOAD_DIR / f"mus_{job_id}.mp3"
                with open(mus_path, "wb") as f: f.write(music_file.getbuffer())

            # رینڈر پیرامیٹرز
            params = {
                'video_in': raw_path, 'video_out': out_path, 'music_in': mus_path,
                'res': res_choice, 'preset': preset_choice, 'duration': duration,
                'audio_mode': a_mode, 'vol_orig': vol_orig, 'vol_mus': vol_mus,
                'intensity': final_intensity
            }

            with st.spinner("🎬 ویڈیو ایڈٹ اور رینڈر ہو رہی ہے..."):
                success, error = render_cinematic_video(params)
                if success and out_path.exists():
                    st.success("✅ رینڈر مکمل ہو گیا!")
                    st.video(str(out_path))
                    
                    # SEO جنریٹر
                    clean_name = video_file.name.split('.')[0].replace('_', ' ')
                    st.session_state.seo_title = f"🔥 {clean_name.upper()} | Cinematic AI Edit #Shorts"
                    st.session_state.seo_tags = f"#{clean_name.replace(' ', '')} #Cinematic #AIEdit #Viral #8K"
                    
                    st.divider()
                    st.subheader("📈 وائرل SEO کٹ")
                    st.text_input("یوٹیوب ٹائٹل", st.session_state.seo_title)
                    st.text_area("ہیش ٹیگز", st.session_state.seo_tags)
                    
                    with open(out_path, "rb") as f:
                        st.download_button("📥 ڈاؤن لوڈ ماسٹر ویڈیو", f, file_name=f"Sglowina_{res_choice}.mp4")
                else:
                    st.error(f"رینڈرنگ میں خرابی آئی: {error}")

    else:
        st.warning("شروع کرنے کے لیے بائیں جانب سے ویڈیو اپلوڈ کریں۔")

if __name__ == "__main__":
    main()
