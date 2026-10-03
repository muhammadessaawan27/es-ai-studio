import streamlit as st
import asyncio
import requests
import urllib.parse
import os
import time
import re
import uuid
import glob
import json
import subprocess
import concurrent.futures

# ==========================================
# STREAMLIT COMPACT CONFIGURATION
# ==========================================
st.set_page_config(page_title="ES Ultra Anti-Copyright & Auto Shorts Studio", layout="wide", page_icon="⚡")

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

if "process_ready" not in st.session_state:
    st.session_state.process_ready = False
if "detected_info" not in st.session_state:
    st.session_state.detected_info = {}
if "current_output_video" not in st.session_state:
    st.session_state.current_output_video = ""
if "generated_shorts" not in st.session_state:
    st.session_state.generated_shorts = []
if "explainer_ready" not in st.session_state:
    st.session_state.explainer_ready = False
if "explainer_data" not in st.session_state:
    st.session_state.explainer_data = {}

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def extract_yt_id(raw_url):
    raw_url = raw_url.strip()
    m = re.search(r'(?:v=|\/|shorts\/)([0-9A-Za-z_-]{11})', raw_url)
    return m.group(1) if m else None

def fetch_oembed_title(clean_url):
    try:
        req_url = f"https://noembed.com/embed?url={urllib.parse.quote(clean_url)}"
        res = requests.get(req_url, timeout=3)
        if res.status_code == 200:
            return res.json().get("title", "")
    except Exception:
        pass
    return ""

def get_video_duration_fast(file_path):
    try:
        ffmpeg_exe = get_ffmpeg()
        ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
        cmd = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        dur = float(res.stdout.strip())
        return dur if dur > 0 else 60.0
    except Exception:
        return 60.0

