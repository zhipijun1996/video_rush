// Reuses wave-game's documented localhost-only __PAIPAI_TEST__ and real DOM
// controls, following its scripts/capture.ts. No renderer/rules are replaced.
import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const [port,which,output,binary]=process.argv.slice(2);
const cases={hadoken:['wave2','charge'],beam:['wave3','charge'],dual:['wave3','wave2'],at:['guard2','wave2'],psycho:['guard3','wave3'],cylinder:['reflect1','wave1'],fan:['reflect2','wave2'],return:['wave2','reflect2'],'pan-break':['guard1','wave3'],'quick-hit':['quick','wave1'],clash:['wave1','wave3'],victory:['wave1','charge']};
assert(cases[which]||['normal','classic','menus','story','streak'].includes(which),'Unknown capture case');
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
const context=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:output,size:{width:1920,height:1080}}});
const page=await context.newPage(),errors=[],observations=[];
page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
const t=(fn,arg)=>page.evaluate(({fn,arg})=>new Function('t','arg',fn)(window.__PAIPAI_TEST__,arg),{fn,arg});
try {
 await page.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);
 await page.click('[data-action="settings"]');await page.click('[data-action="close"]');
 await t('t.setSave({completed:8,tutorial:true,skin:"ribbon",settings:{...t.save.settings,speed:1,music:0,sfx:0}});t.audio.configure(t.save.settings);t.home()');
 const mark=async color=>page.evaluate(c=>{let m=document.getElementById('vr-sync');if(!m){m=document.createElement('div');m.id='vr-sync';m.style.cssText='position:fixed;left:0;top:0;width:16px;height:16px;z-index:999999';document.body.append(m);}m.style.background=c;},color);
 await mark('#ff00ff');const wallStart=await page.evaluate(()=>performance.now());await page.waitForTimeout(250);await page.evaluate(()=>document.getElementById('vr-sync').remove());
 if(which==='menus'||which==='story'){
   await t('t.setSave({completed:arg,tutorial:true});t.home()',which==='story'?0:8);
   await page.waitForTimeout(3000);await page.click('[data-action="story"]');await page.waitForTimeout(4500);
   if(which==='story'){await page.click('[data-level="0"]');await page.waitForTimeout(2500);await page.click('[data-action="start-story"]');}
   else {await t('t.home()');await page.click('[data-action="advanced"]');await page.waitForTimeout(3500);await page.click('[data-action="close"]');await page.click('[data-action="skins"]');}
 }
 if(cases[which]||which==='streak'){
   const [a,b]=cases[which]||['wave1','charge'];
   const state={players:[{hp:5,energy:8,blocked:false,skills:['charge','quick','wave1','wave2','wave3','guard1','guard2','guard3','reflect1','reflect2']},{hp:which==='victory'||which==='streak'?1:5,energy:8,blocked:false,skills:['charge','quick','wave1','wave2','wave3','guard1','guard2','guard3','reflect1','reflect2']}],round:1};
   // Use the game's own initial state shape; update only legal starting HP/qi.
   await t('t.start("advanced",{enemy:arg.b,speed:1,streak:arg.streak});const s=structuredClone(t.clock.startState);s.players.forEach((p,i)=>{p.energy=8;if(i===1&&arg.win)p.hp=1});t.start("advanced",{state:s,enemy:arg.b,speed:1,streak:arg.streak})',{b,win:which==='victory'||which==='streak',streak:which==='streak'});
   await page.waitForFunction(()=>window.__PAIPAI_TEST__.clock.inputOpen);await page.click(`[data-skill="${a}"]`);
   await page.waitForFunction(()=>window.__PAIPAI_TEST__.clock.committed);
   observations.push(await t('return {case:arg,initial:t.clock.startState,result:t.clock.result,state:t.clock.state,log:t.clock.log}',which));
   await page.screenshot({path:output+'/action.png'});
   if(which==='streak'){await page.locator('[data-action="next-streak"]').waitFor();await page.click('[data-action="next-streak"]');}
 }
 if(which==='normal'||which==='classic')await t('t.start(arg.kind,{seed:173,health:3,difficulty:"normal",speed:1})',{kind:which==='normal'?'advanced':'basic'});
 const deadline=which==='normal'?58:which==='classic'?38:which==='story'?25:18;
 while((await page.evaluate(()=>performance.now())-wallStart)/1000<deadline){
   const state=await t('return t.clock?{open:t.clock.inputOpen,round:t.clock.startState.round,finished:t.clock.finished,state:t.clock.startState}:null');
   if(state?.finished){
      observations.push(await t('return {replay:t.exportReplay(),state:t.clock.state,result:t.clock.result,log:t.clock.log}'));
      await page.waitForTimeout(650);
      const again=page.locator('[data-action="rematch"]');if(await again.isVisible())await again.click();
   }else if(state?.open){
      let id='charge';
      if(which==='normal'||which==='classic'||which==='story'||which==='streak'){
        const [me,enemy]=state.state.players,skills=me.skills;
        if(me.blocked)id='guard1';
        else if(enemy.energy===0&&me.energy>=1)id='wave1';
        else if(enemy.energy>=3&&me.energy>=2&&skills.includes('guard3'))id='guard3';
        else if(enemy.energy>=1&&me.energy>=2&&skills.includes('reflect2'))id='reflect2';
        else if(me.energy>=3&&skills.includes('wave2'))id='wave2';
      }else if(state.round>=2)await t('t.setEnemy("charge")');
      const button=page.locator(`[data-skill="${id}"]`);
      if(await button.getAttribute('aria-disabled')==='false')await button.click();
      await page.waitForTimeout(700);
   }else await page.waitForTimeout(60);
 }
 if(await t('return !!t.clock'))observations.push(await t('return {replay:t.exportReplay(),state:t.clock.state,log:t.clock.log}'));
 await page.screenshot({path:output+'/end.png'});
 const wallEnd=await page.evaluate(()=>performance.now());await mark('#00ffff');await page.waitForTimeout(300);
 await fs.writeFile(output+'/trace.json',JSON.stringify({case:which,viewport:[1920,1080],wall_seconds:(wallEnd-wallStart)/1000,page_errors:errors,observations,source_audio:'Muted in the actual game settings for licensed editorial narration/score. No franchise recording excerpts redistributed.',mode:which==='normal'||which==='classic'?'Native sealed AI, player policy only reads public state. No enemy override.':'Source-provided preset action/progress fixture or real UI; not natural campaign completion.'},null,2));
 const video=page.video();await context.close();await video.saveAs(output+'/raw.webm');
 assert.deepEqual(errors,[]);console.log('Recorded actual game',which,(wallEnd-wallStart)/1000);
} finally {await browser.close();}
