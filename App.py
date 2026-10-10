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
import zipfile

# PRE-AUTHENTICATED MASTER API KEY
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

# Bulletproof MoviePy Universal Imports
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
if "msgs" not in st.session_state: st.session_state.msgs = []
if "movie_script_val" not in st.session_state: st.session_state.movie_script_val = ""

st.sidebar.subheader("🎬 Titan Production Master")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
st.session_state.enable_bg_music = enable_bg_music

api_key_input = st.sidebar.text_input("Active Pollinations Key:", value=DEFAULT_POLLINATIONS_KEY, type="password")

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ================= 1. ROBUST STORY CHUNKER (HANDLES 2,000+ WORDS STORIES) =================
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

# ================= 3. ANTI-DOUBLE FACE PROMPT ARCHITECT =================
def build_universal_scene_prompt(scene_english_text, style, char_dna_anchor, scene_index):
    clean_scene = re.sub(r'(?i)\b(character 1|character 2|in every image|grid|collage|character sheet|turnaround)\b', '', scene_english_text)
    clean_scene = re.sub(r'\s+', ' ', clean_scene).strip()
    
    dna_prefix = f"Consistent Character DNA: {char_dna_anchor.strip()}, " if char_dna_anchor.strip() else ""

    camera_perspectives = [
        "cinematic wide-angle establishing shot, glowing rim lighting, solo centered framing",
        "dramatic medium cinematography shot, clear sharp lighting, high dynamic range HDR, single subject",
        "epic wide-angle landscape shot, illuminated background, sharp focus, rich natural contrast",
        "low-angle cinematic shot, deep shadows with clear sharp highlights, 8k crisp details, solo focus"
    ]
    perspective = camera_perspectives[scene_index % len(camera_perspectives)]
    
    # Strict anti-duplicate-face and anti-collage shields
    return f"{perspective}: {dna_prefix}{clean_scene}. Style: {style}, 8k photorealistic, solo subject, single centered face, crystal-clear lighting, strictly NO double faces, NO duplicate heads, NO overlapping faces, NO clone, NO blurry face close-up, NO split screen, NO collage, NO grid"

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

# ================= 4. AUTHENTICATED IMAGE DOWNLOADER =================
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

    im = Image.new("RGB", (w, h), color=(20, 40, 75))
    im.save(out_path, "PNG")
    return True

# ================= 5. ENHANCED HIGH-SPEED KINETIC CAMERA MOTION =================
def render_scene_clip_chunk(img_path, audio_path, out_clip_path, w, h, selected_motion="AI Director (Auto)", motion_index=0):
    apply_filmic_grading(img_path)
    
    # Increased scale factor from 1.20 to 1.32 for bold, clear cinematic motion without exposing borders
    scale_factor = 1.32
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
            modes = ["Pan Left", "Pan Right", "Fast Zoom In", "Fast Zoom Out"]
            active_mode = modes[motion_index % len(modes)]

        # Speed multiplied by 2.5x so the motion is immediately noticeable and cinematic!
        if active_mode in ["Pan Left", "Fast Pan Left"]:
            animated = clip.set_position(lambda t: (int((w - cw)/2 - (45 * (t / dur))), 'center'))
        elif active_mode in ["Pan Right", "Fast Pan Right"]:
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (45 * (t / dur))), 'center'))
        elif active_mode in ["Fast Zoom In", "Smooth Zoom In"]:
            animated = clip.set_position(lambda t: (int((w - cw)/2 - (35 * (t / dur))), int((h - ch)/2 - (35 * (t / dur)))))
        elif active_mode in ["Fast Zoom Out", "Smooth Zoom Out"]:
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
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: آواز اور سولو 8K فریم تیار ہو رہا ہے...")
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
            status.info(f"🎞️ تمام {len(scene_chunk_paths)} مناظر کو تیز اور ہموار کائینیٹک موشن کے ساتھ جوڑا جا رہا ہے...")

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
            status.success(f"🚀 {len(scene_chunk_paths)} مناظر اور تیز سنیما موشن کے ساتھ مووی تیار ہو گئی!")
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
        <h1 class="glow-title">Sglowina AI - Titan Cinema Studio</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_image, tab_chat, tab_enterprise = st.tabs([
    "🎬 Pro Movie Studio", "🎨 Pro Image & Storyboard Studio", "💬 Electric AI Chat", "👤 Founders & Accounts"
])

# 1. MOVIE STUDIO
with tab_movie:
    st.write("### 🎥 Titan Movie Studio (تیز کیمرہ موشن + سولو فیس پروٹیکشن)")
    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", height=140, placeholder="The Forest That Eats Shadows. Deep inside a forgotten forest, a young explorer named Daniel discovered a glowing blue tree...")
    char_dna_input = st.text_input("مستقل کردار ڈی این اے (Character DNA Memory):", placeholder="مثلاً: A 22-year-old explorer Daniel with short brown hair wearing a dark navy leather jacket")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6, c7 = st.columns(3)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art", "Dark Gothic / Mystery"])
    with c6: motion_choice = st.selectbox("کیمرہ موشن (Camera Motion):", ["AI Director (Auto)", "Fast Zoom In", "Fast Zoom Out", "Fast Pan Left", "Fast Pan Right"])
    with c7: sd = st.number_input("سیڈ (Base Seed):", value=786)

    voice_map = {"Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural", "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural"}
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Titan Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 تیز کیمرہ موشن اور سولو چہرے کے ساتھ مووی تیار ہو رہی ہے..."):
                v_res = create_titan_cinematic_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    char_dna=char_dna_input, selected_motion=motion_choice,
                    api_key=api_key_input, enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ماسٹر ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 2. PRO IMAGE & BULK STORYBOARD STUDIO (HANDLES 2,000 WORDS STORIES + ZIP DOWNLOAD)
