import streamlit as st
import subprocess, shutil, re, uuid, asyncio, math
from pathlib import Path

st.set_page_config(page_title="Sglowina AI Cinematic Studio", page_icon="🎬", layout="wide")
ROOT=Path(".")
UPLOAD=ROOT/"uploads"; OUTPUT=ROOT/"rendered"
UPLOAD.mkdir(exist_ok=True); OUTPUT.mkdir(exist_ok=True)
FFMPEG=shutil.which("ffmpeg"); FFPROBE=shutil.which("ffprobe")

def ready(): return bool(FFMPEG and FFPROBE)
def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)
def duration(path):
    r=run([FFPROBE,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)])
    if r.returncode: raise RuntimeError(r.stderr[-1500:])
    return max(.1,float(r.stdout.strip()))
def split_script(text):
    # Paragraphs first, then sentences. Avoid an arbitrary 10-minute or scene-count cap.
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n",text) if p.strip()]
    scenes=[]
    for p in paragraphs:
        pieces=[s.strip() for s in re.split(r"(?<=[۔.!?؟])\s+",p) if s.strip()]
        scenes.extend(pieces or [p])
    return scenes
async def tts(text, voice, rate, pitch, path):
    import edge_tts
    await edge_tts.Communicate(text=text,voice=voice,rate=f"{rate:+d}%",pitch=f"{pitch:+d}Hz").save(str(path))
def atempo(speed):
    factors=[]; v=float(speed)
    while v<0.5: factors.append("atempo=0.5"); v/=0.5
    while v>2.0: factors.append("atempo=2.0"); v/=2.0
    factors.append(f"atempo={v:.5f}")
    return ",".join(factors)
def motion_filter(kind, secs, w, h, fps=24):
    base=f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    frames=max(1,int(secs*fps))
    z="min(zoom+0.0007,1.12)"
    if kind=="Zoom Out": z="if(eq(on,1),1.12,max(1.0,zoom-0.0007))"
    if kind=="Gentle Zoom": z="min(zoom+0.00035,1.07)"
    if kind in ("Pan Left","Pan Right"): z="1.08"
    x="iw/2-(iw/zoom/2)"
    if kind=="Pan Left": x="iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.20"
    if kind=="Pan Right": x="iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.80"
    return f"{base},zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},setsar=1"
def write_concat(paths, txt):
    # Use absolute paths and safely escape single quotes for FFmpeg concat list.
    txt.write_text("".join("file '"+p.resolve().as_posix().replace("'","'\\''")+"'\n" for p in paths),encoding="utf-8")
