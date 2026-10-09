import sys
# 1. Globally patch PIL.Image for Pillow 10+ compatibility with MoviePy
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS if hasattr(PIL.Image, 'Resampling') else 1
    sys.modules['PIL.Image'] = PIL.Image
except:
    pass

import streamlit as st
import asyncio
import requests
import urllib.parse
import os
import time
import re
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import sqlite3
import json

# PRE-AUTHENTICATED MASTER API KEY
DEFAULT_POLLINATIONS_KEY = "sk_H9xxEAoQ2EqSHACZeOBWeFlFTNNFFzm5"

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Authorization": f"Bearer {DEFAULT_POLLINATIONS_KEY}"
}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Bulletproof MoviePy Imports
MOVIEPY_AVAILABLE = False
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except Exception:
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
        MOVIEPY_AVAILABLE = True
    except Exception:
        MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

st.set_page_config(page_title="Sglowina AI - Real Motion Cinema Studio", layout="wide", page_icon="🎬")

if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "msgs" not in st.session_state: st.session_state.msgs = []
if "movie_script_val" not in st.session_state: st.session_state.movie_script_val = ""

st.sidebar.subheader("🎬 Real Motion Engine Settings")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
st.session_state.enable_bg_music = enable_bg_music

# ENGINE MODE TOGGLE
engine_mode = st.sidebar.selectbox(
    "ویڈیو جنریشن موڈ:",
    ["Real AI Video Motion (3s Moving Clips)", "Cinematic 8K Photo Pan & Zoom"]
)

