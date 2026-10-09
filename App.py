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
import json

headers_browser = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
session = requests.Session()
session.headers.update(headers_browser)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    MOVIEPY_AVAILABLE = True
except Exception as e:
    MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

st.set_page_config(page_title="Sglowina AI - Enterprise Studio", layout="wide", page_icon="🎬")

if "enable_bg_music" not in st.session_state: st.session_state.enable_bg_music = True
if "msgs" not in st.session_state: st.session_state.msgs = []

render_semaphore = threading.Semaphore(value=1)

def make_even(val):
    return int(val) if int(val) % 2 == 0 else int(val) + 1

# ================= AI AUTO-DIRECTOR & CHARACTER DNA ENGINE =================
def auto_direct_story(story_text, chosen_style):
    """
    Analyzes Urdu story, automatically identifies characters, builds their persistent visual DNA,
    and breaks the story into clean, single-frame cinematic English scene prompts.
    Zero English typing required from the user!
    """
    system_prompt = (
        "You are an expert Hollywood AI Film Director and Prompt Engineer. "
        "Analyze the provided Urdu story and return a clean JSON object. "
        "1. Identify every character and establish a consistent, highly detailed 'Visual DNA' for each "
        "(exact clothing, colors, age, facial features, hair, skin tone, accessories). "
        "2. Break the story down into 2 to 5 consecutive scenes. "
        "3. For each scene, provide: "
        "'urdu_sentence': The exact Urdu sentence to be spoken, "
        "'visual_prompt': A rich English cinematic prompt for Flux AI that explicitly inserts the visual DNA "
        "of characters appearing in this scene. Strictly enforce: single continuous camera shot, photorealistic, "
        "NO split screen, NO multi-panel collage, NO character sheet, 8k resolution. "
        "Output ONLY valid JSON in this exact structure: "
        '{"scenes": [{"urdu_sentence": "...", "visual_prompt": "..."}]}'
    )

    try:
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Style: {chosen_style}\nUrdu Story:\n{story_text}"}
            ],
            "model": "openai-fast",
            "jsonMode": True
        }
        res = requests.post("https://gen.pollinations.ai/v1/chat/completions", json=payload, headers={"Content-Type": "application/json"}, timeout=25)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            # Clean possible markdown wrapping
            clean_json = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            data = json.loads(clean_json)
            if "scenes" in data and len(data["scenes"]) > 0:
                return data["scenes"]
    except Exception as e:
        pass

    # Robust Fallback if LLM fails: parse sentences manually
    raw_sentences = [s.strip() for s in re.split(r'[۔\n.!|?؛;]', story_text) if len(s.strip()) > 3]
    if not raw_sentences: raw_sentences = [story_text]
    fallback_scenes = []
    for s in raw_sentences:
        fallback_scenes.append({
            "urdu_sentence": s,
            "visual_prompt": f"A cinematic single camera frame depicting: {s}, visual style: {chosen_style}, highly detailed, sharp focus, strictly NO collage, NO split screen, 8k resolution"
        })
    return fallback_scenes

def apply_color_lut_harmony(img_path):
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im = ImageEnhance.Sharpness(im).enhance(1.20)
            im = ImageEnhance.Contrast(im).enhance(1.08)
            im.save(img_path, "PNG")
    except: pass

def get_cached_bg_music(is_horror=True):
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

# ================= EDGE-TTS VOICE ENGINE =================
def save_audio_safe(text, voice, rate, pitch, filename):
    async def _tts_exec():
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await com.save(filename)
    try:
        asyncio.run(_tts_exec())
        return os.path.exists(filename) and os.path.getsize(filename) > 300
    except:
        return False

# ================= SMOOTH CINEMATIC CAMERA MOTION =================
def render_cinematic_motion_clip(img_path, audio_path, out_clip_path, w, h, motion="Dolly In"):
    apply_color_lut_harmony(img_path)
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
    except Exception as e:
        if os.path.exists(temp_scaled): os.remove(temp_scaled)
        return False

