import streamlit as st
import os, tempfile, subprocess, shutil, asyncio, math, re, zipfile
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

st.set_page_config(page_title="Sglowina AI | Cinematic Story Studio", page_icon="🎬", layout="wide")

# -------------------- utilities --------------------
def ffmpeg_path():
    return shutil.which("ffmpeg")
def ffprobe_path():
    return shutil.which("ffprobe")
def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-3500:])
    return p

def audio_duration(path):
    if not ffprobe_path():
        return 0.0
    try:
        out = run([ffprobe_path(), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).stdout.strip()
        return float(out)
    except Exception:
        return 0.0

def sentences(text):
    text = re.sub(r'\s+', ' ', text.strip())
    if not text: return []
    parts = re.split(r'(?<=[.!?۔؟])\s+', text)
    return [p.strip() for p in parts if p.strip()]

def split_story(text, count):
    # Preserve sentence order and distribute contiguous text chunks across images.
    s = sentences(text)
    if not s: return [text.strip()] * count
    if count <= 1: return [" ".join(s)]
    chunks, start = [], 0
    total_chars = sum(len(x) for x in s)
    for i in range(count):
        if i == count - 1:
            chunks.append(" ".join(s[start:]))
            break
        target = total_chars * (i + 1) / count
        cur = sum(len(x) for x in s[:start])
        end = start
        while end < len(s) and cur < target:
            cur += len(s[end]); end += 1
        # Keep at least one sentence per remaining scene where possible
        end = max(start + 1, min(end, len(s) - (count - i - 1)))
        chunks.append(" ".join(s[start:end])); start = end
    while len(chunks) < count: chunks.append("")
    return chunks

def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9_-]+', '_', s)[:60] or 'scene'

def edge_tts_to_file(text, voice, rate, volume, outpath):
    import edge_tts
    async def _go():
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        await communicate.save(outpath)
    asyncio.run(_go())

def voice_filters(preset, thickness, pitch_hz):
    # ffmpeg filters: moderate pitch shifting while retaining some formant character.
    # asetrate pitch-shifts and changes speed; compensate with atempo.
    semitones = float(pitch_hz)
    ratio = 2 ** (semitones / 12.0)
    filters = []
    if abs(semitones) > 0.05:
        filters += [f"asetrate=44100*{ratio:.6f}", "aresample=44100", f"atempo={1/ratio:.6f}"]
    # Thickness is gentle EQ/compression, not a real voice identity change.
    bass = int(2 + thickness * 0.16)
    filters += [f"equalizer=f=120:t=q:w=1:g={bass}", "acompressor=threshold=-18dB:ratio=2.5:attack=15:release=180"]
    if preset == "Extra Deep": filters += ["equalizer=f=180:t=q:w=1:g=2"]
    elif preset == "Deep": filters += ["equalizer=f=160:t=q:w=1:g=1"]
    return ",".join(filters)

