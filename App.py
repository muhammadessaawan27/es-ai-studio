import streamlit as st
import subprocess
import os
import re
import uuid
import shutil
import asyncio
import tempfile
import math
from pathlib import Path

st.set_page_config(page_title="Sglowina AI — Story Cinema Studio", page_icon="🎬", layout="wide")

ROOT = Path(".")
UPLOAD_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "rendered"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

def tool_ready():
    return bool(FFMPEG and FFPROBE)

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe_duration(path):
    if not FFPROBE:
        raise RuntimeError("ffprobe نہیں ملا۔ Hosting میں FFmpeg نصب کریں۔")
    r = run_cmd([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1200:])
    return max(0.1, float(r.stdout.strip()))

def split_script(text):
    # Paragraphs/sentences become scenes; keep Urdu/Arabic punctuation.
    chunks = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    scenes = []
    for chunk in chunks:
        parts = re.split(r"(?<=[۔.!?؟])\s+", chunk)
        parts = [p.strip() for p in parts if p.strip()]
        scenes.extend(parts if parts else [chunk])
    return scenes

async def make_tts(text, voice, rate, pitch, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))

def safe_rate(speed):
    return f"{int(speed):+d}%"

def motion_filter(kind, seconds, width, height, fps=24):
    # Keep image ratio, fill frame, then use a smooth zoompan motion.
    base = f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}"
    frames = max(1, int(seconds * fps))
    z = "min(zoom+0.0007,1.12)"
    if kind == "Zoom Out":
        z = "if(eq(on,1),1.12,max(1.0,zoom-0.0007))"
    elif kind == "Pan Left":
        z = "1.08"
    elif kind == "Pan Right":
        z = "1.08"
    elif kind == "Gentle Zoom":
        z = "min(zoom+0.00035,1.07)"
    if kind == "Pan Left":
        x = "iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.20"
    elif kind == "Pan Right":
        x = "iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.80"
    else:
        x = "iw/2-(iw/zoom/2)"
    y = "ih/2-(ih/zoom/2)"
    return f"{base},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},setsar=1"

