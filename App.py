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
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import numpy as np
import threading
import gc
import json

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

# Bulletproof MoviePy Universal Import
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

st.set_page_config(page_title="Sglowina AI - Titan Master Studio", layout="wide", page_icon="🎬")

if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "enable_watermark" not in st.session_state: st.session_state.enable_watermark = False
if "msgs" not in st.session_state: st.session_state.msgs = []

st.sidebar.subheader("🎬 Titan Production Master")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
enable_watermark = st.sidebar.checkbox("Enable Watermark Logo", value=st.session_state.enable_watermark)
st.session_state.enable_bg_music = enable_bg_music
st.session_state.enable_watermark = enable_watermark

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

# ================= 2. TRANSLATOR & LLM =================
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

def generate_text_pollinations(prompt, system_prompt=""):
    models = ["openai-fast", "openai", "mistral"]
    for model in models:
        try:
            payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], "model": model, "jsonMode": False}
            res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    text_out = data["choices"][0]["message"]["content"]
                    if len(text_out.strip()) > 5: return text_out.strip()
        except: pass
    return ""

def search_web_ddg(query):
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text, re.DOTALL)
            if snippets:
                return "\n".join([re.sub(r'<[^>]*>', '', s).strip() for s in snippets[:3]])
    except: pass
    return ""

# ================= 3. SCENE & CHARACTER PROMPT WITH LOCKED DNA =================
def build_universal_scene_prompt(scene_english_text, style, char_dna_anchor, scene_index):
    clean_scene = re.sub(r'(?i)\b(character 1|character 2|in every image|grid|collage|character sheet|turnaround)\b', '', scene_english_text)
    clean_scene = re.sub(r'\s+', ' ', clean_scene).strip()
    
    dna_prefix = f"Consistent Character DNA: {char_dna_anchor.strip()}, " if char_dna_anchor.strip() else ""

    camera_perspectives = [
        "cinematic wide-angle establishing shot, full environment visible, glowing rim lighting",
        "dramatic medium cinematography shot, clear sharp lighting, high dynamic range HDR, vivid textures",
        "epic wide-angle landscape shot, illuminated background, sharp focus, rich natural contrast",
        "low-angle cinematic shot, deep shadows with clear sharp highlights, 8k crisp details"
    ]
    perspective = camera_perspectives[scene_index % len(camera_perspectives)]
    
    return f"{perspective}: {dna_prefix}{clean_scene}. Style: {style}, 8k photorealistic, crystal-clear lighting, sharp vivid focus on all subjects, deep rich contrast, strictly NO blurry face close-up, NO muddy textures, NO split screen, NO collage, NO grid"

def apply_filmic_grading(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.30)
            im = ImageEnhance.Contrast(im).enhance(1.12)
            im = ImageEnhance.Color(im).enhance(1.10)
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

# ================= 4. AUTHENTICATED IMAGE DOWNLOADER WITH MULTI-ENGINE FAILOVER =================
def download_image_authenticated(prompt, out_path, w, h, seed, key=""):
    clean_p = prompt[:380]
    active_key = key.strip() if key.strip() else DEFAULT_POLLINATIONS_KEY
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {active_key}"
    }

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

    # Failover: Hercai Prodia
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

    # Gradient fallback
    im = Image.new("RGB", (w, h), color=(20, 40, 75))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=(int(20 + 35 * (y / h)), int(40 + 45 * (y / h)), int(75 + 65 * (y / h))))
    im.save(out_path, "PNG")
    return True

# ================= 5. FAST & SMOOTH KINETIC CAMERA MOTION (HIGH SPEED / NO JERKS) =================
def render_scene_clip_chunk(img_path, audio_path, out_clip_path, w, h, selected_motion="AI Director (Auto)", motion_index=0):
    apply_filmic_grading(img_path)
    
    # Increased scale factor to allow faster movement without revealing edges
    scale_factor = 1.35
    cw, ch = make_even(w * scale_factor), make_even(h * scale_factor)
    temp_scaled = img_path.replace(".png", "_scaled.png")

    with Image.open(img_path) as im:
        im.resize((cw, ch), Image.Resampling.LANCZOS).save(temp_scaled, "PNG")

    try:
        a_clip = AudioFileClip(audio_path)
        dur = a_clip.duration
        clip = ImageClip(temp_scaled).set_duration(dur).set_fps(24)

        active_mode = selected_motion
        if selected_motion == "AI Director (Auto)":
            modes = ["Fast Pan Left", "Fast Pan Right", "Fast Zoom In", "Fast Zoom Out"]
            active_mode = modes[motion_index % len(modes)]

        # DOUBLED SPEED COEFFICIENTS FOR VISIBLE FAST MOTION WITH SMOOTH GLIDE
        if active_mode == "Fast Pan Left":
            animated = clip.set_position(lambda t: (int((w - cw)/2 - (42 * (t / dur))), 'center'))
        elif active_mode == "Fast Pan Right":
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (42 * (t / dur))), 'center'))
        elif active_mode == "Fast Zoom In":
            animated = clip.set_position(lambda t: (int((w - cw)/2 - (35 * (t / dur))), int((h - ch)/2 - (35 * (t / dur)))))
        elif active_mode == "Fast Zoom Out":
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (35 * (t / dur))), int((h - ch)/2 + (35 * (t / dur)))))
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

