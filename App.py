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
from PIL import Image
import io
import threading
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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
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
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Inter', sans-serif; }
    
    .executive-header {
        text-align: center; padding: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px; color: #000000;
    }
    .main-names { font-size: 1.5rem; font-weight: 800; color: #000000; }
    .title-tag { font-size: 0.9rem; font-weight: bold; color: #64748b; letter-spacing: 4px; text-transform: uppercase; }

    .logo-container { display: flex; justify-content: center; align-items: center; padding: 20px 0; }
    .circular-s {
        width: 100px; height: 100px; background: #0f172a; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: #ffffff;
        border: 3px solid #00d4ff; box-shadow: 0 0 15px rgba(0,212,255,0.3);
        animation: spin 10s infinite linear;
    }
    @keyframes spin { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }

    .stButton>button { background: #000000 !important; color: white !important; border-radius: 12px !important; height: 55px; width: 100%; font-size: 20px; font-weight: bold; border: none; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# Executive Header
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
    is_holy = any(k in text for k in holy_keywords)
    if is_holy:
        return ", STRICTLY NO FACE, person represented with bright white Noorani light, back view only, extremely respectful"
    if any(k in text for k in ["مسلم", "اسلام", "تاریخ", "Muslim", "Islamic"]):
        return ", traditional modest Muslim clothing, robes and turbans, historical environment"
    return ""

# کریکٹر کی مستقل مزاجی کو پرامپٹ میں شامل کرنے کے لیے اپ ڈیٹ
def get_titan_prompt(text, style, char_desc=""):
    shariah = apply_islamic_visual_logic(text)
    
    # اگر مستقل کریکٹر کی تفصیل دی گئی ہو تو اسے پرامپٹ کے شروع میں جوڑ دیں
    full_subject = text
    if char_desc.strip():
        full_subject = f"The main character is {char_desc.strip()}. The scene shows: {text}"
        
    try:
        instr = f"Act as a Film Director: Extract core subject from Urdu: '{full_subject}'. {shariah}. Professional 3D character animation, high detail, masterpiece. Style: {style}. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else text
    except: return text

# ==========================================
# 4. TITAN PARALLEL MOVIE ENGINE (v40 LOGIC)
# ==========================================
def fetch_img(url):
    try:
        res = session.get(url, timeout=60)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# محفوظ آڈیو جنریشن بشمول آواز کی رفتار (Voice Rate Control)
def save_audio_safe(story, v_code, rate, audio_f):
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # edge_tts میں آواز کی رفتار (rate) کو شامل کیا گیا ہے
            loop.run_until_complete(edge_tts.Communicate(story, v_code, rate=rate).save(audio_f))
        finally:
            loop.close()

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

def create_titan_movie_v1(story, voice, rate, ratio, style, seed, char_desc=""):
    u_id = f"v1_render_{str(uuid.uuid4())[:6]}"
    status = st.empty()
    audio_f = f"a_{u_id}.mp3"
    generated_images = []
    
    try:
        v_code = "ur-PK-UzmaNeural" if voice == "Uzma (Female)" else "ur-PK-AsadNeural"
        
        # آواز کی رفتار کے ساتھ آڈیو فائل بنانا
        save_audio_safe(story, v_code, rate, audio_f)
        audio = AudioFileClip(audio_f)
        
        # Dimensions Fix: Ensuring even numbers
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (1024, 1024)}
        w, h = res_map[ratio]
        
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = audio.duration / len(sentences)
        
        # ہر منظر کے پرامپٹ میں کریکٹر کا مستقل حلیہ (char_desc) بھیجا جا رہا ہے
        img_urls = [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(get_titan_prompt(s, style, char_desc))}?width={w}&height={h}&seed={seed}&nologo=true&negative=girl,female,deformed,bad hands,blurry,bad eyes,bad face,double heads" for s in sentences]

        with ThreadPoolExecutor(max_workers=20) as exe:
            for i, img_data in enumerate(exe.map(fetch_img, img_urls)):
                status.info(f"⚡ Rendering Scene {i+1}/{len(sentences)}...")
                img_p = f"i_{u_id}_{i}.jpg"
                generated_images.append(img_p)
                
                image_saved = False
                if img_data:
                    try:
                        with Image.open(io.BytesIO(img_data)) as im:
                            im.convert("RGB").resize((w, h)).save(img_p, "JPEG")
                        image_saved = True
                    except Exception:
                        pass
                
                # اگر تصویر ڈاؤن لوڈ نہ ہو پائے تو عارضی ڈارک بیک گراؤنڈ بنانا تاکہ پروجیکٹ رکے نہیں
                if not image_saved:
                    try:
                        im = Image.new("RGB", (w, h), color=(15, 23, 42))
                        im.save(img_p, "JPEG")
                    except Exception:
                        pass
                
                clip = ImageClip(img_p).set_duration(dur_per).set_fps(24)
                # v40 Locked Zoom-In: 1.0 to 1.15
                clip = clip.resize(lambda t: 1.0 + 0.15 * (t/dur_per)).set_position('center')
                clips.append(vfx.fadein(clip, 0.4))
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
        out = f"Sglowina_{u_id}.mp4"
        final_video.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        # فائل ہینڈلز بند کرنا
        audio.close()
        final_video.close()
        
        # عارضی فائلز کی آٹو صفائی (Auto-cleanup)
        try:
            if os.path.exists(audio_f): os.remove(audio_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except Exception:
            pass
            
        return out
    except Exception as e: 
        # ایرر کی صورت میں بھی عارضی فائلز ڈیلیٹ کرنا
        try:
            if os.path.exists(audio_f): os.remove(audio_f)
            for img_p in generated_images:
                if os.path.exists(img_p): os.remove(img_p)
        except: pass
        return f"Error: {e}"

# ==========================================
# 5. UI NAVIGATION & TOOLS
# ==========================================
menu = st.sidebar.radio("SGLOWINA COMMAND MENU", ["🏠 Smart Chat", "🎬 Movie Studio", "🎨 Pro Image Studio"])

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
    
    # نیا فیچر: مستقل کریکٹر کی تفصیل
    char_desc = st.text_input("Consistent Character (کریکٹر کا حلیہ - مثلاً لباس، عمر، ڈکھیل):", 
                              placeholder="Example: A 30-year-old brave warrior, short black beard, wearing a traditional dark green turban and grey robe")
    
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1: mv = st.selectbox("Voice:", ["Asad (Male)", "Uzma (Female)"])
    # نیا فیچر: آواز کی رفتار کا کنٹرول
    with mc2: mv_rate = st.selectbox("Voice Speed:", ["+0% (Normal)", "+10% (Fast)", "+20% (Very Fast)", "-10% (Slow)"])
    with mc3: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with mc4: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon"])
    with mc5: sd = st.number_input("Character Seed:", value=786)
    
    if st.button("Generate Master Movie 🚀"):
        # فیصد کی ویلیو کو درست فارمیٹ میں نکالنا
        rate_val = mv_rate.split(" ")[0]
        v_res = create_titan_movie_v1(m_script, mv, rate_val, mr, ms, sd, char_desc)
        if "mp4" in str(v_res): st.video(v_res); st.download_button("Download Full HD", open(v_res, 'rb').read(), file_name=v_res)
        else: st.error(v_res)

elif menu == "🎨 Pro Image Studio":
    st.write("### 🎨 Industrial HD Visual Studio")
    p_i = st.text_area("Describe Image (One per line for batch):", height=150)
    
    # نیا فیچر: مستقل کریکٹر کی تفصیل امیجز کے لیے بھی
    char_desc_img = st.text_input("Consistent Character (کریکٹر کا مستقل حلیہ):", 
                                  placeholder="Example: A young girl, blue eyes, brown braided hair, red scarf")
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: i_style = st.selectbox("Art Style:", ["Realistic", "Anime", "Logo Design", "3D Cartoon"])
    with ic2: i_size = st.selectbox("Resolution:", ["Square (1:1)", "YouTube HD", "TikTok"])
    with ic3: count = st.slider("Quantity:", 1, 10, 1)
    
    if st.button("Generate Titan Visuals 🚀"):
        dim = {"Square (1:1)": (1024, 1024), "YouTube HD": (1280, 720), "TikTok": (720, 1280)}
        w, h = dim[i_size]
        prompt_list = [line.strip() for line in p_i.split('\n') if line.strip()]
        for idx, single_p in enumerate(prompt_list):
            for q in range(count):
                # کریکٹر کی تفصیل کو پرامپٹ میں شامل کرنا
                final_p = single_p
                if char_desc_img.strip():
                    final_p = f"Character is {char_desc_img.strip()}. Action/Scene: {single_p}"
                    
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_p + ' ' + i_style)}?width={w}&height={h}&seed={random.randint(1,9999)}&nologo=true&negative=girl,female,deformed,bad eyes,bad hands,blurry"
                st.image(url, caption=f"Prompt: {single_p[:30]}...")

st.markdown("<p style='text-align: center; font-weight: bold; border-top: 1px solid #eee; padding-top: 20px; color: #000000;'>Sglowina AI Version 1.2 Premium | Founders: Muhammad Essa Awan & Saba Wahid</p>", unsafe_allow_html=True)
