import streamlit as st
import subprocess, shutil, tempfile, os, re, uuid, asyncio, json, time
from pathlib import Path

st.set_page_config(page_title="Sglowina AI — Cinematic Studio", page_icon="🎬", layout="wide")
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
BASE = Path(tempfile.gettempdir()) / "sglowina_ai"
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)


def tools_ready():
    return bool(FFMPEG and FFPROBE)



def run(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)



def probe_duration(path):
    if not FFPROBE:
        raise RuntimeError("ffprobe دستیاب نہیں۔ Hosting packages میں ffmpeg شامل کریں۔")
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])
    return max(0.05, float(r.stdout.strip()))


def split_script(text, mode):
    text = (text or "").strip()
    if not text:
        return []
    if mode == "Paragraphs":
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    elif mode == "Sentences":
        parts = [p.strip() for p in re.split(r"(?<=[۔.!?؟])\s+|\n+", text) if p.strip()]
    else:
        parts = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    return parts or [text]


def safe_concat_list(paths, list_file):
    # FFmpeg concat files require safe escaping for apostrophes in paths.
    lines = []
    for p in paths:
        val = Path(p).resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{val}'\n")
    list_file.write_text("".join(lines), encoding="utf-8")


def motion_filter(mode, duration, width, height, fps=24):
    frames = max(1, int(float(duration) * fps))
    pre = f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},setsar=1"
    # Zoompan uses a looped still input. Keep the expressions simple and FFmpeg-safe.
    if mode == "Zoom Out":
        z = "max(1.0,1.12-on*0.00045)"
    elif mode == "Pan Left":
        z = "1.08"
    elif mode == "Pan Right":
        z = "1.08"
    elif mode == "Slow Zoom":
        z = "min(1.0+on*0.00035,1.10)"
    else:
        z = "min(1.0+on*0.00045,1.12)"
    if mode == "Pan Left":
        x = "(iw-iw/zoom)*0.15"
    elif mode == "Pan Right":
        x = "(iw-iw/zoom)*0.85"
    else:
        x = "(iw-iw/zoom)/2"
    y = "(ih-ih/zoom)/2"
    return f"{pre},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},setsar=1"


