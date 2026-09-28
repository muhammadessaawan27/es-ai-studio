import os
import subprocess
import asyncio
import streamlit as st
import speech_recognition as sr
import edge_tts
from googletrans import Translator

# Page Setup
st.set_page_config(page_title="ES AI Studio - 4K Slowed & Reverb Master", layout="wide")

st.title("🎧 ES Studio: 4K Ultra HD & Slowed + Reverb Engine")
st.write("گانے اور ویڈیوز کو کاپی رائٹ فری 'Slowed + Reverb' اور 4K سنیماٹک لک میں تبدیل کریں۔")

# Sidebar Controls
st.sidebar.header("🎛️ ماسٹرنگ سیٹنگز")

# Mode Selection
engine_mode = st.sidebar.selectbox(
    "1. موڈ منتخب کریں:",
    [
        "🔥 4K Aesthetic + Slowed & Reverb (گانے اور فلمیں)",
        "⚡ 4K Crystal Clear (صرف ویڈیو کوالٹی اور ہلکا اینٹی کاپی رائٹ)",
        "🎙️ مکمل AI اردو / انگلش ڈبنگ"
    ]
)

# Resolution Selection
target_res = st.sidebar.selectbox(
    "2. ویڈیو کوالٹی اور سائز:",
    [
        "4K Ultra HD (3840x2160 - لینڈ اسکیپ)",
        "4K Ultra Shorts (2160x3840 - ٹک ٹاک / ریلز 9:16)",
        "1080p Full HD (1920x1080)"
    ]
)

# Audio Tuning for Slowed + Reverb
st.sidebar.subheader("🎵 Slowed & Reverb ایڈجسٹمنٹ")
slow_rate = st.sidebar.slider("سلو اسپیڈ اور پچ ڈراپ (Slow Factor)", min_value=0.80, max_value=0.96, value=0.88, step=0.01)
reverb_depth = st.sidebar.slider("ریورب کی گہرائی (Echo / Reverb)", min_value=30, max_value=90, value=60, step=5)
bass_boost = st.sidebar.slider("بیس بوسٹ (Bass Boost dB)", min_value=0, max_value=10, value=5)

# Video Upload
uploaded_file = st.file_uploader("ویڈیو یا گانا اپلوڈ کریں (MP4, MKV, MOV, WebM)", type=["mp4", "mkv", "mov", "webm"])

async def generate_tts(text, voice, output_audio_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_audio_path)

def process_dubbing(input_video_path, target_lang):
    st.info("🎙️ آڈیو اسکین اور AI ٹرانسلیشن جاری ہے...")
    extracted_audio = "temp_extracted.wav"
    subprocess.run(["ffmpeg", "-y", "-i", input_video_path, "-vn", "-ar", "16000", "-ac", "1", extracted_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    recognizer = sr.Recognizer()
    transcribed_text = ""
    try:
        with sr.AudioFile(extracted_audio) as source:
            audio_data = recognizer.record(source)
            transcribed_text = recognizer.recognize_google(audio_data)
    except Exception:
        transcribed_text = "Awesome action sequence sound"
    
    translator = Translator()
    dubbed_audio_file = "dubbed_voice.mp3"
    
    if target_lang == "ur":
        try:
            translated = translator.translate(transcribed_text, dest="ur").text
        except Exception:
            translated = transcribed_text
        asyncio.run(generate_tts(translated, "ur-PK-AsadNeural", dubbed_audio_file))
    else:
        try:
            translated = translator.translate(transcribed_text, dest="en").text
        except Exception:
            translated = transcribed_text
        asyncio.run(generate_tts(translated, "en-US-ChristopherNeural", dubbed_audio_file))
        
    return dubbed_audio_file

if uploaded_file is not None:
    input_path = "input_media.mp4"
    output_path = "output_4k_mastered.mp4"
    
    with open(input_path, "wb") as f:
        f.write(uploaded_file.read())
        
    st.success("✅ فائل کامیابی سے اپلوڈ ہو گئی!")
    
    if st.button("🚀 4K Slowed & Reverb پروسیسنگ شروع کریں"):
        with st.spinner("AI 4K اپ اسکیلنگ، کلر گریڈنگ اور ریورب مکسنگ کر رہا ہے..."):
            
            # --- 1. Video Filter Pipeline ---
            v_filters = []
            if "3840x2160" in target_res:
                v_filters.append("scale=3840:2160:flags=lanczos")
            elif "2160x3840" in target_res:
                v_filters.append("scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840")
            else:
                v_filters.append("scale=1920:1080:flags=lanczos")
                
            v_filters.append("unsharp=5:5:1.0:3:3:0.5")
            v_filters.append("eq=contrast=1.08:saturation=1.20:brightness=0.01")
            vf_str = ",".join(v_filters)
            
            # --- 2. Audio Filter Pipeline ---
            cmd = ["ffmpeg", "-y", "-i", input_path]
            
            if "Slowed & Reverb" in engine_mode:
                sample_rate = int(44100 * slow_rate)
                af_str = f"asetrate={sample_rate},aresample=44100,aecho=0.8:0.88:{reverb_depth}:0.4,bass=g={bass_boost}:f=110:w=0.6"
                cmd += ["-vf", vf_str, "-af", af_str, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "320k", output_path]
                
            elif "مکمل AI اردو" in engine_mode:
                dubbed_audio = process_dubbing(input_path, "ur")
                cmd += ["-i", dubbed_audio, "-map", "0:v:0", "-map", "1:a:0", "-vf", vf_str, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-shortest", output_path]
                
            else:
                af_str = "atempo=1.03,asetrate=44100*1.02,bass=g=3:f=100"
                cmd += ["-vf", vf_str, "-af", af_str, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", output_path]
            
            subprocess.run(cmd)
            
            if os.path.exists(output_path):
                st.success("🎉 آپ کا 4K Slowed & Reverb شاہکار تیار ہے!")
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 4K الٹرا ایچ ڈی ویڈیو ڈاؤنلوڈ کریں",
                        data=file,
                        file_name="4k_slowed_reverb_master.mp4",
                        mime="video/mp4"
                      )
