import streamlit as st
import subprocess, shutil, asyncio, uuid, re, tempfile
from pathlib import Path

st.set_page_config(page_title="Sglowina AI Studio", page_icon="🎬", layout="wide")
BASE = Path("/tmp/sglowina")
UPLOAD = BASE / "uploads"; OUTPUT = BASE / "outputs"
UPLOAD.mkdir(parents=True, exist_ok=True); OUTPUT.mkdir(parents=True, exist_ok=True)
FFMPEG = shutil.which("ffmpeg"); FFPROBE = shutil.which("ffprobe")

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)
def duration(path):
    if not FFPROBE: raise RuntimeError("FFprobe دستیاب نہیں۔ packages.txt میں ffmpeg شامل ہونا چاہیے۔")
    r=run([FFPROBE,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)])
    if r.returncode: raise RuntimeError(r.stderr[-1500:])
    return float(r.stdout.strip())
def split_script(text):
    chunks=[x.strip() for x in re.split(r"\n\s*\n",text) if x.strip()]
    out=[]
    for c in chunks:
        out += [x.strip() for x in re.split(r"(?<=[۔.!?؟])\s+",c) if x.strip()] or [c]
    return out[:200]
async def tts(text, voice, rate, pitch, target):
    import edge_tts
    await edge_tts.Communicate(text=text, voice=voice, rate=f"{rate:+d}%", pitch=pitch).save(str(target))
def zoom_filter(kind, secs, w, h, fps=24):
    base=f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    frames=max(1,int(secs*fps)); z="min(zoom+0.00055,1.10)"
    if kind=="Zoom Out": z="if(eq(on,1),1.10,max(1.0,zoom-0.00055))"
    if kind in ("Pan Left","Pan Right"): z="1.06"
    x="iw/2-(iw/zoom/2)"
    if kind=="Pan Left": x="iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.18"
    if kind=="Pan Right": x="iw/2-(iw/zoom/2)+((iw-iw/zoom)/2)*0.82"
    return f"{base},zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},setsar=1"
def story_render(imgs, script, voice, speed, pitch, motion, resolution, musicfile, mvol, progress_cb):
    if not FFMPEG or not FFPROBE: raise RuntimeError("FFmpeg/FFprobe موجود نہیں۔")
    scenes=split_script(script)
    if not scenes: raise RuntimeError("کہانی لکھیں۔")
    job=uuid.uuid4().hex[:8]; work=UPLOAD/job; work.mkdir(parents=True,exist_ok=True)
    w,h=(1280,720) if resolution=="720p" else (1920,1080)
    videos=[]; voicefiles=[]
    for i,txt in enumerate(scenes):
        progress_cb((i+1)/(len(scenes)+2),f"وائس اور منظر {i+1}/{len(scenes)} تیار ہو رہا ہے")
        vf=work/f"voice_{i:03d}.mp3"; cf=work/f"clip_{i:03d}.mp4"
        asyncio.run(tts(txt,voice,speed,pitch,vf)); vd=duration(vf); sec=max(1.0,vd+0.18)
        modes=["Gentle Zoom","Zoom Out","Pan Left","Pan Right"]
        chosen=modes[i%4] if motion=="Auto Mix" else motion
        filterstr=zoom_filter(chosen,sec,w,h)
        rr=run([FFMPEG,"-y","-loop","1","-i",str(imgs[i%len(imgs)]),"-vf",filterstr,"-t",f"{sec:.3f}","-r","24","-c:v","libx264","-preset","ultrafast","-crf","24","-pix_fmt","yuv420p",str(cf)])
        if rr.returncode: raise RuntimeError(rr.stderr[-1800:])
        videos.append(cf); voicefiles.append(vf)
    progress_cb(0.72,"تمام مناظر جوڑ رہے ہیں…")
    vlist=work/"video_list.txt"; vlist.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in videos),encoding="utf-8")
    video=work/"video.mp4"; rr=run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(vlist),"-c","copy",str(video)])
    if rr.returncode: raise RuntimeError(rr.stderr[-1800:])
    # Re-encode audio concat for reliability across generated MP3 segments.
    alist=work/"audio_list.txt"; alist.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in voicefiles),encoding="utf-8")
    narr=work/"narration.mp3"; rr=run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(alist),"-c:a","libmp3lame","-q:a","3",str(narr)])
    if rr.returncode: raise RuntimeError(rr.stderr[-1800:])
    out=OUTPUT/f"Sglowina_Story_{job}.mp4"; total=duration(video)
    if musicfile:
        rr=run([FFMPEG,"-y","-i",str(video),"-i",str(narr),"-stream_loop","-1","-i",str(musicfile),"-filter_complex",f"[1:a]volume=1[n];[2:a]volume={mvol}[m];[n][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]","-t",f"{total:.3f}","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",str(out)])
    else:
        rr=run([FFMPEG,"-y","-i",str(video),"-i",str(narr),"-map","0:v","-map","1:a","-t",f"{total:.3f}","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",str(out)])
    if rr.returncode: raise RuntimeError(rr.stderr[-2000:])
    progress_cb(1.0,"ویڈیو مکمل ہوگئی!"); return out

