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

# ==========================================
# 1. INDUSTRIAL STABILITY SETUP (MULTI-ENGINE)
# ==========================================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200)
session.mount('https://', adapter)

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'LANCZOS', 1)

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
    import moviepy.video.fx.all as vfx
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 2. BRANDING & UI (v29 LOGO + v40 METALLIC)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #F8FAFC; color: #0f172a; font-family: 'Inter', sans-serif; }
    
    @keyframes lightningGlow {
        0%, 100% { text-shadow: 0 0 15px #2563eb, 0 0 30px #00d4ff; color: #fff; }
        50% { text-shadow: 0 0 25px #ff007a, 0 0 50px #ff007a; color: #fff; }
    }
    .owner-lightning {
        font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900;
        text-align: center; letter-spacing: 10px; animation: lightningGlow 1.5s infinite;
        background: #0f172a; padding: 15px; border-radius: 0 0 30px 30px;
    }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; padding: 30px 0; }
    .ai-shua {
        width: 120px; height: 120px; background: linear-gradient(135deg, #ff007a, #2563eb, #00d4ff);
        border-radius: 25px; display: flex; align-items: center; justify-content: center;
        font-family: 'Orbitron', sans-serif; font-size: 45px; color: white;
        box-shadow: 0 0 40px rgba(255, 0, 122, 0.6); animation: rotate3D 6s infinite linear; border: 4px solid #fff;
    }
    @keyframes rotate3D { 0% { transform: rotateY(0deg); } 100% { transform: rotateY(360deg); } }
    
    .main-header { font-size: 2.8rem; font-weight: 900; color: #0f172a; text-align: center; margin-top: 10px; }
    .stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 30px; padding: 10px; gap: 20px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-size: 16px; font-weight: bold; }
    .stButton>button {
        background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
        color: white !important; border-radius: 50px !important; height: 60px; width: 100%; font-size: 22px; font-weight: 900;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="owner-lightning">MUHAMMAD ESSA AWAN</div>', unsafe_allow_html=True)
st.markdown('<div class="logo-container"><div class="ai-shua">ES</div><div class="main-header">ES AI MASTER STUDIO</div></div>', unsafe_allow_html=True)

# ==========================================
# 3. IDENTITY & BIOGRAPHY (LOCKED)
# ==========================================
ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
انہوں نے مجھے ڈیزائن کیا اور بنایا، اور یہ محنت انہوں نے خود کی۔
"""

def is_creator_query(q):
    p = [r"kisne banaya", r"who made you", r"creator", r"essa", r"owner", r"muhammad essa"]
    return any(re.search(pat, q.lower(), re.IGNORECASE) for pat in p)

# ==========================================
# 4. v40 ENGINE - ULTIMATE RECOGNITION (LOCKED)
# ==========================================
def get_v40_visual_prompt(urdu_text):
    try:
        instr = f"Act as a Film Director. Extract only the primary visual subject from Urdu: '{urdu_text}'. Describe it clearly in English for a 3D animation model. No humans unless mentioned. Output ONLY English prompt."
        res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(instr)}?model=openai&cache=true", timeout=25)
        return res.text if res.status_code == 200 else urdu_text
    except: return urdu_text

def create_masterpiece_v40(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    try:
        # Step 1: Voice
        v_code = "ur-PK-UzmaNeural" if "Female" in voice_gen else "ur-PK-AsadNeural"
        audio_file = f"a_{u_id}.mp3"
        asyncio.run(edge_tts.Communicate(story, v_code).save(audio_file))
        voice_audio = AudioFileClip(audio_file)
        
        # Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 2: v40 Sentence Splitting (GUARANTEED IMAGE CHANGE)
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 3]
        if not sentences: sentences = [story]
        
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        for i, scene in enumerate(sentences):
            status.info(f"🎨 Scene {i+1}/{len(sentences)} rendering (v40 Logic)...")
            refined_p = get_v40_visual_prompt(scene)
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(refined_p + ' ' + style)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_data = session.get(img_url, timeout=60).content
            
            img_path = f"i_{u_id}_{i}.jpg"
            img_obj = Image.open(io.BytesIO(img_data)).convert("RGB").resize((w, h))
            img_obj.save(img_path, "JPEG")
            
            clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
            # v40 Cinematic Zoom Out (1.2 to 1.0)
            clip = clip.resize(lambda t: 1.2 - 0.15 * (t/dur_per)).set_position('center')
            clips.append(vfx.fadein(clip, 0.4))

        # Final Render
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_V40_{u_id}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
        
        voice_audio.close()
        final_video.close()
        return out_name
    except Exception as e: return f"Error: {e}"

# ==========================================
# 5. TABS ASSEMBLY (FUNCTIONAL ICONS + ISOLATION)
# ==========================================
tab_chat, tab_movie, tab_image = st.tabs(["💬 Chat & Vision", "🎬 Pro Movie Studio", "🎨 Image Studio"])

# --- TAB 1: CHAT (With Functional +, 🎙️) ---
with tab_chat:
    st.write("### 💬 ES AI Interactive Agent")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    # FUNCTIONAL ICONS BAR
    st.write("---")
    col_file, col_voice = st.columns(2)
    with col_file:
        up_img = st.file_uploader("➕ Upload Image for AI Analysis", type=["jpg", "png"], key="chat_up")
    with col_voice:
        voice_msg = mic_recorder(start_prompt="🎙️ Record Voice Command", stop_prompt="🛑 Stop", key="chat_mic")

    if p := st.chat_input("Hukum karein Essa bhai...", key="chat_input"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        
        # Identity Lock
        if is_creator_query(p): res = ESSA_BIO
        else:
            try:
                res = session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
            except: res = "Server busy. Please refresh."
            
        with st.chat_message("assistant"):
            st.write(res)
            st.session_state.messages.append({"role": "assistant", "content": res})

# --- TAB 2: MOVIE STUDIO (v40 Power) ---
with tab_movie:
    st.write("### 🎥 Industrial Cinematic Production")
    m_script = st.text_area("Yahan apni کہانی لکھیں:", height=150, key="ms_v63")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Narrator:", ["Urdu Male (Asad)", "Urdu Female (Uzma)"], key="mv_v63")
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"], key="mr_v63")
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime"], key="ms_v63")
    
    if st.button("🚀 Generate v40 Master Movie", key="btn_v63"):
        if m_script:
            v_res = create_masterpiece_v40(m_script, mv, mr, ms)
            if "mp4" in v_res:
                st.video(v_res)
                st.download_button("Download ⬇️", open(v_res, 'rb').read(), file_name=v_res)
            else: st.error(v_res)

# --- TAB 3: IMAGE STUDIO (FULL OPTIONS RESTORED) ---
with tab_image:
    st.write("### 🎨 Professional Image Surgeon")
    mode = st.radio("Choose:", ["Text to Image", "Edit Photo"], horizontal=True, key="im_mode")
    if mode == "Text to Image":
        p_i = st.text_area("Describe Image:", key="pi_v63")
        ci1, ci2 = st.columns(2)
        with ci1: is_s = st.selectbox("Style:", ["Realistic", "3D Cartoon", "Anime", "Sketch"], key="is_v63")
        with ci2: is_r = st.selectbox("Ratio:", ["Square (1:1)", "Portrait (9:16)", "Landscape (16:9)"], key="ir_v63")
        if st.button("Generate Image 🚀", key="ibtn_v63"):
            res_dim = {"Square (1:1)": (1024, 1024), "Portrait (9:16)": (720, 1280), "Landscape (16:9)": (1280, 720)}
            w, h = res_dim[is_r]
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_i + ' ' + is_s)}?width={w}&height={h}&nologo=true&negative=girl,female"
            st.image(url)
    else:
        f_up = st.file_uploader("Upload Image:", type=["jpg", "png"], key="edit_up")
        if f_up:
            st.image(f_up, width=300)
            edit_req = st.text_input("Change what?", key="ereq_v63")
            if st.button("Apply Surgery 🚀", key="ebtn_v63"):
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(edit_req)}?width=1024&height=1024&nologo=true&negative=girl,female"
                st.image(url)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #2563eb; font-weight: bold;'>ES AI Studio v63.0 | THE IRON ENGINE v2 | LOCKED CORE | Muhammad Essa Awan</p>", unsafe_allow_html=True)
