import json, math, random, subprocess, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W,H,FPS,SECONDS=720,1280,30,30
N=100; cx,cy=W//2,H//2; maxr=540; ballr=9
random.seed()
palettes=[[(65,220,255),(140,90,255),(255,90,180)],[(70,255,170),(255,210,70),(255,100,100)],[(255,100,80),(255,180,70),(180,100,255)]]
palette=random.choice(palettes)
rings=[{"r":(i+1)*maxr/N,"a":random.random()*math.tau,"gap":random.uniform(.35,.7),"spin":random.choice([-1,1])*random.uniform(.002,.008),"broken":False,"c":palette[i%3]} for i in range(N)]
a=random.random()*math.tau; p=np.array([cx+4*math.cos(a),cy+4*math.sin(a)],float)
a=random.random()*math.tau; speed=5.2; v=np.array([math.cos(a),math.sin(a)])*speed
trail=[]; shards=[]; hits=[]; raw="raw_video.mp4"
cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",raw]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
def ad(a,b): return (a-b+math.pi)%math.tau-math.pi
for frame in range(FPS*SECONDS):
    p+=v; trail.append(tuple(p)); trail=trail[-18:]
    radial=p-np.array([cx,cy]); dist=float(np.linalg.norm(radial)); theta=math.atan2(radial[1],radial[0])
    for r in rings:
        if r["broken"]: continue
        r["a"]=(r["a"]+r["spin"])%math.tau
        if abs(dist-r["r"])<speed+1.5:
            if abs(ad(theta,r["a"]))<r["gap"]/2:
                r["broken"]=True; hits.append((frame/FPS,random.uniform(520,1050)))
                for _ in range(14):
                    z=random.random()*math.tau
                    shards.append([cx+math.cos(theta)*r["r"],cy+math.sin(theta)*r["r"],math.cos(z)*random.uniform(1,5),math.sin(z)*random.uniform(1,5),22,r["c"]])
                speed=min(speed*1.012,15)
            else:
                normal=radial/max(dist,1); v=v-2*np.dot(v,normal)*normal
                p=np.array([cx,cy])+normal*(r["r"]-speed-2); speed=min(speed*1.004,15)
                v=v/max(np.linalg.norm(v),1)*speed; hits.append((frame/FPS,random.uniform(220,460)))
            break
    radial=p-np.array([cx,cy]); normal=radial/max(np.linalg.norm(radial),1)
    tangent=np.array([-normal[1],normal[0]]); v+=tangent*.018; v=v/max(np.linalg.norm(v),1)*speed
    if dist>maxr+25:
        p=np.array([cx,cy])+normal*12; a=math.atan2(v[1],v[0])+random.uniform(-1.2,1.2); v=np.array([math.cos(a),math.sin(a)])*speed
    shards=[[x+vx,y+vy,vx*.985,vy*.985,life-1,c] for x,y,vx,vy,life,c in shards if life>1]
    im=Image.new("RGB",(W,H),(0,0,0)); glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow); d=ImageDraw.Draw(im)
    for r in rings:
        if r["broken"]: continue
        q=int(r["r"]); start=math.degrees(r["a"]+r["gap"]/2); end=math.degrees(r["a"]-r["gap"]/2+math.tau)
        gd.arc((cx-q,cy-q,cx+q,cy+q),start=start,end=end,fill=(*r["c"],155),width=5)
        d.arc((cx-q,cy-q,cx+q,cy+q),start=start,end=end,fill=r["c"],width=2)
    im=Image.alpha_composite(im.convert("RGBA"),glow.filter(ImageFilter.GaussianBlur(9))).convert("RGB"); d=ImageDraw.Draw(im)
    for x,y,vx,vy,life,c in shards: d.ellipse((x-2,y-2,x+2,y+2),fill=c)
    for i,(x,y) in enumerate(trail):
        rr=max(1,int(4*(i+1)/len(trail))); d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=(45,105,170))
    x,y=map(int,p); d.ellipse((x-ballr-3,y-ballr-3,x+ballr+3,y+ballr+3),fill=(35,85,145)); d.ellipse((x-ballr,y-ballr,x+ballr,y+ballr),fill=(245,250,255)); d.ellipse((x-4,y-5,x+1,y),fill="white")
    try: proc.stdin.write(im.tobytes())
    except BrokenPipeError: raise RuntimeError("FFmpeg stopped during rendering")
proc.stdin.close()
if proc.wait()!=0: raise RuntimeError("FFmpeg encoding failed")
sr=44100; audio=np.zeros(SECONDS*sr,dtype=np.float32)
for t,f in hits:
    start=int(t*sr); length=min(int(.22*sr),len(audio)-start)
    if length>0:
        x=np.arange(length)/sr; audio[start:start+length]+=(np.sin(2*np.pi*(f*x-90*x*x))*np.exp(-x*16)*.22).astype(np.float32)
audio=np.clip(audio,-.95,.95)
with wave.open("audio.wav","wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes((audio*32767).astype("<i2").tobytes())
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",raw,"-i","audio.wav","-c:v","copy","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart","output.mp4"],check=True)
Path(raw).unlink(missing_ok=True)
meta={"title":"Can the Ball Escape All 100 Rings? 😳","description":"A glowing ball tries to escape 100 rotating rings. Watch till the end! #shorts #satisfying #physics #simulation","duration_seconds":SECONDS,"width":W,"height":H,"fps":FPS,"made_for_kids":False}
Path("metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("Generated output.mp4",Path("output.mp4").stat().st_size)