async def tts_async(text, voice, rate, pitch, target):
    import edge_tts
    await edge_tts.Communicate(text=text, voice=voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz").save(str(target))


def tts_sync(text, voice, rate, pitch, target):
    # Runs Edge TTS in its own event loop for Streamlit's synchronous script.
    asyncio.run(tts_async(text, voice, rate, pitch, target))



def make_soft_ambient(duration, target):
    """Create a quiet, original synthesized ambient pad (no percussion/lyrics)."""
    duration = max(2.0, float(duration))
    # Three low, softly blended tones; this is ambience, not a religious ruling or sourced nasheed.
    src = (
        f"sine=frequency=196:duration={duration}:sample_rate=44100",
        f"sine=frequency=246.94:duration={duration}:sample_rate=44100",
        f"sine=frequency=293.66:duration={duration}:sample_rate=44100",
    )
    fc = (
        "[0:a]volume=0.10[a0];[1:a]volume=0.065[a1];[2:a]volume=0.045[a2];"
        "[a0][a1][a2]amix=inputs=3:normalize=0,lowpass=f=900,"
        "afade=t=in:st=0:d=3,afade=t=out:st=" + f"{max(0.0, duration-4):.3f}:d=4,volume=0.35[out]"
    )
    cmd = [FFMPEG, "-y"]
    for tone in src:
        cmd += ["-f", "lavfi", "-i", tone]
    cmd += ["-filter_complex", fc, "-map", "[out]", "-t", f"{duration:.3f}", "-ac", "2", "-ar", "44100", str(target)]
    result = run(cmd, timeout=180)
    if result.returncode or not target.exists() or target.stat().st_size == 0:
        raise RuntimeError("Ambient audio بنانے میں خرابی: " + result.stderr[-1500:])
    return target

def render_story(image_files, script, split_mode, voice, rate, pitch, motion, resolution, music_file, music_volume, progress_cb):
    if not tools_ready():
        raise RuntimeError("FFmpeg/FFprobe نہیں ملے۔ Streamlit Cloud کی packages.txt میں ffmpeg درکار ہے۔")
    scenes = split_script(script, split_mode)
    if not scenes:
        raise ValueError("پہلے مکمل کہانی لکھیں۔")
    if not image_files:
        raise ValueError("کم از کم ایک تصویر منتخب کریں۔")
    width, height = (1280, 720) if resolution == "720p" else (1920, 1080)
    job = uuid.uuid4().hex[:10]
    work = UPLOADS / f"story_{job}"
    work.mkdir(parents=True, exist_ok=True)
    out = OUTPUTS / f"Sglowina_Story_{job}.mp4"
    clips = []
    total = len(scenes)
    for idx, scene in enumerate(scenes):
        progress_cb((idx / max(1, total)) * 0.82, f"سین {idx+1}/{total}: وائس تیار ہو رہی ہے")
        img_path = image_files[idx % len(image_files)]
        voice_path = work / f"voice_{idx:04d}.mp3"
        clip_path = work / f"scene_{idx:04d}.mp4"
        tts_sync(scene, voice, rate, pitch, voice_path)
        sec = probe_duration(voice_path) + 0.15
        chosen_motion = motion if motion != "Auto Mix" else ["Slow Zoom", "Zoom Out", "Pan Left", "Pan Right"][idx % 4]
        vf = motion_filter(chosen_motion, sec, width, height)
        cmd = [FFMPEG, "-y", "-loop", "1", "-i", str(img_path), "-i", str(voice_path),
               "-vf", vf, "-map", "0:v:0", "-map", "1:a:0", "-t", f"{sec:.3f}", "-r", "24",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(clip_path)]
        result = run(cmd)
        if result.returncode != 0 or not clip_path.exists() or clip_path.stat().st_size == 0:
            raise RuntimeError(f"سین {idx+1} بنانے میں FFmpeg کی خرابی:\n{result.stderr[-1800:]}")
        clips.append(clip_path)
    progress_cb(0.84, "تمام سین جوڑے جا رہے ہیں…")
    concat_file = work / "scene_list.txt"
    safe_concat_list(clips, concat_file)
    video_only = work / "story_video.mp4"
    r = run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(video_only)])
    if r.returncode:
        raise RuntimeError("Scenes جوڑنے میں خرابی:\n" + r.stderr[-1800:])
    progress_cb(0.90, "آخری آڈیو مکس اور ایکسپورٹ…")
    if music_file:
        bg_path = music_file
    else:
        bg_path = work / "soft_spiritual_ambience.wav"
        make_soft_ambient(probe_duration(video_only), bg_path)
    cmd = [FFMPEG, "-y", "-i", str(video_only), "-i", str(bg_path),
           "-filter_complex", f"[0:a]volume=1.0[narr];[1:a]volume={music_volume}[bg];[narr][bg]amix=inputs=2:duration=first:dropout_transition=3,alimiter=limit=0.95[aout]",
           "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    r = run(cmd)
    if r.returncode or not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("Final export میں خرابی:\n" + r.stderr[-2000:])
    progress_cb(1.0, "ویڈیو مکمل تیار ہے")
    return out



def atempo_filter(speed):
    # Build an FFmpeg atempo chain for supported speeds.
    value = float(speed)
    filters = []
    while value < 0.5:
        filters.append("atempo=0.5")
        value /= 0.5
    while value > 2.0:
        filters.append("atempo=2.0")
        value /= 2.0
    filters.append(f"atempo={value:.5f}")
    return ",".join(filters)


def render_editor(src, out, resolution, style, speed, pitch_shift, audio_mode, music_path, original_vol, music_vol, duration_limit):
    if not tools_ready():
        raise RuntimeError("FFmpeg/FFprobe دستیاب نہیں۔")
    sizes = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440), "4K": (3840, 2160), "8K": (7680, 4320)}
    w, h = sizes[resolution]
    vf = f"setpts=PTS/{speed},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    if style == "Purple Energy":
        vf += ",eq=contrast=1.15:saturation=1.35,colorbalance=rs=0.05:bs=0.12"
    elif style == "Ultra Vibrant":
        vf += ",eq=contrast=1.10:saturation=1.50:brightness=0.01"
    elif style == "Dark Action":
        vf += ",eq=contrast=1.25:saturation=1.15:brightness=-0.04"
    elif style == "Cinematic Warm":
        vf += ",eq=contrast=1.08:saturation=1.12:brightness=0.02,colorbalance=rs=0.04:gs=0.02:bs=-0.03"
    duration = min(probe_duration(src), float(duration_limit))
    job = uuid.uuid4().hex[:8]
    tmp = UPLOADS / f"editor_{job}.mp4"
    cmd = [FFMPEG, "-y", "-i", str(src)]
    if music_path and audio_mode in ("Music Only", "Mix Original + Music"):
        if audio_mode == "Music Only":
            cmd += ["-stream_loop", "-1", "-i", str(music_path)]
            fc = f"[1:a]volume={music_vol},{atempo_filter(speed)}[aout]"
            cmd += ["-filter_complex", fc, "-map", "0:v:0", "-map", "[aout]"]
        else:
            cmd += ["-stream_loop", "-1", "-i", str(music_path)]
            orig_chain = atempo_filter(speed)
            # Optional independent pitch shift, duration restored by atempo.
            if pitch_shift:
                factor = 2 ** (float(pitch_shift) / 12.0)
                orig_chain = f"asetrate=44100*{factor:.6f},aresample=44100,{atempo_filter(speed/factor)}"
            fc = f"[0:a]volume={original_vol},{orig_chain}[orig];[1:a]volume={music_vol}[bg];[orig][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            cmd += ["-filter_complex", fc, "-map", "0:v:0", "-map", "[aout]"]
    elif audio_mode == "Mute":
        cmd += ["-map", "0:v:0", "-an"]
    elif audio_mode == "Music Only" and music_path:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        if pitch_shift:
            factor = 2 ** (float(pitch_shift) / 12.0)
            fc = f"[0:a]volume={original_vol},asetrate=44100*{factor:.6f},aresample=44100,{atempo_filter(speed/factor)}[aout]"
            cmd += ["-filter_complex", fc, "-map", "0:v:0", "-map", "[aout]"]
        else:
            cmd += ["-map", "0:v:0", "-map", "0:a?", "-af", f"volume={original_vol},{atempo_filter(speed)}"]
    cmd += ["-vf", vf, "-t", str(duration), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)]
    r = run(cmd)
    if r.returncode or not tmp.exists() or tmp.stat().st_size == 0:
        return False, r.stderr[-3500:]
    shutil.move(str(tmp), str(out))
    return True, ""