def edit_video(inp,out,res,style,seconds,audio_mode,music,origvol,mvol):
    sizes={"720p":(1280,720),"1080p":(1920,1080),"1440p":(2560,1440),"4K":(3840,2160)}
    w,h=sizes[res]; vf=f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    looks={"Purple Energy":"eq=contrast=1.15:saturation=1.35,colorbalance=rs=0.05:bs=0.12","Ultra Vibrant":"eq=contrast=1.1:saturation=1.45:brightness=0.01","Dark Action":"eq=contrast=1.25:saturation=1.15:brightness=-0.04","Warm Cinematic":"eq=contrast=1.05:saturation=1.12:brightness=0.01"}
    if style in looks: vf += ","+looks[style]
    cmd=[FFMPEG,"-y","-i",str(inp)]; usemusic=bool(music and audio_mode in ("Music Only","Mix Original + Music"))
    if usemusic:
        cmd += ["-stream_loop","-1","-i",str(music)]
        if audio_mode=="Mix Original + Music":
            cmd += ["-filter_complex",f"[0:a]volume={origvol}[a0];[1:a]volume={mvol}[a1];[a0][a1]amix=inputs=2:duration=first[aout]","-map","0:v","-map","[aout]"]
        else: cmd += ["-map","0:v","-map","1:a"]
    else: cmd += ["-map","0:v","-map","0:a?"]
    cmd += ["-vf",vf,"-t",str(seconds),"-c:v","libx264","-preset","ultrafast","-crf","21","-pix_fmt","yuv420p","-c:a","aac","-movflags","+faststart",str(out)]
    rr=run(cmd); return rr.returncode==0,rr.stderr

st.title("🎬 Sglowina AI — Cinematic Studio")
st.caption("Video Editor + Story Cinema | Urdu narration | Image motion")
if not FFMPEG or not FFPROBE: st.warning("FFmpeg/FFprobe ابھی دستیاب نہیں۔ packages.txt میں ffmpeg ہونا چاہیے۔")
t1,t2=st.tabs(["🎞️ Video Editor","📖 Story Cinema"])
with t1:
    st.subheader("Original Video Studio")
    vf=st.file_uploader("ویڈیو اپلوڈ کریں (MP4/MOV/MKV)",type=["mp4","mov","mkv"],key="vid_upload")
    if vf:
        res=st.selectbox("Resolution",["720p","1080p","1440p","4K"],index=1,key="vid_res")
        look=st.selectbox("Cinematic look",["Original","Purple Energy","Ultra Vibrant","Dark Action","Warm Cinematic"],key="vid_look")
        secs=st.slider("Export duration (seconds)",5,600,60,key="vid_secs")
        am=st.selectbox("Audio",["Keep Original","Music Only","Mix Original + Music"],key="vid_audio")
        mf=st.file_uploader("Background music (optional)",type=["mp3","wav","m4a"],key="vid_music") if am!="Keep Original" else None
        ov=st.slider("Original audio volume",0.0,2.0,1.0,0.05,key="vid_ov")
        mv=st.slider("Music volume",0.0,1.0,0.20,0.05,key="vid_mv")
        if st.button("Render video",key="vid_go"):
            job=uuid.uuid4().hex[:8]; ip=UPLOAD/f"src_{job}.mp4"; op=OUTPUT/f"edited_{job}.mp4"; ip.write_bytes(vf.getbuffer()); mp=None
            if mf: mp=UPLOAD/f"music_{job}{Path(mf.name).suffix}"; mp.write_bytes(mf.getbuffer())
            with st.spinner("ویڈیو ایڈٹ ہو رہی ہے…"):
                ok,err=edit_video(ip,op,res,look,secs,am,mp,ov,mv)
            if ok:
                st.success("ویڈیو تیار!"); st.video(str(op)); st.download_button("Download edited video",op.read_bytes(),file_name=op.name,mime="video/mp4",key="vid_dl")
            else: st.error("Rendering error"); st.code(err[-3500:])
