import streamlit as st
import os, tempfile, subprocess, shutil, asyncio, math, re, time, urllib.parse, hashlib
from pathlib import Path
from PIL import Image, ImageOps

st.set_page_config(page_title="Sglowina AI | Cinematic Story Studio", page_icon="🎬", layout="wide")

# -------------------- Core helpers --------------------
def ffmpeg_path():
    return shutil.which("ffmpeg")
def ffprobe_path():
    return shutil.which("ffprobe")
def run(cmd, timeout=900):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-4500:])
    return p

def audio_duration(path):
    if not ffprobe_path(): return 0.0
    try:
        out = run([ffprobe_path(), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], timeout=60).stdout.strip()
        return max(0.0, float(out))
    except Exception: return 0.0

def sentences(text):
    text = re.sub(r'\s+', ' ', (text or '').strip())
    if not text: return []
    # Urdu and English sentence punctuation
    parts = re.split(r'(?<=[.!?۔؟])\s+', text)
    return [p.strip() for p in parts if p.strip()]

def split_story(text, count):
    s = sentences(text)
    if not s: return [text.strip()] * max(1, int(count))
    count = max(1, int(count))
    if count <= 1: return [" ".join(s)]
    # If scene count exceeds sentence count, split continuous word tokens instead
    # of creating empty scenes. Text order is always preserved.
    if len(s) < count:
        words = " ".join(s).split()
        count = min(count, max(1, len(words)))
        chunks = []
        for i in range(count):
            a = round(len(words) * i / count)
            b = round(len(words) * (i + 1) / count)
            chunks.append(" ".join(words[a:b]))
        return chunks
    chunks, start = [], 0
    total_chars = sum(max(1, len(x)) for x in s)
    for i in range(count):
        if i == count - 1:
            chunks.append(" ".join(s[start:])); break
        target = total_chars * (i + 1) / count
        cur = sum(max(1, len(x)) for x in s[:start])
        end = start
        while end < len(s) and cur < target:
            cur += max(1, len(s[end])); end += 1
        end = max(start + 1, min(end, len(s) - (count - i - 1)))
        chunks.append(" ".join(s[start:end])); start = end
    return chunks[:count]

def prophet_or_sacred_mention(text):
    terms = ["نبی", "انبیاء", "انبیا", "پیغمبر", "رسول", "محمد", "ابراہیم", "موسیٰ", "عیسیٰ", "آدم", "نوح", "یوسف", "یعقوب", "داود", "سلیمان", "ایوب", "یونس", "زکریا", "یحییٰ", "اسماعیل", "اسحاق", "لوط", "ہود", "صالح", "شعیب", "ذوالکفل", "الیسع", "ہارون", "مریم", "prophet", "prophets", "prophet muhammad", "prophet ibrahim", "prophet musa", "jesus", "moses", "abraham", "noah", "adam", "joseph", "dawud", "sulayman"]
    t = (text or '').lower()
    return any(term.lower() in t for term in terms)

def scene_image_prompt(scene_text, aspect, protect_prophets=False):
    # Prompt is scene-specific, but we cannot semantically verify the generated image.
    safe_scene = re.sub(r'\s+', ' ', scene_text.strip())[:900]
    ratio = "wide 16:9 landscape" if aspect == "YouTube 16:9" else ("vertical 9:16 portrait" if aspect == "Shorts 9:16" else "square 1:1")
    sacred = bool(protect_prophets) or prophet_or_sacred_mention(scene_text)
    safety = ("STRICT RESPECTFUL PROPHET RULE: Do not show, depict, imply, silhouette, or represent any prophet or messenger as a person. No face, body, hands, shadow, or human figure for prophets. Use only respectful symbolic scenery, architecture, sky, landscape, objects, light, and environment; no writing or calligraphy.") if sacred else "Avoid depicting any religious figure as a prophet; keep scene respectful and historically grounded."
    return (f"Create one single cinematic historical film still, {ratio}, photorealistic, ancient Middle Eastern setting, "
            f"high production value, realistic textures, natural dramatic lighting, volumetric atmosphere, "
            f"wide cinematic composition, detailed environment, no collage, no split-screen, no captions, no watermark. "
            f"Visualize this exact story scene without adding unrelated events: {safe_scene}. {safety}")

