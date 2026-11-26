import streamlit as st
import os, tempfile, subprocess, shutil, asyncio, math, re, time, urllib.parse, hashlib, io
from pathlib import Path
from PIL import Image, ImageOps

st.set_page_config(page_title="Sglowina AI | Cinematic Story Studio", page_icon="🎬", layout="wide")

# ---------- Utilities ----------
def ffmpeg(): return shutil.which("ffmpeg")
def ffprobe(): return shutil.which("ffprobe")
def run(cmd, timeout=900):
    p=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-4500:])
    return p
def duration(path):
    if not ffprobe(): return 0
    try:
        return float(run([ffprobe(),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],60).stdout.strip())
    except Exception: return 0
def sentence_list(text):
    text=re.sub(r"\s+"," ",(text or "").strip())
    return [x.strip() for x in re.split(r"(?<=[.!?۔؟])\s+",text) if x.strip()] if text else []
def split_story(text,n):
    ss=sentence_list(text)
    if not ss: return []
    n=max(1,min(int(n),len(" ".join(ss).split())))
    if len(ss)<n:
        words=" ".join(ss).split(); return [" ".join(words[round(len(words)*i/n):round(len(words)*(i+1)/n)]) for i in range(n)]
    out=[]; start=0; total=sum(len(x) for x in ss)
    for i in range(n):
        if i==n-1: out.append(" ".join(ss[start:])); break
        target=total*(i+1)/n; cur=sum(len(x) for x in ss[:start]); end=start
        while end<len(ss) and cur<target: cur+=len(ss[end]); end+=1
        end=max(start+1,min(end,len(ss)-(n-i-1))); out.append(" ".join(ss[start:end])); start=end
    return out[:n]
def prophet_terms(text):
    terms=["نبی","انبیاء","انبیا","پیغمبر","رسول","محمد","ابراہیم","موسیٰ","عیسیٰ","آدم","نوح","یوسف","یعقوب","داود","سلیمان","ایوب","یونس","زکریا","یحییٰ","اسماعیل","اسحاق","لوط","ہود","صالح","شعیب","ہارون","مریم","prophet","prophets","jesus","moses","abraham","noah","adam"]
    t=(text or "").lower(); return any(x.lower() in t for x in terms)
def image_prompt(scene,ratio,sacred=False):
    shape="wide 16:9" if ratio=="YouTube 16:9" else "vertical 9:16" if ratio=="Shorts 9:16" else "square 1:1"
    safe=re.sub(r"\s+"," ",scene.strip())[:850]
    rule="STRICT: Never depict, imply, silhouette, or show a prophet/messenger as a person. No face, body, hands, shadow, or human figure; use only environment, symbolic objects, architecture, landscape and light." if sacred else "Respectful, historically grounded scene; no captions, watermark, collage or split screen."
    return f"Single photoreal cinematic story still, {shape}, ancient Middle Eastern atmosphere where relevant, realistic texture, dramatic natural lighting, high-production film composition. Depict only this story beat: {safe}. {rule}"
def free_image(prompt,w,h,seed):
    import requests
    url="https://image.pollinations.ai/prompt/"+urllib.parse.quote(prompt,safe="")
    r=requests.get(url,params={"width":min(1024,max(512,int(w))),"height":min(1024,max(512,int(h))),"seed":seed,"nologo":"true"},timeout=(20,180),headers={"User-Agent":"SglowinaAI/1.0"})
    if r.status_code!=200 or not r.headers.get("content-type"," ").lower().startswith("image/") or len(r.content)<10000: raise RuntimeError("Free image service unavailable or rate-limited.")
    return r.content
async def tts_async(text,voice,rate,vol,path):
    import edge_tts
    await edge_tts.Communicate(text,voice,rate=rate,volume=vol).save(str(path))
def tts(text,voice,rate,vol,path): asyncio.run(tts_async(text,voice,rate,vol,path))
def audio_filter(depth,bass,pitch):
    ratio=2**(float(pitch)/12); f=[]
    if abs(pitch)>0.01: f += [f"asetrate=44100*{ratio:.6f}","aresample=44100",f"atempo={1/ratio:.6f}"]
    f += [f"equalizer=f=110:t=q:w=1:g={min(10,max(0,2+bass*.08))}","acompressor=threshold=-18dB:ratio=2.2:attack=15:release=160","alimiter=limit=0.95"]
    if depth=="Deep": f.append("equalizer=f=170:t=q:w=1:g=1.5")
    elif depth=="Extra Deep": f += ["equalizer=f=150:t=q:w=1:g=2.5","equalizer=f=300:t=q:w=1:g=-1"]
    elif depth=="Cinematic Narrator": f += ["equalizer=f=140:t=q:w=1:g=2","acompressor=threshold=-22dB:ratio=3:attack=20:release=220"]
    return ",".join(f)
