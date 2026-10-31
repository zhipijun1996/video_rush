// Story fixtures using only wave-game's existing localhost API and real controls.
// Audio recording and sync markers follow its scripts/capture.ts.
import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const [port,output,binary]=process.argv.slice(2);
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
const context=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:output,size:{width:1920,height:1080}}});
const p=await context.newPage(),errors=[],records=[];p.on('pageerror',e=>errors.push(e.message));p.setDefaultTimeout(15000);
const api=(fn,arg)=>p.evaluate(({fn,arg})=>new Function('t','arg',fn)(window.__PAIPAI_TEST__,arg),{fn,arg});
const cases=[
 {id:'charge',a:'charge',b:'charge',energy:[0,0],hp:[5,5],damage:[0,0]},
 {id:'small',a:'wave1',b:'charge',energy:[1,0],hp:[5,5],damage:[0,1]},
 {id:'guard',a:'guard1',b:'wave1',energy:[0,1],hp:[5,5],damage:[0,0],event:'block'},
 {id:'trap-loss',a:'wave1',b:'reflect1',energy:[1,1],hp:[1,1],damage:[1,0],winner:1,event:'reflect'},
 {id:'medium-small',a:'wave2',b:'wave1',energy:[3,1],hp:[5,5],damage:[0,1]},
 {id:'medium-guard',a:'wave2',b:'guard1',energy:[3,0],hp:[5,5],damage:[0,2],event:'break'},
 {id:'medium-reflect',a:'wave2',b:'reflect1',energy:[3,1],hp:[5,5],damage:[0,2],event:'break'},
 {id:'at-block',a:'wave2',b:'guard2',energy:[3,1],hp:[5,5],damage:[0,0],event:'block'},
 {id:'uchiha-return',a:'wave2',b:'reflect2',energy:[3,2],hp:[5,5],damage:[2,0],event:'reflect'},
 {id:'charge-five',a:'charge',b:'charge',energy:[0,0],hp:[5,5],damage:[0,0],rounds:5},
 {id:'beam-win',a:'wave3',b:'reflect2',energy:[5,2],hp:[3,3],damage:[0,3],winner:0,event:'break'},
];
try{
 await p.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
 await p.click('[data-action="settings"]');await p.click('[data-action="close"]');
 await api('t.setSave({completed:8,tutorial:true,skin:"ribbon",settings:{...t.save.settings,speed:.7,music:0,sfx:.8}});t.audio.configure(t.save.settings);return t.audio.unlock()');
 await p.evaluate(()=>{const a=window.__PAIPAI_TEST__.audio,d=a.ctx.createMediaStreamDestination();a.output.connect(d);window.vrChunks=[];window.vrRecorder=new MediaRecorder(d.stream,{mimeType:'audio/webm;codecs=opus'});window.vrRecorder.ondataavailable=e=>window.vrChunks.push(e.data);window.vrAudioStart=performance.now();window.vrRecorder.start();const m=document.createElement('div');m.id='vr-sync';m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#ff00ff;z-index:999999';document.body.append(m);});
 await p.waitForTimeout(350);await p.evaluate(()=>document.getElementById('vr-sync').remove());
 for(const c of cases){
  const start=await p.evaluate(()=> (performance.now()-window.vrAudioStart)/1000);
  await api('t.start("advanced",{enemy:arg.b,speed:.7});const s=structuredClone(t.clock.startState);s.players.forEach((pl,i)=>{pl.energy=arg.energy[i];pl.hp=arg.hp[i]});t.start("advanced",{state:s,enemy:arg.b,speed:.7})',c);
  const bounds=await p.locator('.stage-canvas').boundingBox();
  for(let round=0;round<(c.rounds||1);round++){
   await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.inputOpen);await p.click(`[data-skill="${c.a}"]`);
   await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.committed);
   const rec=await api('return {initial:t.clock.startState,result:t.clock.result,state:t.clock.state,log:t.clock.log,audio:t.audio.log}');
   assert.deepEqual(rec.result.actions,[c.a,c.b]);assert.deepEqual(rec.result.damage,c.damage);
   if(c.winner!==undefined)assert.equal(rec.result.winner,c.winner);
   if(c.event)assert(rec.result.events.some(e=>e.type===c.event));
   if(round===(c.rounds||1)-1){
    if(c.winner!==undefined){await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.phase==='victory');await p.waitForTimeout(1900);}
    else{await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.phase==='recover');await p.waitForTimeout(250);}
    const end=await p.evaluate(()=> (performance.now()-window.vrAudioStart)/1000);
    await p.screenshot({path:`${output}/${c.id}.png`});
    const audio=await api('return t.audio.log');records.push({case:c,start,end,canvas:bounds,...rec,finalAudio:audio});
   }else await p.waitForFunction(n=>window.__PAIPAI_TEST__.clock.startState.round===n,round+2);
  }
  console.log('Captured',c.id,records.at(-1).end-start);
 }
 const sound=await p.evaluate(()=>new Promise(resolve=>{window.vrRecorder.onstop=()=>{const b=new Blob(window.vrChunks,{type:'audio/webm'}),f=new FileReader();f.onload=()=>resolve({base64:String(f.result).split(',')[1],seconds:(performance.now()-window.vrAudioStart)/1000});f.readAsDataURL(b);};const m=document.createElement('div');m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#00ffff;z-index:999999';document.body.append(m);window.vrRecorder.stop();}));
 await p.waitForTimeout(300);await fs.writeFile(output+'/native-audio.webm',Buffer.from(sound.base64,'base64'));
 await fs.writeFile(output+'/trace.json',JSON.stringify({viewport:[1920,1080],audioSeconds:sound.seconds,page_errors:errors,records,truth:'New real browser recording with actual WebAudio. Original source, renderer and rules unchanged. Legal preset starting resources and source-provided fixed enemy actions; narrative reenactment, not a natural campaign run.'},null,2));
 const video=p.video();await context.close();await video.saveAs(output+'/raw.webm');assert.deepEqual(errors,[]);
}finally{await browser.close();}
