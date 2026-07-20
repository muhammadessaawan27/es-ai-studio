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
from PIL import Image, ImageDraw
import io
import gc

session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein, resize
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. APPROVED ELECTRIC UI (NO CHANGES)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@700&display=swap');
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 10px #2563eb, 0 0 20px #2563eb, 0 0 40px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 20px #ff007a, 0 0 40px #ff007a, 0 0 60px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 900;
        text-align: center; letter-spacing: 8px; animation: lightningGlow 1.5s infinite; margin-top: 20px;
    }
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
    .ai-shua {
        width: 110px; height: 110px; background: linear-gradient(45deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: white;
        box-shadow: 0 0 50px #ff007a, inset 0 0 20px #ffffff;
        animation: rotateShua 4s infinite linear, pulseGlow 2s infinite; border: 5px solid #fff;
    }
    @keyframes rotateShua {
        0% { transform: perspective(1000px) rotateY(0deg) rotateZ(0deg); }
        100% { transform: perspective(1000px) rotateY(360deg) rotateZ(360deg); }
    }
    @keyframes pulseGlow { 0%, 100% { box-shadow: 0 0 30px #ff007a; } 50% { box-shadow: 0 0 70px #00d4ff; } }
    .main-header { font-size: 3rem; font-weight: 900; color: #0f172a; text-align: center; text-transform: uppercase; margin-bottom: 20px; }
    .stButton>button {
        background: linear-gradient(90deg, #ff007a, #2563eb) !important;
        color: white !important; border: none !important; border-radius: 50px !important;
        height: 60px; width: 100%; font-size: 22px; font-weight: 900;
    }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 18px; }
    
    div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.3s ease !important;
    }
    div[data-baseweb="textarea"] textarea:focus, div[data-baseweb="input"] input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 10px rgba(37, 99, 235, 0.2) !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="textarea"] textarea::placeholder, div[data-baseweb="input"] input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 2. CREATOR BIO & SUBJECT EXTRACTION
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
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
    except Exception as e:
        print(f"Primary Translation Exception: {e}")
    return text

def get_visual_prompt_v40(urdu_text, style, char_desc="", scene_desc=""):
    try:
        shariah = apply_islamic_visual_logic(urdu_text)
        english_translation = translate_ur_to_en(urdu_text)
        
        style_details = {
            "Realistic HD": "hyperrealistic photograph, highly detailed 8k resolution, sharp focus, realistic textures, natural volumetric lighting, cinematic photography style",
            "Cinematic Film": "epic cinematic lighting, highly detailed fantasy masterpiece, majestic atmosphere, octane render, volumetric god rays, detailed beautiful environment, realistic fine textures, cinematic look",
            "3D Cartoon": "professional 3D animated character, Pixar style, highly detailed, vibrant colors, clean rendering, smooth textures",
            "Historical Epic": "historical authentic scene, epic detail, ancient historical painting style, dramatic historical atmosphere, highly detailed oil painting, fine details",
            "Rustic Village Life": "rustic rural setting, highly detailed, natural lighting, authentic organic village environment, earthy tones, mud houses, natural textures",
            "Dark Gothic / Mystery": "dark gothic fantasy, mysterious foggy atmosphere, dramatic moody lighting, highly detailed, masterpiece, dark mist"
        }
        style_prompt = style_details.get(style, "epic cinematic lighting, highly detailed masterpiece")
        
        prompt_parts = [f"{style_prompt} style"]
        if char_desc.strip():
            prompt_parts.append(f"character is {char_desc.strip()}. Use the same character identity in every scene, identical face, identical clothing, consistent appearance")
        if scene_desc.strip():
            prompt_parts.append(f"scene background environment of {scene_desc.strip()}, same environment, same camera style")
            
        prompt_parts.append(english_translation)
        if shariah:
            prompt_parts.append(shariah)
        prompt_parts.append("highly detailed, cinematic lighting, 8k, realistic masterpiece, vivid colors, maintain exact same character identity across all scenes")
        
        return ", ".join(prompt_parts)
    except Exception as e:
        print(f"get_visual_prompt_v40 error: {e}")
        return urdu_text

# ==========================================
# 3. MOTION MASTER ENGINE (v40)
# ==========================================
def apply_v40_motion(clip, motion_type, dur_per, w, h):
    try:
        x_max = int(w * 0.15)
        y_max = int(h * 0.15)
        
        if motion_type == "Ken Burns":
            clip = clip.resize(lambda t: 1.15 + 0.10 * (t / dur_per)).set_position(lambda t: (int(-40 * (t / dur_per)), 'center'))
        elif motion_type == "Pan Left":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: (-int(x_max * (t / dur_per)), 'center'))
        elif motion_type == "Pan Right":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: (-int(x_max * (1.0 - (t / dur_per))), 'center'))
        elif motion_type == "Tilt":
            clip = clip.resize(lambda t: 1.15).set_position(lambda t: ('center', -int(y_max * (t / dur_per))))
        elif motion_type == "Dolly In (Zoom In)":
            clip = clip.resize(lambda t: 1.0 + 0.15 * (t / dur_per)).set_position('center')
        elif motion_type == "Dolly Out (Zoom Out)":
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t / dur_per)).set_position('center')
        else:
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t / dur_per)).set_position('center')
    except Exception as e:
        print(f"Motion exception: {e}")
        clip = clip.resize(lambda t: 1.2 - 0.15 * (t / dur_per)).set_position('center')
    return clip

