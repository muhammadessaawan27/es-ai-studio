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
import json

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
TRANSITION_SFX_FILE = "transition_whoosh.mp3"

def download_transition_sfx():
    if os.path.exists(TRANSITION_SFX_FILE) and os.path.getsize(TRANSITION_SFX_FILE) > 5000:
        return
    try:
        res = requests.get("https://www.soundjay.com/mechanical/sounds/whoosh-1.mp3", timeout=10)
        if res.status_code == 200:
            with open(TRANSITION_SFX_FILE, "wb") as f: f.write(res.content)
    except: pass

download_transition_sfx()

# ================= BULLETPROOF UNIVERSAL MOVIEPY IMPORTS =================
MOVIEPY_AVAILABLE = False
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except Exception:
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
        MOVIEPY_AVAILABLE = True
    except Exception as e:
        MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

st.set_page_config(page_title="Sglowina AI - Titan Enterprise Studio", layout="wide", page_icon="🎬")

if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Titan Production Settings")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
st.session_state.enable_bg_music = enable_bg_music

# FUTURE-PROOF API KEY SLOT
user_api_key = st.sidebar.text_input("AI Video API Key (Kling / Fal.ai / Pollen):", type="password", help="Leave blank for Free High-End Cinematic Engine")

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ================= MANDATORY ENGLISH TRANSLATION & GENDER ANCHOR =================
def force_translate_to_english(text):
    """Guarantees text is converted to clean English so Flux never hallucinates"""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={urllib.parse.quote(text)}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            translated = "".join([sentence[0] for sentence in res.json()[0] if sentence[0]]).strip()
            if len(translated) > 2:
                return translated
    except: pass
    return text

def build_gender_locked_prompt(english_text, style):
    """Enforces masculine or feminine anchor at the first 3 tokens so character never inverts"""
    text_l = english_text.lower()
    prefix = ""
    if any(k in text_l for k in ["daniel", "boy", "man", "male", "he", "him", "his", "explorer", "son", "brother", "لڑکا", "مرد"]):
        prefix = "A young male, masculine explorer, handsome authentic male features, strictly male, not a woman, not a girl, "
    elif any(k in text_l for k in ["girl", "woman", "female", "she", "her", "ayesha", "daughter", "sister", "لڑکی", "عورت"]):
        prefix = "A young female woman, authentic female features, strictly female, not a man, "
    
    clean = re.sub(r'(?i)\b(character 1|character 2|in every image|grid|collage|character sheet|turnaround)\b', '', english_text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return f"{prefix}{clean}, single continuous camera shot, wide cinematic angle, photorealistic {style}, 8k resolution, volumetric cinematic lighting, strictly NO split screen, NO multi-panel, NO collage, NO grid"

def apply_filmic_grading(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.22)
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "PNG")
    except: pass

