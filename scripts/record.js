const {chromium}=require('playwright');
const {spawn}=require('child_process');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const waitExit=(proc,label)=>new Promise((resolve,reject)=>{proc.once('close',c=>c===0?resolve():reject(Error(label+' exit '+c)));proc.once('error',reject)});
const drain=stream=>new Promise((resolve,reject)=>{stream.once('drain',resolve);stream.once('error',reject)});
(async()=>{
  const W=720,H=1280,FPS=60,MAX_FRAMES=FPS*100;
  const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:W,height:H},deviceScaleFactor:1});
  await page.goto('file://'+process.cwd()+'/index.html?offline=1&total=400&seconds=60');
  await page.waitForFunction(()=>!!window.__simAdvance);
  await page.mouse.click(8,8);
  await page.waitForTimeout(350);
  const audio=spawn('ffmpeg',['-y','-f','pulse','-i','virtual_speaker.monitor','-ac','2','-ar','44100','-c:a','pcm_s16le','audio.wav'],{stdio:['pipe','ignore','inherit']});
  await sleep(350);
  const video=spawn('ffmpeg',['-y','-f','image2pipe','-vcodec','mjpeg','-framerate',String(FPS),'-i','pipe:0','-vf','scale=1080:1920:flags=lanczos','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart','video-silent.mp4'],{stdio:['pipe','inherit','inherit']});
  let progress={active:0,total:400},frames=0;
  try{
    while(frames<MAX_FRAMES){
      progress=await page.evaluate(()=>window.__simAdvance(2));
      const jpg=await page.screenshot({type:'jpeg',quality:90});
      if(!video.stdin.write(jpg))await drain(video.stdin);
      frames++;
      if(progress.active>=progress.total){for(let i=0;i<30;i++){const hold=await page.screenshot({type:'jpeg',quality:90});if(!video.stdin.write(hold))await drain(video.stdin)}break}
    }
    if(progress.active<progress.total)throw Error('Safety limit reached before completion: '+progress.active+'/'+progress.total);
    video.stdin.end();await waitExit(video,'video ffmpeg');
    audio.stdin.end('q\n');await waitExit(audio,'audio ffmpeg');
    const mux=spawn('ffmpeg',['-y','-i','video-silent.mp4','-i','audio.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-shortest','-movflags','+faststart','output.mp4'],{stdio:['ignore','inherit','inherit']});
    await waitExit(mux,'mux ffmpeg');
    console.log('SUCCESS: '+progress.active+'/'+progress.total+' rings; '+frames+' frames at '+FPS+'fps; 1080x1920; AAC audio.');
  }catch(e){video.stdin.destroy();video.kill('SIGTERM');audio.kill('SIGTERM');throw e}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});