def fetch_img_failover(prompt, w, h, seed):
    try:
        herc_url = f"https://hercai.onrender.com/v3/text2image?prompt={urllib.parse.quote(prompt)}"
        res = session.get(herc_url, timeout=20)
        if res.status_code == 200:
            img_url = res.json().get("url")
            if img_url:
                res_img = session.get(img_url, timeout=25)
                if res_img.status_code == 200 and len(res_img.content) > 5000:
                    return res_img.content
    except Exception as e:
        print(f"Hercai fetch exception: {e}")

    try:
        poll_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
        res = session.get(poll_url, timeout=25)
        if res.status_code == 200 and len(res.content) > 5000:
            return res.content
    except Exception as e:
        print(f"Pollinations fetch exception: {e}")

    return None

def save_audio_safe(story, v_code, rate, pitch, audio_f):
    for attempt in range(2):
        try:
            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    communicate = edge_tts.Communicate(story, v_code, rate=rate, pitch=pitch)
                    loop.run_until_complete(communicate.save(audio_f))
                except Exception as e:
                    print(f"Inner edge_tts exception: {e}")
                finally:
                    loop.close()

            thread = threading.Thread(target=_run)
            thread.start()
            thread.join()
            if os.path.exists(audio_f) and os.path.getsize(audio_f) > 1000:
                return True
        except Exception as e:
            print(f"Audio save attempt {attempt+1} exception: {e}")
        time.sleep(0.2)
    return False