def free_image_generate(prompt, width, height, seed):
    """Best-effort no-key public image endpoint; can be rate-limited/unavailable."""
    import requests
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt, safe="")
    params = {"width": min(1024, max(512, int(width))), "height": min(1024, max(512, int(height))), "seed": int(seed), "nologo": "true"}
    r = requests.get(url, params=params, timeout=(20, 180), headers={"User-Agent": "SglowinaAI/1.0"})
    if r.status_code != 200 or not r.headers.get("content-type", "").lower().startswith("image/"):
        raise RuntimeError(f"Free image service returned HTTP {r.status_code}. It may be busy or rate-limited.")
    if len(r.content) < 10000:
        raise RuntimeError("Generated image response was too small or incomplete.")
    return r.content

def edge_tts_to_file(text, voice, rate, volume, outpath):
    import edge_tts
    async def _go():
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        await communicate.save(outpath)
    asyncio.run(_go())

def voice_filters(preset, thickness, pitch_semitones):
    ratio = 2 ** (float(pitch_semitones) / 12.0)
    filters = []
    if abs(float(pitch_semitones)) > 0.05:
        # Pitch shift with speed compensation; this may slightly affect timbre/formants.
        filters += [f"asetrate=44100*{ratio:.6f}", "aresample=44100", f"atempo={1/ratio:.6f}"]
    bass_gain = max(0, min(10, int(2 + float(thickness) * 0.08)))
    filters += [f"equalizer=f=115:t=q:w=1:g={bass_gain}", "acompressor=threshold=-18dB:ratio=2.2:attack=15:release=160", "alimiter=limit=0.95"]
    if preset == "Deep": filters += ["equalizer=f=170:t=q:w=1:g=1.5"]
    elif preset == "Extra Deep": filters += ["equalizer=f=150:t=q:w=1:g=2.5", "equalizer=f=300:t=q:w=1:g=-1"]
    elif preset == "Cinematic Narrator": filters += ["equalizer=f=140:t=q:w=1:g=2", "acompressor=threshold=-22dB:ratio=3:attack=20:release=220"]
    return ",".join(filters)

