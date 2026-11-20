import streamlit as st
import subprocess
import imageio_ffmpeg
import requests
import base64
import os
import re
import uuid
import math
import glob

st.set_page_config(page_title="Sglowina AI Auto-Director", page_icon="🎬", layout="wide")

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


def get_video_info(video_path):
    """ویڈیو کی کل لمبائی اور آڈیو چیک کرتا ہے"""
    proc = subprocess.run([FFMPEG_BIN, "-i", video_path], capture_output=True, text=True)
    stderr = proc.stderr
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    duration = 0.0
    if dur_match:
        h, m, s = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s
    has_audio = "Audio:" in stderr
    return duration, has_audio


def run_ffmpeg(args, timeout_sec=180):
    proc = subprocess.run([FFMPEG_BIN, "-y"] + args, capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:])


def auto_director_find_action_clips(raw_path, total_dur, target_short_dur=34.0):
    """
    آٹو ڈائریکٹر: 10-20 منٹ کی لمبی ویڈیو میں سے تیز ایکشن / فائٹنگ والے حصے خود ڈھونڈتا ہے۔
    """
    if total_dur <= 45.0:
        return [(0.0, total_dur)]

    clip_len = 3.6  # ہر ایکشن کلپ 3.6 سیکنڈ کا (جو آگے 1.8s کے دو بیٹس میں کٹے گا)
    num_clips = max(4, min(10, int(target_short_dur / clip_len)))

    action_times = []
    try:
        # کی-فریمز پر انتہائی تیز ایکشن/سین چینج اسکین (20 منٹ کی ویڈیو چند سیکنڈ میں اسکین)
        proc = subprocess.run(
            [
                FFMPEG_BIN, "-skip_frame", "nokey", "-i", raw_path,
                "-vf", "scale=160:90,select='gt(scene,0.16)',showinfo",
                "-an", "-f", "null", "-"
            ],
            capture_output=True, text=True, timeout=45
        )
        for m in re.finditer(r"pts_time:(\d+(?:\.\d+)?)", proc.stderr):
            t = float(m.group(1))
            if 2.0 < t < (total_dur - clip_len - 2.0):
                action_times.append(t)
    except Exception:
        action_times = []

    selected = []
    if len(action_times) >= num_clips:
        # 4 سیکنڈ کی ونڈوز بنا کر سب سے زیادہ ایکشن کثافت والے حصے چننا
        buckets = {}
        for t in action_times:
            b = int(t // 4.0)
            buckets[b] = buckets.get(b, 0) + 1

        ranked_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
        for b, _score in ranked_buckets:
            cand_start = max(0.0, min(b * 4.0, total_dur - clip_len))
            # یقینی بنائیں کہ دو کلپس آپس میں ٹکرائیں نہیں (کم از کم 6 سیکنڈ کا فاصلہ)
            if all(abs(cand_start - s) >= 6.0 for s, _ in selected):
                selected.append((cand_start, clip_len))
            if len(selected) >= num_clips:
                break

    # اگر ایکشن پوائنٹس کم ملیں تو پوری ویڈیو کے بہترین درمیانی حصوں سے کلپس لینا
    if len(selected) < num_clips:
        selected = []
        usable_start = total_dur * 0.08
        usable_end = max(usable_start + clip_len, total_dur * 0.92 - clip_len)
        step = (usable_end - usable_start) / max(1, num_clips - 1)
        for i in range(num_clips):
            selected.append((usable_start + i * step, clip_len))

    # سب سے پہلا کلپ زبردست وائرل ہُک (Hook) کے طور پر رکھیں اور باقی ترتیب سے
    if len(selected) > 2:
        hook = selected[0]
        rest = sorted(selected[1:], key=lambda x: x[0])
        selected = [hook] + rest
    else:
        selected.sort(key=lambda x: x[0])

    return selected


def extract_fullscreen_clip(raw_path, out_clip, start_sec, dur_sec, has_audio):
    """کسی بھی لونگ یا شارٹ ویڈیو کو فل اسکرین (9:16 بڑی اسکرین) میں زوم کر کے کاٹتا ہے"""
    vf = (
        "scale=1140:2026:force_original_aspect_ratio=increase,"
        "crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        "fps=30,format=yuv420p"
    )
    cmd = [
        "-ss", f"{start_sec:.3f}",
        "-i", raw_path,
        "-t", f"{dur_sec:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
    ]
    if has_audio:
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd.append(out_clip)
    run_ffmpeg(cmd)


def apply_auto_director_beat(source_clip, seg_out, start_t, dur_t, beat_idx, keep_audio):
    """آٹو ڈائریکٹر ہر 1.8 سیکنڈ کے سین پر خودکار وائرل ایکشن ایفیکٹ لگاتا ہے"""
    effects = [
        # 0: Punch Zoom-In + White Flash
        "scale=1252:2226,zoompan=z='min(1.0+0.006*on,1.20)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,fade=t=in:st=0:d=0.12:color=white",
        # 1: Fighting Impact Shake
        "scale=1154:2054,crop=1080:1920:x='37+if(lt(t,0.32),22*sin(t*58),0)':y='67+if(lt(t,0.32),22*cos(t*50),0)'",
        # 2: Smooth Action Pan Right
        f"scale=1230:2186,crop=1080:1920:x='min(150,150*t/{dur_t:.3f})':y=133",
        # 3: Zoom-Out Reveal + White Flash
        "scale=1252:2226,zoompan=z='max(1.20-0.006*on,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,fade=t=in:st=0:d=0.12:color=white",
        # 4: Smooth Action Pan Left + Vignette
        f"scale=1230:2186,crop=1080:1920:x='max(0,150*(1-t/{dur_t:.3f}))':y=133,vignette=PI/6",
        # 5: Impact Shake + Punch
        "scale=1154:2054,crop=1080:1920:x='37+if(lt(t,0.28),18*cos(t*52),0)':y='67+if(lt(t,0.28),18*sin(t*52),0)'",
    ]
    vf = effects[beat_idx % len(effects)] + ",setpts=PTS-STARTPTS,format=yuv420p"

    cmd = [
        "-ss", f"{start_t:.3f}",
        "-i", source_clip,
        "-t", f"{dur_t:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
    ]
    if keep_audio:
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd.append(seg_out)
    run_ffmpeg(cmd)


def render_crystal_beauty_master(
    seg_paths, out_path, has_audio, quality_choice,
    custom_audio_path, wm_path, work_dir
):
    """
    بیوٹی کیمرہ + شیشے جیسا کرسٹل کلر گریڈ، آڈیو ٹرانسفارمیشن، اور 1080p/4K/8K ماسٹر ایکسپورٹ
    """
    list_file = os.path.join(work_dir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for sp in seg_paths:
            f.write(f"file '{os.path.abspath(sp)}'\n")

    merged_path = os.path.join(work_dir, "merged.mkv")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", merged_path])

    res_map = {
        "Crystal 1080p HD (تیز اور فری کلاؤڈ محفوظ - تجویز کردہ)": (1080, 1920, "16"),
        "4K UHD Crystal (2160x3840 - طاقتور PC/VPS)": (2160, 3840, "15"),
        "8K Ultra Crystal (4320x7680 - صرف ہائی-اینڈ PC/GPU)": (4320, 7680, "14"),
    }
    tw, th, crf_val = res_map[quality_choice]

    # آٹو ڈائریکٹر پروفیشنل سیٹنگز: 1.04x وائرل سپیڈ + بیوٹی کیم شیشہ کلرز + کرسپ شاپنس
    speed = 1.04
    pitch = 1.03
    vf_chain = [
        f"setpts={1.0/speed:.4f}*PTS",
        "hqdn3d=1.4:1.4:3:3",                                      # بیوٹی کیم سموتھنس (دانہ اور شور ختم)
        "eq=contrast=1.09:brightness=0.03:saturation=1.24:gamma=1.02",  # شیشے جیسے چمکدار اور خوبصورت رنگ
        "unsharp=5:5:1.22:5:5:0.0",                                # ہائی ڈیفینیشن کرسپ شاپنس
        f"scale={tw}:{th}:flags=lanczos,setsar=1"
    ]

    args = ["-i", merged_path]

    use_custom_audio = bool(custom_audio_path)
    if use_custom_audio:
        args += ["-stream_loop", "-1", "-i", custom_audio_path]
        audio_idx = 1
    elif has_audio:
        audio_idx = 0
    else:
        audio_idx = None

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

    if audio_idx is not None:
        args += ["-map", f"{audio_idx}:a"]
        if not use_custom_audio:
            atempo_val = speed / pitch
            af = (
                f"aformat=sample_rates=44100,asetrate=44100*{pitch:.3f},"
                f"aresample=44100,atempo={atempo_val:.4f},"
                f"equalizer=f=110:width_type=h:width=100:g=3"
            )
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
    run_ffmpeg(args, timeout_sec=300)


def generate_viral_metadata_from_video(video_path, work_dir, api_key=""):
    """تیار شدہ ویڈیو کے فریم دیکھ کر خودکار وائرل ٹائٹل، ڈسکرپشن اور ہیش ٹیگز لکھتا ہے"""
    dur, _ = get_video_info(video_path)
    sample_times = [max(0.2, dur * 0.2), max(0.5, dur * 0.5), max(0.8, dur * 0.8)]
    content_parts = [{
        "type": "text",
        "text": (
            "Look closely at these frames from a viral Short video. "
            "Understand what is happening (e.g. fighting, action, drama, comedy, motivation, etc.) "
            "and write in Urdu + English:\n"
            "1) 3 Viral Click-Worthy Titles\n"
            "2) A Short Catchy Description\n"
            "3) 15 High-Reach Viral Hashtags for YouTube Shorts & TikTok."
        )
    }]

    for idx, t in enumerate(sample_times):
        img_p = os.path.join(work_dir, f"frame_{idx}.jpg")
        try:
            run_ffmpeg(["-ss", f"{t:.2f}", "-i", video_path, "-vframes", "1", "-vf", "scale=480:-1", img_p])
            if os.path.exists(img_p):
                with open(img_p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except Exception:
            pass

    headers = {"Content-Type": "application/json"}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    payload = {
        "model": "openai",
        "messages": [
            {"role": "system", "content": "You are an expert viral YouTube Shorts & TikTok SEO strategist."},
            {"role": "user", "content": content_parts}
        ]
    }
    try:
        res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        if res.status_code == 200:
            txt = res.json()["choices"][0]["message"]["content"].strip()
            if len(txt) > 20:
                return txt, True
    except Exception:
        pass

    # اگر AI Vision سرور دستیاب نہ ہو تو اسمارٹ فال بیک
    fallback_seo = (
        "🔥 وائرل ٹائٹلز (Viral Titles):\n"
        "1. آخر میں جو ہوا دیکھ کر ہوش اڑ جائیں گے! 😱🔥 #Shorts\n"
        "2. یہ سین مس مت کرنا! Unbelievable Action Moment 💥\n"
        "3. Wait For The End! سب سے خطرناک اور کمال کا سین 🤯\n\n"
        "📝 ڈسکرپشن:\n"
        "یہ زبردست فل اسکرین ایکشن شارٹ آخر تک ضرور دیکھیں! ویڈیو پسند آئے تو لائک اور سبسکرائب ضرور کریں۔\n\n"
        "🏷️ وائرل ہیش ٹیگز:\n"
        "#Shorts #YouTubeShorts #ViralShorts #Trending #ActionShorts #FullScreen #4KStatus "
        "#FYP #ForYou #PakistaniShorts #UrduShorts #EpicMoments #MustWatch #Reels #ViralVideo"
    )
    return fallback_seo, False


# ==========================
# سادہ اور آسان یوزر انٹرفیس (صرف 1 کلک آٹو ڈائریکٹر)
# ==========================
st.title("🎬 Sglowina AI Auto-Director")
st.markdown("آپ کو کوئی سیٹنگ کرنے کی ضرورت نہیں! بس **10-20 منٹ کی لمبی ویڈیو** یا **شارٹ ویڈیو** اپلوڈ کریں — **آٹو ڈائریکٹر** خود فائٹنگ/ایکشن سین نکال کر، شیشے جیسے رنگ، زوم ایفیکٹس اور وائرل ٹائٹل و ہیش ٹیگز بنا کر دے گا۔")

up_video = st.file_uploader("📥 اپنی کوئی بھی ویڈیو اپلوڈ کریں (MP4 / MOV / MKV):", type=["mp4", "mov", "mkv"])

quality_choice = st.selectbox("📺 ویڈیو رزلٹ کوالٹی منتخب کریں:", [
    "Crystal 1080p HD (تیز اور فری کلاؤڈ محفوظ - تجویز کردہ)",
    "4K UHD Crystal (2160x3840 - طاقتور PC/VPS)",
    "8K Ultra Crystal (4320x7680 - صرف ہائی-اینڈ PC/GPU)"
])

with st.expander("⚙️ اختیاری چیزیں (اگر اپنا میوزک، لوگو یا API Key لگانا ہو)"):
    custom_audio_file = st.file_uploader("🎶 اپنا میوزک یا آواز لگائیں (کاپی رائٹ سے بچاؤ کے لیے بہترین):", type=["mp3", "wav", "m4a"])
    wm_file = st.file_uploader("🏷️ اپنا لوگو / واٹر مارک لگائیں:", type=["png", "jpg"])
    vision_api_key = st.text_input("🔑 AI Vision API Key (ویڈیو دیکھ کر 100% درست ٹائٹل/ہیش ٹیگ لکھوانے کے لیے - اختیاری):", type="password")

if st.button("🎬 آٹو ڈائریکٹر: خودکار وائرل شارٹ بنائیں 🚀", use_container_width=True):
    if not up_video:
        st.error("براہ کرم پہلے کوئی ویڈیو اپلوڈ کریں۔")
    else:
        job_id = str(uuid.uuid4())[:8]
        work_dir = f"job_{job_id}"
        os.makedirs(work_dir, exist_ok=True)

        vid_ext = os.path.splitext(up_video.name)[1] or ".mp4"
        raw_path = os.path.join(work_dir, f"raw{vid_ext}")
        out_path = f"Viral_AutoDirector_{job_id}.mp4"

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
            status.info("🤖 آٹو ڈائریکٹر ویڈیو کا جائزہ لے رہا ہے...")
            total_dur, has_orig_audio = get_video_info(raw_path)
            if total_dur <= 0.5:
                raise ValueError("ویڈیو فائل درست نہیں یا بہت چھوٹی ہے۔")

            status.info("🔥 آٹو ڈائریکٹر ویڈیو میں سے بہترین فائٹنگ / ایکشن سین تلاش کر رہا ہے...")
            selected_clips = auto_director_find_action_clips(raw_path, total_dur, target_short_dur=34.0)
            progress.progress(0.15)

            keep_orig_audio = (has_orig_audio and not custom_audio_path)
            seg_paths = []
            beat_dur = 1.8  # ہر 1.8 سیکنڈ پر نیا وائرل ایکشن ایفیکٹ
            beat_counter = 0

            total_beats_est = sum(max(1, math.ceil(d / beat_dur)) for _, d in selected_clips)

            for c_idx, (c_start, c_dur) in enumerate(selected_clips):
                status.info(f"📐 کلپ {c_idx+1}/{len(selected_clips)} کو فل اسکرین (بڑی اسکرین 9:16) میں ڈھالا جا رہا ہے...")
                norm_clip = os.path.join(work_dir, f"norm_{c_idx:03d}.mkv")
                extract_fullscreen_clip(raw_path, norm_clip, c_start, c_dur, keep_orig_audio)

                n_beats = max(1, math.ceil(c_dur / beat_dur))
                for b in range(n_beats):
                    s_t = b * beat_dur
                    d_t = min(beat_dur, c_dur - s_t)
                    if d_t < 0.35:
                        continue
                    status.info(f"⚡ آٹو ڈائریکٹر سین {beat_counter+1} پر زوم، شیک اور فلیش ایفیکٹ لگا رہا ہے...")
                    seg_p = os.path.join(work_dir, f"seg_{beat_counter:03d}.mkv")
                    apply_auto_director_beat(norm_clip, seg_p, s_t, d_t, beat_counter, keep_orig_audio)
                    seg_paths.append(seg_p)
                    beat_counter += 1
                    progress.progress(min(0.78, 0.15 + 0.63 * (beat_counter / max(1, total_beats_est))))

            if not seg_paths:
                raise ValueError("کوئی ویڈیو سین تیار نہیں ہو سکا۔")

            status.info("💎 شیشے جیسے بیوٹی کیم رنگ، کرسٹل شاپنس اور فائنل ماسٹر تیار ہو رہا ہے...")
            render_crystal_beauty_master(
                seg_paths, out_path, keep_orig_audio, quality_choice,
                custom_audio_path, wm_path, work_dir
            )
            progress.progress(0.90)

            status.info("✍️ ویڈیو دیکھ کر وائرل ٹائٹل، ڈسکرپشن اور ہیش ٹیگز لکھے جا رہے ہیں...")
            seo_text, used_ai_vision = generate_viral_metadata_from_video(out_path, work_dir, vision_api_key)
            progress.progress(1.0)
            status.success("✅ آٹو ڈائریکٹر نے آپ کا پروفیشنل وائرل شارٹ اور ٹائٹل/ہیش ٹیگز تیار کر دیے ہیں!")

            col_res1, col_res2 = st.columns([1, 1])
            with col_res1:
                st.video(out_path)
                with open(out_path, "rb") as vid_f:
                    st.download_button(
                        "📥 ویڈیو ڈاؤن لوڈ کریں (Download MP4)",
                        vid_f.read(),
                        file_name=out_path,
                        mime="video/mp4",
                        use_container_width=True
                    )
            with col_res2:
                st.subheader("🔥 وائرل ٹائٹل، ڈسکرپشن اور ہیش ٹیگز")
                if not used_ai_vision:
                    st.caption("نوٹ: AI Vision سرور سے کنکشن نہیں ہو سکا (یا API Key نہیں دی گئی)، اس لیے آٹو ڈائریکٹر نے وائرل ایکشن ٹیمپلیٹ تیار کیا ہے۔")
                st.code(seo_text, language="")

        except Exception as e:
            st.error(f"❌ خرابی: {e}")
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
