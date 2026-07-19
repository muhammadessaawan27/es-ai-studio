import streamlit as st
import asyncio
import edge_tts
import requests
import urllib.parse
import os
import time
import re
import uuid
import random
from PIL import Image, ImageDraw, ImageFont
import io
import threading
import gc
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. INDUSTRIAL STABILITY & LOAD BALANCING
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except Exception:
    pass

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. EXECUTIVE UI (MUHAMMAD ESSA AWAN & SABA WAHID)
# ==========================================
st.set_page_config(page_title="Sglowina AI - Official V1.2", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;500;700&display=swap');
    
    .stApp { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    .executive-header {
        text-align: center; 
        padding: 10px; 
        border-bottom: 1px solid #e2e8f0; 
        margin-bottom: 15px; 
        color: #000000 !important;
    }
    
    .main-names { 
        font-size: 1.5rem; 
        font-weight: 800; 
        color: #000000 !important; 
    }
    
    .title-tag { 
        font-size: 0.9rem; 
        font-weight: bold; 
        color: #64748b !important; 
        letter-spacing: 4px; 
        text-transform: uppercase; 
    }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 20px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: #ffffff !important;
        border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spin 10s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .stButton>button { 
        background: #000000 !important; 
        color: white !important; 
        border-radius: 12px !important; 
        height: 55px; 
        width: 100%; 
        font-size: 20px; 
        font-weight: bold; 
        border: none; 
    }
    
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #e2e8f0; 
    }
    [data-testid="stSidebar"] * { 
        color: #000000 !important; 
        font-weight: bold !important; 
    }
    
    div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.3s ease !important;
    }
    div[data-baseweb="textarea"] textarea:focus, div[data-baseweb="input"] input:focus {
        border-color: #00d4ff !important;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.2) !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="textarea"] textarea::placeholder, div[data-baseweb="input"] input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""<div class="executive-header"><div class="main-names">Muhammad Essa Awan & Saba Wahid</div>
    <div class="title-tag">Founders & CEOs | SGLOWINA AI OFFICIAL STUDIO</div></div>""", unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="circular-s">S</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY & ISLAMIC POLICY ENGINE
# ==========================================
SGLOWINA_BIO = """
Sglowina AI is proudly developed by the Sglowina Team.
Founders & CEOs: Muhammad Essa Awan & Saba Wahid.
Saba Wahid is the Founder and CEO. Muhammad Essa Awan is the COO and the lead visionary.
Muhammad Essa Awan is the spouse of Saba Wahid. (Official Version 1.2 Release).
"""

def apply_islamic_visual_logic(text):
    holy_keywords = ["نبی", "صحابی", "ولی اللہ", "امام", "Prophet", "Sahaba", "Wali Allah", "Buzurg"]
    islamic_keywords = ["مسلم", "اسلام", "تاریخ", "Muslim", "Islamic", "قبر", "عذاب", "آخرت", "نماز", "دعا", "مسجد", "موت", "Grave", "Punishment of Grave", "Deen"]
    village_keywords = ["دیہات", "دیہاتی", "پنڈ", "گاؤں", "Village", "Rural", "Fields", "Desi"]
    
    is_holy = any(k in text for k in holy_keywords)
    if is_holy:
        return ", STRICTLY NO FACE, person represented with bright white Noorani light, back view only, extremely respectful, historical context"
    
    is_islamic = any(k in text for k in islamic_keywords)
    if is_islamic:
        return ", traditional modest Muslim clothing, long robes, white turbans, historical authentic Islamic appearance, strictly no modern Western clothing, respectful facial hair, dignified posture"
        
    is_village = any(k in text for k in village_keywords)
    if is_village:
        return ", authentic rustic traditional village environment, mud houses, farming fields, South Asian rural setting, traditional simple clothing, organic background"
        
    return ""

def translate_ur_to_en(text):
    if not text or not text.strip():
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'ur',
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        res = session.get(url, params=params, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            translated = "".join([part[0] for part in json_data[0] if part and part[0]])
            if translated.strip():
                return translated.strip()
    except Exception:
        pass
    return text

def get_titan_prompt(text, style, char_desc="", scene_desc=""):
    shariah = apply_islamic_visual_logic(text)
    english_translation = translate_ur_to_en(text)
    
    style_details = {
        "Realistic HD": "hyperrealistic photograph, highly detailed 8k resolution, sharp focus, realistic textures, natural volumetric lighting, cinematic photography style",
        "Cinematic Film": "epic cinematic lighting, highly detailed fantasy masterpiece, majestic atmosphere, octane render, volumetric god rays, detailed beautiful environment, realistic fine textures, cinematic look",
        "3D Cartoon": "professional 3D animated character, Pixar style, highly detailed, vibrant colors, clean rendering, smooth textures",
        "Historical Epic": "historical authentic scene, epic detail, ancient historical painting style, dramatic historical atmosphere, highly detailed oil painting, fine details",
        "Rustic Village Life": "rustic rural setting, highly detailed, natural lighting, authentic organic village environment, earthy tones, mud houses, natural textures",
        "Dark Gothic / Mystery": "dark gothic fantasy, mysterious foggy atmosphere, dramatic moody lighting, highly detailed, masterpiece, dark mist"
    }
    style_prompt = style_details.get(style, "epic cinematic lighting, highly detailed masterpiece")
    
    anatomy_helper = "highly detailed face, proportional body, anatomically correct hands and fingers, perfect detailed eyes, realistic human proportions"
    
    subject_part = f"Subject: A person depicted EXACTLY as {char_desc.strip()} (depict this exact same person, face, and clothes)" if char_desc.strip() else f"Subject: {english_translation}"
    action_part = f"Action: {english_translation}" if char_desc.strip() else ""
    environment_part = f"Environment: {scene_desc.strip()}" if scene_desc.strip() else ""
    
    prompt_parts = [subject_part]
    if action_part: prompt_parts.append(action_part)
    if environment_part: prompt_parts.append(environment_part)
    prompt_parts.append(f"Style: {style_prompt}")
    prompt_parts.append(f"Details: {anatomy_helper}")
    
    return " | ".join(prompt_parts)

# ==========================================
# 4. TITAN PARALLEL MOVIE ENGINE (v40 LOGIC)
# ==========================================
def fetch_img(url):
    for attempt in range(3):
        try:
            res = session.get(url, timeout=30)
            if res.status_code == 200 and len(res.content) > 3000:
                return res.content
        except Exception:
            pass
        time.sleep(1.0)
    return None

def fetch_img_with_fallback(prompt, w, h, seed):
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true&enhance=false"
    data = fetch_img(url)
    if data:
        return data
        
    simple_prompt = prompt.split("Style:")[0].strip()
    url_simple = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(simple_prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
    data_simple = fetch_img(url_simple)
    if data_simple:
        return data_simple
        
    return None

def apply_camera_motion(clip, motion_type, duration, w, h):
    if motion_type == "Ken Burns":
        clip = clip.resize(lambda t: 1.15 + 0.10 * (t / duration)).set_position(lambda t: (int(-40 * (t / duration)), 'center'))
    elif motion_type == "Pan Left":
        clip = clip.set_position(lambda t: (int(-80 * (t / duration)), 'center'))
    elif motion_type == "Pan Right":
        clip = clip.set_position(lambda t: (int(-80 * (1.0 - (t / duration))), 'center'))
    elif motion_type == "Tilt":
        clip = clip.set_position(lambda t: ('center', int(-60 * (t / duration))))
    elif motion_type == "Dolly In":
        clip = clip.resize(lambda t: 1.0 + 0.15 * (t / duration)).set_position('center')
    elif motion_type == "Dolly Out":
        clip = clip.resize(lambda t: 1.15 - 0.15 * (t / duration)).set_position('center')
    else:
        clip = clip.resize(lambda t: 1.0 + 0.10 * (t / duration)).set_position('center')
    return clip

def save_audio_safe(story, v_code, rate, pitch, audio_f):
    for attempt in range(3):
        try:
            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(edge_tts.Communicate(story, v_code, rate=rate, pitch=pitch).save(audio_f))
                finally:
                    loop.close()

            thread = threading.Thread(target=_run)
            thread.start()
            thread.join()
            if os.path.exists(audio_f) and os.path.getsize(audio_f) > 1000:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False

def create_titan_movie_v1(story, voice, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="Smooth Camera", transition_type="Cinematic Cut", enable_watermark=True, enable_bg_music=True):
    u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
    
    # پروگریس بار کا قیام
    progress_bar = st.progress(0.0)
    status = st.empty()
    
    audio_f = f"a_{u_id}.mp3"
    bg_music_f = f"bg_{u_id}.mp3"
    generated_images = []
    has_bg_music = False
    
    try:
        progress_bar.progress(0.05)
        status.info("🎙️ Generating Voiceover Track (آڈیو جنریٹ ہو رہی ہے)...")
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        
        # آڈیو آٹو ری ٹرائے سسٹم
        audio_success = save_audio_safe(story, v_code, rate, pitch, audio_f)
        if not audio_success:
            raise Exception("Voice generation failed after multiple retries. Please check server load.")
            
        audio = AudioFileClip(audio_f)
        progress_bar.progress(0.15)
        
        if enable_bg_music:
            status.info("🎵 Downloading Background Atmosphere Music...")
            story_lower = story.lower()
            is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "بھوت", "تاریک", "ڈراؤنی", "grave", "torment", "punishment", "scary", "ghost", "dark", "death", "screaming", "blood", "bloody", "horror"])
            is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "شاہی", "تاریخ", "بہادر", "king", "queen", "throne", "palace", "empire", "warrior", "brave", "history", "castle"])
            is_peaceful = any(k in story_lower or k in story for k in ["نماز", "دعا", "مسجد", "ولی", "صبر", "سکون", "اللہ", "pray", "prayer", "mosque", "peace", "peaceful", "sad", "crying", "tears"])
            
            if is_horror:
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
            elif is_epic:
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
            elif is_peaceful:
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
            else:
                bg_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                
            try:
                res_bg = session.get(bg_url, timeout=30)
                if res_bg.status_code == 200:
                    with open(bg_music_f, 'wb') as f:
                        f.write(res_bg.content)
                    has_bg_music = True
            except:
                pass
                
        progress_bar.progress(0.20)
        
        res_map = {
            "YouTube (16:9)": (1280, 720), 
            "TikTok/Reels (9:16)": (720, 1280), 
            "Instagram (1:1)": (1024, 1024),
            "CinemaScope (21:9)": (1680, 720),
            "Standard Box (4:3)": (1024, 768)
        }
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        generated_prompts = []
        
        for i, s in enumerate(sentences):
            # پروگریس بار کا متحرک حساب کتاب
            img_progress = 0.20 + ((i / len(sentences)) * 0.60)
            progress_bar.progress(img_progress)
            
            status.info(f"🎨 Generating Scene {i+1}/{len(sentences)}...")
            prompt = get_titan_prompt(s, style, char_desc, scene_desc)
            generated_prompts.append(prompt)
            
            # ڈبل لیئرڈ ری ٹرائے سسٹم
            img_data = fetch_img_with_fallback(prompt, w, h, seed)
            img_p = f"i_{u_id}_{i}.jpg"
            generated_images.append(img_p)
            
            image_saved = False
            if img_data:
                try:
                    with Image.open(io.BytesIO(img_data)) as im:
                        im = im.convert("RGB")
                        
                        # اگر کیمرہ پین یا ٹیلٹ ہے تو امیج کو قدرے بڑا کر کے پین کیا جائے گا تاکہ بلیک بارز نہ آئیں
                        if camera_motion in ["Pan Left", "Pan Right", "Tilt", "Ken Burns"]:
                            im = im.resize((int(w * 1.15), int(h * 1.15)))
                        else:
                            im = im.resize((w, h))
                            
                        if enable_watermark:
                            draw = ImageDraw.Draw(im)
                            draw.text((im.width - 140, im.height - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                            
                        im.save(img_p, "JPEG")
                    image_saved = True
                except Exception:
                    pass
            
            if not image_saved:
                try:
                    im = Image.new("RGB", (w, h), color=(15, 23, 42))
                    if enable_watermark:
                        draw = ImageDraw.Draw(im)
                        draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                    im.save(img_p, "JPEG")
                except Exception:
                    pass
            
            # کیمرہ موشن پائپ لائن
            if camera_motion in ["Pan Left", "Pan Right", "Tilt", "Ken Burns"]:
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24).resize((int(w * 1.15), int(h * 1.15)))
            else:
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24).resize((w, h))
                
            clip = apply_camera_motion(clip, camera_motion, dur_per, w, h)
            
            # سین ٹرانزیشن پائپ لائن
            if transition_type == "Cross Fade":
                clip = clip.crossfadein(0.5)
            elif transition_type == "Blur Transition":
                clip = clip.fadein(0.4)
            elif transition_type == "Flash Transition":
                clip = clip.fadein(0.3)
            elif transition_type == "Smooth Fade":
                clip = clip.fadein(0.5)
                
            clips.append(clip)
            time.sleep(0.5)
            
        progress_bar.progress(0.85)
        status.info("🎞️ Mixing Audio & Rendering HD Video (ویڈیو رینڈر ہو رہی ہے)...")
        
        final_audio = audio
        bg_audio = None
        if has_bg_music and os.path.exists(bg_music_f):
            try:
                bg_audio = AudioFileClip(bg_music_f).volumex(0.12)
                bg_audio = bg_audio.subclip(0, audio.duration)
                final_audio = CompositeAudioClip([audio, bg_audio])
            except:
                pass
                
        final_video = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        audio.close()
        if bg_audio:
            bg_audio.close()
        final_video.close()
        
        try:
            if os.path.exists(audio_f): os.remove(audio_f)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except Exception:
            pass
            
        progress_bar.progress(1.0)
        status.success("🚀 Video Generated Successfully (ویڈیو بن چکی ہے)!")
        
        # تیار کردہ پرامپٹس کو کاپی بٹن کے ساتھ ظاہر کرنا
        st.markdown("### 📝 Generated Prompts with Copy Button")
        for idx, prompt_text in enumerate(generated_prompts):
            st.text(f"Prompt {idx+1}:")
            st.code(prompt_text, language="text")
            
        return out
    except Exception as e: 
        try:
            if os.path.exists(audio_f): os.remove(audio_f)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except: pass
        progress_bar.empty()
        return f"Error Details: {e}"
    finally:
        # کلاؤڈ سرور کو کریش سے بچانے کے لیے ریم پروسیس کا صفایا
        gc.collect()

# ==========================================
# 5. UI NAVIGATION & TOOLS
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

st.sidebar.markdown("---")
st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=True)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=True)

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = SGLOWINA_BIO if any(k in p.lower() for k in ["kisne", "who made", "owner", "essa", "saba"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    char_desc = st.text_input("Character Memory (کریکٹر کا مستقل حلیہ - مثلاً لباس، عمر، ڈکھیل):", 
                              placeholder="Example: A 30-year-old brave warrior, short black beard, wearing a traditional dark green turban and grey robe")
                              
    scene_desc = st.text_input("Scene Memory (پس منظر کا مستقل حلیہ - مثلاً مٹی کے گھر، اندھیری رات، تیز بارش):", 
                              placeholder="Example: Ancient rustic mud houses, dark rainy night, traditional old village background")
    
    mc1, mc2, mc3, mc4, mc5, mc6, mc7, mc8 = st.columns(8)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch (بھاری پن):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["Smooth Camera", "Ken Burns", "Pan Left", "Pan Right", "Tilt", "Dolly In", "Dolly Out"])
    with mc7: transition_type = st.selectbox("Scene Transition:", ["Cinematic Cut", "Cross Fade", "Blur Transition", "Flash Transition", "Smooth Fade"])
    with mc8: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        
        pitch_map = {
            "Normal (نارمل)": "+0Hz",
            "Deep (بھاری آواز)": "-15Hz",
            "Very Deep (موٹی آواز)": "-28Hz"
        }
        pitch_val = pitch_map[mv_pitch]
        
        v_res = create_titan_movie_v1(m_script, mv, rate_val, pitch_val, mr, ms, sd, char_desc, scene_desc, camera_motion, transition_type, enable_watermark, enable_bg_music)
            
        if "mp4" in str(v_res): st.video(v_res); st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image (One per line for batch):", height=150)
    
    char_desc_img = st.text_input("Consistent Character (کریکٹر کا مستقل حلیہ):", 
                                  placeholder="Example: A young girl, blue eyes, brown braided hair, red scarf")
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic HD", "Cinematic Film", "Anime Art", "Logo Design", "3D Cartoon", "Rustic Village Life", "Historical Epic"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        dim = {
            "Square (1:1)": (1024, 1024), 
            "YouTube HD": (1280, 720), 
            "TikTok": (720, 1280),
            "CinemaScope (21:9)": (1680, 720),
            "Standard Box (4:3)": (1024, 768)
        }
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                final_p = single_p
                if char_desc_img.strip():
                    final_p = f"Character is {char_desc_img.strip()}. Action/Scene: {single_p}"
                    
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_p + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true&negative=girl,female,deformed,bad_eyes,bad_hands,blurry,modern_western_clothing,t_shirt,jeans,suit"
                st.image(url, caption=f"Prompt: {single_p[:30]}...")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.2 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