st.title("🎬 Sglowina AI — Cinematic Studio")
st.caption("Story Cinema • Multi-image rendering • Voice-over • Video Editor")
if not tools_ready():
    st.warning("اس ہوسٹنگ میں FFmpeg/FFprobe نہیں ملے۔ packages.txt میں ffmpeg ضروری ہے۔")

story_tab, edit_tab = st.tabs(["📚 تصاویر سے Story Video", "🎞️ موجودہ Video Editor"])


with story_tab:
    st.subheader("تصاویر سے مکمل کہانی ویڈیو")
    st.info("یہاں کہانی الگ ڈالیں اور تصاویر الگ منتخب کریں۔ ویڈیو کی کوئی مقررہ 10 منٹ کی حد کوڈ میں نہیں رکھی گئی؛ دورانیہ وائس اور اسکرپٹ کے مطابق ہوگا۔ ہوسٹنگ کی CPU/RAM اور وقت کی حدود پھر بھی اثر انداز ہو سکتی ہیں۔")
    story_script = st.text_area("مکمل کہانی / Voice-over", height=280, key="story_text", placeholder="یہاں اپنی مکمل کہانی پیسٹ کریں…")
    split_mode = st.radio("کہانی کو سینز میں کیسے تقسیم کریں؟", ["Sentences", "Paragraphs", "Lines"], horizontal=True, key="split_mode")
    images = st.file_uploader("ایک ساتھ متعدد تصاویر منتخب کریں (زیادہ سے زیادہ 200؛ JPG, PNG, WEBP)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="story_images", max_files=200)
    if images:
        total_mb = sum(x.size for x in images) / (1024 * 1024)
        st.success(f"تصاویر منتخب ہوئیں: {len(images)}  |  کل سائز: {total_mb:.1f} MB")
        if total_mb > 120:
            st.warning("تصاویر کا سائز کافی بڑا ہے؛ موبائل یا ہوسٹنگ میں اپ لوڈ/رینڈرنگ سست ہو سکتی ہے۔ بہتر ہے تصاویر کو پہلے compress کریں۔")
        st.caption("تصاویر سینز کے ساتھ ترتیب وار استعمال ہوں گی؛ اگر سین زیادہ ہوں تو تصاویر دوبارہ استعمال ہوں گی۔")
    c1, c2, c3 = st.columns(3)
    with c1:
        voice_option = st.selectbox("اردو وائس", ["Asad — پاکستانی مرد", "Uzma — پاکستانی خاتون"], key="story_voice")
    with c2:
        speed_option = st.select_slider("وائس کی رفتار", options=[-25, -15, -5, 0, 5, 15, 25], value=0, key="story_speed")
    with c3:
        pitch_option = st.select_slider("وائس Pitch", options=[-20, -15, -10, -5, 0, 5, 10, 15, 20], value=-10, key="story_pitch")
    c4, c5 = st.columns(2)
    with c4:
        story_motion = st.selectbox("تصاویر کی حرکت", ["Auto Mix", "Slow Zoom", "Zoom Out", "Pan Left", "Pan Right"], key="story_motion")
    with c5:
        story_res = st.selectbox("Story Video Resolution", ["720p", "1080p"], index=0, key="story_resolution")
    music = st.file_uploader("پس منظر آڈیو / نعت / موسیقی (اختیاری)", type=["mp3", "wav", "m4a", "aac"], key="story_audio")
    music_vol = st.slider("پس منظر آڈیو والیوم (خودکار نرم Ambient بھی شامل ہوگا)", 0.0, 0.5, 0.08, 0.01, key="story_music_volume")
    st.caption("اگر اپنی آڈیو اپ لوڈ نہیں کریں گے تو ایپ خود نرم synthesized ambience بنائے گی (بغیر percussion یا lyrics کے)۔ یہ نغمہ/نشید نہیں اور مذہبی حکم کا دعویٰ نہیں۔")
    if st.button("🎬 Story Video بنائیں", type="primary", key="create_story"):
        if not story_script.strip():
            st.error("اسکرپٹ درج کریں۔")
        elif not images:
            st.error("کم از کم ایک تصویر منتخب کریں۔")
        elif not tools_ready():
            st.error("FFmpeg/FFprobe دستیاب نہیں۔")
        else:
            job = uuid.uuid4().hex[:10]
            image_paths = []
            upload_error = None
            with st.spinner("منتخب تصاویر محفوظ اور جانچ کی جا رہی ہیں…"):
                try:
                    for n, f in enumerate(images):
                        ext = Path(f.name).suffix.lower()
                        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                            continue
                        path = UPLOADS / f"{job}_image_{n:04d}{ext}"
                        path.write_bytes(f.getbuffer())
                        # Basic FFprobe validation; corrupt image fails early and is skipped.
                        chk = run([FFPROBE, "-v", "error", "-show_entries", "stream=width,height", "-of", "json", str(path)])
                        if chk.returncode == 0 and chk.stdout.strip():
                            image_paths.append(path)
                        else:
                            path.unlink(missing_ok=True)
                except Exception as e:
                    upload_error = str(e)
            if upload_error:
                st.error(f"تصویر محفوظ کرنے میں مسئلہ: {upload_error}")
            elif not image_paths:
                st.error("کوئی قابلِ استعمال تصویر نہیں ملی۔")
            else:
                music_path = None
                if music:
                    music_path = UPLOADS / f"{job}_bg_{Path(music.name).suffix.lower()}"
                    music_path.write_bytes(music.getbuffer())
                progress = st.progress(0.0)
                status = st.empty()
                def update_progress(val, msg):
                    progress.progress(min(1.0, max(0.0, val)))
                    status.write(msg)
                try:
                    voice = "ur-PK-AsadNeural" if voice_option.startswith("Asad") else "ur-PK-UzmaNeural"
                    with st.spinner("رینڈرنگ چل رہی ہے؛ تصاویر کی تعداد اور کہانی کے دورانیے کے مطابق وقت لگے گا…"):
                        result = render_story(image_paths, story_script, split_mode, voice, int(speed_option), int(pitch_option), story_motion, story_res, music_path, music_vol, update_progress)
                    st.success("Story Video مکمل تیار ہے!")
                    st.video(str(result))
                    with open(result, "rb") as vf:
                        st.download_button("📥 مکمل MP4 ڈاؤن لوڈ کریں", vf, file_name=result.name, mime="video/mp4", key="story_download")
                except Exception as e:
                    st.error("ویڈیو بنانے میں مسئلہ آیا:")
                    st.code(str(e))


with edit_tab:
    st.subheader("Original Video Editor")
    video_file = st.file_uploader("Video upload (MP4 / MOV / MKV)", type=["mp4", "mov", "mkv"], key="editor_video")
    if video_file:
        res = st.selectbox("Output Resolution", ["720p", "1080p", "1440p", "4K", "8K"], index=1, key="edit_res")
        style = st.selectbox("Cinematic Filter", ["Original", "Purple Energy", "Ultra Vibrant", "Dark Action", "Cinematic Warm"], key="edit_style")
        speed = st.slider("Video / Audio Speed", 0.25, 2.0, 1.0, 0.05, key="edit_speed")
        pitch = st.slider("Independent Audio Pitch (semitones)", -12, 12, 0, key="edit_pitch")
        audio_mode = st.selectbox("Audio Mode", ["Keep Original", "Music Only", "Mix Original + Music", "Mute"], key="edit_audio_mode")
        music = st.file_uploader("Background Music (optional)", type=["mp3", "wav", "m4a", "aac"], key="edit_music")
        original_vol = st.slider("Original Audio Volume", 0.0, 2.0, 0.8, 0.05, key="edit_orig_vol")
        music_vol = st.slider("Music Volume", 0.0, 2.0, 0.25, 0.05, key="edit_music_vol")
        max_duration = st.number_input("Max output duration (seconds; 0 = full video)", min_value=0, max_value=86400, value=0, step=30, key="edit_duration")
        if st.button("🚀 Render Edited Video", type="primary", key="render_editor"):
            job = uuid.uuid4().hex[:10]
            src = UPLOADS / f"source_{job}{Path(video_file.name).suffix.lower()}"
            out = OUTPUTS / f"Edited_{job}.mp4"
            src.write_bytes(video_file.getbuffer())
            music_path = None
            if music:
                music_path = UPLOADS / f"music_{job}{Path(music.name).suffix.lower()}"
                music_path.write_bytes(music.getbuffer())
            try:
                dur = probe_duration(src)
                limit = dur if int(max_duration) == 0 else min(dur, int(max_duration))
                with st.spinner("ویڈیو رینڈر ہو رہی ہے… اعلیٰ ریزولوشن میں وقت زیادہ لگ سکتا ہے۔"):
                    ok, err = render_editor(src, out, res, style, speed, pitch, audio_mode, music_path, original_vol, music_vol, limit)
                if ok:
                    st.success("ویڈیو تیار ہے!")
                    st.video(str(out))
                    with open(out, "rb") as vf:
                        st.download_button("📥 Edited MP4 ڈاؤن لوڈ کریں", vf, file_name=out.name, mime="video/mp4", key="editor_download")
                else:
                    st.error("FFmpeg Render میں مسئلہ آیا:")
                    st.code(err)
            except Exception as e:
                st.error("رینڈرنگ میں مسئلہ:")
                st.code(str(e))
