import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
import asyncio
import streamlit as st

# ==========================================
# 0. CONFIGURATION & SECRETS
# ==========================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

# ==========================================
# 1. PROCESSING ENGINE (ROBUST & ERROR-RESILIENT)
# ==========================================
class MovieExplainerEngine:
    @staticmethod
    def verify_dependencies():
        """Check if FFmpeg and yt-dlp are accessible"""
        ffmpeg_path = shutil.which("ffmpeg")
        ytdlp_path = shutil.which("yt-dlp")
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg سسٹم میں دستیاب نہیں ہے۔ برائے مہربانی packages.txt میں ffmpeg شامل کریں۔")
        return ffmpeg_path, ytdlp_path

    @staticmethod
    def download_video_and_audio(url, output_dir, progress_bar, status_text):
        """
        Safely downloads video & extracts audio with dynamic format fallback and full stderr capture
        """
        status_text.text("⬇️ Accessing & downloading media stream...")
        progress_bar.progress(15)

        output_template = os.path.join(output_dir, "source_movie.%(ext)s")
        
        # Smart Format Selection: Prioritize 720p, fallback to best available
        format_selector = "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best"

        cmd_vid = [
            "yt-dlp",
            "--no-playlist",
            "--no-warnings",
            "--ignore-errors",
            "-f", format_selector,
            "--merge-output-format", "mp4",
            "-o", output_template,
            url
        ]

        result = subprocess.run(cmd_vid, capture_output=True, text=True)
        
        if result.returncode != 0:
            err_msg = result.stderr.strip() or result.stdout.strip() or "نامعلوم خرابی (Unknown Error)"
            raise RuntimeError(f"yt-dlp Download Failed:\n{err_msg}")

        # Locate the downloaded file
        downloaded_video = None
        for f in os.listdir(output_dir):
            if f.startswith("source_movie."):
                downloaded_video = os.path.join(output_dir, f)
                break

        if not downloaded_video or not os.path.exists(downloaded_video):
            raise RuntimeError(f"ویڈیو ڈاؤن لوڈ مکمل نہیں ہو سکی۔ yt-dlp تفصیلات:\n{result.stderr}")

        # Extract lightweight 16kHz audio for Whisper transcription
        status_text.text("🎧 Extracting audio track for AI transcription...")
        progress_bar.progress(35)
        audio_output = os.path.join(output_dir, "audio_speech.mp3")

        cmd_aud = [
            "ffmpeg", "-y", "-i", downloaded_video,
            "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
            audio_output
        ]
        res_aud = subprocess.run(cmd_aud, capture_output=True, text=True)
        if res_aud.returncode != 0:
            raise RuntimeError(f"FFmpeg آڈیو نکالنے میں ناکام رہا:\n{res_aud.stderr}")

        return downloaded_video, audio_output

    @staticmethod
    def transcribe_audio(audio_path, progress_bar, status_text):
        status_text.text("📝 Transcribing story dialogues with timestamps...")
        progress_bar.progress(50)

        if GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            with open(audio_path, "rb") as file:
                res = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3"
                )
            return res.text
        elif OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(audio_path, "rb") as file:
                res = client.audio.transcriptions.create(
                    file=file,
                    model="whisper-1"
                )
            return res.text
        return "An engaging movie story with deep conflicts and dramatic twists."

    @staticmethod
    def generate_story_narration(transcript, target_duration, language, voice_style):
        prompt = f"""
        You are an elite Movie Explainer & Film Critic.
        Language: {language}
        Target Duration: {target_duration}
        Voice Style: {voice_style}

        Analyze this movie transcript and generate:
        1. Catchy YouTube Title
        2. Viral Hashtags
        3. Full original narration script (Transformative cinematic recap)
        4. Scene cut timestamps list (in seconds)

        Transcript excerpt:
        \"\"\"{transcript[:7000]}\"\"\"

        Respond in valid JSON format:
        {{
            "seo_title": "Catchy Viral Title",
            "seo_hashtags": "#MovieExplained #StoryRecap #FilmReview",
            "narration_script": "Full original story commentary in {language}...",
            "timeline_segments": [
                {{"start": 10, "end": 40}},
                {{"start": 120, "end": 160}},
                {{"start": 250, "end": 290}}
            ]
        }}
        """
        if OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        elif GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)

        return {
            "seo_title": f"Shocking Movie Explained in {language}",
            "seo_hashtags": "#MovieRecap #StoryExplained",
            "narration_script": "کہانی کی شروعات ایک پراسرار واقعے سے ہوتی ہے جو سب کچھ بدل کر رکھ دیتا ہے۔",
            "timeline_segments": [{"start": 0, "end": 45}]
        }

    @staticmethod
    async def generate_voiceover(text, output_file, language, gender, voice_style):
        import edge_tts
        if language in ["اردو", "Roman Urdu"]:
            voice = "ur-PK-AsadNeural" if gender == "Male" else "ur-PK-UzmaNeural"
        elif language == "Hindi":
            voice = "hi-IN-MadhurNeural" if gender == "Male" else "hi-IN-SwaraNeural"
        else:
            voice = "en-US-ChristopherNeural" if gender == "Male" else "en-US-AriaNeural"

        # 10% Slow and Deep Voice
        rate = "-10%"
        pitch = "-8Hz" if "Dramatic" in voice_style or "Cinematic" in voice_style else "+0Hz"

        comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await comm.save(output_file)

    @staticmethod
    def create_subtitles(script, output_srt):
        words = script.split()
        chunk = 8
        lines = [" ".join(words[i:i+chunk]) for i in range(0, len(words), chunk)]
        with open(output_srt, "w", encoding="utf-8") as f:
            for idx, line in enumerate(lines, 1):
                start = time.strftime('%H:%M:%S,000', time.gmtime((idx-1)*4))
                end = time.strftime('%H:%M:%S,000', time.gmtime(idx*4))
                f.write(f"{idx}\n{start} --> {end}\n{line}\n\n")

    @staticmethod
    def render_video(video_path, tts_audio, segments, output_mp4, progress_bar, status_text):
        status_text.text("🎞️ Merging scenes and AI narration with FFmpeg...")
        progress_bar.progress(85)
        temp_dir = os.path.dirname(output_mp4)
        concat_txt = os.path.join(temp_dir, "concat.txt")
        clips = []

        for i, seg in enumerate(segments[:8]):
            start = seg.get("start", i * 30)
            end = seg.get("end", start + 25)
            dur = max(5, end - start)
            seg_file = os.path.join(temp_dir, f"clip_{i}.mp4")
            cmd = [
                "ffmpeg", "-y", "-ss", str(start), "-i", video_path,
                "-t", str(dur),
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-an", "-c:v", "libx264", "-preset", "ultrafast", seg_file
            ]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(seg_file):
                clips.append(seg_file)

        with open(concat_txt, "w") as f:
            for c in clips:
                f.write(f"file '{c}'\n")

        cmd_final = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_txt,
            "-i", tts_audio,
            "-c:v", "libx264", "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", "-pix_fmt", "yuv420p",
            output_mp4
        ]
        res = subprocess.run(cmd_final, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg Rendering Error:\n{res.stderr}")

# ==========================================
# 2. UI LAYOUT
# ==========================================
def render_explainer_studio():
    st.markdown("""
    <div style="background:#1E293B; padding:20px; border-radius:10px; border-left:6px solid #F43F5E; margin-bottom:20px;">
        <h2 style="color:#F43F5E; margin:0;">🎬 AI Movie Explainer Studio</h2>
        <p style="color:#94A3B8; margin:5px 0 0 0;">Transform Full Movies into 10–20 Min Explanations with Cinematic Voice & SEO.</p>
    </div>
    <div style="background:#18181B; padding:12px; border-radius:8px; border:1px solid #3F3F46; color:#A1A1AA; font-size:13px; margin-bottom:20px;">
        ⚖️ <strong>Notice:</strong> Transformative commentary and recap format help create original explanatory content.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.subheader("1. Video Source")
        src_type = st.radio("Source Type", ["Video URL (YouTube/Direct)", "Upload File"], horizontal=True)
        url_input = st.text_input("Paste Movie URL") if src_type == "Video URL (YouTube/Direct)" else ""
        file_input = st.file_uploader("Upload Video", type=["mp4", "mkv"]) if src_type == "Upload File" else None

    with c2:
        st.subheader("2. AI Settings")
        duration = st.selectbox("Target Duration", ["10 Minutes", "15 Minutes", "20 Minutes", "Custom"])
        lang = st.selectbox("Language", ["اردو", "English", "Hindi", "Roman Urdu"])
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            voice_gender = st.selectbox("Voice", ["Male", "Female"])
        with col_v2:
            voice_style = st.selectbox("Voice Style", ["Dramatic (10% Deep & Slow)", "Cinematic", "Normal"])

    st.markdown("---")

    if st.button("🎬 CREATE MOVIE EXPLAINER", type="primary", use_container_width=True):
        if not url_input and not file_input:
            st.error("⚠️ Please provide a video link or upload a file!")
            return

        p_bar = st.progress(5)
        status = st.empty()
        temp_dir = tempfile.mkdtemp()

        try:
            # 0. Check Environment Dependencies
            MovieExplainerEngine.verify_dependencies()

            # 1. Download Video & Extract Audio
            if url_input:
                src_video, audio_f = MovieExplainerEngine.download_video_and_audio(url_input, temp_dir, p_bar, status)
            else:
                src_video = os.path.join(temp_dir, file_input.name)
                with open(src_video, "wb") as f:
                    f.write(file_input.getbuffer())
                audio_f = os.path.join(temp_dir, "audio_speech.mp3")
                subprocess.run(["ffmpeg", "-y", "-i", src_video, "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", audio_f], check=True)

            # 2. Transcribe
            transcript = MovieExplainerEngine.transcribe_audio(audio_f, p_bar, status)

            # 3. Generate Story & Script
            status.text("🧠 Generating story narration & SEO tags...")
            p_bar.progress(65)
            data = MovieExplainerEngine.generate_story_narration(transcript, duration, lang, voice_style)

            # 4. Generate AI Voice (Edge-TTS)
            status.text("🎙️ Generating AI voiceover (10% Deep & Cinematic)...")
            p_bar.progress(75)
            tts_audio = os.path.join(temp_dir, "narration.mp3")
            asyncio.run(MovieExplainerEngine.generate_voiceover(data["narration_script"], tts_audio, lang, voice_gender, voice_style))

            # 5. Subtitles & Render Video
            srt_f = os.path.join(temp_dir, "subtitles.srt")
            MovieExplainerEngine.create_subtitles(data["narration_script"], srt_f)

            out_video = os.path.join(temp_dir, "final_explainer.mp4")
            MovieExplainerEngine.render_video(src_video, tts_audio, data.get("timeline_segments", []), out_video, p_bar, status)

            p_bar.progress(100)
            status.text("✅ Completed Successfully!")
            st.balloons()

            # Output UI
            st.success("🎉 Movie Explainer is Ready!")
            res1, res2 = st.columns([1.5, 1])
            with res1:
                st.video(out_video)
                with open(out_video, "rb") as f:
                    st.download_button("⬇️ Download Final Video (MP4)", f, file_name="Movie_Explainer.mp4", mime="video/mp4", use_container_width=True)
            with res2:
                with open(srt_f, "rb") as f:
                    st.download_button("⬇️ Download Subtitles (SRT)", f, file_name="subtitles.srt", mime="text/plain", use_container_width=True)
                st.markdown(f"**🔥 Title:** `{data.get('seo_title')}`")
                st.markdown(f"**🏷️ Hashtags:** `{data.get('seo_hashtags')}`")

            with st.expander("📖 View Full AI Script (کہانی پڑھیں)", expanded=True):
                st.text_area("Full Narration Script", data.get("narration_script"), height=200)

        except Exception as e:
            st.error("❌ خرابی پیش آئی ہے:")
            st.code(str(e), language="text")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

# ==========================================
# 3. MAIN RUNNER
# ==========================================
def main():
    st.set_page_config(page_title="Sglowina AI Studio", page_icon="🎬", layout="wide")
    st.sidebar.title("⚡ Navigation")
    mode = st.sidebar.radio("Modules", ["🎬 AI Movie Explainer Studio", "🎙️ Other Studio Tools"])
    
    if mode == "🎬 AI Movie Explainer Studio":
        render_explainer_studio()
    else:
        st.info("Other AI features are operational.")

if __name__ == "__main__":
    main()