def create_cinematic_v40(story, voice_gen, rate, pitch, ratio, style, seed, char_desc="", scene_desc="", camera_motion="Dolly Out (Zoom Out)", enable_watermark=True, enable_bg_music=True):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    progress_bar = st.progress(0.0)
    audio_file = f"a_{u_id}.mp3"
    bg_music_f = f"bg_{u_id}.mp3"
    generated_images = []
    has_bg_music = False
    
    try:
        # Step 1: Human Voice
        progress_bar.progress(0.05)
        status.info("🎙️ Generating Voiceover Track (آڈیو جنریٹ ہو رہی ہے)...")
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        
        save_audio_success = save_audio_safe(story, v_code, rate, pitch, audio_file)
        if not save_audio_success:
            raise Exception("Voice generation failed.")
            
        voice_audio = AudioFileClip(audio_file)
        progress_bar.progress(0.15)
        
        if enable_bg_music:
            status.info("🎵 Downloading Atmospheric Classical Background Track...")
            story_lower = story.lower()
            is_horror = any(k in story_lower or k in story for k in ["قبر", "عذاب", "موت", "خوفناک", "خوف", "جن", "بھوت", "تاریک", "ڈراؤنی", "grave", "torment", "punishment", "scary", "ghost", "dark", "death", "screaming", "blood", "bloody", "horror"])
            is_epic = any(k in story_lower or k in story for k in ["بادشاہ", "تخت", "محل", "سلطنت", "جنگ", "شاہی", "تاریخ", "بہادر", "king", "queen", "throne", "palace", "empire", "warrior", "brave", "history", "castle"])
            is_peaceful = any(k in story_lower or k in story for k in ["نماز", "دعا", "مسجد", "ولی", "صبر", "سکون", "اللہ", "pray", "prayer", "mosque", "peace", "peaceful", "sad", "crying", "tears"])
            
            if is_horror:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/1/18/Beethoven_-_Moonlight_Sonata_-_1st_movement.mp3"
            elif is_epic:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/d/df/Johann_Sebastian_Bach_-_Air_on_the_G_String_-_arranged_for_piano_and_violin.mp3"
            elif is_peaceful:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/e/e6/Chopin_-_Nocturne_op._9_no._2.mp3"
            else:
                bg_url = "https://upload.wikimedia.org/wikipedia/commons/e/e6/Chopin_-_Nocturne_op._9_no._2.mp3"
                
            try:
                res_bg = session.get(bg_url, timeout=20)
                if res_bg.status_code == 200:
                    with open(bg_music_f, 'wb') as f:
                        f.write(res_bg.content)
                    has_bg_music = True
            except Exception as e:
                print(f"Background music load error: {e}")
                
        progress_bar.progress(0.20)
        
        # Dimensions
        res_map = {
            "YouTube (16:9)": (1280, 720), 
            "TikTok/Reels (9:16)": (720, 1280), 
            "Instagram (1:1)": (720, 720),
            "CinemaScope (21:9)": (1680, 720),
            "Standard Box (4:3)": (1024, 768)
        }
        w, h = res_map[ratio]

        # Step 2: Split by Sentences
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)
        generated_prompts = []

        for i, scene in enumerate(sentences):
            progress_bar.progress(0.20 + (i / len(sentences)) * 0.60)
            status.info(f"🎨 منظر {i+1} بن رہا ہے: {scene[:30]}...")
            
            # SUBJECT LOCKING LOGIC (With Sglowina Character and Scene memory layered)
            refined_p = get_visual_prompt_v40(scene, style, char_desc, scene_desc)
            generated_prompts.append(refined_p)
            
            img_data = fetch_img_failover(refined_p, w, h, seed + i)
            if not img_data:
                # v40 Style: Fallback to high-quality slate colored image on failure
                im = Image.new("RGB", (w, h), color=(30, 41, 59))
                if enable_watermark:
                    draw = ImageDraw.Draw(im)
                    draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                img_byte_arr = io.BytesIO()
                im.save(img_byte_arr, format='JPEG')
                img_data = img_byte_arr.getvalue()
            
            img_path = f"i_{u_id}_{i}.jpg"
            generated_images.append(img_path)
            
            with open(img_path, "wb") as f: 
                f.write(img_data)
            
            # Force Resize and Format Fix
            try:
                with Image.open(img_path) as img_obj:
                    img_obj = img_obj.convert("RGB").resize((w, h))
                    
                    if enable_watermark:
                        draw = ImageDraw.Draw(img_obj)
                        draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                        
                    img_obj.save(img_path, "JPEG")
            except Exception as e:
                print(f"PIL Force Resize exception: {e}")
                im = Image.new("RGB", (w, h), color=(30, 41, 59))
                if enable_watermark:
                    draw = ImageDraw.Draw(im)
                    draw.text((w - 140, h - 45), "Sglowina AI [S]", fill=(200, 200, 200))
                im.save(img_path, "JPEG")
            
            # Step 3: RELIABLE ZOOM OUT (Force Motion 1.2 to 1.0)
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # The Formula: Start big (1.2) and shrink to normal (1.0), with custom selectboxes layered
            clip = apply_v40_motion(clip, camera_motion, dur_per, w, h)
            clip = fadein(clip, 0.4)
            clips.append(clip)

        # Step 4: Final High-Stability Render
        progress_bar.progress(0.85)
        status.info("🎞️ Rendering final MP4 movie (v40 High-Stability Export)...")
        
        final_audio = voice_audio
        bg_audio = None
        if has_bg_music and os.path.exists(bg_music_f):
            try:
                bg_audio = AudioFileClip(bg_music_f).volumex(0.10)
                bg_audio = bg_audio.subclip(0, voice_audio.duration)
                final_audio = CompositeAudioClip([voice_audio, bg_audio])
            except Exception as e:
                print(f"Background mixing exception: {e}")
                
        final_video = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        out_name = f"Sglowina_{u_id}.mp4"
        
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        if bg_audio:
            bg_audio.close()
        final_video.close()
        
        # Sglowina Automatic Cleanup (Temporary Files Delete)
        try:
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except Exception as e:
            print(f"Cleanup exception: {e}")
            
        progress_bar.progress(1.0)
        status.success("🚀 Video Generated Successfully (ویڈیو بن چکی ہے)!")
        
        # Saved Projects History management
        st.session_state.project_history.append({
            "name": out_name,
            "prompts": generated_prompts,
            "story": story,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Prompt Copy Button features
        st.markdown("### 📝 Generated Prompts with Copy Button")
        for idx, prompt_text in enumerate(generated_prompts):
            st.text(f"Prompt {idx+1}:")
            st.code(prompt_text, language="text")
            if prompt_text not in st.session_state.saved_prompts:
                st.session_state.saved_prompts.append(prompt_text)
            
        st.session_state.user_credits = max(0, st.session_state.user_credits - 10)
        
        return out_name
    except Exception as e: 
        try:
            if os.path.exists(audio_file): os.remove(audio_file)
            if os.path.exists(bg_music_f): os.remove(bg_music_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except: pass
        progress_bar.empty()
        return f"Error: {e}"
    finally:
        gc.collect()

# ==========================================
# 6. UI NAVIGATION & CONTROL PANEL
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", [
    "🏠 Smart Chat", 
    "🎬 Movie Studio", 
    "🎨 Pro Image Studio",
    "👤 Enterprise Center"
])

# Sidebar Settings
st.sidebar.markdown("---")
st.sidebar.subheader("🎬 Video Settings")
enable_watermark = st.sidebar.checkbox("Enable Sglowina Watermark", value=True)
enable_bg_music = st.sidebar.checkbox("Enable Dynamic Background Music", value=True)

# Sglowina Enterprise Center (Credits display)
st.sidebar.markdown("---")
st.sidebar.subheader("👤 Sglowina Enterprise Center")
st.sidebar.write(f"Logged in as: **{st.session_state.logged_in_user}**")
st.sidebar.write(f"Credits Remaining: **{st.session_state.user_credits}** 🪙")

if menu == "🏠 Smart Chat":
    st.write("### 💬 Sglowina Intelligence Dashboard")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("How can I help you?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if any(k in p.lower() for k in ["kisne", "creator", "essa"]) else requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res.replace("ChatGPT", "Sglowina AI").replace("OpenAI", "Sglowina Team")); st.session_state.msgs.append({"role": "assistant", "content": res})

elif menu == "🎬 Movie Studio":
    st.write("### 🎥 Industrial Cinematic Production (v40 Power)")
    m_script = st.text_area("Enter Movie Script (Urdu/English):", height=150)
    
    char_desc = st.text_input("Character Memory (کریکٹر کا مستقل حلیہ - مثلاً لباس, عمر, ڈکھیل):", 
                              placeholder="Example: A 30-year-old brave warrior, short black beard, wearing a traditional dark green turban and grey robe")
                              
    scene_desc = st.text_input("Scene Memory (پس منظر کا مستقل حلیہ - مثلاً مٹی کے گھر, اندھیری رات, تیز بارش):", 
                              placeholder="Example: Ancient rustic mud houses, dark rainy night, traditional old village background")
    
    mc1, mc2, mc3 = st.columns(3)
    with mc1: mv = st.selectbox("Voice:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"])
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)", "-10% (Slow)"])
    with mc3: mv_pitch = st.selectbox("Voice Pitch (بھاری پن):", ["Normal (نارمل)", "Deep (بھاری آواز)", "Very Deep (موٹی آواز)"])
    
    mc4, mc5, mc6 = st.columns(3)
    with mc4: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)", "CinemaScope (21:9)", "Standard Box (4:3)"])
    with mc5: ms = st.selectbox("Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon", "Historical Epic", "Rustic Village Life", "Dark Gothic / Mystery"])
    with mc6: camera_motion = st.selectbox("Camera Motion:", ["Dolly Out (Zoom Out)", "Dolly In (Zoom In)", "Ken Burns", "Pan Left", "Pan Right", "Tilt"])
    
    st.markdown("---")
    sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        rate_val = mv_rate.split(" ")[0]
        
        pitch_map = {
            "Normal (نارمل)": "+0Hz",
            "Deep (بھاری آواز)": "-15Hz",
            "Very Deep (موٹی آواز)": "-28Hz"
        }
        pitch_val = pitch_map[mv_pitch]
        
        with st.spinner("🎬 Sglowina AI is generating your video with voice and motion... Please wait..."):
            v_res = create_cinematic_v40(m_script, mv, rate_val, pitch_val, mr, ms, sd, char_desc, scene_desc, camera_motion, enable_watermark, enable_bg_music)
            
        if isinstance(v_res, str) and v_res.endswith(".mp4") and os.path.exists(v_res): 
            st.video(v_res)
            st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: 
            st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    
    tab_txt, tab_img = st.tabs(["🎨 Text to Image", "📤 Image Modify & Upload"])
    
    with tab_txt:
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
                        
                    img_data = fetch_img_failover(final_p, w, h, random.randint(1,999999))
                    if img_data:
                        with Image.open(io.BytesIO(img_data)) as im:
                            st.image(im, caption=f"Prompt: {single_p[:30]}...")
                            if final_p not in st.session_state.favorites:
                                st.session_state.favorites.append(final_p)
                    else:
                        st.error(f"Image generation failed for prompt: {single_p}")

    with tab_img:
        uploaded_file = st.file_uploader("Upload Image to Modify:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Original Image", use_container_width=True)
            
        modify_prompt = st.text_input("Modification Instructions (تبدیلی کے احکامات):", placeholder="Example: Make the background dark green, add cinematic volumetric light")
        i_style_mod = st.selectbox("Modification Style:", ["Realistic HD", "Cinematic Film", "3D Cartoon"])
        
        if st.button("Modify & Re-render Image 🎨"):
            if uploaded_file and modify_prompt:
                with st.spinner("Modifying image..."):
                    img_name = translate_ur_to_en(modify_prompt)
                    img_data = fetch_img_failover(img_name, 1024, 1024, random.randint(1,999999))
                    if img_data:
                        with Image.open(io.BytesIO(img_data)) as im:
                            st.image(im, caption="Modified Masterpiece")
                    else:
                        st.error("Modification failed.")
            else:
                st.warning("Please upload an image and write instructions first.")

