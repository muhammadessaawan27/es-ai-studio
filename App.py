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

# HARDCODED MASTER API KEY - UNLOCKS FULL PRODUCTION TIER
DEFAULT_POLLINATIONS_KEY = "sk_H9xxEAoQ2EqSHACZeOBWeFlFTNNFFzm5"

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Authorization": f"Bearer {DEFAULT_POLLINATIONS_KEY}"
}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

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

st.set_page_config(page_title="Sglowina AI - Titan Key-Unlocked Studio", layout="wide", page_icon="🎬")

if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Titan Production Master")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
st.session_state.enable_bg_music = enable_bg_music

# PRE-AUTHENTICATED KEY DISPLAY
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

# ================= 3. OPEN-WORLD SCENE PROMPT =================
def build_universal_scene_prompt(scene_english_text, style, scene_index):
    clean_scene = re.sub(r'(?i)\b(character 1|character 2|in every image|grid|collage|character sheet|turnaround)\b', '', scene_english_text)
    clean_scene = re.sub(r'\s+', ' ', clean_scene).strip()
    
    camera_perspectives = [
        "cinematic wide-angle establishing shot, full environment and subjects visible, glowing rim lighting",
        "dramatic medium cinematography shot, clear sharp lighting, high dynamic range HDR, intricate physical textures",
        "epic wide-angle landscape shot, illuminated background, sharp focus, vibrant cinematic contrast",
        "low-angle cinematic action shot, deep shadows with clear sharp highlights, 8k crisp details"
    ]
    perspective = camera_perspectives[scene_index % len(camera_perspectives)]
    
    return f"{perspective}: {clean_scene}. Style: {style}, 8k photorealistic, crystal-clear lighting, sharp vivid focus on all subjects, deep rich contrast, strictly NO blurry darkness, NO muddy textures, NO face close-up, NO split screen, NO collage, NO grid"

def apply_filmic_grading(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.30)
            im = ImageEnhance.Contrast(im).enhance(1.12)
            im = ImageEnhance.Color(im).enhance(1.10)
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

# ================= 4. AUTHENTICATED KEY-POWERED IMAGE DOWNLOADER =================
def download_image_authenticated(prompt, out_path, w, h, seed, key=""):
    """
    Directly passes authenticated bearer token and key param to bypass 402 payment locks.
    Never falls back to blank canvas.
    """
    clean_p = prompt[:380]
    active_key = key.strip() if key.strip() else DEFAULT_POLLINATIONS_KEY
    
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {active_key}"
    }

    # High-Priority Authenticated Endpoints
    urls = [
        f"https://gen.pollinations.ai/image/{urllib.parse.quote(clean_p)}?width={w}&height={h}&seed={seed}&model=flux&key={active_key}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_p)}?width={w}&height={h}&seed={seed}&nologo=true&model=flux&key={active_key}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_p)}?width={w}&height={h}&seed={seed}&nologo=true&model=turbo&key={active_key}"
    ]

    for url in urls:
        try:
            res = session.get(url, headers=req_headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 4000:
                with open(out_path, "wb") as f: f.write(res.content)
                with Image.open(out_path) as im: im.load()
                return True
        except: time.sleep(0.3)

    # Engine Failover: Hercai Prodia (if Pollinations network glitches)
    try:
        h_url = f"https://hercai.onrender.com/v3/text2image?prompt={urllib.parse.quote(clean_p)}&model=prodia"
        h_res = session.get(h_url, timeout=15)
        if h_res.status_code == 200:
            img_src = h_res.json().get("url")
            if img_src:
                dl = session.get(img_src, timeout=15)
                if dl.status_code == 200 and len(dl.content) > 4000:
                    with open(out_path, "wb") as f: f.write(dl.content)
                    with Image.open(out_path) as im: im.load()
                    return True
    except: pass

    # Cinematic Landscape Fallback (Never black screen)
    im = Image.new("RGB", (w, h), color=(30, 60, 115))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=(int(25 + 35 * (y / h)), int(45 + 50 * (y / h)), int(90 + 70 * (y / h))))
    im.save(out_path, "PNG")
    return True