with tab_image:
    st.write("### 🎨 Pro Image & Storyboard Studio")
    studio_mode = st.radio("موڈ منتخب کریں:", ["📚 Bulk Storyboard Generator (مکمل لمبی کہانی سے تمام مناظر کی تصاویر)", "🎯 Single Image Studio"], horizontal=True)

    if "Bulk Storyboard" in studio_mode:
        st.write("#### 📚 لمبی کہانی کے تمام مناظر کی خودکار تصاویر بنائیں اور ترتیب سے ڈاؤنلوڈ کریں")
        bulk_story = st.text_area("یہاں 500 سے 2,000 الفاظ کی مکمل کہانی درج کریں:", height=180, placeholder="یہاں اپنی لمبی کہانی لکھیں، سسٹم ہر سین کی تصویر بنا کر ترتیب سے لسٹ کر دے گا...")
        b_dna = st.text_input("مستقل کردار کی تفصیل (Character DNA):", placeholder="e.g. A brave 22-year-old warrior with short black hair wearing silver armor")
        
        bc1, bc2, bc3 = st.columns(3)
        with bc1: b_style = st.selectbox("اسٹائل:", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art"], key="b_style_sel")
        with bc2: b_res = st.selectbox("سائز:", ["YouTube HD (16:9)", "Square (1:1)", "TikTok (9:16)"], key="b_res_sel")
        with bc3: b_seed = st.number_input("سیڈ:", value=786, key="b_seed_num")

        if st.button("تمام مناظر کی تصاویر جنریٹ کریں 🚀"):
            if not bulk_story.strip():
                st.error("پہلے کہانی درج کریں!")
            else:
                scenes_list = smart_story_slicer(bulk_story)
                st.info(f"کل {len(scenes_list)} مناظر کی نشاندہی ہوئی۔ تصاویر کی تیاری شروع ہو رہی ہے...")
                
                dim_map = {"YouTube HD (16:9)": (1280, 720), "Square (1:1)": (1024, 1024), "TikTok (9:16)": (720, 1280)}
                bw, bh = dim_map.get(b_res, (1280, 720))
                
                generated_images_zip = io.BytesIO()
                with zipfile.ZipFile(generated_images_zip, "w") as zip_f:
                    for s_idx, scene_text in enumerate(scenes_list):
                        eng_text = translate_text_dynamic(scene_text, target_lang="en")
                        scene_p = build_universal_scene_prompt(eng_text, b_style, b_dna, s_idx)
                        img_filename = f"Scene_{s_idx+1:02d}.png"
                        local_path = os.path.join(TEMP_DIR, img_filename)
                        
                        download_image_authenticated(scene_p, local_path, bw, bh, seed=int(b_seed)+(s_idx*47), key=api_key_input)
                        apply_filmic_grading(local_path)
                        
                        if os.path.exists(local_path):
                            st.write(f"**منظر {s_idx + 1}:** {scene_text}")
                            st.image(local_path, width=500)
                            with open(local_path, "rb") as f_img:
                                img_bytes = f_img.read()
                                st.download_button(f"ڈاؤنلوڈ منظر {s_idx + 1}", img_bytes, file_name=img_filename, key=f"dl_btn_{s_idx}")
                                zip_f.writestr(img_filename, img_bytes)
                            try: os.remove(local_path)
                            except: pass

                st.success("تمام مناظر کی تصاویر کامیابی سے تیار ہو گئیں!")
                st.download_button("📦 تمام مناظر کی تصاویر ایک ساتھ زپ میں ڈاؤنلوڈ کریں (Download All as ZIP)", 
                                   generated_images_zip.getvalue(), file_name="Storyboard_All_Scenes.zip", mime="application/zip")

    else:
        st.write("#### 🎯 سنگل امیج اسٹوڈیو")
        p_i = st.text_area("تصویر کی تفصیل درج کریں:", height=100)
        canva_overlay_text = st.text_input("Canva Text Overlay (پوسٹر کا عنوان):", placeholder="e.g. Sglowina Blockbuster")
        ic1, ic2 = st.columns(2)
        with ic1: i_style = st.selectbox("Art Style:", ["Photorealistic Hollywood", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art"])
        with ic2: i_size = st.selectbox("Resolution:", ["YouTube HD (16:9)", "Square (1:1)", "TikTok (9:16)"])

        if st.button("Generate Titan Visual 🚀"):
            dim_map = {"YouTube HD (16:9)": (1280, 720), "Square (1:1)": (1024, 1024), "TikTok (9:16)": (720, 1280)}
            w, h = dim_map.get(i_size, (1280, 720))
            img_path = "temp_single_img.png"
            clean_p = f"{p_i}, solo centered subject, visual style: {i_style}, 8k photorealistic, single face, strictly NO double faces, strictly NO collage"
            download_image_authenticated(clean_p, img_path, w, h, seed=int(time.time())%10000, key=api_key_input)
            apply_filmic_grading(img_path)
            if os.path.exists(img_path):
                st.image(img_path)
                with open(img_path, "rb") as f:
                    st.download_button("ڈاؤنلوڈ تصویر (Full HD)", f.read(), file_name="Titan_Visual.png")
                try: os.remove(img_path)
                except: pass

# 3. CHAT
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

# 4. FOUNDERS & ACCOUNTS
with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Cinema | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
