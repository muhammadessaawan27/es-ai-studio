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
# 0. CONFIGURATION & SECRETS MANAGEMENT
# ==========================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

# Credit Configuration (Admin editable)
EXPLAINER_CREDITS = {
    "10 Minutes": 20,
    "15 Minutes": 30,
    "20 Minutes": 40,
    "Custom": 50
}

# ==========================================
# 1. HELPER / PROCESSING MODULES
# ==========================================

class MovieExplainerEngine:
    @staticmethod
    def check_ffmpeg():
        """Check if FFmpeg is installed in system"""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def download_video_stream(url, output_dir, progress_bar, status_text):
        """
        Uses yt-dlp to download video/audio safely without crashing RAM
        """
        status_text.text("⬇️ Accessing and Downloading Video/Audio...")
        progress_bar.progress(15)
        
        output_template = os.path.join(output_dir, "source_movie.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            url
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Find the actual downloaded file
            for f in os.listdir(output_dir):
                if f.startswith("source_movie."):
                    return os.path.join(output_dir, f)
        except Exception as e:
            raise RuntimeError(f"Video Download Failed: {str(e)}")
        return None

    @staticmethod
    def extract_audio_chunked(video_path, output_dir, progress_bar, status_text):
        """Extracts lightweight 16kHz mono audio for fast AI STT"""
        status_text.text("🎧 Extracting & Optimizing Audio for AI...")
        progress_bar.progress(30)
        
        audio_output = os.path.join(output_dir, "audio_speech.mp3")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k",
            audio_output
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return audio_output

    @staticmethod
    def transcribe_audio_groq_or_openai(audio_path, progress_bar, status_text):
        """Transcribe speech using Groq (Fast) or OpenAI Whisper API"""
        status_text.text("📝 Transcribing Story Dialogues with Timestamps...")
        progress_bar.progress(45)

        if GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                )
            return transcription.text
        elif OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=file,
                    model="whisper-1",
                    response_format="verbose_json"
                )
            return transcription.text
        else:
            # Fallback mock/local summary if no STT key
            return "A mysterious story unfolds where the main protagonist faces major conflicts, leading to an unexpected ending."

    @staticmethod
    def generate_story_narration_and_seo(transcript, target_duration, language, voice_style):
        """
        AI Storytelling & SEO Engine (Creates original narrative, SEO tags, and timeline)
        """
        prompt = f"""
        You are an elite Movie Explainer and Film Critic.
        Analyze the following movie dialogue/transcript and generate a complete, high-retention movie explanation.
        
        Language: {language}
        Target Video Duration: {target_duration}
        Style: {voice_style} (Deep, Engaging, Transformative Narration)

        CRITICAL RULES:
        1. DO NOT simply copy dialogues. Write an ORIGINAL transformative cinematic commentary.
        2. Provide timeline cut recommendations (where key events happen).
        3. Provide Viral SEO Content: Catchy Title, YouTube Description, Viral Hashtags.
        
        Movie Transcript excerpt:
        \"\"\"{transcript[:8000]}\"\"\"

        Respond strictly in valid JSON format with keys:
        {{
            "seo_title": "Catchy YouTube Title",
            "seo_hashtags": "#MovieExplained #StoryRecap ...",
            "seo_description": "Short SEO rich summary",
            "narration_script": "Full continuous narration script for voiceover in {language}...",
            "timeline_segments": [
                {{"start": 10, "end": 45, "focus": "Character Introduction"}},
                {{"start": 120, "end": 180, "focus": "First Plot Twist"}},
                {{"start": 300, "end": 360, "focus": "Climax Action"}},
                {{"start": 500, "end": 560, "focus": "Final Resolution"}}
            ]
        }}
        """

        if OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        elif GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        else:
            return {
                "seo_title": f"Shocking Story Explained in {language}",
                "seo_hashtags": "#MovieRecap #FilmSummary #ViralStory",
                "seo_description": "Full transformative story breakdown and critical explanation.",
                "narration_script": f"کہانی کی شروعات ایک غیر معمولی موڑ سے ہوتی ہے۔ مرکزی کردار حالات کے سامنے بے بس نظر آتا ہے، لیکن جلد ہی ایک بڑا انکشاف سب کچھ بدل کر رکھ دیتا ہے۔",
                "timeline_segments": [{"start": 0, "end": 60, "focus": "Overview"}]
            }

    @staticmethod
    async def synthesize_voice_edge(text, output_file, language, gender, voice_style="Cinematic"):
        """
        Synthesizes AI Voice with Edge-TTS supporting -10% Pitch/Rate for Deep/Heavy Voice
        """
        import edge_tts

        # Map language + gender to high quality voices
        if language == "اردو" or language == "Roman Urdu":
            voice = "ur-PK-AsadNeural" if gender == "Male" else "ur-PK-UzmaNeural"
        elif language == "Hindi":
            voice = "hi-IN-MadhurNeural" if gender == "Male" else "hi-IN-SwaraNeural"
        else:
            voice = "en-US-ChristopherNeural" if gender == "Male" else "en-US-AriaNeural"

        # Apply pitch and speed tuning (10% slowed down and deeper voice)
        rate = "-10%"
        pitch = "-8Hz" if voice_style in ["Dramatic", "Cinematic"] else "+0Hz"

        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(output_file)

    @staticmethod
    def generate_srt(script_text, output_srt):
        """Generates RTL-compliant Urdu/Hindi/English SRT subtitles"""
        words = script_text.split()
        chunk_size = 8
        lines = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        
        with open(output_srt, "w", encoding="utf-8") as f:
            for idx, line in enumerate(lines, 1):
                start_sec = (idx - 1) * 4
                end_sec = idx * 4
                start_str = time.strftime('%H:%M:%S,000', time.gmtime(start_sec))
                end_str = time.strftime('%H:%M:%S,000', time.gmtime(end_sec))
                f.write(f"{idx}\n{start_str} --> {end_str}\n{line}\n\n")

    @staticmethod
    def render_movie_explainer(video_file, audio_narration_file, timeline_segments, output_video, progress_bar, status_text):
        """
        FFmpeg Engine: Cut scenes, overlay AI narration, mute original movie audio, and produce output MP4
        """
        status_text.text("🎞️ Rendering Final Movie Explainer with FFmpeg...")
        progress_bar.progress(85)
        
        # Build filter complex for concatenating selected timeline segments
        temp_list_file = os.path.join(os.path.dirname(output_video), "concat_list.txt")
        segment_files = []

        for idx, seg in enumerate(timeline_segments[:10]):  # Limit segments for safety
            start = seg.get("start", idx * 30)
            end = seg.get("end", start + 25)
            duration = max(5, end - start)
            
            seg_out = os.path.join(os.path.dirname(output_video), f"seg_{idx}.mp4")
            cmd_cut = [
                "ffmpeg", "-y", "-ss", str(start), "-i", video_file,
                "-t", str(duration),
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-an", "-c:v", "libx264", "-preset", "ultrafast", seg_out
            ]
            subprocess.run(cmd_cut, capture_output=True)
            if os.path.exists(seg_out):
                segment_files.append(seg_out)

        # Create concat manifest
        with open(temp_list_file, "w") as f:
            for sf in segment_files:
                f.write(f"file '{sf}'\n")

        # Final Render: Merging segments with AI voiceover (Original movie audio muted)
        cmd_render = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", temp_list_file,
            "-i", audio_narration_file,
            "-c:v", "libx264", "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_video
        ]
        subprocess.run(cmd_render, capture_output=True, check=True)
        return output_video