with t2:
    st.subheader("Story Cinema — تصاویر سے ویڈیو")
    script=st.text_area("مکمل کہانی / وائس اوور",height=250,key="story_text",placeholder="یہاں مکمل کہانی پیسٹ کریں…")
    images=st.file_uploader("کہانی کی تصاویر منتخب کریں (ایک ساتھ متعدد)",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="story_images_v2")
    st.caption(f"منتخب تصاویر: {len(images) if images else 0} | تصاویر کہانی کے جملوں کے مطابق خود باری باری استعمال ہوں گی")
    c1,c2,c3=st.columns(3)
    with c1: voiceopt=st.selectbox("Urdu voice",["Asad (Male)","Uzma (Female)"],key="story_voice")
    with c2: sp=st.selectbox("Speed",["Slow","Normal","Fast"],key="story_speed")
    with c3: mot=st.selectbox("Image motion",["Auto Mix","Gentle Zoom","Zoom Out","Pan Left","Pan Right"],key="story_motion")
    sr=st.selectbox("Story resolution",["720p","1080p"],key="story_res")
    deep=st.checkbox("Deep voice",value=False,key="story_deep")
    musicf=st.file_uploader("Background ambient / music (optional)",type=["mp3","wav","m4a"],key="story_music_file")
    mvol=st.slider("Background volume",0.0,0.5,0.10,0.01,key="story_vol")
    if st.button("🎬 Create Story Video",type="primary",key="story_make"):
        if not script.strip(): st.error("پہلے کہانی پیسٹ کریں۔")
        elif not images: st.error("کم از کم ایک تصویر منتخب کریں۔")
        elif not FFMPEG or not FFPROBE: st.error("FFmpeg/FFprobe دستیاب نہیں۔")
        else:
            job=uuid.uuid4().hex[:8]; imagepaths=[]
            with st.spinner("تصاویر محفوظ ہو رہی ہیں…"):
                for i,img in enumerate(images):
                    p=UPLOAD/f"img_{job}_{i:03d}{Path(img.name).suffix.lower()}"; p.write_bytes(img.getbuffer()); imagepaths.append(p)
            mp=None
            if musicf: mp=UPLOAD/f"storymusic_{job}{Path(musicf.name).suffix}"; mp.write_bytes(musicf.getbuffer())
            voice="ur-PK-AsadNeural" if voiceopt.startswith("Asad") else "ur-PK-UzmaNeural"
            rate={"Slow":-12,"Normal":0,"Fast":12}[sp]; pitch="-12Hz" if deep else "+0Hz"
            bar=st.progress(0); status=st.empty()
            try:
                out=story_render(imagepaths,script,voice,rate,pitch,mot,sr,mp,mvol,lambda p,m:(bar.progress(min(1,max(0,p))),status.write(m)))
                st.success("✨ Story Video تیار ہے!"); st.video(str(out)); st.download_button("📥 Download Story Video",out.read_bytes(),file_name=out.name,mime="video/mp4",key="story_download")
            except Exception as e: st.error("ویڈیو بناتے وقت خرابی:"); st.exception(e)