def make_scene_video(image_path, duration, outpath, w, h, motion, intensity, fps, style, idx):
    duration = max(1.5, float(duration))
    frames = max(1, int(math.ceil(duration * fps)))
    zstep = {"Low": 0.0008, "Medium": 0.0016, "High": 0.0028, "Extreme": 0.0045}.get(intensity, 0.0028)
    # Zoompan only for image scenes. Motion varies per scene while upload order remains fixed.
    if motion == "Auto Director":
        modes = ["Zoom In", "Zoom Out", "Pan Left", "Pan Right", "Dynamic"]
        motion = modes[(idx - 1) % len(modes)]
    if motion == "Zoom Out":
        z = f"max(1.0,1.0+{zstep:.6f}*({frames}-on))"
    else:
        z = f"min(1.18,1.0+{zstep:.6f}*on)"
    if motion == "Pan Left": x = "(iw-iw/zoom)*0.15+(iw-iw/zoom)*0.70*on/{frames}"
    elif motion == "Pan Right": x = "(iw-iw/zoom)*0.85-(iw-iw/zoom)*0.70*on/{frames}"
    elif motion == "Dynamic": x = "(iw-iw/zoom)*(0.5+0.20*sin(on/18))"
    else: x = "(iw-iw/zoom)/2"
    y = "(ih-ih/zoom)/2"
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"
    if style == "Warm Cinematic": vf += ",eq=saturation=1.12:contrast=1.06:brightness=0.015,colorbalance=rs=0.04:gs=0.01:bs=-0.03"
    elif style == "Vibrant": vf += ",eq=saturation=1.25:contrast=1.08:brightness=0.02"
    elif style == "Dark Drama": vf += ",eq=saturation=0.92:contrast=1.14:brightness=-0.035,colorbalance=rs=-0.02:bs=0.04"
    elif style == "Purple Energy": vf += ",colorbalance=rs=0.04:gs=-0.02:bs=0.06,eq=saturation=1.18"
    vf += ",format=yuv420p"
    run([ffmpeg_path(), "-y", "-loop", "1", "-i", str(image_path), "-vf", vf, "-t", f"{duration:.3f}", "-an", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", str(outpath)])

def build_srt(chunks, durations, outpath):
    def ts(t):
        ms = int(round(t * 1000)); hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
        return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"
    t=0; lines=[]; n=1
    for text, dur in zip(chunks, durations):
        if text.strip():
            lines += [str(n), f"{ts(t)} --> {ts(t+dur)}", text.strip(), ""]
            n+=1
        t+=dur
    Path(outpath).write_text("\n".join(lines), encoding="utf-8")

# -------------------- UI --------------------
st.title("🎬 Sglowina AI — Cinematic Story Studio")
st.caption("Sequential Story Scenes • Urdu Voice Studio • Camera Motion • FFmpeg Rendering")
if not ffmpeg_path():
    st.error("FFmpeg دستیاب نہیں۔ Streamlit Cloud میں packages.txt کے اندر ffmpeg شامل کریں۔")

with st.sidebar:
    st.header("🎛️ Film Controls")
    render_mode = st.selectbox("Output Format", ["YouTube 16:9", "Shorts 9:16", "Square 1:1"])
    resolution = st.selectbox("Resolution", ["720p", "1080p", "1440p", "4K"], index=1)
    fps = st.select_slider("FPS", options=[24, 25, 30, 50, 60], value=30)
    style = st.selectbox("Color Grade", ["Original", "Warm Cinematic", "Vibrant", "Dark Drama", "Purple Energy"])
    motion = st.selectbox("Camera Motion", ["Auto Director", "Zoom In", "Zoom Out", "Pan Left", "Pan Right", "Dynamic"])
    motion_power = st.select_slider("Motion Power", options=["Low", "Medium", "High", "Extreme"], value="High")
    st.subheader("🎙️ Voice")
    voice_choice = st.selectbox("Urdu Voice", ["Asad (Male)", "Uzma (Female)"])
    voice_preset = st.selectbox("Voice Depth", ["Normal", "Deep", "Extra Deep", "Cinematic Narrator"])
    thickness = st.slider("Voice Thickness / Bass", 0, 100, 55)
    pitch = st.slider("Pitch Shift (semitones)", -8.0, 3.0, -2.0, 0.5)
    speed = st.slider("Speech Speed", 0.75, 1.25, 1.0, 0.05)
    volume = st.slider("Voice Volume", 50, 150, 100)
    st.subheader("🎵 Audio")
    music_volume = st.slider("Background Music Volume", 0, 100, 12)
    audio_mode = st.selectbox("Audio Mix", ["Voice + Music", "Voice Only", "Music Only", "Mute"])
    st.subheader("📝 Subtitles")
    make_subtitles = st.checkbox("Export SRT subtitles", value=True)

story = st.text_area("📖 یہاں مکمل کہانی / وائس اوور اسکرپٹ پیسٹ کریں", height=240, placeholder="اپنی مکمل کہانی یہاں پیسٹ کریں…")
images = st.file_uploader("🖼️ تصاویر ترتیب سے اپلوڈ کریں (تصویر 1 = Scene 1، تصویر 2 = Scene 2)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
# File order is preserved from the uploader; no sorting/reordering is done.
if images:
    st.info(f"{len(images)} تصاویر موصول ہوئیں۔ ترتیب بالکل اسی اپلوڈ ترتیب میں رکھی جائے گی۔")
    with st.expander("تصاویر کی ترتیب چیک کریں", expanded=False):
        for i, f in enumerate(images, 1):
            st.write(f"Scene {i}: {f.name} · {f.size/1024:.1f} KB")
            try: st.image(f, width=140)
            except Exception: st.warning(f"Preview نہیں دکھا سکے: {f.name}")
background_music = st.file_uploader("🎵 اختیاری Background Music (MP3/WAV/M4A)", type=["mp3", "wav", "m4a", "aac", "ogg"])

st.warning("Static images پر کیمرہ حرکت ہوگی۔ حقیقی کرداروں کی walking/lip movement کے لیے الگ AI image-to-video سروس درکار ہے۔")

if st.button("🚀 Create Cinematic Video", type="primary", use_container_width=True):
    if not ffmpeg_path(): st.error("FFmpeg missing ہے۔")
    elif not story.strip(): st.error("پہلے کہانی پیسٹ کریں۔")
    elif not images: st.error("کم از کم ایک تصویر اپلوڈ کریں۔")
    else:
        try:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                progress = st.progress(0, text="Preparing scenes…")
                # Stable sequential image/chunk mapping
                chunks = split_story(story, len(images))
                scene_files, scene_audio, durations = [], [], []
                voice_id = "ur-PK-AsadNeural" if voice_choice.startswith("Asad") else "ur-PK-UzmaNeural"
                rate = f"{int(round((speed-1)*100)):+d}%"
                vol = f"{volume-100:+d}%"
                depth_pitch = pitch
                if voice_preset == "Deep": depth_pitch -= 1.5
                elif voice_preset == "Extra Deep": depth_pitch -= 3.0
                elif voice_preset == "Cinematic Narrator": depth_pitch -= 1.0
                audio_filter = voice_filters(voice_preset, thickness, depth_pitch)
                size_map = {"720p": (1280,720), "1080p": (1920,1080), "1440p": (2560,1440), "4K": (3840,2160)}
                w,h = size_map[resolution]
                if render_mode == "Shorts 9:16": w,h = (720,1280) if resolution == "720p" else (1080,1920)
                elif render_mode == "Square 1:1": w,h = (720,720) if resolution == "720p" else (1080,1080)
                # Limit render size on hosted/free environments to reduce memory/timeouts
                if w > 1920: w,h = (1920,1080) if render_mode == "YouTube 16:9" else (1080,1920)
                for i, (img_file, chunk) in enumerate(zip(images, chunks), 1):
                    progress.progress((i-1)/len(images), text=f"Preparing Scene {i}/{len(images)}…")
                    imgp = td / f"image_{i:04}.png"
                    try:
                        im = Image.open(img_file).convert("RGB")
                        im = ImageOps.exif_transpose(im)
                        im.save(imgp, quality=95)
                    except Exception as e: raise RuntimeError(f"تصویر {i} پڑھنے میں مسئلہ: {e}")
                    wavp = td / f"voice_{i:04}.mp3"
                    if chunk.strip():
                        edge_tts_to_file(chunk, voice_id, rate, vol, str(wavp))
                        # Apply pitch/EQ processing to per-scene audio
                        filtered = td / f"voice_filtered_{i:04}.mp3"
                        run([ffmpeg_path(), "-y", "-i", str(wavp), "-af", audio_filter, "-c:a", "libmp3lame", "-q:a", "3", str(filtered)])
                        aud = filtered
                        dur = max(2.2, audio_duration(aud) + 0.35)
                    else:
                        aud = None; dur = 3.0
                    durations.append(dur); scene_audio.append(aud)
                    scene = td / f"scene_{i:04}.mp4"
                    make_scene_video(imgp, dur, scene, w, h, motion, motion_power, fps, style, i)
                    scene_files.append(scene)
                progress.progress(0.78, text="Joining scenes in exact order…")
                concat_txt = td / "concat.txt"
                concat_txt.write_text("\n".join([f"file '{p.as_posix()}'" for p in scene_files]), encoding="utf-8")
                silent = td / "joined_video.mp4"
                run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(silent)])
                # Join scene voice clips, filling silent scenes with silence
                audio_parts=[]
                for i, aud in enumerate(scene_audio):
                    ap = td / f"audio_part_{i:04}.wav"
                    if aud:
                        run([ffmpeg_path(), "-y", "-i", str(aud), "-af", f"apad=pad_dur={durations[i]:.3f},atrim=duration={durations[i]:.3f}", "-ar", "44100", "-ac", "2", str(ap)])
                    else:
                        run([ffmpeg_path(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{durations[i]:.3f}", str(ap)])
                    audio_parts.append(ap)
                audio_concat = td / "audio_concat.txt"
                audio_concat.write_text("\n".join([f"file '{p.as_posix()}'" for p in audio_parts]), encoding="utf-8")
                voice_full = td / "voice_all.wav"
                run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat), "-c:a", "pcm_s16le", str(voice_full)])
                final = td / "Sglowina_Cinematic.mp4"
                inputs=["-i", str(silent)]
                filters=[]; maps=[]
                if audio_mode == "Mute":
                    cmd=[ffmpeg_path(), "-y", *inputs, "-an", "-c:v", "copy", str(final)]
                elif audio_mode == "Music Only" and background_music:
                    musicp=td/"music_input"
                    musicp.write_bytes(background_music.getvalue())
                    cmd=[ffmpeg_path(), "-y", *inputs, "-stream_loop", "-1", "-i", str(musicp), "-filter_complex", f"[1:a]volume={music_volume/100:.2f}[m]", "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                elif audio_mode == "Voice Only" or not background_music:
                    cmd=[ffmpeg_path(), "-y", *inputs, "-i", str(voice_full), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                else:
                    musicp=td/"music_input"
                    musicp.write_bytes(background_music.getvalue())
                    cmd=[ffmpeg_path(), "-y", *inputs, "-i", str(voice_full), "-stream_loop", "-1", "-i", str(musicp), "-filter_complex", f"[1:a]volume=1.0[v];[2:a]volume={music_volume/100:.2f}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                run(cmd)
                progress.progress(0.94, text="Finalizing downloads…")
                video_bytes=final.read_bytes()
                st.success("🎉 ویڈیو تیار ہوگئی!")
                st.video(video_bytes)
                st.download_button("⬇️ Download MP4", video_bytes, file_name="Sglowina_Cinematic.mp4", mime="video/mp4", use_container_width=True)
                if make_subtitles:
                    srt=td/"subtitles.srt"
                    build_srt(chunks, durations, srt)
                    st.download_button("⬇️ Download SRT Subtitles", srt.read_bytes(), file_name="Sglowina_Subtitles.srt", mime="text/plain")
                progress.progress(1.0, text="Complete")
        except Exception as e:
            st.error("ویڈیو بناتے وقت خرابی ہوئی:")
            st.code(str(e))
            st.info("کم تصاویر، 720p، یا Medium motion سے دوبارہ کوشش کریں۔")