# ================= 100% AUTOMATED DIRECTOR MASTER PIPELINE =================
def create_cinematic_v40(story, voice_gen, rate_val, pitch_val, ratio, style, seed, enable_bg_music=True):
    if not MOVIEPY_AVAILABLE: return "MoviePy library missing."
    u_id = str(uuid.uuid4())[:8]

    with render_semaphore:
        progress_bar = st.progress(0.0)
        status = st.empty()

        # Step 1: AI Director automatically extracts characters & builds consistent DNA prompts
        status.info("🧠 AI ڈائریکٹر کہانی کا تجزیہ کر رہا ہے اور خودکار 'کریکٹر ڈی این اے' لاک کر رہا ہے...")
        directed_scenes = auto_direct_story(story, style)
        total_scenes = len(directed_scenes)

        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map.get(ratio, (1280, 720))
        w, h = make_even(w), make_even(h)

        scene_clips = []
        temp_files_to_clean = []

        try:
            for idx, sc in enumerate(directed_scenes):
                urdu_line = sc.get("urdu_sentence", "")
                flux_prompt = sc.get("visual_prompt", "")
                
                status.info(f"🎬 منظر {idx + 1} از {total_scenes}: آواز اور مستقل کردار کا 4K فریم تیار ہو رہا ہے...")
                progress_bar.progress((idx / total_scenes) * 0.8)

                # 1. Synthesize audio
                sub_audio = f"a_{u_id}_{idx}.mp3"
                if not save_audio_safe(urdu_line, voice_gen, rate_val, pitch_val, sub_audio):
                    continue
                temp_files_to_clean.append(sub_audio)

                # 2. Generate Flux Image with LOCKED SEED & Persistent Character DNA
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

                # 3. Dynamic Camera Motion
                clip_mp4 = f"clip_{u_id}_{idx}.mp4"
                temp_files_to_clean.append(clip_mp4)
                
                motion_type = "Dolly In" if idx % 2 == 0 else "Pan Left"
                if render_cinematic_motion_clip(img_p, sub_audio, clip_mp4, w, h, motion=motion_type):
                    scene_clips.append(VideoFileClip(clip_mp4))

            if not scene_clips: raise Exception("کوئی منظر رینڈر نہیں ہو سکا۔")

            progress_bar.progress(0.85)
            status.info("🎞️ مووی کلپس جوڑے جا رہے ہیں اور بیک گراؤنڈ میوزک سنک ہو رہا ہے...")

            final_video = concatenate_videoclips(scene_clips, method="compose")

            if enable_bg_music:
                bg_m = get_cached_bg_music(is_horror=True)
                if bg_m and os.path.exists(bg_m):
                    try:
                        bg_track = AudioFileClip(bg_m).volumex(0.04).set_duration(final_video.duration)
                        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_track]))
                    except: pass

            out_name = f"Sglowina_{u_id}_{int(time.time())}.mp4"
            final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)

            final_video.close()
            for c in scene_clips: c.close()
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass

            progress_bar.progress(1.0)
            status.success("🚀 مستقل کرداروں والی مکمل اینیمیٹڈ مووی تیار ہو گئی!")
            return out_name
        except Exception as e:
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f): os.remove(f)
                except: pass
            return f"Error: {e}"