def apply_canva_typography(img_path, overlay_text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            w, h = im.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.06))
            except: font = ImageFont.load_default()
            draw.rectangle([(int(w * 0.08), int(h * 0.08)), (int(w * 0.92), int(h * 0.22))], fill=(37, 99, 235, 200))
            draw.text((w // 2, int(h * 0.15)), overlay_text, font=font, fill=(255, 255, 255, 255), anchor="mm")
            Image.alpha_composite(im, overlay).convert("RGB").save(img_path, "PNG")
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

# ================= ROBUST FLUX IMAGE DOWNLOADER (NO BLACK FRAMES) =================
def download_flux_image_robust(prompt, out_path, w, h, seed, last_valid_path=None):
    url_flux = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
    url_turbo = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=turbo"

    for url in [url_flux, url_turbo]:
        for attempt in range(2):
            try:
                res = session.get(url, timeout=20)
                if res.status_code == 200 and len(res.content) > 4000:
                    with open(out_path, "wb") as f: f.write(res.content)
                    with Image.open(out_path) as im: im.load()
                    return True
            except: time.sleep(0.5)

    if last_valid_path and os.path.exists(last_valid_path):
        try:
            with Image.open(last_valid_path) as prev_im:
                prev_im.save(out_path, "PNG")
            return True
        except: pass

    im = Image.new("RGB", (w, h), color=(30, 58, 138))
    im.save(out_path, "PNG")
    return True

# ================= CHUNKED LOW-RAM CINEMATIC MOTION RENDERER =================
def render_scene_clip_chunk(img_path, audio_path, out_clip_path, w, h, motion="Dolly In"):
    apply_filmic_grading(img_path)
    scale_factor = 1.15
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_scaled = img_path.replace(".png", "_scaled.png")

    with Image.open(img_path) as im:
        im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_scaled, "PNG")

    try:
        a_clip = AudioFileClip(audio_path)
        dur = a_clip.duration
        clip = ImageClip(temp_scaled).set_duration(dur).set_fps(24)

        if motion == "Dolly In":
            animated = clip.set_position(lambda t: ('center', int((h - ch)/2 + (15 * (t / dur)))))
        elif motion == "Pan Left":
            animated = clip.set_position(lambda t: (int((w - cw) * (t / dur)), 'center'))
        elif motion == "Pan Right":
            animated = clip.set_position(lambda t: (int((w - cw) * (1 - t / dur)), 'center'))
        else:
            animated = clip.set_position('center')

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

# ================= TITAN MASTER PRODUCTION PIPELINE =================
def create_titan_cinematic_movie(story, voice_gen, rate_val, pitch_val, ratio, style, seed, api_key="", enable_bg_music=True):
    if not MOVIEPY_AVAILABLE: return "MoviePy library missing."
    u_id = str(uuid.uuid4())[:8]

    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()

        # Step 1: Parse sentences cleanly
        raw_sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story) if len(s.strip()) > 3]
        if not sentences if 'sentences' in locals() else None: raw_sentences = [s for s in raw_sentences if s]
        if not raw_sentences: raw_sentences = [story.strip()]
        total_scenes = len(raw_sentences)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)

        scene_chunk_paths = []
        temp_files_to_clean = []
        last_good_image = None

        is_horror = any(k in story.lower() or k in style.lower() for k in ["horror", "خوف", "مونسٹر", "جن", "ڈراونا", "موت", "قبر", "shadows"])

        try:
            for idx, raw_line in enumerate(raw_sentences):
                # 1. Translate sentence strictly to English and inject Subject-First Anchor
                english_line = force_translate_to_english(raw_line)
                flux_prompt = build_gender_locked_prompt(english_line, style)

                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: آواز اور 4K فریم کی تیاری...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                # 2. Voiceover Synthesis
                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(raw_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                # 3. Robust Image Generation (Zero Black Frames & Correct Gender)
                img_p = f"img_{u_id}_{idx}.png"
                temp_files_to_clean.append(img_p)
                download_flux_image_robust(flux_prompt, img_p, w, h, seed=seed, last_valid_path=last_good_image)
                if os.path.exists(img_p) and os.path.getsize(img_p) > 2000:
                    last_good_image = img_p

                # 4. Chunked Filmic Motion Render
                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                motion_type = "Dolly In" if idx % 2 == 0 else "Pan Left"
                if render_scene_clip_chunk(img_p, sub_audio, clip_mp4, w, h, motion=motion_type):
                    scene_chunk_paths.append(clip_mp4)

                gc.collect()

            if not scene_chunk_paths: raise Exception("کوئی منظر رینڈر نہیں ہو سکا۔")

            progress_bar.progress(0.85)
            status.info("🎞️ تمام مناظر کو جوڑا جا رہا ہے اور ڈکڈ بیک گراؤنڈ میوزک سنک ہو رہا ہے...")

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
            status.success("🚀 ٹائٹن پروڈکشن گریڈ مووی کامیابی سے تیار ہو گئی!")
            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
            return f"Error Details: {e}"

# ================= UI DASHBOARD =================
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
        <h1 class="glow-title">Sglowina AI - Titan Enterprise Studio</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_chat, tab_image, tab_enterprise = st.tabs([
    "🎬 Titan Movie Studio", "💬 Electric AI Chat", "🎨 Pro Image & Canva Studio", "👤 Founders & Accounts"
])

# 1. MOVIE STUDIO
with tab_movie:
    st.write("### 🎥 Titan Movie Studio (100% صنف کا تحفظ — نو بلیک اسکرین — نو امپورٹ کریش)")
    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", height=140, placeholder="Deep inside a forgotten forest, a young explorer named Daniel discovered a glowing blue tree...")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6 = st.columns(2)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Photorealistic Horror", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art"])
    with c6: sd = st.number_input("کردار کا فکسڈ سیڈ (Character Seed Lock):", value=786)

    voice_map = {"Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural", "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural"}
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Titan Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 ٹائٹن انجن تمام فریمز اور آڈیو سنک کر رہا ہے..."):
                v_res = create_titan_cinematic_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    api_key=user_api_key, enable_bg_music=st.session_state.enable_bg_music
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

# 3. PRO IMAGE & CANVA STUDIO
with tab_image:
    st.write("### 🎨 Visual & Canva Poster Studio")
    p_i = st.text_area("تصویر کی تفصیل درج کریں:", height=100)
    canva_overlay_text = st.text_input("Canva Poster Title Overlay:", placeholder="e.g. Sglowina Blockbuster")
    ic1, ic2 = st.columns(2)
    with ic1: i_style = st.selectbox("Art Style:", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon", "Anime Art"])
    with ic2: i_size = st.selectbox("Resolution:", ["YouTube HD", "Square (1:1)", "TikTok"])

    if st.button("Generate Titan Visual 🚀"):
        dim = {"YouTube HD": (1280, 720), "Square (1:1)": (1024, 1024), "TikTok": (720, 1280)}
        w, h = dim.get(i_size, (1280, 720))
        img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ', visual style: ' + i_style)}?width={w}&height={h}&nologo=true&model=flux"
        r = session.get(img_url)
        if r.status_code == 200:
            temp_p = "temp_canva.jpg"
            with open(temp_p, "wb") as f: f.write(r.content)
            if canva_overlay_text.strip(): apply_canva_typography(temp_p, canva_overlay_text.strip())
            st.image(temp_p)
            try: os.remove(temp_p)
            except: pass

# 4. FOUNDERS & ACCOUNTS
with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