elif menu == "👤 Enterprise Center":
    st.write("### 👤 Sglowina Enterprise Administration Center")
    
    ent_tab_user, ent_tab_history, ent_tab_admin = st.tabs(["👤 User Profile", "📁 Project History & Prompts", "🔒 Admin Control Panel"])
    
    with ent_tab_user:
        st.write(f"#### Logged-in User Profile")
        st.info(f"User: **{st.session_state.logged_in_user}** | Allocated Credits: **{st.session_state.user_credits}** 🪙")
        st.write("Secure Session Token:")
        st.code(str(uuid.uuid5(uuid.NAMESPACE_DNS, st.session_state.logged_in_user))[:20])
        
    with ent_tab_history:
        st.write("#### 📁 Active Download Manager & Saved Projects")
        if not st.session_state.project_history:
            st.write("No projects found in this session.")
        else:
            for proj in st.session_state.project_history:
                st.write(f"🎬 **{proj['name']}** (Created: {proj['timestamp']})")
                st.write(f"Script: `{proj['story']}`")
                st.write("Saved Prompts for this video:")
                for p_text in proj['prompts']:
                    st.code(p_text, language="text")
                st.markdown("---")
                
        st.write("#### ⭐ Saved & Favorite Prompts")
        if not st.session_state.favorites:
            st.write("No saved prompts found.")
        else:
            for fav in st.session_state.favorites:
                st.code(fav, language="text")
                
    with ent_tab_admin:
        st.write("#### 🔒 Secured Admin Control Settings")
        admin_pass = st.text_input("Enter Admin Passcode:", type="password")
        if admin_pass == "786" or admin_pass == "1234":
            st.success("Access Granted!")
            st.session_state.logged_in_user = st.selectbox("Manage Account:", ["essa_awan", "saba_wahid"])
            new_credits = st.number_input("Adjust Allocated Credits:", min_value=0, max_value=10000, value=st.session_state.user_credits)
            if st.button("Apply Changes"):
                st.session_state.user_credits = new_credits
                st.success("Credits adjusted successfully!")
        else:
            st.error("Access Denied: Invalid passcode.")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.2 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