def render_story(images, script, voice, speed, pitch, motion, resolution, music_path,
                music_volume, deep_voice, max_minutes, job_id, progress):
    if not tool_ready():
        raise RuntimeError("FFmpeg/FFprobe دستیاب نہیں۔ Hosting کے packages میں FFmpeg شامل کریں۔")
    scenes = split_script(script)
    if not scenes:
        raise RuntimeError("براہ کرم اسکرپٹ لکھیں۔")
    if len(scenes) > 200:
        scenes = scenes[:200]
    if not images:
        raise RuntimeError("کم از کم ایک تصویر منتخب کریں۔")

    w, h = (1280, 720) if resolution == "720p" else (1920, 1080)
    work = UPLOAD_DIR / f"story_{job_id}"
    work.mkdir(exist_ok=True)
    clips = []
    audios = []
    total = len(scenes)

    for i, scene in enumerate(scenes):
        progress((i + 1) / (total + 3), f"Scene {i+1}/{total}: وائس تیار ہو رہی ہے…")
        image = images[i % len(images)]
        voice_file = work / f"voice_{i:03d}.mp3"
        clip_file = work / f"clip_{i:03d}.mp4"
        asyncio.run(make_tts(scene, voice, safe_rate(speed), pitch, voice_file))
        voice_duration = probe_duration(voice_file)
        # Small visual tail for natural pacing; capped to prevent excessive duration.
        clip_duration = min(voice_duration + 0.25, 600)
        vf = motion_filter(motion if motion != "Auto Mix" else
                          ["Gentle Zoom", "Zoom Out", "Pan Left", "Pan Right"][i % 4],
                          clip_duration, w, h)
        cmd = [
            FFMPEG, "-y", "-loop", "1", "-i", str(image),
            "-vf", vf, "-t", f"{clip_duration:.3f}", "-r", "24",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", str(clip_file)
        ]
        rr = run_cmd(cmd)
        if rr.returncode:
            raise RuntimeError(f"Scene video error:\n{rr.stderr[-1800:]}")
        clips.append(clip_file)
        audios.append(voice_file)

    progress(0.75, "Scenes جوڑی جا رہی ہیں…")
    concat_file = work / "concat.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips), encoding="utf-8")
    video_only = work / "video_only.mp4"
    rr = run_cmd([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                  "-c", "copy", str(video_only)])
    if rr.returncode:
        raise RuntimeError(rr.stderr[-1800:])

    # Concatenate scene voice tracks in the same order as the video.
    voice_concat = work / "voice_concat.txt"
    voice_concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in audios), encoding="utf-8")
    voice_full = work / "voice_full.mp3"
    rr = run_cmd([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(voice_concat),
                  "-c", "copy", str(voice_full)])
    if rr.returncode:
        raise RuntimeError(rr.stderr[-1800:])

    final = OUTPUT_DIR / f"Sglowina_Story_{job_id}.mp4"
    progress(0.84, "وائس اور بیک گراؤنڈ آڈیو مکس ہو رہی ہے…")
    if music_path:
        # Loop background music to video length and mix under narration.
        duration = min(probe_duration(video_only), max_minutes * 60)
        rr = run_cmd([
            FFMPEG, "-y", "-i", str(video_only), "-i", str(voice_full),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex",
            f"[1:a]volume=1.0[narr];[2:a]volume={music_volume}[bg];"
            "[narr][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]", "-t", f"{duration:.3f}",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(final)
        ])
    else:
        duration = min(probe_duration(video_only), max_minutes * 60)
        rr = run_cmd([FFMPEG, "-y", "-i", str(video_only), "-i", str(voice_full),
                      "-map", "0:v", "-map", "1:a", "-t", f"{duration:.3f}",
                      "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                      "-movflags", "+faststart", str(final)])
    if rr.returncode:
        raise RuntimeError(rr.stderr[-2000:])
    progress(1.0, "ویڈیو تیار ہے!")
    return final

def render_existing_video(video_path, out_path, resolution, style, duration, music_path, audio_mode,
                        original_volume, music_volume):
    width, height = {
        "720p": (720, 1280), "1080p": (1080, 1920),
        "1440p": (1440, 2560), "4K": (2160, 3840), "8K": (4320, 7680)
    }[resolution]
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}"
    if style == "Purple Energy":
        vf += ",eq=contrast=1.15:saturation=1.35,colorbalance=rs=0.05:bs=0.12"
    elif style == "Ultra Vibrant":
        vf += ",eq=contrast=1.1:saturation=1.5:brightness=0.01"
    elif style == "Dark Action":
        vf += ",eq=contrast=1.25:saturation=1.15:brightness=-0.04"
    cmd = [FFMPEG, "-y", "-i", str(video_path)]
    if music_path and audio_mode in ("Music Only", "Mix Original + Music"):
        cmd += ["-i", str(music_path)]
        if audio_mode == "Mix Original + Music":
            fc = f"[0:a]volume={original_volume}[a0];[1:a]volume={music_volume}[a1];[a0][a1]amix=inputs=2:duration=first[aout]"
            cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a", "-shortest"]
    else:
        cmd += ["-map", "0:v", "-map", "0:a?"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-t", str(duration), "-movflags", "+faststart", str(out_path)]
    result = run_cmd(cmd)
    return result.returncode == 0, result.stderr

st.title("💎 Sglowina AI — Cinematic Studio")
st.caption("Video Editor + Image Story Cinema | FFmpeg-powered")

if not tool_ready():
    st.warning("اس ہوسٹنگ پر FFmpeg/FFprobe نہیں ملے۔ Story Video اور Video Rendering چلانے کے لیے دونوں tools ضروری ہیں۔")

tab1, tab2 = st.tabs(["🎞️ Original Video Studio", "📖 Story Cinema — تصاویر سے ویڈیو"])

with tab1:
    st.subheader("Original Video Editor")
    video_file = st.file_uploader("Video Upload (MP4 / MOV)", type=["mp4", "mov"], key="old_video")
    if video_file:
        resolution = st.selectbox("Resolution", ["720p", "1080p", "1440p", "4K", "8K"], index=1, key="old_res")
        style = st.selectbox("Cinematic Style", ["Original", "Purple Energy", "Ultra Vibrant", "Dark Action"], key="old_style")
        duration = st.slider("Duration (seconds)", 5, 600, 30, key="old_duration")
        audio_mode = st.selectbox("Audio", ["Keep Original", "Music Only", "Mix Original + Music"], key="old_audio")
        music = st.file_uploader("Background Music (optional)", type=["mp3", "wav", "m4a"], key="old_music") if audio_mode != "Keep Original" else None
        original_volume = st.slider("Original Volume", 0.0, 2.0, 0.8, 0.05, key="old_ov")
        music_volume = st.slider("Music Volume", 0.0, 2.0, 0.25, 0.05, key="old_mv")
        if st.button("🚀 Render Video", key="old_render"):
            jid = uuid.uuid4().hex[:8]
            src = UPLOAD_DIR / f"input_{jid}.mp4"
            out = OUTPUT_DIR / f"edited_{jid}.mp4"
            src.write_bytes(video_file.getbuffer())
            mpath = None
            if music:
                mpath = UPLOAD_DIR / f"music_{jid}.{music.name.split('.')[-1]}"
                mpath.write_bytes(music.getbuffer())
            with st.spinner("Rendering…"):
                ok, err = render_existing_video(src, out, resolution, style, duration, mpath,
                                              audio_mode, original_volume, music_volume)
            if ok:
                st.success("Render complete!")
                st.video(str(out))
                with open(out, "rb") as f:
                    st.download_button("📥 Download video", f, file_name=out.name, mime="video/mp4")
            else:
                st.error("FFmpeg Error")
                st.code(err[-4000:])

with tab2:
    st.subheader("AI Story Cinema")
    st.write("اسکرپٹ دیں، تصاویر منتخب کریں، وائس اور موشن سیٹنگز منتخب کریں، پھر مکمل کہانی ویڈیو بنائیں۔")
    script = st.text_area("📝 Story / Voice-over Script", height=240,
                         placeholder="یہاں اپنی مکمل کہانی لکھیں۔ ہر پیراگراف یا جملہ الگ Scene بن سکتا ہے۔")
    images = st.file_uploader("🖼️ تصاویر منتخب کریں (ایک ساتھ متعدد؛ 200 تک کی کوشش)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="story_images")
    st.caption(f"منتخب تصاویر: {len(images) if images else 0}")
    col1, col2, col3 = st.columns(3)
    with col1:
        voice_choice = st.selectbox("Voice", ["Asad — Urdu Pakistan (Male)", "Uzma — Urdu Pakistan (Female)"])
    with col2:
        speed_label = st.selectbox("Voice Speed", ["Slow", "Normal", "Fast"])
    with col3:
        motion_choice = st.selectbox("Image Motion", ["Auto Mix", "Gentle Zoom", "Zoom Out", "Pan Left", "Pan Right"])
    resolution = st.selectbox("Story Resolution", ["720p", "1080p"], index=0)
    deep_voice = st.checkbox("Deep Voice (مزید بھاری آواز)", value=False)
    music = st.file_uploader("Background Nasheed / Audio (optional)", type=["mp3", "wav", "m4a"], key="story_music")
    music_volume = st.slider("Background audio volume", 0.0, 0.5, 0.12, 0.01, key="story_mv")
    max_minutes = st.slider("Video length limit (minutes)", 1, 10, 10)

    if st.button("🎬 Create Story Video", type="primary", key="story_render"):
        if not script.strip():
            st.error("پہلے اسکرپٹ لکھیں۔")
        elif not images:
            st.error("براہ کرم تصاویر منتخب کریں۔")
        elif not tool_ready():
            st.error("FFmpeg اور FFprobe دستیاب نہیں۔")
        else:
            jid = uuid.uuid4().hex[:8]
            image_paths = []
            for i, img in enumerate(images):
                ext = Path(img.name).suffix.lower() or ".jpg"
                ip = UPLOAD_DIR / f"story_{jid}_{i:03d}{ext}"
                ip.write_bytes(img.getbuffer())
                image_paths.append(ip)
            mpath = None
            if music:
                mpath = UPLOAD_DIR / f"story_music_{jid}.{music.name.split('.')[-1]}"
                mpath.write_bytes(music.getbuffer())
            voice = "ur-PK-AsadNeural" if voice_choice.startswith("Asad") else "ur-PK-UzmaNeural"
            rate = {"Slow": -15, "Normal": 0, "Fast": 15}[speed_label]
            pitch = "-15Hz" if deep_voice else "+0Hz"
            progress = st.progress(0, text="شروع ہو رہا ہے…")
            status = st.empty()
            try:
                with st.spinner("Story Video Render ہو رہی ہے۔ تصاویر زیادہ ہوں تو وقت لگ سکتا ہے۔"):
                    out = render_story(image_paths, script, voice, rate, pitch, motion_choice,
                                      resolution, mpath, music_volume, deep_voice, max_minutes, jid,
                                      lambda val, msg: (progress.progress(min(1.0, max(0.0, val))), status.write(msg)))
                st.success("✨ آپ کی Story Video تیار ہے!")
                st.video(str(out))
                with open(out, "rb") as f:
                    st.download_button("📥 Download Story Video", f, file_name=out.name, mime="video/mp4")
            except Exception as ex:
                st.error("Video بنانے میں مسئلہ آیا:")
                st.exception(ex)
import streamlit as st
import subprocess, os, re, uuid, shutil, asyncio
from pathlib import Path

st.set_page_config(page_title="Sglowina AI — Cinematic Studio", page_icon="🎬", layout="wide")
ROOT=Path('.')
UPLOAD_DIR=ROOT/'uploads'; OUTPUT_DIR=ROOT/'rendered'
UPLOAD_DIR.mkdir(exist_ok=True); OUTPUT_DIR.mkdir(exist_ok=True)
FFMPEG=shutil.which('ffmpeg'); FFPROBE=shutil.which('ffprobe')

def ready(): return bool(FFMPEG and FFPROBE)
def run(cmd): return subprocess.run(cmd,capture_output=True,text=True)
def duration(path):
    if not FFPROBE: raise RuntimeError('ffprobe نہیں ملا۔ Hosting میں FFmpeg/FFprobe نصب کریں۔')
    r=run([FFPROBE,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)])
    if r.returncode: raise RuntimeError(r.stderr[-1500:])
    return max(.1,float(r.stdout.strip()))
def split_script(text):
    paras=[p.strip() for p in re.split(r'\n\s*\n',text) if p.strip()]
    out=[]
    for p in paras:
        pieces=[x.strip() for x in re.split(r'(?<=[۔.!?؟])\s+',p) if x.strip()]
        out.extend(pieces or [p])
    return out
async def tts(text,voice,rate,pitch,path):
    import edge_tts
    await edge_tts.Communicate(text=text,voice=voice,rate=f'{rate:+d}%',pitch=f'{pitch:+d}Hz').save(str(path))
def motion_filter(kind,secs,w,h,fps=24):
    base=f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    frames=max(1,int(secs*fps)); z="min(zoom+0.0007,1.12)"
    if kind=='Zoom Out': z="if(eq(on,1),1.12,max(1.0,zoom-0.0007))"
    elif kind in ('Pan Left','Pan Right'): z='1.08'
    elif kind=='Gentle Zoom': z='min(zoom+0.00035,1.07)'
    x='iw/2-(iw/zoom/2)'
    if kind=='Pan Left': x='iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.20'
    if kind=='Pan Right': x='iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.80'
    y='ih/2-(ih/zoom/2)'
    return f"{base},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},setsar=1"
def concat_list(paths,txt):
    # FFmpeg concat demuxer list; escape apostrophes in filenames
    txt.write_text(''.join("file '"+p.resolve().as_posix().replace("'", "'\\''")+"'\n" for p in paths),encoding='utf-8')
def render_story(images,script,voice,voice_rate,voice_pitch,motion,resolution,music_path,music_volume,job,progress):
    if not ready(): raise RuntimeError('FFmpeg/FFprobe دستیاب نہیں۔')
    scenes=split_script(script)
    if not scenes: raise RuntimeError('اسکرپٹ درج کریں۔')
    if not images: raise RuntimeError('کم از کم ایک تصویر منتخب کریں۔')
    w,h=(1280,720) if resolution=='720p' else (1920,1080)
    work=UPLOAD_DIR/f'story_{job}'; work.mkdir(exist_ok=True)
    clips=[]; audios=[]
    for i,scene in enumerate(scenes):
        progress((i+1)/(len(scenes)+3),f'Scene {i+1}/{len(scenes)}: آواز اور موشن…')
        img=images[i%len(images)]; af=work/f'voice_{i:05d}.mp3'; vf=work/f'clip_{i:05d}.mp4'
        asyncio.run(tts(scene,voice,voice_rate,voice_pitch,af))
        sec=duration(af)+0.12
        motion_type=motion if motion!='Auto Mix' else ['Gentle Zoom','Zoom Out','Pan Left','Pan Right'][i%4]
        vfilt=motion_filter(motion_type,sec,w,h)
        cmd=[FFMPEG,'-y','-loop','1','-i',str(img),'-vf',vfilt,'-t',f'{sec:.3f}','-r','24','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(vf)]
        r=run(cmd)
        if r.returncode: raise RuntimeError('Scene video error: '+r.stderr[-1800:])
        clips.append(vf); audios.append(af)
    progress(.72,'Scenes جوڑی جا رہی ہیں…')
    cfile=work/'clips.txt'; concat_list(clips,cfile)
    video=work/'video.mp4'; r=run([FFMPEG,'-y','-f','concat','-safe','0','-i',str(cfile),'-c','copy',str(video)])
    if r.returncode: raise RuntimeError(r.stderr[-1800:])
    afile=work/'audio.txt'; concat_list(audios,afile)
    narr=work/'narration.mp3'; r=run([FFMPEG,'-y','-f','concat','-safe','0','-i',str(afile),'-c','copy',str(narr)])
    if r.returncode: raise RuntimeError(r.stderr[-1800:])
    final=OUTPUT_DIR/f'Sglowina_Story_{job}.mp4'; progress(.86,'آڈیو مکس اور فائنل ایکسپورٹ…')
    if music_path:
        # Keep narration, loop music underneath, and mix with narration duration.
        fc=f'[1:a]volume=1.0[narr];[2:a]volume={music_volume},aloop=loop=-1:size=2e+09[bg];[narr][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]'
        cmd=[FFMPEG,'-y','-i',str(video),'-i',str(narr),'-i',str(music_path),'-filter_complex',fc,'-map','0:v','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(final)]
    else:
        cmd=[FFMPEG,'-y','-i',str(video),'-i',str(narr),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(final)]
    r=run(cmd)
    if r.returncode: raise RuntimeError(r.stderr[-2200:])
    progress(1,'ویڈیو مکمل ہوگئی!'); return final

def atempo_chain(speed):
    # FFmpeg atempo supports 0.5-2 per filter; chain factors for extreme rates.
    parts=[]; value=float(speed)
    while value < 0.5:
        parts.append('atempo=0.5'); value /= 0.5
    while value > 2.0:
        parts.append('atempo=2.0'); value /= 2.0
    parts.append(f'atempo={value:.5f}')
    return ','.join(parts)

def render_video(src,out,res,style,video_speed,audio_mode,music,orig_vol,music_vol):
    size={'720p':(720,1280),'1080p':(1080,1920),'1440p':(1440,2560),'4K':(2160,3840),'8K':(4320,7680)}[res]
    w,h=size; vf=f"setpts=PTS/{video_speed},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    if style=='Purple Energy': vf+=',eq=contrast=1.15:saturation=1.35,colorbalance=rs=0.05:bs=0.12'
    elif style=='Ultra Vibrant': vf+=',eq=contrast=1.1:saturation=1.5:brightness=0.01'
    elif style=='Dark Action': vf+=',eq=contrast=1.25:saturation=1.15:brightness=-0.04'
    cmd=[FFMPEG,'-y','-i',str(src)]
    if music and audio_mode in ('Music Only','Mix Original + Music'):
        if audio_mode=='Mix Original + Music': cmd+=['-i',str(music)]
        else: cmd+=['-stream_loop','-1','-i',str(music)]
    if music and audio_mode=='Mix Original + Music':
        fc=f'[0:a]volume={orig_vol},{atempo_chain(video_speed)}[orig];[1:a]volume={music_vol}[bg];[orig][bg]amix=inputs=2:duration=first[aout]'
        cmd+=['-filter_complex',fc,'-map','0:v','-map','[aout]']
    elif music and audio_mode=='Music Only': cmd+=['-map','0:v','-map','1:a','-shortest']
    else: cmd+=['-map','0:v','-map','0:a?']
    cmd+=['-vf',vf,'-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
    r=run(cmd); return r.returncode==0,r.stderr

st.title('💎 Sglowina AI — Cinematic Studio')
st.caption('Story Cinema + Video Editor | FFmpeg-powered | Story duration based on your script — no 10-minute cap')
if not ready(): st.warning('اس ہوسٹنگ پر FFmpeg/FFprobe نہیں ملے۔ packages.txt میں ffmpeg شامل کریں۔')
tab1,tab2=st.tabs(['🎞️ Original Video Studio','📖 Story Cinema — تصاویر سے ویڈیو'])
with tab1:
    st.subheader('Original Video Editor')
    video=st.file_uploader('Video Upload (MP4/MOV)',type=['mp4','mov','mkv'],key='old_video')
    if video:
        res=st.selectbox('Resolution',['720p','1080p','1440p','4K','8K'],index=1,key='old_res')
        style=st.selectbox('Cinematic Look',['Original','Purple Energy','Ultra Vibrant','Dark Action'],key='old_style')
        speed=st.slider('Video Speed',0.25,2.0,1.0,0.05,help='0.5 = آدھی رفتار، 2 = دوگنی رفتار')
        audio_mode=st.selectbox('Audio Mode',['Keep Original','Music Only','Mix Original + Music'])
        music=st.file_uploader('Background Music (optional)',type=['mp3','wav','m4a'],key='old_music') if audio_mode!='Keep Original' else None
        orig_vol=st.slider('Original Audio Volume',0.0,2.0,0.8,0.05)
        music_vol=st.slider('Music Volume',0.0,2.0,0.25,0.05)
        if st.button('🚀 Render Edited Video',type='primary'):
            jid=uuid.uuid4().hex[:8]; src=UPLOAD_DIR/f'input_{jid}.mp4'; out=OUTPUT_DIR/f'edited_{jid}.mp4'; src.write_bytes(video.getbuffer())
            mp=None
            if music: mp=UPLOAD_DIR/f'music_{jid}.{music.name.split('.')[-1]}'; mp.write_bytes(music.getbuffer())
            with st.spinner('Rendering video…'):
                ok,err=render_video(src,out,res,style,speed,audio_mode,mp,orig_vol,music_vol)
            if ok:
                st.success('Video تیار!'); st.video(str(out))
                with open(out,'rb') as f: st.download_button('📥 Download video',f,file_name=out.name,mime='video/mp4')
            else: st.error('FFmpeg Error'); st.code(err[-4000:])
with tab2:
    st.subheader('Unlimited Story Cinema')
    st.info('کوئی 10 منٹ کی حد نہیں۔ دورانیہ آپ کے مکمل اسکرپٹ اور منتخب وائس اسپیڈ کے مطابق ہوگا؛ بہت لمبی کہانی بھی دے سکتے ہیں۔')
    script=st.text_area('📝 Full Story / Voice-over Script',height=260,placeholder='اپنی مکمل کہانی یہاں لکھیں… جتنی چاہیں طویل۔ ہر جملہ/پیراگراف الگ Scene بن سکتا ہے۔')
    images=st.file_uploader('🖼️ تصاویر (متعدد منتخب کریں)',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,key='story_images')
    st.caption(f'منتخب تصاویر: {len(images) if images else 0} — تصاویر کم ہوں تو موشن کے ساتھ دوبارہ استعمال ہوں گی۔')
    c1,c2,c3=st.columns(3)
    with c1: voice_choice=st.selectbox('Urdu Voice',['Asad — Pakistan Male','Uzma — Pakistan Female'])
    with c2: rate=st.slider('Narration Speed',-40,40,0,5,help='منفی = آہستہ، مثبت = تیز')
    with c3: pitch=st.slider('Voice Pitch / گہرائی',-30,30,0,2,help='منفی = بھاری آواز، مثبت = باریک/اونچی آواز')
    motion=st.selectbox('Image Motion',['Auto Mix','Gentle Zoom','Zoom Out','Pan Left','Pan Right'])
    resolution=st.selectbox('Story Resolution',['720p','1080p'],index=0)
    music=st.file_uploader('Background Audio / Nasheed (optional)',type=['mp3','wav','m4a'],key='story_music')
    music_volume=st.slider('Background Audio Volume',0.0,0.5,0.10,0.01)
    st.caption('اسٹوری ویڈیو کی لمبائی اسکرپٹ کے مطابق خود طے ہوگی؛ یہاں 10 منٹ یا کوئی دوسری سخت حد نہیں رکھی گئی۔')
    if st.button('🎬 Create Unlimited Story Video',type='primary',key='story_render'):
        if not script.strip(): st.error('پہلے اسکرپٹ لکھیں۔')
        elif not images: st.error('کم از کم ایک تصویر منتخب کریں۔')
        elif not ready(): st.error('FFmpeg/FFprobe دستیاب نہیں۔')
        else:
            jid=uuid.uuid4().hex[:8]; imgpaths=[]
            for i,img in enumerate(images):
                ext=Path(img.name).suffix.lower() or '.jpg'; p=UPLOAD_DIR/f'story_{jid}_{i:04d}{ext}'; p.write_bytes(img.getbuffer()); imgpaths.append(p)
            mp=None
            if music: mp=UPLOAD_DIR/f'storymusic_{jid}.{music.name.split('.')[-1]}' ; mp.write_bytes(music.getbuffer())
            voice='ur-PK-AsadNeural' if voice_choice.startswith('Asad') else 'ur-PK-UzmaNeural'
            progress=st.progress(0); status=st.empty()
            try:
                with st.spinner('Story render ہو رہی ہے — اسکرپٹ جتنا لمبا ہوگا، وقت بھی اسی حساب سے لگ سکتا ہے۔'):
                    out=render_story(imgpaths,script,voice,rate,pitch,motion,resolution,mp,music_volume,jid,lambda v,m:(progress.progress(min(1,max(0,v))),status.write(m)))
                st.success('✨ مکمل ویڈیو تیار ہے!'); st.video(str(out))
                with open(out,'rb') as f: st.download_button('📥 Download Story Video',f,file_name=out.name,mime='video/mp4')
            except Exception as e: st.error('ویڈیو بنانے میں مسئلہ:'); st.exception(e)