# ==========================================
# PARALLEL ULTRA-FAST MULTI-SOURCE DOWNLOADER
# ==========================================
def try_download_node(node_url, vid_id, target_path):
    try:
        api_url = f"{node_url}/api/v1/videos/{vid_id}"
        res = requests.get(api_url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", "Movie Video Scene")
            streams = data.get("formatStreams", [])
            mp4s = [s for s in streams if "mp4" in s.get("container", "").lower() or "video/mp4" in s.get("type", "").lower()] or streams
            if mp4s:
                dl_url = mp4s[-1]["url"]
                if dl_url.startswith("/"): dl_url = node_url + dl_url
                r_file = requests.get(dl_url, stream=True, timeout=12)
                if r_file.status_code == 200:
                    with open(target_path, "wb") as f:
                        for chunk in r_file.iter_content(chunk_size=1024*1024*4):
                            if chunk: f.write(chunk)
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                        return True, title
    except Exception:
        pass
    return False, ""

def download_unblockable_media_parallel(input_query_or_url, target_path):
    input_str = input_query_or_url.strip()
    is_url = bool(re.match(r'^https?://', input_str, re.IGNORECASE))
    title = input_str if not is_url else "Movie Video Scene"

    if is_url and any(input_str.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.mov', '.webm']):
        try:
            r = requests.get(input_str, stream=True, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024*4):
                        if chunk: f.write(chunk)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                    return True, title
        except Exception:
            pass

    vid_id = extract_yt_id(input_str)
    if vid_id:
        title = fetch_oembed_title(f"https://www.youtube.com/watch?v={vid_id}") or title
        nodes = [
            "https://inv.tux.pizza",
            "https://invidious.nerdvpn.de",
            "https://invidious.privacydev.net",
            "https://invidious.drgns.space",
            "https://invidious.projectsegfau.lt"
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_download_node, node, vid_id, target_path) for node in nodes]
            for future in concurrent.futures.as_completed(futures):
                success, t = future.result()
                if success:
                    return True, t

    try:
        import yt_dlp
        ydl_opts = {
            'format': '18/best[height<=480][ext=mp4]/best[height<=480]/best',
            'outtmpl': target_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'socket_timeout': 8,
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
            'http_headers': {'User-Agent': 'Mozilla/5.0'}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(input_str, download=True)
            if meta: title = meta.get('title', title)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
            return True, title
    except Exception:
        pass

    return False, title

# ==========================================
# CELEBRITY EXACT-LIKENESS THUMBNAIL & METADATA
# ==========================================
def extract_celebrity_name(title):
    t_clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    return t_clean if t_clean else title

def analyze_video_and_generate_exact_prompt(title):
    clean_t = extract_celebrity_name(title)
    exact_thumb_prompt = (
        f"Hyper-realistic 8K award-winning cinematic movie poster portrait of the lead actor in '{clean_t[:45]}', "
        f"exact recognizable facial features, photorealistic skin pores and eyes, intense dramatic emotional expression, "
        f"35mm film photography, volumetric cinematic lighting, action sparks and debris background, high visual contrast, "
        f"ultra-detailed blockbuster aesthetic, 16:9 aspect ratio, masterpiece quality, no cartoon, no distortion."
    )
    titles = [
        f"🔥 {clean_t[:45]} | The Most Uncut Action Climax Scene!",
        f"⚡ Unstoppable Blockbuster Highlights | {clean_t[:40]}",
        f"😱 Dramatic Climax Reaction: {clean_t[:40]}"
    ]
    hashtags = "#MovieClimax #ActionHighlights #BlockbusterMovie #TrendingCinema #ViralScene #MovieRecap"
    return clean_t, titles, hashtags, exact_thumb_prompt

# ==========================================
# MULTI-SCENE DYNAMIC RUNNING MOVIE ENGINE
# ==========================================
def generate_rich_story_and_multi_scenes(movie_title, duration_type, language):
    """
    Generates a full comprehensive story with 6-8 distinct visual scenes that will change during the video
    """
    prompt = f"""
    You are an elite Movie Explainer and Film Storyteller.
    Language: {language}
    Target Duration: {duration_type}
    Movie / Story Title: {movie_title}

    Create an EPIC, continuous, gripping movie recap script in {language}.
    Breakdown the story progression into 6 distinct action/cinematic visual scenes (with English image prompts for each scene).

    Respond strictly in valid JSON format:
    {{
        "seo_title": "{movie_title} - Full Story Explained in {language} (Shocking Climax)",
        "seo_hashtags": "#MovieExplained #StoryRecap #{movie_title.replace(' ', '')} #FilmReview",
        "narration_script": "Full complete detailed story narration in {language} with dramatic suspense, plot twists, character confrontations, and full climax resolution...",
        "visual_scenes": [
            "Cinematic 8K movie scene, hero introduction in dark city streets, cinematic lighting, photorealistic film still",
            "Dramatic action shootout scene inside abandoned warehouse, fire sparks, cinematic smoke",
            "High speed car chase night scene on highway, cinematic action explosion background",
            "Intense emotional confrontation between hero and villain in heavy rain, dramatic facial expression",
            "Massive hand-to-hand fight battle climax, intense martial arts action, sparks flying",
            "Epic final sunset resolution scene, hero standing victorious, blockbuster cinematic wide shot"
        ]
    }}
    """
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
            return json.loads(res.choices[0].message.content)
        except Exception: pass
    elif GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
            return json.loads(res.choices[0].message.content)
        except Exception: pass

    return {
        "seo_title": f"{movie_title} - Full Story Explained in {language}",
        "seo_hashtags": f"#MovieExplained #StoryRecap #{movie_title.replace(' ', '')}",
        "narration_script": f"کہانی کی شروعات ایک پراسرار اور خوفناک واقعے سے ہوتی ہے۔ {movie_title} میں مرکزی کردار کو جب معلوم ہوتا ہے کہ حالات اس کے خلاف ایک بڑی سازش بن چکے ہیں، تو وہ تن تنہا دشمنوں کی پوری فوج کے سامنے آ کھڑا ہوتا ہے۔ راستے میں آنے والے ہر خطرے کو پار کرتے ہوئے، وہ اپنے بدلے اور انصاف کے لیے آخری حد تک جاتا ہے۔ کلائمیکس میں ہونے والا فیصلہ کن مقابلہ کہانی کو ایک سنسنی خیز انجام تک پہنچا دیتا ہے۔",
        "visual_scenes": [
            f"Cinematic 8K action hero introduction shot of {movie_title}, dramatic lighting, blockbuster movie still",
            f"Intense gunfight and car chase action scene of {movie_title}, motion blur, explosion background",
            f"Dramatic confrontation between hero and villain of {movie_title} in rain, hyper-realistic cinematic look",
            f"Epic climax battle and fight explosion of {movie_title}, sparks flying, award-winning cinematography"
        ]
    }

async def generate_voiceover_asad(text, output_file, language, gender="Male"):
    import edge_tts
    if language in ["اردو", "Roman Urdu"]:
        voice = "ur-PK-AsadNeural" if gender == "Male" else "ur-PK-UzmaNeural"
    elif language == "Hindi":
        voice = "hi-IN-MadhurNeural" if gender == "Male" else "hi-IN-SwaraNeural"
    else:
        voice = "en-US-ChristopherNeural" if gender == "Male" else "en-US-AriaNeural"

    # Asad 10% slowed rate and deep cinematic pitch
    rate = "-10%"
    pitch = "-8Hz"
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await comm.save(output_file)

def create_srt_file(script, output_srt):
    words = script.split()
    chunk = 7
    lines = [" ".join(words[i:i+chunk]) for i in range(0, len(words), chunk)]
    with open(output_srt, "w", encoding="utf-8") as f:
        for idx, line in enumerate(lines, 1):
            start = time.strftime('%H:%M:%S,000', time.gmtime((idx-1)*3))
            end = time.strftime('%H:%M:%S,000', time.gmtime(idx*3))
            f.write(f"{idx}\n{start} --> {end}\n{line}\n\n")

def render_multi_scene_running_movie(scenes_prompts, audio_narration_path, aspect_ratio, output_mp4, progress_bar, status_text):
    """
    Renders multiple dynamic changing motion scenes stitched smoothly across the entire voiceover length!
    """
    ffmpeg_exe = get_ffmpeg()
    temp_dir = os.path.dirname(output_mp4)
    total_audio_dur = get_video_duration_fast(audio_narration_path)
    
    num_scenes = max(4, len(scenes_prompts))
    per_scene_dur = max(5.0, total_audio_dur / num_scenes)

    status_text.write(f"🎨 کل {num_scenes} مختلف سنیماٹک ایکشن مناظر تیار اور رینڈر ہو رہے ہیں...")
    progress_bar.progress(55)

    if aspect_ratio == "9:16 (Shorts / Reels / TikTok)":
        scale_cmd = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280"
    elif aspect_ratio == "1:1 (Square)":
        scale_cmd = "scale=720:720:force_original_aspect_ratio=increase,crop=720:720"
    else:
        scale_cmd = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720"

    scene_clips = []
    
    # Render each scene with different motion directions (Zoom In, Pan Left, Tilt, Zoom Out)
    for idx, prompt in enumerate(scenes_prompts):
        img_path = os.path.join(temp_dir, f"scene_img_{idx}.jpg")
        clip_path = os.path.join(temp_dir, f"scene_clip_{idx}.mp4")
        
        # Fast Image Generation
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1280&height=720&nologo=true&model=flux"
        try:
            r = requests.get(img_url, timeout=7)
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
        except Exception: pass

        # Motion Effects variation per scene
        if idx % 2 == 0:
            zoom_expr = "zoompan=z='min(zoom+0.002,1.25)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        else:
            zoom_expr = "zoompan=z='if(lte(zoom,1.0),1.22,max(1.001,zoom-0.0018))':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

        if os.path.exists(img_path):
            vf_filter = f"loop=loop=-1:size=1:start=0,{scale_cmd},{zoom_expr}:s=1280x720,format=yuv420p"
            cmd_clip = [
                ffmpeg_exe, "-nostdin", "-y", "-i", img_path,
                "-t", str(per_scene_dur), "-vf", vf_filter,
                "-r", "25", "-c:v", "libx264", "-preset", "ultrafast", clip_path
            ]
        else:
            cmd_clip = [
                ffmpeg_exe, "-nostdin", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={per_scene_dur}",
                "-vf", scale_cmd, "-c:v", "libx264", "-preset", "ultrafast", clip_path
            ]
        subprocess.run(cmd_clip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(clip_path):
            scene_clips.append(clip_path)

    # Stitch all scenes together
    concat_txt = os.path.join(temp_dir, "concat_scenes.txt")
    with open(concat_txt, "w") as f:
        for sc in scene_clips:
            f.write(f"file '{sc}'\n")

    # Ambient soft BGM
    bgm_file = os.path.join(temp_dir, "ambient_bgm.mp3")
    cmd_bgm = [
        ffmpeg_exe, "-nostdin", "-y", "-f", "lavfi", "-i", f"anoisesrc=d={int(total_audio_dur)+10}:c=pink:r=44100:a=0.012",
        "-af", "lowpass=f=380,volume=0.12", bgm_file
    ]
    subprocess.run(cmd_bgm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    status_text.write("🎞️ تمام مناظر کو اسد کی بھاری آواز اور بی جی ایم کے ساتھ جوڑا جا رہا ہے...")
    progress_bar.progress(85)

    # Final Merged Render matching exact voiceover duration
    cmd_final = [
        ffmpeg_exe, "-nostdin", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-i", audio_narration_path,
        "-i", bgm_file,
        "-filter_complex", "[1:a]volume=1.25[a1];[2:a]volume=0.10[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_mp4
    ]
    subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_mp4

# ==========================================
# SLEEK COMPACT DASHBOARD STYLING
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; font-size: 13px !important; }
    .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
    .compact-header {
        display: flex; align-items: center; justify-content: space-between;
        background: #ffffff; padding: 8px 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 12px;
    }
    .compact-title { font-size: 1.15rem !important; font-weight: 800 !important; color: #0284c7 !important; margin: 0 !important; }
    .badge { background: #0f172a; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .stButton>button { 
        background: #0284c7 !important; color: white !important; border-radius: 6px !important; 
        height: 38px !important; font-size: 13px !important; font-weight: 600 !important; border: none !important;
    }
    .stTabs [data-baseweb="tab"] { height: 34px !important; font-size: 12px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="compact-header">
    <div class="compact-title">⚡ ES ULTRA ANTI-COPYRIGHT, AUTO SHORTS & MULTI-SCENE MOVIE STUDIO</div>
    <div class="badge">10 SHIELDS + VIRAL SHORTS + MULTI-SCENE EXPLAINER</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# NAVIGATION TABS (ORIGINAL 4 LOCKED + TAB 5 MULTI-SCENE)
# ==========================================
tab_shield, tab_shorts, tab_clip, tab_lofi, tab_explainer = st.tabs([
    "🛡️ 1. فل اینٹی کاپی رائٹ شیلڈ (10 ہتھیار + تھمب نیل)",
    "📱 2. آٹومیٹک وائرل شارٹس کٹر (New - 1 تا 5 شارٹس)",
    "⚔️ 3. کلپ کٹر (10 تا 20 منٹ کٹ)",
    "🎧 4. لوفی گانے (Slowed + Reverb)",
    "🎬 5. AI ملٹی سین مووی ایکسپلینر (مکمل کہانی + تبدیل ہوتے مناظر)"
])

# -----------------
# TAB 1: FAST FULL SHIELD WITH ALL 10 WEAPONS (ORIGINAL LOCKED)
# -----------------
with tab_shield:
    c1, c2 = st.columns([1, 1])
    with c1:
        shield_mode = st.selectbox("اینٹی کاپی رائٹ شیلڈ لیول:", [
            "🛡️ 10 ہتھیار: 0.75s کٹ + ہائپر زوم + فلپ + کلر اسکریبل (100% محفوظ)",
            "⚡ الٹرا فاسٹ کٹ + لیٹرباکس میٹ"
        ], key="sm_t1")
    with c2:
        audio_mode = st.selectbox("آواز کی موٹائی و گڑبڑ شیلڈ:", [
            "🔊 بھاری موٹی آواز (Deep Baritone) + ایکوسٹک گڑبڑ لہریں",
            "🎵 میڈیم پچ شفٹ (Medium Thick)"
        ], key="am_t1")
        
    up_file = st.file_uploader("📂 اپنے موبائل یا کمپیوٹر سے ویڈیو فائل منتخب کریں (فوری واٹس ایپ اسپیڈ):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_main")
    url_input = st.text_input("🔗 یا یوٹیوب کا لنک یہاں پیسٹ کریں:", placeholder="https://www.youtube.com/watch?v=...", key="url_main")
    
    if st.button("🚀 10 اینٹی کاپی رائٹ شیلڈز لگائیں اور AI تھمب نیل بنائیں", type="primary", key="btn_main"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"in_vid_{uid}.mp4"
        target_out = f"es_turbo_{uid}.mp4"
        info = {'title': 'Action Scene Video'}
        has_input = False
        
        if up_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_file.getbuffer())
            if os.path.exists(target_in) and os.path.getsize(target_in) > 1000:
                has_input = True
                info['title'] = up_file.name
        elif url_input.strip():
            with st.spinner("🔗 پیرلل نیٹ ورک سے ایچ ڈی ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
                else:
                    st.error("❌ لنک ڈاؤنلوڈ نہیں ہو سکا۔ برائے مہربانی ڈائریکٹ فائل منتخب کریں۔")

        if has_input and os.path.exists(target_in):
            t_start = time.time()
            with st.spinner("⚡ تمام 10 اینٹی کاپی رائٹ شیلڈز ویڈیو پر لگ رہی ہیں..."):
                ffmpeg_exe = get_ffmpeg()
                
                vf_str = (
                    "select='not(eq(mod(n\\,18)\\,0))',setpts=N/(24*TB),"
                    "hflip,crop=iw*0.82:ih*0.82,scale=1280:720:flags=fast_bilinear,"
                    "eq=contrast=1.18:saturation=1.24:brightness=0.02,"
                    "drawbox=y=0:h=36:color=black@0.75:t=fill,"
                    "drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                )
                
                if "بھاری موٹی آواز" in audio_mode:
                    af_str = "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,bass=g=7:f=100,treble=g=-4:f=3000,aecho=0.8:0.5:15:0.2"
                else:
                    af_str = "volume=0.75,asetrate=44100*0.94,aresample=44100:async=1,atempo=1.0638,bass=g=4:f=110"
                
                cmd = [
                    ffmpeg_exe, "-nostdin", "-y", "-i", target_in,
                    "-map_metadata", "-1", "-vf", vf_str, "-af", af_str,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode",
                    "-threads", "4", "-crf", "28", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "96k", target_out
                ]
                try: subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                except Exception: pass

                dur = round(time.time() - t_start, 1)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    st.success(f"⚡ ویڈیو صرف **{dur} سیکنڈ** میں 10 اینٹی کاپی رائٹ شیلڈز کے ساتھ تیار ہو گئی!")
                    try: os.remove(target_in)
                    except Exception: pass
                else:
                    st.error("❌ ویڈیو پروسیسنگ مکمل نہ ہو سکی۔")

# -----------------
# TAB 2: AUTOMATIC VIRAL SHORTS CREATOR (ORIGINAL LOCKED)
# -----------------
with tab_shorts:
    st.write("### 📱 لانگ ویڈیو سے خودکار وائرل شارٹس و ریلز جنریٹر")
    st.info("💡 **شارٹس انجن:** یہ فیچر آپ کی 5 سے 30 منٹ کی لمبی ویڈیو میں سے خودکار طریقے سے دلکش ایکشن اور ڈائیلاگ والے سینز نکال کر 9:16 ورٹیکل ریلز بنا دیتا ہے!")
    
    col_sh1, col_sh2 = st.columns(2)
    with col_sh1:
        num_shorts = st.selectbox("کتنے وائرل شارٹس بنانے ہیں؟", [
            "1 شارٹ (Best Climax Scene)",
            "2 شارٹس (Opening Hook + Climax)",
            "3 شارٹس (Hook + Turning Point + Climax)",
            "5 شارٹس (Full Multi-Highlight Pack)"
        ], key="num_sh")
    with col_sh2:
        short_dur = st.selectbox("ہر شارٹ کا دورانیہ:", [
            "30 سیکنڈ (30s - سب سے زیادہ وائرل)",
            "15 سیکنڈ (15s - فاسٹ ریلز)",
            "60 سیکنڈ (60s - فل اسٹوری شارٹ)"
        ], key="dur_sh")

    count_target = 1 if "1" in num_shorts else 2 if "2" in num_shorts else 3 if "3" in num_shorts else 5
    dur_sec_target = 30 if "30" in short_dur else 15 if "15" in short_dur else 60

    up_shorts_file = st.file_uploader("📂 لمبی ویڈیو فائل منتخب کریں (5 تا 30 منٹ):", type=["mp4", "mov", "mkv", "avi", "webm"], key="up_shorts")
    url_shorts_input = st.text_input("🔗 یا لمبی ویڈیو کا یوٹیوب لنک ڈالیں:", placeholder="https://www.youtube.com/watch?v=...", key="url_shorts")

    if st.button(f"🚀 خودکار طریقے سے {count_target} وائرل شارٹس تیار کریں", type="primary", key="btn_run_shorts"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"shorts_in_{uid}.mp4"
        has_input = False
        info = {'title': 'Long Video Highlights'}

        if up_shorts_file is not None:
            with open(target_in, "wb") as f:
                f.write(up_shorts_file.getbuffer())
            has_input = True
            info['title'] = up_shorts_file.name
        elif url_shorts_input.strip():
            with st.spinner("🔗 لمبی ویڈیو ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(url_shorts_input.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched

        if has_input and os.path.exists(target_in):
            total_dur = get_video_duration_fast(target_in)
            ffmpeg_exe = get_ffmpeg()
            created_shorts = []
            
            points = []
            if count_target == 1:
                points = [max(10.0, total_dur * 0.65)]
            elif count_target == 2:
                points = [max(10.0, total_dur * 0.20), max(20.0, total_dur * 0.70)]
            elif count_target == 3:
                points = [max(10.0, total_dur * 0.15), max(20.0, total_dur * 0.50), max(30.0, total_dur * 0.80)]
            else:
                points = [max(10.0, total_dur * 0.10), max(20.0, total_dur * 0.30), max(30.0, total_dur * 0.55), max(40.0, total_dur * 0.75), max(50.0, total_dur * 0.90)]

            progress_bar = st.progress(0.0)
            status_text = st.empty()

            for idx, start_pt in enumerate(points, 1):
                status_text.write(f"⚡ وائرل شارٹ #{idx} کٹ کر کے 9:16 فارمیٹ اور اینٹی کاپی رائٹ شیلڈ لگائی جا رہی ہے...")
                short_out = f"viral_short_{uid}_{idx}.mp4"
                
                vf_vertical = (
                    "select='not(eq(mod(n\\,18)\\,0))',setpts=N/(24*TB),"
                    "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,"
                    "hflip,eq=contrast=1.18:saturation=1.24:brightness=0.02,"
                    "drawbox=y=0:h=60:color=black@0.75:t=fill,drawbox=y=ih-70:h=70:color=black@0.85:t=fill"
                )
                af_shield = "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,bass=g=7:f=100,treble=g=-4:f=3000,aecho=0.8:0.5:15:0.2"

                cmd = [
                    ffmpeg_exe, "-nostdin", "-y", "-ss", str(start_pt), "-t", str(dur_sec_target),
                    "-i", target_in, "-map_metadata", "-1", "-vf", vf_vertical, "-af", af_shield,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k",
                    short_out
                ]
                try: subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                except Exception: pass

                if os.path.exists(short_out) and os.path.getsize(short_out) > 5000:
                    created_shorts.append((short_out, f"🔥 وائرل شارٹ #{idx} ({dur_sec_target}s)"))
                
                progress_bar.progress(idx / len(points))

            try: os.remove(target_in)
            except Exception: pass
            
            st.session_state.generated_shorts = created_shorts
            status_text.success(f"🎉 مبارک ہو! آپ کے تمام **{len(created_shorts)} وائرل شارٹس** 9:16 سائز اور اینٹی کاپی رائٹ شیلڈ کے ساتھ تیار ہیں!")

    if st.session_state.generated_shorts:
        st.divider()
        st.subheader("📱 تیار شدہ وائرل شارٹس (Download YouTube Shorts / Reels):")
        cols = st.columns(len(st.session_state.generated_shorts))
        for i, (s_path, s_title) in enumerate(st.session_state.generated_shorts):
            with cols[i]:
                st.write(f"**{s_title}**")
                s_bytes = open(s_path, 'rb').read()
                st.video(s_bytes)
                st.download_button(
                    label=f"📥 ڈاؤنلوڈ شارٹ #{i+1}",
                    data=s_bytes,
                    file_name=f"viral_short_{i+1}.mp4",
                    mime="video/mp4",
                    key=f"dl_sh_{i}"
                )

# -----------------
# TAB 3: CLIP CUTTER (ORIGINAL LOCKED)
# -----------------
with tab_clip:
    c1, c2 = st.columns(2)
    with c1: scene_type = st.selectbox("سین کا آغاز:", ["⚔️ منٹ 30", "👻 منٹ 45", "🏔️ منٹ 15", "⏱️ کسٹم"], key="s_t2")
    with c2: clip_len = st.slider("دورانیہ (منٹ):", 1, 20, 10, key="len_t2")
        
    start_min = 30 if "30" in scene_type else 45 if "45" in scene_type else 15 if "15" in scene_type else st.number_input("اسٹارٹ منٹ:", 0, 300, 10)
    clip_url = st.text_input("🔗 یوٹیوب لنک:", placeholder="https://...", key="clip_url")
    upload_opt2 = st.file_uploader("📂 یا ویڈیو فائل اپلوڈ کریں:", type=["mp4", "mov", "mkv", "webm"], key="up_t2")

    if st.button("🚀 کلپ کاٹیں اور شیلڈ لگائیں", type="primary", key="run_t2"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"clip_in_{uid}.mp4"
        target_out = f"clip_out_{uid}.mp4"
        info = {'title': 'Clip Highlight'}
        has_input = False
        
        if upload_opt2 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt2.getbuffer())
            has_input = True
            info['title'] = upload_opt2.name
        elif clip_url.strip():
            with st.spinner("ویڈیو لنک سے ڈاؤنلوڈ ہو رہی ہے..."):
                success, title_fetched = download_unblockable_media_parallel(clip_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
            
        if has_input and os.path.exists(target_in):
            with st.spinner("کلپ کٹ کر کے فاسٹ شیلڈ لگائی جا رہی ہے..."):
                ffmpeg_exe = get_ffmpeg()
                start_sec = start_min * 60
                dur_sec = clip_len * 60
                vf = "select='not(eq(mod(n\\,18)\\,0))',setpts=N/(24*TB),hflip,crop=iw*0.80:ih*0.80,scale=1280:720:flags=fast_bilinear,eq=contrast=1.18:saturation=1.24:brightness=0.02,drawbox=y=0:h=36:color=black@0.75:t=fill,drawbox=y=ih-44:h=44:color=black@0.85:t=fill"
                af = "volume=0.35,asetrate=44100*0.88,aresample=44100:async=1,atempo=1.13636,bass=g=7:f=100,treble=g=-4:f=3000,aecho=0.8:0.5:15:0.2"
                
                cmd = [
                    ffmpeg_exe, "-nostdin", "-y", "-ss", str(start_sec), "-t", str(dur_sec),
                    "-i", target_in, "-map_metadata", "-1", "-vf", vf, "-af", af,
                    "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-threads", "4", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", target_out
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    try: os.remove(target_in)
                    except Exception: pass
        else:
            st.error("❌ درست لنک دیں یا ویڈیو فائل اپلوڈ کریں۔")

# -----------------
# TAB 4: LO-FI & SONGS (ORIGINAL LOCKED)
# -----------------
with tab_lofi:
    col_s1, col_s2 = st.columns(2)
    with col_s1: slow_val = st.slider("سلو اسپیڈ:", 0.80, 0.96, 0.88, 0.01, key="sl_t3")
    with col_s2: reverb_val = st.slider("گونج / Reverb:", 20, 80, 50, 5, key="rev_t3")
        
    song_url = st.text_input("🔗 گانے کا لنک:", placeholder="https://...", key="song_url")
    upload_opt3 = st.file_uploader("📂 یا آڈیو فائل منتخب کریں:", type=["mp3", "wav", "mp4", "m4a"], key="up_t3")
    
    if st.button("🚀 فاسٹ لوفی بنائیں", type="primary", key="run_t3"):
        uid = str(uuid.uuid4())[:8]
        target_in = f"song_in_{uid}.mp4"
        target_out = f"song_out_{uid}.mp4"
        has_input = False
        info = {'title': 'Lo-Fi Chill Track'}
        
        if upload_opt3 is not None:
            with open(target_in, "wb") as f:
                f.write(upload_opt3.getbuffer())
            has_input = True
            info['title'] = upload_opt3.name
        elif song_url.strip():
            with st.spinner("گانا ڈاؤنلوڈ ہو رہا ہے..."):
                success, title_fetched = download_unblockable_media_parallel(song_url.strip(), target_in)
                if success and os.path.exists(target_in) and os.path.getsize(target_in) > 5000:
                    has_input = True
                    info['title'] = title_fetched
            
        if has_input and os.path.exists(target_in):
            with st.spinner("لوفی گانا تیار ہو رہا ہے..."):
                ffmpeg_exe = get_ffmpeg()
                sample_rate = int(44100 * slow_val)
                af_filter = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_val}:0.4,bass=g=6:f=110"
                cmd_song = [
                    ffmpeg_exe, "-nostdin", "-y", "-i", target_in,
                    "-map_metadata", "-1", "-af", af_filter, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", target_out
                ]
                subprocess.run(cmd_song, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    st.session_state.detected_info = info
                    st.session_state.current_output_video = target_out
                    st.session_state.process_ready = True
                    try: os.remove(target_in)
                    except Exception: pass
        else:
            st.error("❌ گانے کا درست لنک دیں یا فائل اپلوڈ کریں۔")

# -----------------
# TAB 5: MULTI-SCENE DYNAMIC MOVIE EXPLAINER STUDIO
# -----------------
with tab_explainer:
    st.write("### 🎬 AI ملٹی سین مووی ایکسپلینر اسٹوڈیو (Multi-Scene Running Video)")
    st.info("💡 **رننگ ویڈیو انجن:** صرف مووی یا کہانی کا عنوان لکھیں! AI پوری کہانی کے مطابق 6 سے 8 مختلف ایکشن مناظر کو حرکت (Motion/Pan) کے ساتھ چلائے گا اور اسد کی 10% بھاری آواز میں مکمل ویڈیو بنائے گا۔")

    c_ex1, c_ex2 = st.columns([1.5, 1])
    with c_ex1:
        st.subheader("1. مووی کا نام یا کہانی کا عنوان لکھیں")
        ex_movie_title = st.text_input(
            "🎬 مووی کا نام یا کوئی بھی کہانی کا عنوان:",
            placeholder="مثلاً: Animal / KGF 2 / Jawan / Salaar / Dracula Horror Story",
            key="ex_movie_title_final"
        )
        st.caption("✨ کوئی بھی عنوان لکھیں، AI خود اس کے ملٹی پل ایکشن مناظر اور کہانی تیار کر کے ویڈیو رن کرے گا۔")

    with c_ex2:
        st.subheader("2. ویڈیو و وائس سیٹنگز")
        ex_ratio = st.selectbox("📐 ویڈیو کا سائز (Aspect Ratio):", [
            "16:9 (یوٹیوب لینڈ اسکیپ)",
            "9:16 (Shorts / Reels / TikTok)",
            "1:1 (Square)"
        ], key="ex_ratio_f")
        ex_dur = st.selectbox("⏱️ دورانیہ (Target Duration):", [
            "1 سے 2 منٹ (فاسٹ شارٹس / ریلز)",
            "10 Minutes (فل مووی سمری)",
            "15 Minutes",
            "20 Minutes"
        ], key="ex_dur_f")
        ex_lang = st.selectbox("🗣️ وضاحتی زبان:", ["اردو", "English", "Hindi", "Roman Urdu"], key="ex_lang_f")
        ex_gender = st.selectbox("🎙️ وائس اوور:", ["Male (اسد - Deep 10% Slow)", "Female (عظمیٰ)"], key="ex_gender_f")

    if st.button("🎬 مکمل ملٹی سین مووی تیار کریں (Create Movie Explainer)", type="primary", key="btn_run_multi_scene"):
        if not ex_movie_title.strip():
            st.error("⚠️ برائے مہربانی مووی کا نام یا کہانی کا عنوان درج کریں۔")
        else:
            uid = str(uuid.uuid4())[:8]
            target_out = f"exp_multi_{uid}.mp4"
            tts_audio = f"exp_tts_{uid}.mp3"
            srt_path = f"exp_sub_{uid}.srt"
            movie_name = ex_movie_title.strip()

            progress_bar = st.progress(10)
            status_text = st.empty()

            try:
                # 1. AI Story & Multi-Scene Prompts Breakdown
                status_text.write(f"🧠 '{movie_name}' کی کہانی اور 6 مختلف سنیماٹک ایکشن مناظر تیار ہو رہے ہیں...")
                progress_bar.progress(30)
                data = generate_rich_story_and_multi_scenes(movie_name, ex_dur, ex_lang)

                # 2. Asad Voiceover (10% Deep & Slow)
                status_text.write("🎙️ اسد کی بھاری اور سلو آواز میں مکمل وائس اوور ریکارڈ ہو رہا ہے...")
                progress_bar.progress(50)
                gender_val = "Male" if "Male" in ex_gender else "Female"
                asyncio.run(generate_voiceover_asad(data["narration_script"], tts_audio, ex_lang, gender_val))
                create_srt_file(data["narration_script"], srt_path)

                # 3. Render Multi-Scene Running Video with Motion
                status_text.write("🎞️ تمام مناظر کو موشن زوم اور بیک گراؤنڈ میوزک کے ساتھ رینڈر کیا جا رہا ہے...")
                progress_bar.progress(70)
                render_multi_scene_running_movie(
                    data.get("visual_scenes", []),
                    tts_audio,
                    ex_ratio,
                    target_out,
                    progress_bar,
                    status_text
                )
                progress_bar.progress(100)

                if os.path.exists(target_out) and os.path.getsize(target_out) > 5000:
                    status_text.success("🎉 آپ کا ملٹی سین رننگ مووی ایکسپلینر کامیابی سے تیار ہو گیا ہے!")
                    st.session_state.explainer_ready = True
                    st.session_state.explainer_data = {
                        "video": target_out,
                        "srt": srt_path,
                        "data": data,
                        "title": movie_name
                    }
            except Exception as ex:
                st.error(f"❌ خرابی: {str(ex)}")

    if st.session_state.explainer_ready and st.session_state.explainer_data:
        exp_info = st.session_state.explainer_data
        st.divider()
        st.subheader("🎬 تیار شدہ ملٹی سین مووی ایکسپلینر ویڈیو:")
        c_res1, c_res2 = st.columns([1.4, 1.0])
        with c_res1:
            vid_bytes = open(exp_info["video"], "rb").read()
            st.video(vid_bytes)
            st.download_button("📥 ڈاؤنلوڈ مووی ایکسپلینر ویڈیو (MP4)", vid_bytes, file_name=f"{exp_info['title']}_Explainer.mp4", mime="video/mp4", use_container_width=True)
        with c_res2:
            st.markdown(f"**🔥 وائرل ٹائٹل:** `{exp_info['data'].get('seo_title')}`")
            st.markdown(f"**🏷️ ہیش ٹیگز:** `{exp_info['data'].get('seo_hashtags')}`")
            if os.path.exists(exp_info["srt"]):
                srt_bytes = open(exp_info["srt"], "rb").read()
                st.download_button("📥 ڈاؤنلوڈ سب ٹائٹلز (SRT)", srt_bytes, file_name="subtitles.srt", mime="text/plain", use_container_width=True)

        with st.expander("📖 AI وائس اوور اسکرپٹ یہاں پڑھیں (Full Story Script)", expanded=True):
            st.text_area("Full Narration Script", exp_info["data"].get("narration_script", ""), height=180)

# ==========================================
# OUTPUT, 1-CLICK COPY & EXACT LIKENESS DASHBOARD (FOR TAB 1, 3, 4)
# ==========================================
active_out = st.session_state.current_output_video
if st.session_state.process_ready and active_out and os.path.exists(active_out) and os.path.getsize(active_out) > 5000:
    st.divider()
    st.write("#### 🎬 پروسیس شدہ 100% اینٹی کاپی رائٹ ویڈیو:")
    
    video_bytes = open(active_out, 'rb').read()
    st.video(video_bytes)
    
    st.download_button(
        label="📥 محفوظ ویڈیو ڈاؤنلوڈ کریں (Download Protected MP4)",
        data=video_bytes,
        file_name=f"es_protected_{os.path.basename(active_out)}",
        mime="video/mp4",
        use_container_width=True
    )

    st.markdown("---")
    st.write("#### 🧠 اصلی ہیرو کے چہرے والا AI تھمب نیل پرامپٹ و وائرل ٹائٹلز (1-Click Copy):")
    
    raw_title = st.session_state.detected_info.get('title', 'Action Video')
    clean_hero_title, titles, hashtags, exact_thumb_prompt = analyze_video_and_generate_exact_prompt(raw_title)
    
    col_out1, col_out2 = st.columns(2)
    with col_out1:
        st.markdown("**🔥 وائرل ہائی-CTR ٹائٹلز (کاپی کرنے کے لیے دائیں طرف کاپی آئیکن دبائیں):**")
        for idx, t in enumerate(titles, 1):
            st.code(t, language="text")
            
        st.markdown("**🏷️ وائرل ہیش ٹیگز:**")
        st.code(hashtags, language="text")

    with col_out2:
        st.markdown(f"**🎨 اصلی ہیرو ({clean_hero_title[:30]}) کے چہرے کا تھمب نیل پرامپٹ:**")
        st.info("💡 یہ پرامپٹ اصلی اداکار کے فیشل فیچرز کے ساتھ تیار کیا گیا ہے۔ اوپر دائیں کونے سے کاپی کریں:")
        st.code(exact_thumb_prompt, language="text")
        
        with st.expander("🖼️ ایپ کے اندر لائیو AI تھمب نیل دیکھیں اور ڈاؤنلوڈ کریں"):
            thumb_gen_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(exact_thumb_prompt)}?width=1280&height=720&nologo=true&model=flux"
            try:
                st.image(thumb_gen_url, caption="Live AI Generated Thumbnail (Celebrity Likeness Active)", use_column_width=True)
            except Exception:
                st.write("پرامپٹ کو کاپی کر کے Midjourney یا Bing Creator میں استعمال کریں۔")

st.markdown("<p style='text-align: center; font-size: 11px; color: #64748b; margin-top: 20px;'>ES Ultra Anti-Copyright & Auto Shorts Studio | Developers: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