# ================= 6. MASTER PRODUCTION PIPELINE =================
def create_titan_cinematic_movie(story, voice_gen, rate_val, pitch_val, ratio, style, base_seed, char_dna="", selected_motion="AI Director (Auto)", api_key="", enable_bg_music=True):
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
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: تیز رفتار کیمرہ موشن اور تصویر تیار ہو رہی ہے...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                if is_urdu_voice:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="ur")
                else:
                    spoken_line = translate_text_dynamic(raw_scene_text, target_lang="en")

                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(spoken_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                english_scene_desc = translate_text_dynamic(raw_scene_text, target_lang="en")
                scene_flux_prompt = build_universal_scene_prompt(english_scene_desc, style, char_dna, idx)

                scene_seed = int(base_seed) + (idx * 53)
                img_p = f"img_{u_id}_{idx}.png"
                temp_files_to_clean.append(img_p)
                
                download_image_authenticated(scene_flux_prompt, img_p, w, h, seed=scene_seed, key=api_key)

                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                if render_scene_clip_chunk(img_p, sub_audio, clip_mp4, w, h, selected_motion=selected_motion, motion_index=idx):
                    scene_chunk_paths.append(clip_mp4)

                gc.collect()

            if not scene_chunk_paths: raise Exception("کوئی منظر رینڈر نہیں ہو سکا۔")

            progress_bar.progress(0.85)
            status.info(f"🎞️ تمام {len(scene_chunk_paths)} مناظر کو فائنل مووی میں جوڑا جا رہا ہے...")

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
            status.success(f"🚀 تیز رفتار کائینیٹک موشن کے ساتھ ماسٹر مووی تیار ہو گئی!")
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
        <h1 class="glow-title">Sglowina AI - Titan Fast Motion Studio</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_canva, tab_chat, tab_enterprise = st.tabs([
    "🎬 Titan Movie Studio", "🎨 Pro Canva Studio", "💬 Electric AI Chat", "👤 Founders & Accounts"
])

# 1. MOVIE STUDIO
with tab_movie:
    st.write("### 🎥 Titan Movie Studio (تیز رفتار کیمرہ موشن + مستقل کریکٹر ڈی این اے)")
    
    # Script Generator Helper
    with st.expander("✨ AI Script Generator (کہانی خودکار بنوائیں)"):
        gen_topic = st.text_input("کہانی کا موضوع (Topic):", placeholder="عقاب اور شیر کی دوستی...")
        if st.button("Generate Script ✍️"):
            if gen_topic:
                with st.spinner("AI کہانی لکھ رہا ہے..."):
                    res_script = generate_text_pollinations(f"Write a 5-scene cinematic short story in Urdu about: {gen_topic}", "You are a professional story writer.")
                    if res_script:
                        st.session_state.movie_script_val = res_script
                        st.success("اسکرپٹ تیار ہو گیا!")
                        st.rerun()

    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", value=st.session_state.get("movie_script_val", ""), height=140, placeholder="یہاں کہانی لکھیں...")
    char_dna_input = st.text_input("مستقل کردار ڈی این اے (Character DNA Lock - اختیاری):", placeholder="مثلاً: A 22-year-old explorer Daniel with short brown hair")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6, c7 = st.columns(3)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art", "Dark Gothic / Mystery"])
    with c6: motion_choice = st.selectbox("کیمرہ موشن (Fast & Smooth):", ["AI Director (Auto)", "Fast Pan Left", "Fast Pan Right", "Fast Zoom In", "Fast Zoom Out"])
    with c7: sd = st.number_input("سیڈ (Base Seed):", value=786)

    voice_map = {"Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural", "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural"}
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Titan Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 تیز رفتار کیمرہ موشن اور آڈیو سنک کے ساتھ مووی رینڈر ہو رہی ہے..."):
                v_res = create_titan_cinematic_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    char_dna=char_dna_input, selected_motion=motion_choice,
                    api_key=api_key_input, enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ماسٹر ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 2. CANVA STUDIO
with tab_canva:
    st.write("### 🎨 Pro Canva Typography & Image Studio")
    canva_prompt = st.text_input("تصویر کا پرامپٹ (Image Prompt):", "A majestic glowing crystal castle in a magical forest, 8k")
    canva_text = st.text_input("بینر پر لکھنے کے لیے متن (Canva Text Overlay - اختیاری):", "Sglowina Studio")
    c_style = st.selectbox("تصویر کا اسٹائل:", ["Photorealistic Hollywood", "3D Cartoon Pixar Style", "Anime Art", "Cinematic Dark"], key="c_st")
    c_qty = st.slider("تصویروں کی تعداد:", 1, 5, 1)

    if st.button("Generate Pro Images 🎨"):
        if canva_prompt:
            with st.spinner("تصویریں تیار ہو رہی ہیں..."):
                for i in range(c_qty):
                    temp_img = f"canva_{i}.png"
                    download_image_authenticated(canva_prompt + f", Style: {c_style}", temp_img, 1280, 720, seed=786+i, key=api_key_input)
                    if canva_text:
                        apply_canva_typography(temp_img, canva_text)
                    st.image(temp_img, caption=f"Image {i+1}")
                    st.download_button(f"Download Image {i+1}", open(temp_img, "rb").read(), file_name=f"sglowina_{i}.png", key=f"dl_{i}")

# 3. CHAT
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard (DuckDuckGo Live Web Search)")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        web_info = search_web_ddg(p)
        sys_p = f"You are Sglowina AI Titan, developed by founders Muhammad Essa Awan & Saba Wahid. Live Web Context: {web_info}"
        res = generate_text_pollinations(p, system_prompt=sys_p)
        if not res: res = "I am here to assist you."
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

# 4. FOUNDERS & ACCOUNTS
with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Studio | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
