// Observer-only replay of one continuous legal battle using original game rules,
// controls, rendering and WebAudio. No mid-battle resource/health injection.
import {chromium} from '@playwright/test';
import {initial,ALL,resolve} from './src/rules.ts';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const [port,output,binary,victoryHold='1650']=process.argv.slice(2);
assert(Number(victoryHold)>=1650 && Number(victoryHold)<=6000);
const moves=[['charge','charge'],['wave1','guard1'],['charge','charge'],['wave1','reflect1'],
 ['charge','charge'],['charge','charge'],['charge','charge'],['wave2','reflect1'],
 ['charge','charge'],['charge','charge'],['charge','charge'],['wave2','guard2'],
 ['charge','charge'],['charge','charge'],['reflect2','wave2'],
 ['charge','charge'],['charge','charge'],['charge','charge'],['charge','charge'],['charge','charge'],['wave3','reflect2']];
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
const context=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:output,size:{width:1920,height:1080}}});
const p=await context.newPage();p.setDefaultTimeout(12000);const errors=[],rounds=[];p.on('pageerror',e=>errors.push(e.message));
const api=(fn,arg)=>p.evaluate(({fn,arg})=>new Function('t','arg',fn)(window.__PAIPAI_TEST__,arg),{fn,arg});
const perf=()=>p.evaluate(()=>(performance.now()-window.vrAudioStart)/1000);
try{
 await p.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
 await p.click('[data-action="settings"]');await p.click('[data-action="close"]');
 await api('t.setSave({completed:8,tutorial:true,skin:"ribbon",settings:{...t.save.settings,speed:.7,music:0,sfx:.8}});t.audio.configure(t.save.settings);return t.audio.unlock()');
 await p.evaluate(()=>{const a=window.__PAIPAI_TEST__.audio,d=a.ctx.createMediaStreamDestination();a.output.connect(d);window.vrChunks=[];window.vrRecorder=new MediaRecorder(d.stream,{mimeType:'audio/webm;codecs=opus'});window.vrRecorder.ondataavailable=e=>window.vrChunks.push(e.data);window.vrAudioStart=performance.now();window.vrRecorder.start();window.vrEvents=[];const m=document.createElement('div');m.id='vr-sync';m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#ff00ff;z-index:999999';document.body.append(m);});
 await p.waitForTimeout(350);await p.evaluate(()=>document.getElementById('vr-sync').remove());
 const battleStart=await perf();await api('t.start("advanced",{enemy:"charge",speed:.7,seed:173});const clock=t.clock,original=clock.onEvent;clock.onEvent=type=>{original(type);window.vrEvents.push({type,round:clock.startState.round,seconds:(performance.now()-window.vrAudioStart)/1000});}');
 const canvas=await p.locator('.stage-canvas').boundingBox();let previous=initial(5,ALL);
 for(let i=0;i<moves.length;i++){
  await p.waitForFunction(n=>window.__PAIPAI_TEST__.clock.startState.round===n,i+1);
  const before=await api('return {state:t.clock.startState,locked:t.clock.locked}');assert.deepEqual(before.state,previous);assert(!before.locked);
  // Select the fixed opponent action BEFORE the public player input window.
  await api('t.setEnemy(arg)',moves[i][1]);
  await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.inputOpen);await p.click(`[data-skill="${moves[i][0]}"]`);
  await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.committed);
  const rec=await api('return {initial:t.clock.startState,result:t.clock.result,state:t.clock.state,log:t.clock.log,audio:t.audio.log,events:window.vrEvents}');
  const expected=resolve(previous,moves[i]);assert.deepEqual(rec.result.actions,moves[i]);assert.deepEqual(rec.state,expected.next);
  const events=rec.events.filter(e=>e.round===i+1);const start=i===0?battleStart:events.find(e=>e.type==='start').seconds;
  const launch=events.find(e=>e.type==='launch')?.seconds;const reveal=events.find(e=>e.type==='reveal')?.seconds;
  const commit=events.find(e=>e.type==='commit').seconds;
  rounds.push({round:i+1,start,launch,reveal,commit,initial:rec.initial,result:rec.result,state:rec.state,log:rec.log});previous=rec.state;
  if([2,4,8,12,15,21].includes(i+1))await p.screenshot({path:`${output}/round-${i+1}.png`});
  console.log('Real round',i+1,moves[i].join(' / '),rec.result.damage,rec.state.players.map(x=>x.hp));
 }
 assert.equal(rounds[14].result.actions[0],'reflect2');assert.equal(rounds[14].result.events.find(e=>e.type==='reflect').side,0);
 const last=rounds.at(-1);assert(last.initial.players[0].energy>=5);assert(last.initial.players[1].energy>=2);assert(last.initial.players[1].hp<=3);assert.equal(last.result.winner,0);
 await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.phase==='victory');await p.waitForTimeout(Number(victoryHold));const battleEnd=await perf();
 await api('t.home()');const homeStart=await perf();await p.waitForTimeout(2600);await p.screenshot({path:output+'/home.png'});
 await p.click('[data-action="basic"]');await p.waitForTimeout(400);await p.click('[data-action="start-basic"]');const phoneStart=await perf();
 await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.inputOpen);await p.click('[data-skill="guard1"]');await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.committed);await p.waitForTimeout(100);const phoneEnd=await perf();
 const actualAudio=await api('return t.audio.log');
 const sound=await p.evaluate(()=>new Promise(resolve=>{window.vrRecorder.onstop=()=>{const b=new Blob(window.vrChunks,{type:'audio/webm'}),f=new FileReader();f.onload=()=>resolve({base64:String(f.result).split(',')[1],seconds:(performance.now()-window.vrAudioStart)/1000});f.readAsDataURL(b);};const m=document.createElement('div');m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#00ffff;z-index:999999';document.body.append(m);window.vrRecorder.stop();}));
 await p.waitForTimeout(300);await fs.writeFile(output+'/native-audio.webm',Buffer.from(sound.base64,'base64'));
 await fs.writeFile(output+'/trace.json',JSON.stringify({viewport:[1920,1080],canvas,battleStart,battleEnd,homeStart,phoneStart,phoneEnd,audioSeconds:sound.seconds,rounds,actualAudio,page_errors:errors,truth:'One continuous 21-round legal battle from 5 HP and zero energy; fixed opponent action sealed before player window; original source rules/renderer/audio unchanged. Epilogue uses actual basic single-player UI and guard input. New recording, not a historical original or online multiplayer.'},null,2));
 const video=p.video();await context.close();await video.saveAs(output+'/raw.webm');assert.deepEqual(errors,[]);
}finally{await browser.close();}