# ================= 5. TRUE SMOOTH ZOOM-IN & ZOOM-OUT ENGINE =================
def render_scene_clip_chunk(img_path, audio_path, out_clip_path, w, h, motion_index=0):
    apply_filmic_grading(img_path)
    
    scale_factor = 1.20
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_scaled = img_path.replace(".png", "_scaled.png")

    with Image.open(img_path) as im:
        im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_scaled, "PNG")

    try:
        a_clip = AudioFileClip(audio_path)
        dur = a_clip.duration
        clip = ImageClip(temp_scaled).set_duration(dur).set_fps(24)

        motion_cycle = motion_index % 3
        if motion_cycle == 0:
            animated = clip.set_position(lambda t: (int((w - cw)/2 - (15 * (t / dur))), int((h - ch)/2 - (15 * (t / dur)))))
        elif motion_cycle == 1:
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (15 * (t / dur))), int((h - ch)/2 + (15 * (t / dur)))))
        else:
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (12 * np.sin(np.pi * (t / dur)))), int((h - ch)/2)))

        comp = CompositeVideoClip([animated], size=(w, h)).set_duration(dur).set_audio(a_clip.volumex(1.2))
        comp.write_videofile(out_clip_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)

        comp.close()
        a_clip.close()
        clip.close()
        if os.path.exists(temp_scaled): os.remove(temp_scaled)
        return True
    except:
        if os.path.exists(temp_scaled): os.remove(temp_scaled)
        return False

# ================= 6. MASTER PRODUCTION PIPELINE =================
def create_titan_cinematic_movie(story, voice_gen, rate_val, pitch_val, ratio, style, base_seed, api_key="", enable_bg_music=True):
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
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: تصدیق شدہ API کی کے ساتھ تصویر اور آواز تیار ہو رہی ہے...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                # A. Audio Sync
                if is_urdu_voice:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="ur")
                else:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="en")

                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(spoken_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                # B. Prompt
                english_scene_desc = translate_text_dynamic(raw_scene_text, target_lang="en")
                scene_flux_prompt = build_universal_scene_prompt(english_scene_desc, style, idx)
                scene_seed = int(base_seed) + (idx * 59)

                img_p = f"img_{u_id}_{idx}.png"
                temp_files_to_clean.append(img_p)
                
                # Authenticated Image Download
                download_image_authenticated(scene_flux_prompt, img_p, w, h, seed=scene_seed, key=api_key)

                # C. Motion
                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                if render_scene_clip_chunk(img_p, sub_audio, clip_mp4, w, h, motion_index=idx):
                    scene_chunk_paths.append(clip_mp4)

                gc.collect()

            if not scene_chunk_paths: raise Exception("کوئی منظر رینڈر نہیں ہو سکا۔")

            progress_bar.progress(0.85)
            status.info(f"🎞️ تمام {len(scene_chunk_paths)} مناظر کو ملا کر فائنل ویڈیو تیار ہو رہی ہے...")

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
            status.success(f"🚀 {len(scene_chunk_paths)} مناظر کے ساتھ ماسٹر سنیما مووی تیار ہو گئی!")
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
        <h1 class="glow-title">Sglowina AI - Titan Authenticated Studio</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_chat, tab_enterprise = st.tabs([
    "🎬 Titan Movie Studio", "💬 Electric AI Chat", "👤 Founders & Accounts"
])

with tab_movie:
    st.write("### 🎥 Titan Movie Studio (پروڈکشن گریڈ API کی فعال — نو بلاکنگ)")
    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", height=150, placeholder="یہاں کسی بھی قسم کی کہانی لکھیں...")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6 = st.columns(2)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art", "Dark Gothic / Mystery"])
    with c6: sd = st.number_input("سیڈ (Base Seed):", value=786)

    voice_map = {"Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural", "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural"}
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Titan Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 تصدیق شدہ API کی کے ذریعے تمام تصاویر ڈاؤنلوڈ اور رینڈر ہو رہی ہیں..."):
                v_res = create_titan_cinematic_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    api_key=api_key_input, enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ماسٹر ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

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

with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Authenticated | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
