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

# Senior Engineer Fix: Persistent Session with Optimized Retries
session = requests.Session()

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from moviepy.video.fx.all import fadein
except Exception as e:
    st.error(f"Engine Load Error: {e}")

from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. BRANDING & IDENTITY (MUHAMMAD ESSA AWAN)
# ==========================================
st.set_page_config(page_title="ES AI Master Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    h1 { 
        text-align: center; 
        background: linear-gradient(90deg, #00d4ff, #ff007a); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 80px; font-weight: 900;
    }
    .stButton>button { 
        background: linear-gradient(45deg, #00d4ff, #ff007a); 
        color: white; border-radius: 12px; height: 55px; width: 100%; 
        font-size: 18px; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

ESSA_BIO = """
مجھے محمد عیسیٰ اعوان صاحب نے بنایا، ڈیزائن کیا اور کنفیگر کیا ہے۔
محمد عیسیٰ اعوان صاحب، صوفی محمد انور رحمۃ اللہ علیہ کے صاحبزادے ہیں۔
وہ ایک انجینئر بھی ہیں، مکینیکل انجینئر بھی ہیں، فیبرکیٹر بھی ہیں، اور مختلف شعبہ جات میں دینی و اسلامی شعبہ جات میں بھی ماہر ہیں۔
وہ حضرت مولانا شیخ امیر محمد اکرم اعوان رحمۃ اللہ علیہ کے بیعت تھے اور اب حضرت مولانا شیخ امیر عبدالقدیر اعوان مدظلہ العالی کے بیعت ہیں۔
"""

def is_creator_query(q):
    patterns = [r"kisne banaya", r"who made you", r"creator", r"essa", r"awan", r"owner"]
    return any(re.search(p, q.lower(), re.IGNORECASE) for p in patterns)

# ==========================================
# 2. THE VISUAL CONTENT ISOLATOR (GPT-4 POWERED)
# ==========================================
def get_strict_visual_prompt(urdu_text, style_choice):
    """
    This function strictly forces the AI to focus ONLY on what is written.
    It removes default humans/characters if not mentioned.
    """
    try:
        # Complex instruction to the background Director AI
        director_instr = (
            f"Task: Extract the core physical subject from this Urdu text: '{urdu_text}'. "
            "Rule 1: If it mentions an object (house, stone, mountain), describe ONLY that object. "
            "Rule 2: If it mentions an animal, describe ONLY that animal. "
            "Rule 3: If no human, boy, or girl is mentioned, STERNLY EXCLUDE them from the description. "
            "Rule 4: Describe weather, lighting, and texture accurately (sunlight, shade, fire, water). "
            "Output only a detailed English prompt. No preamble."
        )
        
        encoded_instr = urllib.parse.quote(director_instr)
        url = f"https://text.pollinations.ai/{encoded_instr}?model=openai&cache=true"
        
        res = session.get(url, timeout=30)
        visual_desc = res.text if res.status_code == 200 else urdu_text
        
        # Assemble Final Prompt with Negative Enforcement
        neg_prompt = ""
        # If the Urdu text doesn't contain human keywords, force-add negative prompts
        human_keywords = ["احمد", "لڑکا", "لڑکی", "آدمی", "عورت", "بچہ", "انسان", "people", "person", "boy", "girl", "man", "woman"]
        if not any(k in urdu_text for k in human_keywords):
            neg_prompt = ", no humans, no people, no faces, no boys, no girls"

        return f"{style_choice} style, {visual_desc}{neg_prompt}, highly detailed cinematic 4k, realistic texture, masterpiece"
    except:
        return f"{style_choice} style, {urdu_text}, masterpiece, 8k"

# ==========================================
# 3. MOVIE ENGINE v27.0 (STRICT CONTENT MATCH)
# ==========================================
def create_accurate_movie(story, voice_gen, ratio, style):
    u_id = str(uuid.uuid4())[:8]
    status = st.empty()
    
    try:
        # Step 1: Voice
        status.info("🎙️ آواز تیار کی جا رہی ہے...")
        v_code = "ur-PK-UzmaNeural" if voice_gen == "Female" else "ur-PK-AsadNeural"
        audio_file = f"{u_id}_v.mp3"
        async def gv(): await edge_tts.Communicate(story, v_code).save(audio_file)
        asyncio.run(gv())
        voice_audio = AudioFileClip(audio_file)

        # Step 2: Dimensions
        res_map = {"YouTube (16:9)": (1280, 720), "TikTok/Reels (9:16)": (720, 1280), "Instagram (1:1)": (720, 720)}
        w, h = res_map[ratio]

        # Step 3: Sentence Split
        sentences = [s.strip() for s in re.split(r'[۔.!]', story) if len(s.strip()) > 5]
        clips = []
        dur_per = voice_audio.duration / len(sentences)

        # Step 4: Strict Scene Generation
        for i, scene in enumerate(sentences):
            status.info(f"🖼️ منظر {i+1} کی پہچان ہو رہی ہے: {scene[:30]}...")
            
            # Use the Content Isolator to get a specific prompt
            strict_prompt = get_strict_visual_prompt(scene, style)
            
            img_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(strict_prompt)}?width={w}&height={h}&seed={random.randint(1,999999)}&nologo=true"
            img_path = f"{u_id}_{i}.jpg"
            
            r = session.get(img_url, timeout=60)
            if r.status_code == 200:
                with open(img_path, "wb") as f: f.write(r.content)
                # Cleanup & Playback Fix
                img = Image.open(img_path).convert("RGB")
                img.save(img_path, "JPEG")
                
                clip = ImageClip(img_path).set_duration(dur_per).set_fps(24)
                clip = clip.resize(newsize=(w, h))
                # Cinematic Motion
                clip = clip.resize(lambda t: 1.1 - 0.06 * (t/dur_per)).set_position('center')
                clips.append(fadein(clip, 0.4))

        if not clips: raise ValueError("مناظر جنریٹ نہیں ہوسکے۔")

        # Step 5: Rendering
        status.info("⚙️ ویڈیو فائل تیار ہو رہی ہے...")
        final_video = concatenate_videoclips(clips, method="compose").set_audio(voice_audio)
        out_name = f"ES_AI_{u_id}.mp4"
        
        final_video.write_videofile(
            out_name, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            preset="medium", 
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        
        # Cleanup
        for i in range(len(sentences)):
            p = f"{u_id}_{i}.jpg"
            if os.path.exists(p): os.remove(p)
        
        status.success("✅ ویڈیو اسکرپٹ کے عین مطابق تیار ہے!")
        return out_name
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown("<h1>ES AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#00d4ff; font-weight:bold; letter-spacing:5px;'>PRECISION CONTENT STUDIO</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Chat", "🎙️ Voice", "🎬 Pro Movie Studio"])

with tab1:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Hukum karein Essa bhai..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        res = ESSA_BIO if is_creator_query(p) else session.get(f"https://text.pollinations.ai/{urllib.parse.quote(p)}?model=openai&cache=true").text
        with st.chat_message("assistant"):
            st.write(res); st.session_state.messages.append({"role": "assistant", "content": res})

with tab3:
    st.header("🎬 Pro Movie Studio v27.0")
    st.write("یہ انجن اسکرپٹ کے ایک ایک لفظ کی شناخت کر کے تصویر بناتا ہے۔")
    m_script = st.text_area("کہانی یہاں لکھیں:", height=150, placeholder="مثال: پہاڑوں کے پیچھے سورج ڈوب رہا ہے اور بادل سرخ ہو رہے ہیں۔")
    c1, c2, c3 = st.columns(3)
    with c1: mv = st.selectbox("Voice:", ["Male", "Female"])
    with c2: mr = st.selectbox("Format:", ["YouTube (16:9)", "TikTok/Reels (9:16)", "Instagram (1:1)"])
    with c3: ms = st.selectbox("Style:", ["Realistic", "Cinematic", "3D Cartoon", "Anime", "Sketch"])

    if st.button("🚀 Generate Accurate Video"):
        if m_script:
            video = create_accurate_movie(m_script, mv, mr, ms)
            if "mp4" in video:
                st.video(video)
                with open(video, "rb") as f: st.download_button("Download Full HD", f, file_name=video)
            else: st.error(video)

st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>ES AI Studio v27.0 | Word Recognition Engine | Muhammad Essa Awan</p>", unsafe_allow_html=True)