def make_scene_video(image_path, duration, outpath, w, h, motion, intensity, fps, style, idx):
    duration = max(1.5, float(duration))
    frames = max(2, int(math.ceil(duration * fps)))
    step = {"Low": 0.035, "Medium": 0.065, "High": 0.10, "Extreme": 0.15}.get(intensity, 0.10)
    modes = ["Zoom In", "Zoom Out", "Pan Left", "Pan Right", "Dynamic"]
    if motion == "Auto Director": motion = modes[(idx - 1) % len(modes)]
    # All expressions use numeric frames, not a literal {frames} placeholder.
    if motion == "Zoom Out": z = f"1.0+{step:.5f}*(1-on/{frames})"
    else: z = f"1.0+{step:.5f}*on/{frames}"
    if motion == "Pan Left": x = f"(iw-iw/zoom)*(0.15+0.70*on/{frames})"
    elif motion == "Pan Right": x = f"(iw-iw/zoom)*(0.85-0.70*on/{frames})"
    elif motion == "Dynamic": x = "(iw-iw/zoom)*(0.5+0.22*sin(on/14))"
    else: x = "(iw-iw/zoom)/2"
    y = "(ih-ih/zoom)/2"
    # Upscale source canvas to provide headroom for motion; crop remains centered before zoom.
    vf = f"scale={int(w*1.15)}:{int(h*1.15)}:force_original_aspect_ratio=increase,crop={int(w*1.15)}:{int(h*1.15)},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"
    if style == "Warm Cinematic": vf += ",eq=saturation=1.12:contrast=1.06:brightness=0.015,colorbalance=rs=0.04:gs=0.01:bs=-0.03"
    elif style == "Vibrant": vf += ",eq=saturation=1.22:contrast=1.08:brightness=0.02"
    elif style == "Dark Drama": vf += ",eq=saturation=0.92:contrast=1.14:brightness=-0.035,colorbalance=rs=-0.02:bs=0.04"
    elif style == "Purple Energy": vf += ",colorbalance=rs=0.04:gs=-0.02:bs=0.06,eq=saturation=1.18"
    vf += ",format=yuv420p"
    run([ffmpeg_path(), "-y", "-loop", "1", "-i", str(image_path), "-vf", vf, "-t", f"{duration:.3f}", "-an", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", str(outpath)], timeout=900)

def build_srt(chunks, durations, outpath):
    def ts(t):
        ms = int(round(t * 1000)); hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
        return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"
    t = 0; lines = []; n = 1
    for txt, dur in zip(chunks, durations):
        if txt.strip():
            lines += [str(n), f"{ts(t)} --> {ts(t+dur)}", txt.strip(), ""]
            n += 1
        t += dur
    Path(outpath).write_text("\n".join(lines), encoding="utf-8")

def write_concat_list(paths, target):
    # FFmpeg concat demuxer escaping single quotes in file names.
    lines = []
    for p in paths:
        s = Path(p).as_posix().replace("'", "'\\''")
        lines.append(f"file '{s}'")
    Path(target).write_text("\n".join(lines), encoding="utf-8")

# -------------------- UI --------------------
st.title("🎬 Sglowina AI — Cinematic Story Studio")
st.caption("Ordered scenes • Urdu voice studio • Strong camera motion • Auto-fill missing scenes (best-effort, no key) • FFmpeg")
if not ffmpeg_path(): st.error("FFmpeg دستیاب نہیں۔ packages.txt میں ffmpeg شامل کریں۔")

with st.sidebar:
    st.header("🎛️ Film Controls")
    render_mode = st.selectbox("Output Format", ["YouTube 16:9", "Shorts 9:16", "Square 1:1"])
    resolution = st.selectbox("Resolution", ["720p", "1080p", "1440p", "4K"], index=0, help="Free hosting پر 720p تجویز ہے۔ 4K بہت بھاری ہو سکتا ہے۔")
    fps = st.select_slider("FPS", options=[24, 25, 30, 50, 60], value=24)
    style = st.selectbox("Color Grade", ["Original", "Warm Cinematic", "Vibrant", "Dark Drama", "Purple Energy"])
    motion = st.selectbox("Camera Motion", ["Auto Director", "Zoom In", "Zoom Out", "Pan Left", "Pan Right", "Dynamic"])
    motion_power = st.select_slider("Motion Power", options=["Low", "Medium", "High", "Extreme"], value="High")
    st.subheader("🎙️ Voice")
    voice_choice = st.selectbox("Urdu Voice", ["Asad (Male)", "Uzma (Female)"])
    voice_preset = st.selectbox("Voice Depth", ["Normal", "Deep", "Extra Deep", "Cinematic Narrator"])
    thickness = st.slider("Voice Thickness / Bass", 0, 100, 45)
    pitch = st.slider("Pitch Shift (semitones)", -8.0, 3.0, -2.0, 0.5)
    speed = st.slider("Speech Speed", 0.75, 1.25, 1.0, 0.05)
    volume = st.slider("Voice Volume", 50, 150, 100)
    st.subheader("🎵 Audio")
    music_volume = st.slider("Background Music Volume", 0, 100, 12)
    audio_mode = st.selectbox("Audio Mix", ["Voice + Music", "Voice Only", "Music Only", "Mute"])
    st.subheader("📝 Subtitles")
    make_subtitles = st.checkbox("Export SRT subtitles", value=True)

story = st.text_area("📖 یہاں مکمل کہانی / وائس اوور اسکرپٹ پیسٹ کریں", height=250, placeholder="اپنی مکمل کہانی یہاں پیسٹ کریں…")
images = st.file_uploader("🖼️ تصاویر ترتیب سے اپلوڈ کریں (تصویر 1 = Scene 1)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="story_images")
if images:
    st.success(f"{len(images)} تصاویر موصول ہوئیں۔ فائل اپلوڈر کی موجودہ ترتیب برقرار رکھی جائے گی؛ کوئی filename sorting نہیں ہوگی۔")
    with st.expander("تصاویر کی ترتیب اور preview چیک کریں", expanded=False):
        for i, f in enumerate(images, 1):
            st.markdown(f"**Scene {i} — {f.name}** · {f.size/1024:.1f} KB")
            try: st.image(f, width=160)
            except Exception: st.caption("Preview نہیں دکھا سکے")

# Scene count can exceed uploaded image count, in which case missing scenes are generated.
word_count = len((story or "").split())
# Heuristic scene estimate (roughly one scene per 30 words), never below the uploaded count.
estimated_scenes = min(80, max(1, len(images) if images else 1, math.ceil(word_count / 30) if word_count else 1))
scene_count = st.slider("🎞️ کل Scenes (کہانی کی لمبائی کے مطابق تجویز)", min_value=1, max_value=80, value=estimated_scenes, step=1, help="ابتدائی اندازہ تقریباً ہر 30 الفاظ پر ایک Scene ہے۔ آپ اسے کم یا زیادہ کر سکتے ہیں۔")
auto_missing = st.checkbox("🤖 کم تصاویر والے Scenes کے لیے مفت AI تصاویر خود بنانے کی کوشش کریں (API Key نہیں)", value=True, help="No-key public image service استعمال ہوگی۔ سروس کی رفتار، حد یا دستیابی کی ضمانت نہیں؛ نئی تصویر بننے میں کافی انتظار بھی ہو سکتا ہے۔")
if images and scene_count > len(images) and auto_missing:
    st.warning(f"آپ کے پاس {len(images)} تصاویر ہیں، منتخب Scenes {scene_count} ہیں؛ {scene_count-len(images)} اضافی تصاویر مفت سروس سے بنانے کی کوشش ہوگی۔ یہ سروس محدود/سست ہو سکتی ہے۔")
bgm = st.file_uploader("🎵 اختیاری Background Music (MP3/WAV/M4A/AAC/OGG)", type=["mp3", "wav", "m4a", "aac", "ogg"], key="music_upload")
st.info("Static images پر camera movement ہوگی۔ کرداروں کی حقیقی walking، lip-sync یا body animation اس ایپ کے FFmpeg موشن سے نہیں بنتی؛ اس کے لیے image-to-video ماڈل درکار ہے۔")

if st.button("🚀 Create Cinematic Video", type="primary", use_container_width=True):
    if not ffmpeg_path(): st.error("FFmpeg missing ہے۔")
    elif not story.strip(): st.error("پہلے کہانی پیسٹ کریں۔")
    elif not images and not auto_missing: st.error("تصاویر اپلوڈ کریں یا Auto Missing Images آن کریں۔")
    elif not images and auto_missing and not sentences(story): st.error("کہانی کے جملے نہیں ملے؛ پہلے مکمل اسکرپٹ لکھیں۔")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                td = Path(tmp)
                progress = st.progress(0, text="کہانی کے Scenes تیار ہو رہے ہیں…")
                chunks = split_story(story, scene_count)
                protect_prophets = prophet_or_sacred_mention(story)
                scene_sources = [None] * scene_count
                # Uploaded pictures always remain first and in the uploader order.
                for i, uploaded in enumerate(images[:scene_count]):
                    scene_sources[i] = uploaded
                missing_indices = [i for i, src in enumerate(scene_sources) if src is None]
                if missing_indices and not auto_missing:
                    st.error(f"{len(missing_indices)} تصاویر کم ہیں۔ Auto Missing Images آن کریں یا Scenes کی تعداد کم کریں۔")
                    st.stop()
                voice_id = "ur-PK-AsadNeural" if voice_choice.startswith("Asad") else "ur-PK-UzmaNeural"
                rate = f"{int(round((speed-1)*100)):+d}%"
                vol = f"{volume-100:+d}%"
                depth_pitch = float(pitch)
                if voice_preset == "Deep": depth_pitch -= 1.5
                elif voice_preset == "Extra Deep": depth_pitch -= 3.0
                elif voice_preset == "Cinematic Narrator": depth_pitch -= 1.0
                audio_filter = voice_filters(voice_preset, thickness, depth_pitch)
                size_map = {"720p": (1280,720), "1080p": (1920,1080), "1440p": (2560,1440), "4K": (3840,2160)}
                w, h = size_map[resolution]
                if render_mode == "Shorts 9:16": w, h = (720,1280) if resolution == "720p" else (1080,1920)
                elif render_mode == "Square 1:1": w, h = (720,720) if resolution == "720p" else (1080,1080)
                # Protect free-host memory by capping larger requests.
                if w > 1920 or h > 1920:
                    w, h = ((1920,1080) if render_mode == "YouTube 16:9" else (1080,1920) if render_mode == "Shorts 9:16" else (1080,1080))
                # Best-effort missing image generation, one image at a time.
                for j, idx in enumerate(missing_indices):
                    progress.progress(0.04 + 0.18*(j+1)/max(1, len(missing_indices)), text=f"Free AI image generation: Scene {idx+1}/{scene_count}…")
                    if not auto_missing: break
                    aspect = render_mode
                    prompt = scene_image_prompt(chunks[idx], aspect, protect_prophets=protect_prophets)
                    seed = int(hashlib.sha256(f"sglowina-{idx}-{chunks[idx]}".encode("utf-8")).hexdigest()[:8], 16) % 2147483647
                    # The no-key public service may rate-limit; wait between calls to reduce chance of throttling.
                    if j > 0: time.sleep(46)
                    try:
                        data = free_image_generate(prompt, w, h, seed)
                        gen_path = td / f"generated_scene_{idx+1:04}.jpg"
                        gen_path.write_bytes(data)
                        scene_sources[idx] = gen_path
                    except Exception as gen_err:
                        st.warning(f"Scene {idx+1} کی تصویر خود نہیں بن سکی: {gen_err}")
                        st.stop()
                scene_files, scene_audio, durations = [], [], []
                # Each scene is rendered independently and checked, then joined in exact order.
                for i, (source, chunk) in enumerate(zip(scene_sources, chunks), 1):
                    progress.progress(0.22 + 0.60*(i-1)/scene_count, text=f"Preparing Scene {i}/{scene_count}…")
                    imgp = td / f"scene_image_{i:04}.png"
                    if isinstance(source, Path):
                        im = Image.open(source)
                    else:
                        im = Image.open(source)
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.save(imgp, format="PNG")
                    wavp = td / f"voice_{i:04}.mp3"
                    if chunk.strip():
                        edge_tts_to_file(chunk, voice_id, rate, vol, str(wavp))
                        filtered = td / f"voice_filtered_{i:04}.mp3"
                        run([ffmpeg_path(), "-y", "-i", str(wavp), "-af", audio_filter, "-c:a", "libmp3lame", "-q:a", "3", str(filtered)], timeout=240)
                        aud = filtered
                        dur = max(2.4, audio_duration(aud) + 0.30)
                    else:
                        aud = None; dur = 3.0
                    durations.append(dur); scene_audio.append(aud)
                    scene = td / f"rendered_scene_{i:04}.mp4"
                    # Per-scene fallback: if camera motion fails, retry with a safe static zoom.
                    try:
                        make_scene_video(imgp, dur, scene, w, h, motion, motion_power, fps, style, i)
                    except Exception as motion_err:
                        st.warning(f"Scene {i}: موشن فلٹر ناکام، Static fallback استعمال ہو رہا ہے۔")
                        make_scene_video(imgp, dur, scene, w, h, "Zoom In", "Low", fps, "Original", i)
                    if not scene.exists() or scene.stat().st_size < 1000:
                        raise RuntimeError(f"Scene {i} کی ویڈیو فائل صحیح نہیں بنی۔")
                    scene_files.append(scene)
                progress.progress(0.83, text="Scenes کو ترتیب سے جوڑا جا رہا ہے…")
                concat_txt = td / "video_concat.txt"
                write_concat_list(scene_files, concat_txt)
                silent = td / "joined_video.mp4"
                run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(silent)], timeout=900)
                # Assemble voice timeline with silence for any empty scene.
                audio_parts = []
                for i, aud in enumerate(scene_audio):
                    ap = td / f"audio_part_{i:04}.wav"
                    if aud:
                        run([ffmpeg_path(), "-y", "-i", str(aud), "-af", f"apad=pad_dur={durations[i]:.3f},atrim=duration={durations[i]:.3f}", "-ar", "44100", "-ac", "2", str(ap)], timeout=240)
                    else:
                        run([ffmpeg_path(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{durations[i]:.3f}", str(ap)], timeout=240)
                    audio_parts.append(ap)
                audio_concat = td / "audio_concat.txt"
                write_concat_list(audio_parts, audio_concat)
                voice_full = td / "voice_all.wav"
                run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat), "-c:a", "pcm_s16le", str(voice_full)], timeout=900)
                final = td / "Sglowina_Cinematic.mp4"
                music_path = None
                if bgm:
                    music_path = td / "music_input"
                    music_path.write_bytes(bgm.getvalue())
                if audio_mode == "Mute":
                    cmd = [ffmpeg_path(), "-y", "-i", str(silent), "-an", "-c:v", "copy", str(final)]
                elif audio_mode == "Music Only" and music_path:
                    cmd = [ffmpeg_path(), "-y", "-i", str(silent), "-stream_loop", "-1", "-i", str(music_path), "-filter_complex", f"[1:a]volume={music_volume/100:.2f}[m]", "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                elif audio_mode == "Voice Only" or not music_path:
                    cmd = [ffmpeg_path(), "-y", "-i", str(silent), "-i", str(voice_full), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                else:
                    cmd = [ffmpeg_path(), "-y", "-i", str(silent), "-i", str(voice_full), "-stream_loop", "-1", "-i", str(music_path), "-filter_complex", f"[1:a]volume=1.0[v];[2:a]volume={music_volume/100:.2f}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)]
                run(cmd, timeout=900)
                progress.progress(0.95, text="Finalizing output…")
                if not final.exists() or final.stat().st_size < 10000:
                    raise RuntimeError("Final MP4 نہیں بن سکی یا فائل خالی ہے۔")
                video_bytes = final.read_bytes()
                st.success("🎉 ویڈیو تیار ہوگئی!")
                st.video(video_bytes)
                st.download_button("⬇️ Download MP4", video_bytes, file_name="Sglowina_Cinematic.mp4", mime="video/mp4", use_container_width=True)
                if make_subtitles:
                    srt = td / "subtitles.srt"
                    build_srt(chunks, durations, srt)
                    st.download_button("⬇️ Download SRT Subtitles", srt.read_bytes(), file_name="Sglowina_Subtitles.srt", mime="text/plain")
                progress.progress(1.0, text="Complete")
        except Exception as e:
            st.error("ویڈیو بناتے وقت خرابی ہوئی:")
            st.code(str(e))
            st.info("اگر رینڈر ناکام ہو تو 720p، 24 FPS، Medium motion سے آزمائیں۔")