def scene_video(img,dur,out,w,h,motion,power,fps,grade,idx):
    frames=max(2,int(math.ceil(dur*fps))); step={"Low":.035,"Medium":.065,"High":.10,"Extreme":.15}.get(power,.10)
    modes=["Zoom In","Zoom Out","Pan Left","Pan Right","Dynamic"]
    if motion=="Auto Director": motion=modes[(idx-1)%len(modes)]
    z=f"1+{step:.5f}*(1-on/{frames})" if motion=="Zoom Out" else f"1+{step:.5f}*on/{frames}"
    x=f"(iw-iw/zoom)*(0.15+0.70*on/{frames})" if motion=="Pan Left" else f"(iw-iw/zoom)*(0.85-0.70*on/{frames})" if motion=="Pan Right" else "(iw-iw/zoom)*(0.5+0.22*sin(on/14))" if motion=="Dynamic" else "(iw-iw/zoom)/2"
    y="(ih-ih/zoom)/2"
    vf=f"scale={int(w*1.15)}:{int(h*1.15)}:force_original_aspect_ratio=increase,crop={int(w*1.15)}:{int(h*1.15)},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"
    if grade=="Warm Cinematic": vf+=",eq=saturation=1.12:contrast=1.06:brightness=0.015,colorbalance=rs=0.04:gs=0.01:bs=-0.03"
    elif grade=="Vibrant": vf+=",eq=saturation=1.22:contrast=1.08:brightness=0.02"
    elif grade=="Dark Drama": vf+=",eq=saturation=0.92:contrast=1.14:brightness=-0.035,colorbalance=rs=-0.02:bs=0.04"
    elif grade=="Purple Energy": vf+=",colorbalance=rs=0.04:gs=-0.02:bs=0.06,eq=saturation=1.18"
    vf+=",format=yuv420p"
    run([ffmpeg(),"-y","-loop","1","-i",str(img),"-vf",vf,"-t",f"{dur:.3f}","-an","-r",str(fps),"-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(out)],900)
def concat_list(paths,dest):
    Path(dest).write_text("\n".join("file '"+Path(p).as_posix().replace("'","'\\''")+"'" for p in paths),encoding="utf-8")
def srt_time(t):
    ms=int(round(t*1000)); hh,ms=divmod(ms,3600000); mm,ms=divmod(ms,60000); ss,ms=divmod(ms,1000); return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"
def build_srt(chunks,durs,path):
    t=0; rows=[]
    for i,(c,d) in enumerate(zip(chunks,durs),1):
        if c.strip(): rows += [str(i),f"{srt_time(t)} --> {srt_time(t+d)}",c.strip(),""]
        t+=d
    Path(path).write_text("\n".join(rows),encoding="utf-8")

# ---------- UI ----------
st.title("🎬 Sglowina AI — Cinematic Story Studio")
st.caption("Story scenes • Urdu TTS • Camera motion • Music mix • MP4/SRT export")
if not ffmpeg() or not ffprobe(): st.warning("Hosting پر FFmpeg/FFprobe نہیں مل رہے۔ packages.txt میں ffmpeg ہونا چاہیے۔")

with st.sidebar:
    st.header("🎛️ Film controls")
    aspect=st.selectbox("Video format",["YouTube 16:9","Shorts 9:16","Square 1:1"])
    resolution=st.selectbox("Resolution",["720p","1080p","1440p","4K"],0,help="Free hosting کے لیے 720p بہتر ہے۔")
    fps=st.select_slider("FPS",[24,25,30,50,60],value=24)
    grade=st.selectbox("Color grade",["Original","Warm Cinematic","Vibrant","Dark Drama","Purple Energy"])
    motion=st.selectbox("Camera motion",["Auto Director","Zoom In","Zoom Out","Pan Left","Pan Right","Dynamic"])
    power=st.select_slider("Motion intensity",["Low","Medium","High","Extreme"],value="High")
    st.subheader("🎙️ Voice")
    voice_choice=st.selectbox("Urdu voice",["Asad (Male)","Uzma (Female)"])
    depth=st.selectbox("Voice depth",["Normal","Deep","Extra Deep","Cinematic Narrator"])
    bass=st.slider("Voice thickness / bass",0,100,45)
    pitch=st.slider("Pitch shift (semitones)",-8.0,3.0,-2.0,0.5)
    speed=st.slider("Speech speed",0.75,1.25,1.0,0.05)
    volume=st.slider("Voice volume",50,150,100)
    st.subheader("🎵 Audio")
    music_volume=st.slider("Background music volume",0,100,12)
    audio_mode=st.selectbox("Audio mix",["Voice + Music","Voice Only","Music Only","Mute"])
    subtitles=st.checkbox("Export SRT subtitles",True)

story=st.text_area("📖 اپنی مکمل کہانی / وائس اوور اسکرپٹ یہاں پیسٹ کریں",height=230,key="story_text")

# Keep uploaded image bytes in session state after a completed upload/rerun.
if "saved_story_images" not in st.session_state: st.session_state.saved_story_images=[]
if "saved_story_image_names" not in st.session_state: st.session_state.saved_story_image_names=[]
uploaded=st.file_uploader("🖼️ متعدد تصاویر ترتیب سے منتخب کریں",type=["png","jpg","jpeg","webp"],accept_multiple_files=True,key="story_images_upload",help="ایک وقت میں منتخب تصاویر اپلوڈ کریں؛ گیلری سے واپس آنے کے بعد اگر اپلوڈ مکمل ہو چکا ہو تو یہ فہرست سیشن میں رکھی جاتی ہے۔")
if uploaded:
    st.session_state.saved_story_images=[f.getvalue() for f in uploaded]
    st.session_state.saved_story_image_names=[f.name for f in uploaded]
    st.success(f"{len(uploaded)} تصاویر منتخب ہیں۔")
if st.session_state.saved_story_images:
    st.info(f"محفوظ اپلوڈ تصاویر: {len(st.session_state.saved_story_images)}")
    with st.expander("تصاویر کا Preview / ترتیب"):
        for i,(raw,name) in enumerate(zip(st.session_state.saved_story_images,st.session_state.saved_story_image_names),1):
            st.write(f"Scene {i} — {name}")
            st.image(raw,width=150)
    if st.button("🗑️ منتخب تصاویر صاف کریں"):
        st.session_state.saved_story_images=[]; st.session_state.saved_story_image_names=[]; st.rerun()

word_count=len((story or "").split())
img_count=len(st.session_state.saved_story_images)
scene_est=min(80,max(1,img_count,math.ceil(word_count/30) if word_count else 1))
scene_count=st.slider("کل Scenes",1,80,scene_est,help="ابتدائی اندازہ تقریباً ہر 30 الفاظ پر ایک Scene۔")
auto_missing=st.checkbox("کم تصاویر والے Scenes کے لیے مفت AI تصاویر بنانے کی کوشش (API Key نہیں)",True)
if img_count and scene_count>img_count and auto_missing: st.warning(f"{img_count} اپلوڈ تصاویر، {scene_count} Scenes؛ باقی {scene_count-img_count} تصاویر بنانے کی کوشش ہوگی۔")
bgm=st.file_uploader("🎵 اختیاری Background Music",type=["mp3","wav","m4a","aac","ogg"],key="music_upload")
st.caption("Static pictures پر camera motion ہوگا؛ حقیقی walking/lip-sync کے لیے image-to-video model درکار ہے۔")

if st.button("🚀 Create Cinematic Video",type="primary",use_container_width=True):
    if not ffmpeg() or not ffprobe(): st.error("FFmpeg/FFprobe دستیاب نہیں۔")
    elif not story.strip(): st.error("پہلے کہانی پیسٹ کریں۔")
    elif not img_count and not auto_missing: st.error("تصاویر اپلوڈ کریں یا auto image option آن کریں۔")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                td=Path(tmp); prog=st.progress(0,text="Scenes تیار ہو رہے ہیں…")
                chunks=split_story(story,scene_count); sources=[None]*scene_count
                for i,raw in enumerate(st.session_state.saved_story_images[:scene_count]): sources[i]=raw
                missing=[i for i,x in enumerate(sources) if x is None]
                if missing and not auto_missing: st.error("Scenes کے لیے تصاویر کم ہیں۔"); st.stop()
                voice="ur-PK-AsadNeural" if voice_choice.startswith("Asad") else "ur-PK-UzmaNeural"
                rate=f"{round((speed-1)*100):+d}%"; vol=f"{volume-100:+d}%"
                p=pitch-(1.5 if depth=="Deep" else 3 if depth=="Extra Deep" else 1 if depth=="Cinematic Narrator" else 0)
                af=audio_filter(depth,bass,p)
                sizes={"720p":(1280,720),"1080p":(1920,1080),"1440p":(1920,1080),"4K":(1920,1080)}
                w,h=sizes[resolution]
                if aspect=="Shorts 9:16": w,h=(720,1280) if resolution=="720p" else (1080,1920)
                elif aspect=="Square 1:1": w,h=(720,720) if resolution=="720p" else (1080,1080)
                if missing:
                    for j,idx in enumerate(missing):
                        prog.progress(.03+.16*(j+1)/len(missing),text=f"Scene {idx+1}: تصویر بنانے کی کوشش…")
                        prompt=image_prompt(chunks[idx],aspect,prophet_terms(story))
                        seed=int(hashlib.sha256(f"sglowina-{idx}-{chunks[idx]}".encode()).hexdigest()[:8],16)%2147483647
                        if j: time.sleep(46)
                        try:
                            data=free_image(prompt,w,h,seed); sources[idx]=data
                        except Exception as e: st.error(f"Scene {idx+1} کی تصویر نہیں بنی: {e}"); st.stop()
                videos=[]; audios=[]; durs=[]
                for i,(raw,chunk) in enumerate(zip(sources,chunks),1):
                    prog.progress(.2+.6*(i-1)/scene_count,text=f"Scene {i}/{scene_count} بن رہا ہے…")
                    im=Image.open(io.BytesIO(raw)) if isinstance(raw,bytes) else Image.open(raw)
                    im=ImageOps.exif_transpose(im).convert("RGB"); ip=td/f"img_{i:03}.jpg"; im.save(ip,quality=92)
                    audio=None; dur=3.0
                    if chunk.strip():
                        vp=td/f"voice_{i:03}.mp3"; tts(chunk,voice,rate,vol,vp)
                        filtered=td/f"voicefx_{i:03}.mp3"; run([ffmpeg(),"-y","-i",str(vp),"-af",af,"-c:a","libmp3lame","-q:a","3",str(filtered)],240)
                        audio=filtered; dur=max(2.4,duration(audio)+.3)
                    durs.append(dur); audios.append(audio)
                    clip=td/f"scene_{i:03}.mp4"
                    try: scene_video(ip,dur,clip,w,h,motion,power,fps,grade,i)
                    except Exception: scene_video(ip,dur,clip,w,h,motion,"Low",fps,"Original",i)
                    videos.append(clip)
                prog.progress(.83,text="Scenes جوڑ رہے ہیں…")
                vlist=td/"vconcat.txt"; concat_list(videos,vlist); silent=td/"video.mp4"
                run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(vlist),"-c","copy",str(silent)],900)
                audio_parts=[]
                for i,a in enumerate(audios):
                    ap=td/f"ap_{i:03}.wav"
                    if a: run([ffmpeg(),"-y","-i",str(a),"-af",f"apad=pad_dur={durs[i]},atrim=duration={durs[i]}","-ar","44100","-ac","2",str(ap)],240)
                    else: run([ffmpeg(),"-y","-f","lavfi","-i","anullsrc=r=44100:cl=stereo","-t",str(durs[i]),str(ap)],240)
                    audio_parts.append(ap)
                alist=td/"aconcat.txt"; concat_list(audio_parts,alist); voicefile=td/"voice.wav"
                run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(alist),"-c:a","pcm_s16le",str(voicefile)],900)
                musicfile=None
                if bgm: musicfile=td/"bgm"; musicfile.write_bytes(bgm.getvalue())
                out=td/"Sglowina_Cinematic.mp4"
                if audio_mode=="Mute": cmd=[ffmpeg(),"-y","-i",str(silent),"-an","-c:v","copy",str(out)]
                elif audio_mode=="Music Only" and musicfile: cmd=[ffmpeg(),"-y","-i",str(silent),"-stream_loop","-1","-i",str(musicfile),"-filter_complex",f"[1:a]volume={music_volume/100}[m]","-map","0:v","-map","[m]","-c:v","copy","-c:a","aac","-shortest",str(out)]
                elif audio_mode=="Voice Only" or not musicfile: cmd=[ffmpeg(),"-y","-i",str(silent),"-i",str(voicefile),"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-shortest",str(out)]
                else: cmd=[ffmpeg(),"-y","-i",str(silent),"-i",str(voicefile),"-stream_loop","-1","-i",str(musicfile),"-filter_complex",f"[1:a]volume=1[v];[2:a]volume={music_volume/100}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(out)]
                run(cmd,900)
                if not out.exists() or out.stat().st_size<10000: raise RuntimeError("MP4 output نہیں بنی یا خالی ہے۔")
                video=out.read_bytes(); st.success("🎉 ویڈیو تیار ہے!"); st.video(video)
                st.download_button("⬇️ MP4 ڈاؤن لوڈ",video,"Sglowina_Cinematic.mp4","video/mp4",use_container_width=True)
                if subtitles:
                    srt=td/"subs.srt"; build_srt(chunks,durs,srt)
                    st.download_button("⬇️ SRT ڈاؤن لوڈ",srt.read_bytes(),"Sglowina_Subtitles.srt","text/plain")
                prog.progress(1,text="مکمل")
        except Exception as e: st.error("Render میں خرابی:"); st.code(str(e)); st.info("720p، 24 FPS، Medium motion پر کوشش کریں۔")
