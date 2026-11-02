import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const [port,output,binary]=process.argv.slice(2);const browser=await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
const c=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,recordVideo:{dir:output,size:{width:390,height:844}}});const p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
const api=(fn,arg)=>p.evaluate(({fn,arg})=>new Function('t','arg',fn)(window.__PAIPAI_TEST__,arg),{fn,arg});
try{
 await p.goto(`http://127.0.0.1:${port}`);await p.evaluate(()=>document.fonts.ready);await p.tap('[data-action="settings"]');await p.tap('[data-action="close"]');
 await api('t.setSave({tutorial:true,settings:{...t.save.settings,music:0,sfx:.8,speed:.7}});t.audio.configure(t.save.settings);return t.audio.unlock()');
 await p.evaluate(()=>{const a=window.__PAIPAI_TEST__.audio,d=a.ctx.createMediaStreamDestination();a.output.connect(d);window.parts=[];window.rec=new MediaRecorder(d.stream,{mimeType:'audio/webm;codecs=opus'});window.rec.ondataavailable=e=>window.parts.push(e.data);window.start=performance.now();window.rec.start();const m=document.createElement('div');m.id='mark';m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#ff00ff;z-index:999999';document.body.append(m);});
 await p.waitForTimeout(300);await p.evaluate(()=>document.getElementById('mark').remove());
 await api('t.home()');await p.waitForTimeout(3000);const setup=await p.evaluate(()=>(performance.now()-window.start)/1000);await p.tap('[data-action="basic"]');await p.waitForTimeout(650);await p.tap('[data-action="start-basic"]');const battle=await p.evaluate(()=>(performance.now()-window.start)/1000);
 for(let i=0;i<2;i++){
  await p.waitForFunction(n=>window.__PAIPAI_TEST__.clock.startState.round===n,i+1);await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.inputOpen);await p.tap('[data-skill="guard1"]');await p.waitForFunction(()=>window.__PAIPAI_TEST__.clock.committed);
 }
 await p.waitForTimeout(250);const log=await api('return {replay:t.exportReplay(),state:t.clock.state,log:t.clock.log,audio:t.audio.log}');
 const sound=await p.evaluate(()=>new Promise(resolve=>{window.rec.onstop=()=>{const f=new FileReader();f.onload=()=>resolve({base64:String(f.result).split(',')[1],seconds:(performance.now()-window.start)/1000});f.readAsDataURL(new Blob(window.parts,{type:'audio/webm'}));};const m=document.createElement('div');m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;background:#00ffff;z-index:999999';document.body.append(m);window.rec.stop();}));
 await p.waitForTimeout(300);await fs.writeFile(output+'/mobile-audio.webm',Buffer.from(sound.base64,'base64'));await fs.writeFile(output+'/mobile-trace.json',JSON.stringify({viewport:[390,844],hasTouch:true,isMobile:true,setup,battle,audioSeconds:sound.seconds,...log,page_errors:errors,truth:'Actual mobile browser viewport and tap inputs; native basic single-player AI; not a painted phone UI or multiplayer.'},null,2));const v=p.video();await c.close();await v.saveAs(output+'/mobile-raw.webm');assert.deepEqual(errors,[]);
}finally{await browser.close();}
