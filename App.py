import streamlit as st
import subprocess
import imageio_ffmpeg
import os
import re
import uuid
import math
import glob

st.set_page_config(page_title="Sglowina Long-to-Shorts Pro Editor", page_icon="✂️", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


def get_video_info(video_path):
    """ویڈیو کی کل لمبائی اور آڈیو کی موجودگی چیک کرتا ہے"""
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
        raise RuntimeError(proc.stderr[-500:])


def extract_and_normalize_clip(
    raw_path, out_clip_path, start_sec, dur_sec,
    bw, bh, framing_mode, extra_zoom, focus_x, has_audio
):
    """لونگ یا شارٹ ویڈیو کے مطلوبہ حصے کو کاٹ کر فل اسکرین (بڑی اسکرین) 9:16 یا 16:9 میں ڈھالتا ہے"""
    zw = (int(bw * extra_zoom) // 2) * 2
    zh = (int(bh * extra_zoom) // 2) * 2

    if framing_mode == "Blurred Background + Fit (پوری چوڑائی نظر آئے)":
        vf = (
            f"split[bg][fg];"
            f"[bg]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},boxblur=20:5[bgb];"
            f"[fg]scale={bw}:{bh}:force_original_aspect_ratio=decrease[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p"
        )
    else:
        vf = (
            f"scale={zw}:{zh}:force_original_aspect_ratio=increase,"
            f"crop={bw}:{bh}:(iw-{bw})*{focus_x:.2f}:(ih-{bh})/2,"
            f"fps=30,format=yuv420p"
        )

    cmd = [
        "-ss", f"{start_sec:.3f}",
        "-i", raw_path,
        "-t", f"{dur_sec:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
    ]
    if has_audio:
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    else:
        cmd += ["-an"]

    cmd.append(out_clip_path)
    run_ffmpeg(cmd)


def render_scene_segment(source_clip, seg_out_path, start_t, dur_t, bw, bh, effect_idx, style_pack, keep_seg_audio):
    """ہر سین پر الگ زوم، شیک، فلیش اور پین ایفیکٹ لگاتا ہے"""
    zw_zoom = (int(bw * 1.16) // 2) * 2
    zh_zoom = (int(bh * 1.16) // 2) * 2

    zw_shake = (int(bw * 1.07) // 2) * 2
    zh_shake = (int(bh * 1.07) // 2) * 2
    sx = (zw_shake - bw) // 2
    sy = (zh_shake - bh) // 2
    amp = max(4, min(20, sx - 2, sy - 2))

    zw_pan = (int(bw * 1.14) // 2) * 2
    zh_pan = (int(bh * 1.14) // 2) * 2
    px_max = zw_pan - bw
    py_mid = (zh_pan - bh) // 2

    if style_pack == "Action & Viral Shorts (زوم + شیک + فلیش)":
        effects = [
            f"scale={zw_zoom}:{zh_zoom},zoompan=z='min(1.0+0.005*on,1.20)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={bw}x{bh}:fps=30,fade=t=in:st=0:d=0.14:color=white",
            f"scale={zw_shake}:{zh_shake},crop={bw}:{bh}:x='{sx}+if(lt(t,0.30),{amp}*sin(t*55),0)':y='{sy}+if(lt(t,0.30),{amp}*cos(t*48),0)',eq=contrast=1.10:saturation=1.18",
            f"scale={zw_pan}:{zh_pan},crop={bw}:{bh}:x='min({px_max},{px_max}*t/{dur_t:.3f})':y={py_mid}",
            f"scale={zw_zoom}:{zh_zoom},zoompan=z='max(1.20-0.005*on,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={bw}x{bh}:fps=30,fade=t=in:st=0:d=0.14:color=white",
            f"scale={zw_pan}:{zh_pan},crop={bw}:{bh}:x='max(0,{px_max}*(1-t/{dur_t:.3f}))':y={py_mid},vignette=PI/5",
            f"scale={zw_shake}:{zh_shake},crop={bw}:{bh}:x='{sx}+if(lt(t,0.28),{amp}*cos(t*50),0)':y='{sy}+if(lt(t,0.28),{amp}*sin(t*50),0)',eq=saturation=1.22:gamma=0.97",
        ]
    else:
        effects = [
            f"scale={zw_zoom}:{zh_zoom},zoompan=z='min(1.0+0.003*on,1.16)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={bw}x{bh}:fps=30,fade=t=in:st=0:d=0.15:color=black",
            f"scale={zw_pan}:{zh_pan},crop={bw}:{bh}:x='min({px_max},{px_max}*t/{dur_t:.3f})':y={py_mid}",
            f"scale={zw_zoom}:{zh_zoom},zoompan=z='max(1.16-0.003*on,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={bw}x{bh}:fps=30",
            f"scale={zw_pan}:{zh_pan},crop={bw}:{bh}:x='max(0,{px_max}*(1-t/{dur_t:.3f}))':y={py_mid},vignette=PI/5",
        ]

    vf = effects[effect_idx % len(effects)] + ",setpts=PTS-STARTPTS,format=yuv420p"

    cmd = [
        "-ss", f"{start_t:.3f}",
        "-i", source_clip,
        "-t", f"{dur_t:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
    ]
    if keep_seg_audio:
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    else:
        cmd += ["-an"]

    cmd.append(seg_out_path)
    run_ffmpeg(cmd)


def finalize_master_video(
    seg_paths, out_path, is_landscape, has_audio_stream,
    quality_choice, speed_factor, pitch_factor,
    mirror_flip, color_grade, sharpen_on,
    audio_mode, custom_audio_path, wm_path, work_dir
):
    """تمام سینز کو جوڑ کر کلر گریڈنگ، شاپنس، آڈیو، واٹر مارک اور HD/4K/8K فائنل آؤٹ پٹ بناتا ہے"""
    list_file = os.path.join(work_dir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for sp in seg_paths:
            f.write(f"file '{os.path.abspath(sp)}'\n")

    merged_path = os.path.join(work_dir, "merged_master.mkv")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", merged_path])

    if is_landscape:
        res_map = {
            "1080p Full HD+ (تیز اور کلاؤڈ محفوظ)": (1920, 1080, "18"),
            "4K UHD (انٹرنیشنل معیار)": (3840, 2160, "16"),
            "8K Ultra (صرف طاقتور PC/VPS)": (7680, 4320, "15"),
        }
    else:
        res_map = {
            "1080p Full HD+ (تیز اور کلاؤڈ محفوظ)": (1080, 1920, "18"),
            "4K UHD (انٹرنیشنل معیار)": (2160, 3840, "16"),
            "8K Ultra (صرف طاقتور PC/VPS)": (4320, 7680, "15"),
        }
    tw, th, crf_val = res_map[quality_choice]

    vf_chain = [f"setpts={1.0/speed_factor:.4f}*PTS"]
    if mirror_flip:
        vf_chain.append("hflip")
    if color_grade:
        vf_chain.append("eq=contrast=1.09:brightness=0.01:saturation=1.20:gamma=0.97")
    if sharpen_on:
        vf_chain.append("unsharp=5:5:1.10:5:5:0.0")
    vf_chain.append(f"scale={tw}:{th}:flags=lanczos,setsar=1")

    args = ["-i", merged_path]

    use_custom_audio = (audio_mode == "اپنا نیا میوزک/آواز لگائیں (کاپی رائٹ سے سب سے محفوظ)" and custom_audio_path)
    use_orig_audio = (audio_mode == "اصل آڈیو تبدیل کریں (Pitch + Speed + Bass EQ)" and has_audio_stream)

    if use_custom_audio:
        args += ["-stream_loop", "-1", "-i", custom_audio_path]
        audio_input_idx = 1
    elif use_orig_audio:
        audio_input_idx = 0
    else:
        audio_input_idx = None

    wm_idx = None
    if wm_path and os.path.exists(wm_path):
        args += ["-i", wm_path]
        wm_idx = 2 if use_custom_audio else 1

    vf_str = ",".join(vf_chain)
    if wm_idx is not None:
        fc = f"[0:v]{vf_str}[vbase];[{wm_idx}:v]scale={int(tw*0.18)}:-1[wm];[vbase][wm]overlay=W-w-{int(tw*0.04)}:{int(th*0.04)}[vout]"
        args += ["-filter_complex", fc, "-map", "[vout]"]
    else:
        args += ["-vf", vf_str, "-map", "0:v"]

    if audio_input_idx is not None:
        args += ["-map", f"{audio_input_idx}:a"]
        if use_orig_audio:
            atempo_val = max(0.55, min(1.9, speed_factor / pitch_factor))
            af = f"aformat=sample_rates=44100,asetrate=44100*{pitch_factor:.3f},aresample=44100,atempo={atempo_val:.4f},equalizer=f=110:width_type=h:width=100:g=3"
            args += ["-af", af]
        args += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        args += ["-an"]

    args += [
        "-map_metadata", "-1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", crf_val,
        "-pix_fmt", "yuv420p",
        out_path
    ]
    run_ffmpeg(args)


# ==========================
# Streamlit User Interface
# ==========================
st.title("✂️ Sglowina Long-to-Shorts Auto Editor")
st.markdown("چاہے **لونگ ویڈیو (16:9)** دیں یا **شارٹ ویڈیو** — ایک کلک پر اسے **بڑی اسکرین (Full-Screen 9:16)** میں بدل کر ہر سین پر زوم، شیک، فلیش اور 4K/8K رزلٹ حاصل کریں!")

up_video = st.file_uploader("📥 اپنی لونگ یا شارٹ ویڈیو اپلوڈ کریں (MP4 / MOV / MKV):", type=["mp4", "mov", "mkv"])

st.subheader("1️⃣ آؤٹ پٹ سائز اور بڑی اسکرین (Long → Short) سیٹنگز")
c_top1, c_top2, c_top3 = st.columns(3)
with c_top1:
    output_format = st.selectbox("📱 ویڈیو کا فارمیٹ منتخب کریں:", [
        "Shorts Full-Screen (9:16 بڑی اسکرین)",
        "YouTube Long Video (16:9 ہوریزونٹل)"
    ])
    framing_mode = st.selectbox("🔍 بڑی اسکرین کیسے بنے؟", [
        "Full-Screen Zoom Fill (پوری اسکرین بڑی ہو، کالا بارڈر نہیں)",
        "Blurred Background + Fit (پوری چوڑائی نظر آئے)"
    ])
with c_top2:
    long_extract_mode = st.selectbox("🎞️ لمبی ویڈیو میں سے کتنا حصہ شارٹ بنے؟", [
        "Continuous Clip (کسی ایک حصے سے مسلسل شارٹ بنائیں)",
        "Auto Highlight Montage (پوری لونگ ویڈیو سے بہترین کلپس جوڑیں)"
    ])
    short_target_dur = st.slider("⏳ شارٹ ویڈیو کی کل لمبائی (سیکنڈ):", 10, 60, 30, 5)
with c_top3:
    clip_start_sec = st.number_input("⏩ ویڈیو کس سیکنڈ سے شروع ہو (Continuous موڈ):", min_value=0, value=0, step=5)
    extra_zoom = st.slider("🔎 اسکرین کو مزید بڑا (Zoom) کریں:", 1.00, 1.40, 1.05, 0.05)
    focus_label = st.selectbox("🎯 فوکس کہاں رکھیں (بڑی اسکرین کراپ):", ["درمیان (Center)", "بائیں طرف (Left)", "دائیں طرف (Right)"])

focus_map = {"درمیان (Center)": 0.50, "بائیں طرف (Left)": 0.22, "دائیں طرف (Right)": 0.78}
focus_x = focus_map[focus_label]

st.subheader("2️⃣ ایڈیٹنگ ایفیکٹس، کوالٹی اور کاپی رائٹ پروٹیکشن")
col1, col2, col3 = st.columns(3)
with col1:
    style_pack = st.selectbox("🎬 ایڈیٹنگ اسٹائل:", [
        "Action & Viral Shorts (زوم + شیک + فلیش)",
        "Cinematic Smooth Shorts (سلو زوم + پین)"
    ])
    scene_beat = st.slider("⚡ ہر کتنے سیکنڈ بعد نیا ایفیکٹ لگے:", 1.2, 4.0, 2.0, 0.2)

with col2:
    quality_choice = st.selectbox("📺 آؤٹ پٹ کوالٹی:", [
        "1080p Full HD+ (تیز اور کلاؤڈ محفوظ)",
        "4K UHD (انٹرنیشنل معیار)",
        "8K Ultra (صرف طاقتور PC/VPS)"
    ])
    speed_factor = st.slider("🏃 ویڈیو اسپیڈ (Micro-Shift):", 0.95, 1.15, 1.04, 0.01)
    pitch_factor = st.slider("🎵 آواز کی پِچ (Pitch Shift):", 0.94, 1.06, 1.03, 0.01)

with col3:
    color_grade = st.checkbox("🎨 انٹرنیشنل کلر گریڈنگ", value=True)
    sharpen_on = st.checkbox("✨ کرسپ شاپنس (4K/8K Detail Boost)", value=True)
    mirror_flip = st.checkbox("🪞 ویڈیو مرر / پلٹیں (Mirror Flip)", value=False)
    wm_file = st.file_uploader("🏷️ اپنا لوگو / واٹر مارک (اختیاری):", type=["png", "jpg"])

st.markdown("---")
audio_mode = st.radio("🔊 آڈیو اور کاپی رائٹ پروٹیکشن موڈ:", [
    "اصل آڈیو تبدیل کریں (Pitch + Speed + Bass EQ)",
    "اپنا نیا میوزک/آواز لگائیں (کاپی رائٹ سے سب سے محفوظ)",
    "آواز بند کر دیں (Mute Video)"
], horizontal=True)

custom_audio_file = None
if audio_mode == "اپنا نیا میوزک/آواز لگائیں (کاپی رائٹ سے سب سے محفوظ)":
    custom_audio_file = st.file_uploader("🎶 اپنا میوزک یا وائس اوور اپلوڈ کریں (MP3 / WAV):", type=["mp3", "wav", "m4a"])

if st.button("🚀 1-Click Edit & Export Video", use_container_width=True):
    if not up_video:
        st.error("براہ کرم پہلے کوئی ویڈیو اپلوڈ کریں۔")
    elif audio_mode.startswith("اپنا نیا") and not custom_audio_file:
        st.error("براہ کرم اپنا میوزک یا وائس اوور فائل اپلوڈ کریں۔")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        vid_ext = os.path.splitext(up_video.name)[1] or ".mp4"
        raw_path = os.path.join(work_dir, f"raw_input{vid_ext}")
        out_path = f"Edited_Pro_{job_id}.mp4"

        with open(raw_path, "wb") as f:
            f.write(up_video.getvalue())

        wm_path = None
        if wm_file:
            wm_path = os.path.join(work_dir, "wm.png")
            with open(wm_path, "wb") as f:
                f.write(wm_file.getvalue())

        custom_audio_path = None
        if custom_audio_file:
            aud_ext = os.path.splitext(custom_audio_file.name)[1] or ".mp3"
            custom_audio_path = os.path.join(work_dir, f"custom_audio{aud_ext}")
            with open(custom_audio_path, "wb") as f:
                f.write(custom_audio_file.getvalue())

        progress = st.progress(0.0)
        status = st.empty()

        try:
            status.info("🔍 ویڈیو کی لمبائی اور آڈیو کا تجزیہ ہو رہا ہے...")
            total_dur, has_orig_audio = get_video_info(raw_path)
            if total_dur <= 0.5:
                raise ValueError("ویڈیو درست نہیں یا بہت چھوٹی ہے۔")

            is_landscape = (output_format == "YouTube Long Video (16:9 ہوریزونٹل)")
            bw, bh = (1920, 1080) if is_landscape else (1080, 1920)
            keep_seg_audio = (audio_mode == "اصل آڈیو تبدیل کریں (Pitch + Speed + Bass EQ)" and has_orig_audio)

            seg_paths = []

            if long_extract_mode.startswith("Auto Highlight") and total_dur > short_target_dur:
                num_clips = max(2, int(short_target_dur / scene_beat))
                per_clip_dur = short_target_dur / num_clips
                step = (total_dur - per_clip_dur) / max(1, num_clips - 1)

                for i in range(num_clips):
                    c_start = min(i * step, max(0.0, total_dur - per_clip_dur))
                    status.info(f"🎬 لونگ ویڈیو سے کلپ {i+1}/{num_clips} نکال کر فل اسکرین اور ایفیکٹ لگایا جا رہا ہے...")
                    temp_clip = os.path.join(work_dir, f"norm_{i:03d}.mkv")
                    extract_and_normalize_clip(
                        raw_path, temp_clip, c_start, per_clip_dur,
                        bw, bh, framing_mode, extra_zoom, focus_x, keep_seg_audio
                    )
                    seg_path = os.path.join(work_dir, f"seg_{i:03d}.mkv")
                    render_scene_segment(temp_clip, seg_path, 0.0, per_clip_dur, bw, bh, i, style_pack, keep_seg_audio)
                    seg_paths.append(seg_path)
                    progress.progress(0.10 + 0.65 * ((i + 1) / num_clips))
            else:
                safe_start = min(float(clip_start_sec), max(0.0, total_dur - 1.0))
                active_dur = min(float(short_target_dur), total_dur - safe_start)

                status.info("📐 ویڈیو کو فل اسکرین (بڑی اسکرین) فارمیٹ میں سیٹ کیا جا رہا ہے...")
                norm_clip = os.path.join(work_dir, "norm_clip.mkv")
                extract_and_normalize_clip(
                    raw_path, norm_clip, safe_start, active_dur,
                    bw, bh, framing_mode, extra_zoom, focus_x, keep_seg_audio
                )
                progress.progress(0.25)

                num_scenes = max(1, math.ceil(active_dur / scene_beat))
                for i in range(num_scenes):
                    s_t = i * scene_beat
                    d_t = min(scene_beat, active_dur - s_t)
                    if d_t < 0.3:
                        continue
                    status.info(f"⚡ سین {i+1}/{num_scenes} پر زوم، شیک اور فلیش ایفیکٹ لگ رہا ہے...")
                    seg_path = os.path.join(work_dir, f"seg_{i:03d}.mkv")
                    render_scene_segment(norm_clip, seg_path, s_t, d_t, bw, bh, i, style_pack, keep_seg_audio)
                    seg_paths.append(seg_path)
                    progress.progress(0.25 + 0.50 * ((i + 1) / num_scenes))

            if not seg_paths:
                raise ValueError("کوئی ویڈیو سین تیار نہیں ہو سکا۔")

            status.info(f"🚀 تمام سینز کو جوڑ کر {quality_choice.split(' ')[0]} میں فائنل ویڈیو تیار ہو رہی ہے...")
            finalize_master_video(
                seg_paths, out_path, is_landscape, keep_seg_audio,
                quality_choice, speed_factor, pitch_factor,
                mirror_flip, color_grade, sharpen_on,
                audio_mode, custom_audio_path, wm_path, work_dir
            )
            progress.progress(1.0)
            status.success("✅ آپ کی فل اسکرین ایڈٹ شدہ ویڈیو تیار ہے!")

            st.video(out_path)
            with open(out_path, "rb") as vid_f:
                st.download_button(
                    "📥 ویڈیو ڈاؤن لوڈ کریں (Download MP4)",
                    vid_f.read(),
                    file_name=out_path,
                    mime="video/mp4",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"❌ ایڈیٹنگ کے دوران خرابی آئی: {e}")
        finally:
            for f_tmp in glob.glob(os.path.join(work_dir, "*")):
                try:
                    os.remove(f_tmp)
                except Exception:
                    pass
            try:
                os.rmdir(work_dir)
            except Exception:
                pass
