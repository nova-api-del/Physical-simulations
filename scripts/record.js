const {chromium}=require('playwright');
const {spawn,execFileSync}=require('child_process');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const drain=stream=>new Promise((resolve,reject)=>{stream.once('drain',resolve);stream.once('error',reject)});
(async()=>{
  const W=720,H=1280,MAX_FRAMES=5400,FPS=30;
  const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader']});
  const page=await browser.newPage({viewport:{width:W,height:H},deviceScaleFactor:1});
  await page.goto('file://'+process.cwd()+'/index.html?offline=1');
  await page.waitForFunction(()=>!!window.__simAdvance);
  const ff=spawn('ffmpeg',['-y','-f','image2pipe','-vcodec','mjpeg','-framerate',String(FPS),'-i','pipe:0','-vf','scale=1080:1920:flags=lanczos','-an','-c:v','libx264','-preset','ultrafast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart','output.mp4'],{stdio:['pipe','inherit','inherit']});
  let progress={active:0,total:120},frames=0;
  try{
    while(frames<MAX_FRAMES){
      progress=await page.evaluate(()=>window.__simAdvance(4));
      const jpg=await page.screenshot({type:'jpeg',quality:88});
      if(!ff.stdin.write(jpg)) await drain(ff.stdin);
      frames++;
      if(progress.active>=progress.total){for(let i=0;i<12;i++){const hold=await page.screenshot({type:'jpeg',quality:88});if(!ff.stdin.write(hold))await drain(ff.stdin)}break}
    }
    if(progress.active<progress.total)throw Error('Safety limit reached before completion: '+progress.active+'/'+progress.total);
    ff.stdin.end();
    await new Promise((resolve,reject)=>{ff.once('close',c=>c===0?resolve():reject(Error('ffmpeg exit '+c)));ff.once('error',reject)});
    console.log('Completed '+progress.active+'/'+progress.total+' rings; '+frames+' deterministic frames at '+FPS+'fps.');
  }catch(e){ff.stdin.destroy();ff.kill('SIGTERM');throw e}
  finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});