# ================= UI & STYLING =================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;600;800&display=swap');
    .stApp { background: #f8fafc !important; color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .glow-title { font-size: 1.3rem !important; font-weight: 700 !important; color: #1e3a8a !important; text-align: center; }
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
        <h1 class="glow-title">Sglowina AI | ایس گلووینا</h1>
    </div>
""", unsafe_allow_html=True)

tab_movie, tab_chat, tab_founders = st.tabs([
    "🎬 Auto-Director Movie Studio", "💬 Electric AI Chat", "👤 Founders & Accounts"
])

with tab_movie:
    st.write("### 🎥 Auto-Director Movie Studio (صرف کہانی درج کریں — باقی سب خودکار)")
    m_script = st.text_area("کہانی یہاں درج کریں (Urdu / English):", height=150, placeholder="رات کو عائشہ نے اپنے کمرے میں ایک بچے کی آواز سنی۔ دروازہ کھولا تو ایک سرخ آنکھوں والا مونسٹر کھڑا تھا، جو اسے ماں کہہ رہا تھا۔")

    c1, c2, c3, c4 = st.columns(4)
    with c1: mv = st.selectbox("آواز (Voice):", ["Urdu Male (Asad)", "Urdu Female (Uzma)", "English US Male (Guy)", "English US Female (Jenny)", "Arabic Egypt Male (Shakir)", "Persian Male (Farid)"])
    with c2: mv_rate = st.selectbox("آواز کی رفتار (Speed):", ["-10% (Slow)", "+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)"])
    with c3: mv_pitch = st.selectbox("آواز کا لہجہ (Pitch):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with c4: mr = st.selectbox("سائز (Format):", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])

    c5, c6 = st.columns(2)
    with c5: ms = st.selectbox("اسٹائل (Style):", ["Photorealistic Horror", "Realistic HD", "Cinematic Hollywood", "3D Cartoon", "Anime Art"])
    with c6: sd = st.number_input("فکسڈ سیڈ (Character Seed Lock):", value=786)

    voice_map = {
        "Urdu Male (Asad)": "ur-PK-AsadNeural", "Urdu Female (Uzma)": "ur-PK-UzmaNeural",
        "English US Male (Guy)": "en-US-GuyNeural", "English US Female (Jenny)": "en-US-JennyNeural",
        "Arabic Egypt Male (Shakir)": "ar-EG-ShakirNeural", "Persian Male (Farid)": "fa-IR-FaridNeural"
    }
    pitch_map = {"Normal (نارمل)": "+0Hz", "Deep (بھاری آواز)": "-15Hz", "Very Deep (موٹی آواز)": "-28Hz"}
    active_voice = voice_map.get(mv, "ur-PK-AsadNeural")
    rate_val = mv_rate.split(" ")[0]
    pitch_val = pitch_map.get(mv_pitch, "+0Hz")

    if st.button("Generate Master Movie 🚀", use_container_width=True):
        if not m_script.strip(): st.error("پہلے کہانی درج کریں!")
        else:
            with st.spinner("🎬 AI ڈائریکٹر خود کرداروں کا ڈی این اے لاک کر کے مووی بنا رہا ہے..."):
                v_res = create_cinematic_v40(
                    m_script, active_voice, rate_val, pitch_val, mr, ms, int(sd),
                    enable_bg_music=st.session_state.enable_bg_music
                )
            if v_res.endswith(".mp4") and os.path.exists(v_res):
                st.video(v_res)
                st.download_button("ڈاؤنلوڈ ویڈیو (Full HD)", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

with tab_chat:
    st.write("### 💬 Sglowina Intelligence Dashboard")
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you today?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        sys_p = f"You are Sglowina AI, developed by founders Muhammad Essa Awan & Saba Wahid."
        res = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(sys_p + ' ' + p)}?model=openai").text
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.msgs.append({"role": "assistant", "content": res})

with tab_founders:
    st.write("### 👤 فاؤنڈرز اور اکاؤنٹ تفصیلات")
    st.info("🏆 **Founders:** Muhammad Essa Awan & Saba Wahid")
    st.markdown("---")
    st.write("### 📱 پاکستانی لوکل پیمنٹ اکاؤنٹس")
    st.write("💚 **EasyPaisa Account:** Saba Wahid | **03086834020**\n\n❤️ **JazzCash Account:** Ayisha bi bi | **03240755475**")

st.markdown("<p style='text-align: center; font-weight: bold; padding-top: 25px; color: #475569;'>Sglowina AI Enterprise | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