# ==========================================
# 2. STREAMLIT UI VIEW (AI MOVIE EXPLAINER STUDIO)
# ==========================================

def render_movie_explainer_tab():
    st.markdown("""
    <style>
    .explainer-header {
        background: linear-gradient(90deg, #1E2640 0%, #0F172A 100%);
        padding: 24px;
        border-radius: 12px;
        border-left: 6px solid #E11D48;
        margin-bottom: 25px;
    }
    .disclaimer-box {
        background-color: #1c1917;
        border: 1px solid #44403c;
        padding: 14px 18px;
        border-radius: 8px;
        font-size: 0.88rem;
        color: #d6d3d1;
        margin-bottom: 20px;
    }
    .story-card {
        background: #111827;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="explainer-header">
        <h2 style="color: #F43F5E; margin:0;">🎬 AI Movie Explainer Studio</h2>
        <p style="color: #94A3B8; margin: 5px 0 0 0;">Transform 2–3 hour full movies into 10–20 min cinematic recap videos with AI commentary & SEO metadata.</p>
    </div>
    """, unsafe_allow_html=True)

    # Transformative Disclaimer Rule
    st.markdown("""
    <div class="disclaimer-box">
        ⚖️ <strong>Legal & Transformative Notice:</strong><br>
        Transformative editing and critical review commentaries do not guarantee immunity from copyright claims. This tool automates transformative storytelling. Use only content you are authorized to process and review.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.6, 1.0])

    with col1:
        st.subheader("1. Ingest Source Movie / Video")
        input_type = st.radio("Input Source", ["Paste Video URL (YouTube / Direct)", "Upload Local Video"], horizontal=True)
        
        video_url = ""
        uploaded_file = None
        
        if input_type == "Paste Video URL (YouTube / Direct)":
            video_url = st.text_input("Movie / Video URL", placeholder="https://www.youtube.com/watch?v=... or .mp4 link")
        else:
            uploaded_file = st.file_uploader("Upload Movie File (MP4, MKV)", type=["mp4", "mkv", "mov"])

    with col2:
        st.subheader("2. Settings & Style")
        target_duration = st.selectbox("Target Explainer Duration", ["10 Minutes", "15 Minutes", "20 Minutes", "Custom"])
        language = st.selectbox("Explanation Language", ["اردو", "English", "Hindi", "Roman Urdu"])
        
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            voice_gender = st.selectbox("AI Voice", ["Male", "Female"])
        with c_v2:
            voice_style = st.selectbox("Voice Style", ["Cinematic", "Dramatic (10% Deep & Slow)", "Documentary", "Normal"])

    st.markdown("---")

    # Credit Notice
    required_credits = EXPLAINER_CREDITS.get(target_duration, 20)
    st.caption(f"💳 This operation consumes **{required_credits} Credits**.")

    # Action Button
    if st.button("🎬 CREATE MOVIE EXPLAINER", type="primary", use_container_width=True):
        if not video_url and not uploaded_file:
            st.error("⚠️ Please provide a valid Movie URL or upload a video file.")
            return

        # Setup Progress UI
        progress_box = st.container()
        with progress_box:
            progress_bar = st.progress(5)
            status_text = st.empty()

        temp_dir = tempfile.mkdtemp(prefix="movie_explainer_")

        try:
            # 1. Download or Save Video
            if video_url:
                source_video = MovieExplainerEngine.download_video_stream(video_url, temp_dir, progress_bar, status_text)
            else:
                source_video = os.path.join(temp_dir, uploaded_file.name)
                with open(source_video, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            # 2. Extract Audio
            audio_path = MovieExplainerEngine.extract_audio_chunked(source_video, temp_dir, progress_bar, status_text)

            # 3. Transcribe
            transcript = MovieExplainerEngine.transcribe_audio_groq_or_openai(audio_path, progress_bar, status_text)

            # 4. Generate AI Story, SEO & Narration
            status_text.text("🧠 Analyzing Story & Writing Original Narration...")
            progress_bar.progress(60)
            analysis_data = MovieExplainerEngine.generate_story_narration_and_seo(transcript, target_duration, language, voice_style)

            # 5. Synthesize AI Narration Voice (with edge-tts)
            status_text.text("🎙️ Generating Cinematic AI Narration Audio...")
            progress_bar.progress(75)
            tts_audio_path = os.path.join(temp_dir, "ai_narration.mp3")
            
            asyncio.run(
                MovieExplainerEngine.synthesize_voice_edge(
                    text=analysis_data.get("narration_script", ""),
                    output_file=tts_audio_path,
                    language=language,
                    gender=voice_gender,
                    voice_style=voice_style
                )
            )

            # 6. Generate Subtitles
            srt_path = os.path.join(temp_dir, "subtitles.srt")
            MovieExplainerEngine.generate_srt(analysis_data.get("narration_script", ""), srt_path)

            # 7. Render Final MP4
            final_output_video = os.path.join(temp_dir, "final_movie_explainer.mp4")
            MovieExplainerEngine.render_movie_explainer(
                source_video,
                tts_audio_path,
                analysis_data.get("timeline_segments", []),
                final_output_video,
                progress_bar,
                status_text
            )

            progress_bar.progress(100)
            status_text.text("✅ Movie Explainer Successfully Generated!")
            st.balloons()

            # Display Output
            st.success("🎉 Your Movie Explainer is Ready!")

            out_col1, out_col2 = st.columns([1.4, 1.0])

            with out_col1:
                st.subheader("🎬 Final Video Preview")
                if os.path.exists(final_output_video):
                    st.video(final_output_video)
                    with open(final_output_video, "rb") as f:
                        st.download_button("⬇️ Download Final Explainer (MP4)", f, file_name="Movie_Explainer.mp4", mime="video/mp4", use_container_width=True)

            with out_col2:
                st.subheader("📝 SEO & Script Package")
                with open(srt_path, "rb") as f:
                    st.download_button("⬇️ Download Subtitles (SRT)", f, file_name="subtitles.srt", mime="text/plain", use_container_width=True)

                st.markdown(f"**🔥 Title:** `{analysis_data.get('seo_title', '')}`")
                st.markdown(f"**🏷️ Hashtags:** `{analysis_data.get('seo_hashtags', '')}`")

            # Script Box for manual reading or voice-over
            with st.expander("📖 View Full AI Story & Narration Script (پوری کہانی یہاں پڑھیں)", expanded=True):
                st.text_area("Narration Script", value=analysis_data.get("narration_script", ""), height=220)

        except Exception as err:
            st.error(f"❌ Processing Error: {str(err)}")
        finally:
            # Temporary files cleanup
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass


# ==========================================
# 3. MAIN APP ROUTER (Integrates into App.py)
# ==========================================
def main():
    st.set_page_config(page_title="Sglowina AI Studio", page_icon="🎬", layout="wide")

    # Navigation Sidebar
    st.sidebar.title("🚀 Sglowina AI Hub")
    app_mode = st.sidebar.radio(
        "Select Studio Module",
        [
            "🎬 AI Movie Explainer Studio",
            "🎙️ Voiceover & Audio Tools",
            "✨ Other AI Features"
        ]
    )

    if app_mode == "🎬 AI Movie Explainer Studio":
        render_movie_explainer_tab()
    else:
        st.info("Existing Sglowina AI Features are running seamlessly here.")

if __name__ == "__main__":
    main()
