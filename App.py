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
import sqlite3
import hashlib
import json

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
TEMP_DIR = "temp_render_chunks"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
DB_BACKUP_FILE = "sglowina_saas_backup.json"
TRANSITION_SFX_FILE = "transition_whoosh.mp3"

def download_transition_sfx():
    if os.path.exists(TRANSITION_SFX_FILE) and os.path.getsize(TRANSITION_SFX_FILE) > 5000:
        return
    try:
        res = requests.get("https://www.soundjay.com/mechanical/sounds/whoosh-1.mp3", timeout=12)
        if res.status_code == 200:
            with open(TRANSITION_SFX_FILE, "wb") as f: f.write(res.content)
    except: pass

download_transition_sfx()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
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

st.sidebar.subheader("🎬 Titan Audio & Video Master")
enable_bg_music = st.sidebar.checkbox("Enable Filmic Background Music", value=st.session_state.enable_bg_music)
st.session_state.enable_bg_music = enable_bg_music

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ================= DATABASE & PERSISTENCE (HONORING FOUNDERS) =================
def get_db_connection():
    conn = sqlite3.connect("sglowina_titan_v3.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_titan_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            plan TEXT DEFAULT 'Enterprise', credits INTEGER DEFAULT 5000, role TEXT DEFAULT 'Founder', created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, title TEXT, prompt TEXT, out_path TEXT, created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS local_payments (
            id TEXT PRIMARY KEY, sender_name TEXT, method TEXT, trx_id TEXT UNIQUE, amount REAL, status TEXT DEFAULT 'Approved', created_at TEXT
        )
    """)
    # Founders Registration: Muhammad Essa Awan & Saba Wahid
    for founder in ["muhammad_essa_awan", "saba_wahid"]:
        c.execute("INSERT OR IGNORE INTO users (username, plan, credits, role, created_at) VALUES (?, 'Enterprise', 5000, 'Founder', ?)", (founder, time.strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

init_titan_db()

# ================= AI AUTO-DIRECTOR & PERSISTENT CHARACTER DNA =================
def auto_direct_story_pipeline(story_text, chosen_style):
    """
    Titan Automated Screenplay Director:
    1. Analyzes story in Urdu.
    2. Identifies character names & builds a persistent visual DNA.
    3. Breaks down story into coherent sequential scenes.
    4. Automatically writes pure cinematic English Flux prompts with strict anti-collage shields.
    """
    system_prompt = (
        "You are an elite Hollywood Film Director and Master AI Prompt Architect. "
        "Analyze the provided story and decompose it into a clean cinematic screenplay JSON object.\n"
        "RULES:\n"
        "1. Identify main characters and establish an absolute 'Visual DNA' for each (exact attire colors, facial bone structure, skin tone, hairstyle, age).\n"
        "2. Break down the story into 3 to 6 chronological visual scenes.\n"
        "3. For each scene, return:\n"
        "   - 'urdu_sentence': The precise spoken sentence for audio narration.\n"
        "   - 'visual_prompt': A breathtaking, photorealistic English visual prompt for Flux AI. Explicitly insert the exact Visual DNA of characters active in this frame. Strictly include: single camera frame, anamorphic lens, volumetric lighting, photorealistic skin textures, and strictly NO split screen, NO multi-panel collage, NO character sheet, 8k resolution.\n"
        "Return strictly valid JSON in this exact structure:\n"
        '{"scenes": [{"urdu_sentence": "...", "visual_prompt": "..."}]}'
    )

    try:
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Cinematic Visual Style: {chosen_style}\nStory:\n{story_text}"}
            ],
            "model": "openai-fast",
            "jsonMode": True
        }
        res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers={"Content-Type": "application/json"}, timeout=25)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            clean_json = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            data = json.loads(clean_json)
            if "scenes" in data and len(data["scenes"]) > 0:
                return data["scenes"]
    except: pass

    # Bulletproof fallback parser
    raw_sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story_text) if len(s.strip()) > 3]
    if not raw_sentences: raw_sentences = [story_text]
    fallback_scenes = []
    for s in raw_sentences:
        fallback_scenes.append({
            "urdu_sentence": s,
            "visual_prompt": f"A cinematic Hollywood single camera frame: {s}, style: {chosen_style}, 8k photorealistic, volumetric cinematic lighting, sharp focus, strictly NO collage, NO split screen"
        })
    return fallback_scenes

# ================= IMAGE PROCESSING, ANTI-COLLAGE SHIELD & CANVA =================
def sanitize_visual_prompt(raw_prompt):
    cleaned = raw_prompt
    for token in ["character 1", "character 2", "character consistency rules", "in every image", "turnaround", "character sheet", "grid", "collage"]:
        cleaned = re.sub(r'(?i)\b' + token + r'\b', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return f"{cleaned}, single continuous cinematic scene, wide camera angle, highly detailed facial features, strictly NO split screen, NO multi-panel, NO collage, NO grid, 8k resolution"

def apply_filmic_grading(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.22)
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "PNG")
    except: pass

def burn_subtitles_to_image(img_path, scene_text):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGBA")
            w, h = im.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            bar_height = int(h * 0.12)
            draw.rectangle([(0, h - bar_height), (w, h)], fill=(0, 0, 0, 160))
            clean_sub = scene_text[:85]
            try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.038))
            except: font = ImageFont.load_default()
            draw.text((w // 2, h - (bar_height // 2)), clean_sub, font=font, fill=(255, 255, 255, 240), anchor="mm")
            Image.alpha_composite(im, overlay).convert("RGB").save(img_path, "PNG")
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

# ================= EDGE-TTS VOICE ENGINE (RATE & PITCH FULLY ACTIVE) =================
def save_audio_safe(text, voice, rate, pitch, filename):
    async def _tts_exec():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(_tts_exec())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except:
        return False

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
        elif motion == "Handheld":
            animated = clip.set_position(lambda t: (int((w - cw)/2 + (3 * np.sin(2 * np.pi * t * 1.5))), int((h - ch)/2 + (3 * np.cos(2 * np.pi * t * 1.2)))))
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
def create_titan_cinematic_movie(story, voice_gen, rate_val, pitch_val, ratio, style, seed, enable_bg_music=True):
    if not MOVIEPY_AVAILABLE: return "MoviePy missing."
    u_id = str(uuid.uuid4())[:8]

    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()

        status.info("🧠 AI ڈائریکٹر کہانی کا پوسٹ مارٹم کر کے 'کریکٹر ڈی این اے' اور مناظر لاک کر رہا ہے...")
        directed_scenes = auto_direct_story_pipeline(story, style)
        total_scenes = len(directed_scenes)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)

        scene_chunk_paths = []
        temp_files_to_clean = []

        is_horror = any(k in story.lower() or k in style.lower() for k in ["horror", "خوف", "مونسٹر", "جن", "ڈراونا", "موت", "قبر"])

        try:
            for idx, sc in enumerate(directed_scenes):
                urdu_line = sc.get("urdu_sentence", "")
                raw_flux_prompt = sc.get("visual_prompt", "")
                flux_prompt = sanitize_visual_prompt(raw_flux_prompt)

                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: آواز اور اینٹی گرڈ 4K فریم تیار ہو رہا ہے...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                # 1. Voiceover Synthesis
                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(urdu_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                # 2. Flux Image Generation with Persistent Seed
                img_p = f"img_{u_id}_{idx}.png"
                temp_files_to_clean.append(img_p)
                img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(flux_prompt[:380])}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"

                try:
                    res = session.get(img_url, timeout=25)
                    if res.status_code == 200 and len(res.content) > 3000:
                        with open(img_p, "wb") as f: f.write(res.content)
                    else:
                        Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_p, "PNG")
                except:
                    Image.new("RGB", (w, h), color=(15, 23, 42)).save(img_p, "PNG")

                # 3. Chunked Filmic Motion Render
                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)

                motion_type = "Dolly In" if idx % 2 == 0 else "Pan Left"
                if render_scene_clip_chunk(img_p, sub_audio, clip_mp4, w, h, motion=motion_type):
                    scene_chunk_paths.append(clip_mp4)

                # Explicit Memory Clean per chunk
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

            # Resources Release
            final_video.close()
            for c in loaded_clips: c.close()
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass

            progress_bar.progress(1.0)
            status.success("🚀 ٹائٹن پروڈکشن گریڈ اینیمیٹڈ مووی کامیابی سے تیار ہو گئی!")
            
            # Log project to Database
            conn = get_db_connection()
            conn.execute("INSERT INTO projects (id, title, prompt, out_path, created_at) VALUES (?, ?, ?, ?, ?)",
                         (u_id, f"Project {u_id}", story[:100], out_name, time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()

            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
            return f"Error: {e}"

# ================= UI SYSTEM STYLE & DASHBOARD =================
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
    "🎬 Auto-Director Movie Studio", "💬 Electric AI Chat", "🎨 Pro Image & Canva Studio", "👤 Founders & Accounts"
])

# 1. AUTO-DIRECTOR PRO MOVIE STUDIO
with tab_movie:
    st.write("### 🎥 Titan Movie Studio (صرف کہانی درج کریں — باقی سب 100% خودکار)")
    m_script = st.text_area("کہانی یا ڈائیلاگ یہاں درج کریں (Urdu / English):", height=140, placeholder="رات کو عائشہ نے اپنے کمرے میں ایک بچے کی آواز سنی۔ دروازہ کھولا تو ایک سرخ آنکھوں والا مونسٹر کھڑا تھا، جو اسے ماں کہہ رہا تھا۔")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6 = st.columns(2)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Hollywood", "Photorealistic Horror", "Realistic HD", "3D Cartoon Pixar Style", "Anime Art"])
    with c6: sd = st.number_input("کردار کا فکسڈ سیڈ (Character Seed Lock):", value=786)

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
            with st.spinner("🎬 ٹائٹن آٹو ڈائریکٹر کریکٹر ڈی این اے لاک کر کے مووی رینڈر کر رہا ہے..."):
                v_res = create_titan_cinematic_movie(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ماسٹر ویڈیو (1080p Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# 2. ELECTRIC AI CHAT
with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        web_snippets = search_web_ddg(p) if any(k in p.lower() for k in ["search", "live", "news", "گوگل"]) else ""
        sys_p = f"You are Sglowina AI Titan, developed by founders Muhammad Essa Awan & Saba Wahid.\nContext: {web_snippets}"
        res = generate_text_pollinations(p, sys_p)
        with st.chat_message("assistant"):
            st.write(res)
            st.code(res, language="")
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

# 4. FOUNDERS & ENTERPRISE CENTER
with tab_enterprise:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders & Owners:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")
    
    with st.form("pay_proof_form"):
        st.write("#### 💳 Submit Payment Verification")
        p_name = st.text_input("Sender Name:")
        p_method = st.selectbox("Method:", ["EasyPaisa", "JazzCash"])
        p_trx = st.text_input("Transaction ID (TrxID):")
        p_amount = st.number_input("Amount (PKR):", value=1000.0)
        if st.form_submit_button("Submit TrxID 🚀"):
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO local_payments (id, sender_name, method, trx_id, amount, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (str(uuid.uuid4())[:8], p_name, p_method, p_trx.strip(), p_amount, time.strftime("%Y-%m-%d")))
                conn.commit()
                st.success("Payment proof logged successfully!")
            except: st.error("TrxID already submitted.")
            finally: conn.close()

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Titan Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