api_key_input = st.sidebar.text_input("Active Pollinations Key:", value=DEFAULT_POLLINATIONS_KEY, type="password")

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ================= 1. ROBUST STORY CHUNKER =================
def smart_story_slicer(story_text):
    clean_text = re.sub(r'\s+', ' ', story_text).strip()
    punctuated_chunks = [p.strip() for p in re.split(r'[۔\n.!|?؛;:]+', clean_text) if len(p.strip()) > 2]
    if not punctuated_chunks: punctuated_chunks = [clean_text]
    
    final_scenes = []
    for chunk in punctuated_chunks:
        words = chunk.split()
        if len(words) <= 15:
            final_scenes.append(chunk)
        else:
            sub_chunk_size = 12
            for i in range(0, len(words), sub_chunk_size):
                sub_part = " ".join(words[i:i + sub_chunk_size])
                if len(sub_part.split()) >= 3:
                    final_scenes.append(sub_part)

    all_words = clean_text.split()
    if len(all_words) >= 20 and len(final_scenes) < 3:
        step = max(8, len(all_words) // 4)
        final_scenes = [" ".join(all_words[i:i + step]) for i in range(0, len(all_words), step)]

    return [s for s in final_scenes if len(s.strip()) > 2]

# ================= 2. TRANSLATOR =================
def translate_text_dynamic(text, target_lang="en"):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            translated = "".join([sentence[0] for sentence in res.json()[0] if sentence[0]]).strip()
            if len(translated) > 2:
                return translated
    except: pass
    return text

def build_universal_scene_prompt(scene_english_text, style, char_dna_anchor, scene_index):
    clean_scene = re.sub(r'(?i)\b(character 1|character 2|in every image|grid|collage|character sheet|turnaround)\b', '', scene_english_text)
    clean_scene = re.sub(r'\s+', ' ', clean_scene).strip()
    dna_prefix = f"Main Character DNA: {char_dna_anchor.strip()}, " if char_dna_anchor.strip() else ""
    return f"Cinematic action motion scene: {dna_prefix}{clean_scene}. Style: {style}, 8k photorealistic, dynamic character movement, sharp focus, strictly NO blurry close-up, NO split screen, NO collage"

def apply_filmic_grading(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.25)
            im = ImageEnhance.Contrast(im).enhance(1.10)
            im.save(img_path, "PNG")
    except: pass

def get_cached_bg_music(is_horror=False):
    fn = "bg_horror.mp3" if is_horror else "bg_standard.mp3"
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3" if is_horror else "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
    cf = os.path.join(AUDIO_CACHE_DIR, fn)
    if os.path.exists(cf) and os.path.getsize(cf) > 100000: return cf
    try:
        res = session.get(url, timeout=12)
        if res.status_code == 200:
            with open(cf, "wb") as f: f.write(res.content)
            return cf
    except: pass
    return None

def save_audio_safe(text, voice, rate, pitch, filename):
    async def _tts_exec():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(_tts_exec())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except:
        return False

# ================= 3. AUTHENTICATED REAL 3-SECOND VIDEO MOTION ENGINE =================
def generate_real_motion_clip(prompt, audio_path, out_clip_path, w, h, seed=786, key="", video_model="wan-fast"):
    """
    Downloads true moving 3-second MP4 clip using authenticated key.
    Loops video smoothly if spoken audio is longer than 3 seconds.
    """
    aspect = "16:9" if w > h else "9:16"
    active_key = key.strip() if key.strip() else DEFAULT_POLLINATIONS_KEY
    motion_prompt = f"high cinematic action motion, dynamic movement, character walking, lifelike physics, {prompt}"
    
    vid_url = f"https://gen.pollinations.ai/video/{urllib.parse.quote(motion_prompt[:380])}?model={video_model}&aspectRatio={aspect}&duration=3&seed={seed}&key={active_key}"
    temp_raw = out_clip_path.replace(".mp4", "_raw.mp4")
    
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {active_key}"
    }

    success = False
    for attempt in range(2):
        try:
            r = session.get(vid_url, headers=req_headers, timeout=50)
            if r.status_code == 200 and len(r.content) > 30000:
                with open(temp_raw, "wb") as f: f.write(r.content)
                success = True
                break
        except: time.sleep(1)

    if success and os.path.exists(temp_raw):
        try:
            a_clip = AudioFileClip(audio_path)
            target_dur = a_clip.duration
            v_clip = VideoFileClip(temp_raw).resize((w, h))

            # If voiceover is longer than 3 seconds, loop video seamlessly
            if v_clip.duration < target_dur:
                loops = int(np.ceil(target_dur / v_clip.duration))
                v_clip = concatenate_videoclips([v_clip] * loops)

            final_clip = v_clip.subclip(0, target_dur).set_audio(a_clip.volumex(1.2))
            final_clip.write_videofile(out_clip_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
            
            final_clip.close()
            v_clip.close()
            a_clip.close()
            if os.path.exists(temp_raw): os.remove(temp_raw)
            return True
        except: pass

    if os.path.exists(temp_raw): os.remove(temp_raw)
    return False

# High-Fidelity Photo Fallback (Used if network drop occurs)
def render_photo_motion_fallback(prompt, audio_path, out_clip_path, w, h, seed, key=""):
    clean_p = prompt[:380]
    active_key = key.strip() if key.strip() else DEFAULT_POLLINATIONS_KEY
    img_p = out_clip_path.replace(".mp4", ".png")
    
    url = f"https://gen.pollinations.ai/image/{urllib.parse.quote(clean_p)}?width={w}&height={h}&seed={seed}&model=flux&key={active_key}"
    try:
        r = session.get(url, timeout=25)
        if r.status_code == 200 and len(r.content) > 4000:
            with open(img_p, "wb") as f: f.write(r.content)
    except:
        im = Image.new("RGB", (w, h), color=(20, 40, 75))
        im.save(img_p, "PNG")

    apply_filmic_grading(img_p)
    scale_factor = 1.20
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_scaled = img_p.replace(".png", "_scaled.png")

    with Image.open(img_p) as im:
        im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_scaled, "PNG")

    try:
        a_clip = AudioFileClip(audio_path)
        dur = a_clip.duration
        clip = ImageClip(temp_scaled).set_duration(dur).set_fps(24)
        animated = clip.set_position(lambda t: (int((w - cw)/2 - (15 * (t / dur))), int((h - ch)/2 - (15 * (t / dur)))))
        comp = CompositeVideoClip([animated], size=(w, h)).set_duration(dur).set_audio(a_clip.volumex(1.2))
        comp.write_videofile(out_clip_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
        comp.close()
        a_clip.close()
        clip.close()
    except: pass

    for f in [img_p, temp_scaled]:
        if os.path.exists(f): os.remove(f)

# ================= 4. MASTER CINEMATIC PRODUCTION PIPELINE =================
def create_master_movie(story, voice_gen, rate_val, pitch_val, ratio, style, base_seed, char_dna="", mode="Real AI Video Motion (3s Moving Clips)", api_key="", enable_bg_music=True):
    if not MOVIEPY_AVAILABLE: return "MoviePy missing."
    u_id = str(uuid.uuid4())[:8]

    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()

        sliced_scenes = smart_story_slicer(story)
        total_scenes = len(sliced_scenes)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)

        scene_chunk_paths = []
        temp_files_to_clean = []

        is_urdu_voice = voice_gen.startswith("ur-PK")
        is_horror = any(k in story.lower() or k in style.lower() for k in ["horror", "خوف", "مونسٹر", "جن", "ڈراونا", "موت", "قبر", "shadows", "monster", "tree"])

        try:
            for idx, raw_scene_text in enumerate(sliced_scenes):
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: متحرک ویڈیو کلپ اور آواز رینڈر ہو رہی ہے...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                # 1. Spoken Audio Line
                if is_urdu_voice:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="ur")
                else:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="en")

                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(spoken_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                # 2. Scene Prompt
                english_scene_desc = translate_text_dynamic(raw_scene_text, target_lang="en")
                scene_prompt = build_universal_scene_prompt(english_scene_desc, style, char_dna, idx)
                scene_seed = int(base_seed) + (idx * 47)

                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                # 3. Generate Video (True Motion or Photo Zoom)
                if "Real AI Video" in mode:
                    success = generate_real_motion_clip(scene_prompt, sub_audio, clip_mp4, w, h, seed=scene_seed, key=api_key, video_model="wan-fast")
                    if not success or not os.path.exists(clip_mp4):
                        render_photo_motion_fallback(scene_prompt, sub_audio, clip_mp4, w, h, seed=scene_seed, key=api_key)
                else:
                    render_photo_motion_fallback(scene_prompt, sub_audio, clip_mp4, w, h, seed=scene_seed, key=api_key)

                if os.path.exists(clip_mp4):
                    scene_chunk_paths.append(clip_mp4)

                gc.collect()

            if not scene_chunk_paths: raise Exception("کوئی منظر رینڈر نہیں ہو سکا۔")

            progress_bar.progress(0.85)
            status.info(f"🎞️ تمام {len(scene_chunk_paths)} متحرک مناظر کو ملا کر فائنل ویڈیو تیار ہو رہی ہے...")

            loaded_clips = [VideoFileClip(p) for p in scene_chunk_paths if os.path.exists(p)]
            final_video = concatenate_videoclips(loaded_clips, method="compose")

            if enable_bg_music:
                bg_m = get_cached_bg_music(is_horror=is_horror)
                if bg_m and os.path.exists(bg_m):
                    try:
                        bg_track = AudioFileClip(bg_m).volumex(0.04).set_duration(final_video.duration)
                        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                    except: pass

            out_name = f"Sglowina_Titan_{u_id}_{int(time.time())}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)

            final_video.close()
            for c in loaded_clips: c.close()
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass

            progress_bar.progress(1.0)
            status.success(f"🚀 {len(scene_chunk_paths)} متحرک مناظر کے ساتھ مکمل مووی کامیابی سے تیار ہو گئی!")
            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
            return f"Error Details: {e}"

# ================= UI & DASHBOARD =================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;800&display=swap');
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 1.35rem !important; font-weight: 700 !important; color: #1e3a8a !important; text-align: center; }
    .dashboard-header { display: flex; justify-content: center; align-items: center; gap: 15px; margin: 15px 0; }
    .circular-s { width: 50px; height: 50px; background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #2563eb; animation: rotateSpins 10s infinite linear; }
    .metallic-s { font-family: 'Orbitron'; font-size: 28px; font-weight: 900; color: #2563eb; }
    @keyframes rotateSpins { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .stButton>button, .stFormSubmitButton>button { background: linear-gradient(90deg, #2563eb, #1d4ed8) !important; color: white !important; font-size: 19px !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="dashboard-header">
        <div class="circular-s"><span class="metallic-s">S</span></div>
        <h1 class="glow-title">Sglowina AI - Titan Motion Cinema</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_chat, tab_enterprise = st.tabs([
    "🎬 Pro Movie Studio", "💬 Electric AI Chat", "👤 Founders & Accounts"
])

# 1. MOVIE STUDIO
with tab_movie:
    st.write("### 🎥 Titan Real Motion Studio (3 سیکنڈ متحرک ویڈیو کلپس + آڈیو سنک)")
    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", height=140, placeholder="The Forest That Eats Shadows. Deep inside a forgotten forest, a young explorer named Daniel discovered a glowing blue tree...")
    char_dna_input = st.text_input("مستقل کردار ڈی این اے (Character DNA Memory - اختیاری):", placeholder="مثلاً: A 22-year-old explorer Daniel with short brown hair wearing a dark navy leather jacket")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6 = st.columns(2)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art", "Dark Gothic / Mystery"])
    with c6: sd = st.number_input("سیڈ (Base Seed):", value=786)

    voice_map = {
        "Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
        "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural",
        "Arabic Egypt Male (Shakir)": "ar-EG-ShakirNeural", "Persian Male (Farid)": "fa-IR-FaridNeural"
    }
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Titan Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 تصدیق شدہ API کی کے ذریعے متحرک ویڈیوز اور آڈیو تیار ہو رہی ہے..."):
                v_res = create_master_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    char_dna=char_dna_input, mode=engine_mode,
                    api_key=api_key_input, enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ماسٹر ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 2. CHAT
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        sys_p = "You are Sglowina AI Titan, developed by founders Muhammad Essa Awan & Saba Wahid."
        res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(sys_p + ' ' + p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# 3. FOUNDERS & ACCOUNTS
with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Motion Cinema | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