def render_story(images, script, voice, voice_rate, pitch, motion, resolution, music_path, music_vol, job, progress):
    if not ready(): raise RuntimeError("FFmpeg/FFprobe hosting پر دستیاب نہیں۔ packages.txt میں ffmpeg شامل کریں۔")
    scenes=split_script(script)
    if not scenes: raise RuntimeError("اسکرپٹ درج کریں۔")
    if not images: raise RuntimeError("کم از کم ایک تصویر منتخب کریں۔")
    w,h=(1280,720) if resolution=="720p" else (1920,1080)
    work=UPLOAD/f"story_{job}"; work.mkdir(exist_ok=True)
    clips=[]; voices=[]
    for i,scene in enumerate(scenes):
        progress((i+1)/(len(scenes)+3),f"Scene {i+1}/{len(scenes)}: وائس تیار…")
        img=images[i%len(images)]
        audio=work/f"voice_{i:05d}.mp3"; clip=work/f"clip_{i:05d}.mp4"
        asyncio.run(tts(scene,voice,voice_rate,pitch,audio))
        secs=duration(audio)+0.15
        kind=motion if motion!="Auto Mix" else ["Gentle Zoom","Zoom Out","Pan Left","Pan Right"][i%4]
        vf=motion_filter(kind,secs,w,h)
        cmd=[FFMPEG,"-y","-loop","1","-i",str(img),"-vf",vf,"-t",f"{secs:.3f}","-r","24","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p",str(clip)]
        rr=run(cmd)
        if rr.returncode: raise RuntimeError("Scene video error: "+rr.stderr[-1800:])
        clips.append(clip); voices.append(audio)
    progress(.72,"Scenes جوڑی جا رہی ہیں…")
    listv=work/"video_list.txt"; write_concat(clips,listv)
    video=work/"video_noaudio.mp4"
    rr=run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(listv),"-c","copy",str(video)])
    if rr.returncode: raise RuntimeError(rr.stderr[-1800:])
    lista=work/"voice_list.txt"; write_concat(voices,lista)
    narration=work/"narration.mp3"
    rr=run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(lista),"-c","copy",str(narration)])
    if rr.returncode: raise RuntimeError(rr.stderr[-1800:])
    final=OUTPUT/f"Sglowina_Story_{job}.mp4"; progress(.88,"آڈیو مکس اور فائنل ایکسپورٹ…")
    if music_path:
        fc=f"[1:a]volume=1[narr];[2:a]volume={music_vol}[bg];[narr][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        cmd=[FFMPEG,"-y","-i",str(video),"-i",str(narration),"-stream_loop","-1","-i",str(music_path),"-filter_complex",fc,"-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)]
    else:
        cmd=[FFMPEG,"-y","-i",str(video),"-i",str(narration),"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)]
    rr=run(cmd)
    if rr.returncode: raise RuntimeError(rr.stderr[-2200:])
    progress(1,"ویڈیو مکمل ہوگئی!"); return final

def render_uploaded(src,out,res,style,video_speed,audio_mode,music,orig_vol,music_vol,pitch_shift,voice_speed):
    # Speed changes apply to video and its original audio together.
    dims={"720p":(1280,720),"1080p":(1920,1080),"1440p":(2560,1440),"4K":(3840,2160),"8K":(7680,4320)}
    w,h=dims[res]
    vf=f"setpts=PTS/{video_speed},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    if style=="Purple Energy": vf+=",eq=contrast=1.15:saturation=1.35,colorbalance=rs=0.05:bs=0.12"
    elif style=="Ultra Vibrant": vf+=",eq=contrast=1.10:saturation=1.50:brightness=0.01"
    elif style=="Dark Action": vf+=",eq=contrast=1.25:saturation=1.15:brightness=-0.04"
    elif style=="Cinematic Warm": vf+=",eq=contrast=1.08:saturation=1.12:brightness=0.01,colorbalance=rs=0.04:gs=0.02:bs=-0.04"
    # Audio speed/pitch chain. Original audio is optional in the input.
    orig_filter=f"{atempo(video_speed*voice_speed)},volume={orig_vol}"
    if pitch_shift:
        # Pitch shift by semitones with a sample-rate compensation chain.
        factor=2**(pitch_shift/12)
        orig_filter+=f",asetrate=44100*{factor:.6f},aresample=44100"
    cmd=[FFMPEG,"-y","-i",str(src)]
    if music and audio_mode in ("Music Only","Mix Original + Music"): cmd+=["-stream_loop","-1","-i",str(music)]
    if music and audio_mode=="Mix Original + Music":
        fc=f"[0:a]{orig_filter}[orig];[1:a]volume={music_vol}[bg];[orig][bg]amix=inputs=2:duration=first[aout]"
        cmd+=["-filter_complex",fc,"-map","0:v","-map","[aout]"]
    elif music and audio_mode=="Music Only": cmd+=["-map","0:v","-map","1:a"]
    elif audio_mode=="Mute": cmd+=["-map","0:v","-an"]
    else: cmd+=["-map","0:v","-map","0:a?"]
    cmd+=["-vf",vf,"-c:v","libx264","-preset","ultrafast","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",str(out)]
    rr=run(cmd); return rr.returncode==0,rr.stderr

st.title("💎 Sglowina AI — Professional Cinematic Studio")
st.caption("Story Cinema • Video Editor • Audio Controls • FFmpeg")
if not ready(): st.warning("FFmpeg/FFprobe نہیں ملے۔ packages.txt میں ffmpeg کی ضرورت ہے۔")
tab1,tab2=st.tabs(["🎞️ Video Editor","📖 Unlimited Story Cinema"])
with tab1:
    st.subheader("موجودہ ویڈیو ایڈیٹر")
    uploaded=st.file_uploader("ویڈیو اپ لوڈ کریں (MP4/MOV/MKV)",type=["mp4","mov","mkv"],key="editvideo")
    if uploaded:
        resolution=st.selectbox("Resolution",["720p","1080p","1440p","4K","8K"],index=1)
        look=st.selectbox("Cinematic Color Look",["Original","Purple Energy","Ultra Vibrant","Dark Action","Cinematic Warm"])
        video_speed=st.slider("Video Speed",0.25,2.0,1.0,0.05)
        voice_speed=st.slider("Audio Speed",0.5,2.0,1.0,0.05)
        pitch_shift=st.slider("Pitch (semitones)",-8,8,0,1,help="منفی آواز بھاری، مثبت نسبتاً باریک")
        audio_mode=st.selectbox("Audio Mode",["Keep Original","Mix Original + Music","Music Only","Mute"])
        music=st.file_uploader("Background Music (optional)",type=["mp3","wav","m4a"],key="editmusic") if audio_mode in ["Mix Original + Music","Music Only"] else None
        original_vol=st.slider("Original Audio Volume",0.0,2.0,0.8,0.05)
        music_vol=st.slider("Music Volume",0.0,2.0,0.25,0.05)
        st.caption("یہ Editor موجودہ ویڈیو کو رینڈر کرتا ہے؛ Story tab میں اسکرپٹ سے ویڈیو بنتی ہے۔")
        if st.button("🚀 Render Edited Video",type="primary",key="render_existing"):
            jid=uuid.uuid4().hex[:8]; src=UPLOAD/f"input_{jid}.mp4"; out=OUTPUT/f"edited_{jid}.mp4"
            src.write_bytes(uploaded.getbuffer()); mp=None
            if music:
                mp=UPLOAD/f"music_{jid}.{Path(music.name).suffix.lstrip('.')}"
                mp.write_bytes(music.getbuffer())
            try:
                with st.spinner("ویڈیو رینڈر ہو رہی ہے…"):
                    ok,err=render_uploaded(src,out,resolution,look,video_speed,audio_mode,mp,original_vol,music_vol,pitch_shift,voice_speed)
                if ok:
                    st.success("ویڈیو تیار ہے!"); st.video(str(out))
                    st.download_button("📥 Download MP4",out.read_bytes(),file_name=out.name,mime="video/mp4")
                else: st.error("FFmpeg Error"); st.code(err[-4000:])
            except Exception as e: st.error("Rendering error"); st.exception(e)
with tab2:
    st.subheader("Unlimited Story Cinema")
    st.info("اسکرپٹ کے مطابق دورانیہ خود بنے گا؛ کوئی مقررہ 10 منٹ کی پابندی یا 200 Scenes کی سخت حد نہیں۔ لمبی ویڈیو سرور کی میموری/وقت کے باعث رینڈرنگ میں زیادہ وقت لے سکتی ہے۔")
    script=st.text_area("📝 مکمل کہانی / وائس اوور",height=280,placeholder="اپنی مکمل کہانی یہاں لکھیں… جتنی چاہیں طویل۔")
    images=st.file_uploader("🖼️ تصاویر (ایک ساتھ متعدد)",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="storyimgs")
    st.caption(f"منتخب تصاویر: {len(images) if images else 0} — تصاویر کم ہوں تو ترتیب کے مطابق دوبارہ استعمال ہوں گی۔")
    a,b,c=st.columns(3)
    with a: voice=st.selectbox("Urdu Voice",["Asad — Pakistan Male","Uzma — Pakistan Female"])
    with b: rate=st.slider("Voice Speed", -40,40,0,5)
    with c: pitch=st.slider("Voice Pitch / بھاری یا باریک", -30,30,0,2)
    motion=st.selectbox("Image Motion",["Auto Mix","Gentle Zoom","Zoom Out","Pan Left","Pan Right"])
    story_res=st.selectbox("Story Resolution",["720p","1080p"],index=0)
    music=st.file_uploader("Background Audio / Nasheed (optional)",type=["mp3","wav","m4a"],key="storymusic")
    music_volume=st.slider("Background Audio Volume",0.0,0.5,0.10,0.01)
    st.caption("ویڈیو کی لمبائی مکمل اسکرپٹ اور وائس کے مطابق؛ غیر ضروری حد نہیں۔")
    if st.button("🎬 Create Unlimited Story Video",type="primary",key="storycreate"):
        if not script.strip(): st.error("پہلے اسکرپٹ لکھیں۔")
        elif not images: st.error("کم از کم ایک تصویر منتخب کریں۔")
        elif not ready(): st.error("FFmpeg/FFprobe دستیاب نہیں۔")
        else:
            jid=uuid.uuid4().hex[:8]; image_paths=[]
            for i,img in enumerate(images):
                ext=Path(img.name).suffix.lower() or ".jpg"
                p=UPLOAD/f"story_{jid}_{i:04d}{ext}"; p.write_bytes(img.getbuffer()); image_paths.append(p)
            mp=None
            if music:
                mp=UPLOAD/f"storymusic_{jid}.{Path(music.name).suffix.lstrip('.')}"
                mp.write_bytes(music.getbuffer())
            tts_voice="ur-PK-AsadNeural" if voice.startswith("Asad") else "ur-PK-UzmaNeural"
            progress=st.progress(0); status=st.empty()
            try:
                with st.spinner("اسکرپٹ کے تمام Scenes رینڈر ہو رہے ہیں۔ لمبی کہانی میں وقت لگ سکتا ہے۔"):
                    out=render_story(image_paths,script,tts_voice,rate,pitch,motion,story_res,mp,music_volume,jid,lambda v,m:(progress.progress(min(1,max(0,v))),status.write(m)))
                st.success("✨ ویڈیو تیار ہے!")
                st.video(str(out))
                st.download_button("📥 Download Story Video",out.read_bytes(),file_name=out.name,mime="video/mp4")
            except Exception as e: st.error("ویڈیو بنانے میں مسئلہ:"); st.exception(e)
