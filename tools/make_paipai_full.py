"""Conform the seven-chapter film from verified original captures and AV trials."""
import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import numpy as np
import requests
from video_rush.common import ROOT,read,write,sha,run,duration,probe,digest,font
from video_rush.render import ass_file
from video_rush.narration import audio_metrics
from video_rush.transfers import download_chunks
from video_rush.paipai_opening import render as draw_opening
from video_rush.paipai_v2_score import compose,Synth
from tools import make_paipai_film as oldfilm,make_paipai_dialogue as dialogue
from tools import make_paipai_matchcut as match,make_paipai_accel as accel
from tools.make_paipai_v2_review import plan_trials,pcm,envelope
from tools.make_wave_story import verify_final_shots


def prepare(spec,out):
    bank=out/'full-inputs'
    if not (bank/'manifest.json').exists():
        groups=json.loads(os.environ['VR_FULL_BANK_GROUPS']);assert len(groups)==len(spec['full_bank_groups'])
        session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
        raw=b''.join(download_chunks(session,os.environ['GITHUB_REPOSITORY'],ids,h) for ids,h in zip(groups,spec['full_bank_groups']))
        if len(raw)!=spec['full_bank_bytes'] or hashlib.sha256(raw).hexdigest()!=spec['full_bank_sha256']:raise ValueError('Full input bank differs')
        z=zipfile.ZipFile(io.BytesIO(raw))
        if sum(i.file_size for i in z.infolist())>20_000_000:raise ValueError('Unexpected bank expansion')
        for name in z.namelist():
            dest=(out/name).resolve()
            if not dest.is_relative_to(out.resolve()):raise ValueError('Unsafe bank member')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    for name,h in read(bank/'manifest.json').items():
        if sha(bank/name)!=h:raise ValueError('Original bank mismatch: '+name)
    for name,h in spec['new_voice_assets'].items():
        if sha(out/name)!=h:raise ValueError('New acted performance mismatch')
    match.prepare(spec,out)
    refs=read('episodes/ep008-r3-film.json')['references']
    from tools.collect_anime_reference import collect
    for key,r in refs.items():
        dest=ROOT/r['file']
        if dest.exists() and sha(dest)==r['sha256']:continue
        dest.parent.mkdir(parents=True,exist_ok=True)
        if r.get('bvid'):
            collect(r['bvid'],'build/research/ep008-r2/anime',cid=r.get('cid'),metadata=r)
            src=ROOT/'build/research/ep008-r2/anime'/(r['bvid']+'.mp4')
            if src!=dest:shutil.copyfile(src,dest)
        else:
            response=requests.get(r['url'],timeout=60);response.raise_for_status();dest.write_bytes(response.content)
        if sha(dest)!=r['sha256']:raise ValueError('Reference changed: '+key)
    for name,r in spec['native_claps'].items():
        dest=out/'extra'/name
        if not dest.exists() or sha(dest)!=r['sha256']:
            response=requests.get(r['url'],timeout=30);response.raise_for_status();dest.write_bytes(response.content)
        if sha(dest)!=r['sha256']:raise ValueError('Native clap changed')


def plan(spec,out):
    bank=read(out/'full-inputs/bank.json');original=bank['original_storyboard'];byid={s['id']:copy.deepcopy(s) for s in original['shots']}
    for layer in byid['3-03']['layers']:
        if layer['layer']=='AN' and layer['source']=='sore':layer.update(**{'in':154.50,'out':156.50,'at':.10,'seconds':2.0})
        if layer['layer']=='AN' and layer['source']=='cylinder':layer.update(**{'in':37.95,'out':39.60,'at':2.95,'seconds':1.65})
    for layer in byid['5-06']['layers']:
        if layer['layer']=='AN':layer.update(seconds=.80,out=layer['in']+.80)
    p={'segments':[],'voices':[],'seconds':0,'original':original,'bank':bank,'chapters':{}}
    def add(s,chapter):
        s=copy.deepcopy(s);s.update(start=p['seconds'],id=f"f-{len(p['segments']):03}",chapter=chapter)
        p['chapters'].setdefault(str(chapter),s['start']);p['segments'].append(s);p['seconds']+=s['seconds'];return s
    def voice(id,path,start,text,source_in=0,seconds=None):
        n=duration(path)-source_in if seconds is None else seconds;p['voices'].append({'id':id,'path':str(path),'start':start,'source_in':source_in,'seconds':n,'text':text})
    def legacy(id,chapter,trim=0):
        s=byid[id];s['legacy_id']=id
        a=add({'kind':'FILM','seconds':s['seconds']-trim,'shot':s,'trim':trim},chapter)
        for line in s['scheduled_lines']:
            voice(line['id'],out/'full-inputs'/bank['voices'][line['id']]['file'],a['start']+line['start']-trim,line['text'],seconds=line['end']-line['start'])
        return a
    n=duration(out/'extra/OPEN-ADULT.m4a');s=add({'kind':'OPEN','mode':'intro','seconds':match.round_frame(n+.61)},1);voice('OPEN-ADULT',out/'extra/OPEN-ADULT.m4a',.25,'日复一日的一天。')
    s=add({'kind':'OPEN','mode':'boss','seconds':2.0},1);p['boss_start']=s['start'];voice('1-01-0',out/'full-inputs'/bank['voices']['1-01-0']['file'],s['start']+.78,'好的好的……')
    for id in ['1-02','1-03','1-04']:legacy(id,1)
    for id in ['2-01','2-02','2-03','2-04']:legacy(id,2)
    for id in ['3-01','3-02','3-03']:legacy(id,3)
    # Keep A's objection, then a single newly acted B performance. The full
    # 9-second audition is trimmed to the spoken rule declaration, not replayed.
    a=byid['3-04A'];a['lines']=a['lines'][:1];a['scheduled_lines']=a['scheduled_lines'][:1];a['seconds']=match.round_frame(a['scheduled_lines'][0]['end']+.15);legacy('3-04A',3)
    b=byid['3-04B'];b['seconds']=match.round_frame(5.70+.15);b['scheduled_lines']=[{'speaker':'evilB','text':'规则，就是用来打破的！有趣即是正义！','start':.06,'end':5.76}]
    s=add({'kind':'FILM','seconds':b['seconds'],'shot':b,'trim':0},3);p['villain_at']=s['start'];voice('K01-B',out/'portable/voices/K01-B.m4a',s['start']+.06,b['scheduled_lines'][0]['text'],source_in=1.0,seconds=5.70)
    wave=dialogue.plan(spec,out);wave_offset=p['seconds'];p['wave_offset']=wave_offset;p['rock_at']=wave_offset+wave['idea_at']-.10;p['wave_peak']=wave_offset+wave['peak_at']
    # Omit only the review-only end hold; the next real AT reversal follows.
    ending=wave['segments'][-1];extra=max(0,wave['seconds']-match.round_frame(wave['speech_end']+.12));ending['seconds']-=extra
    for s in wave['segments']:add(s,3 if s['start']<wave['idea_at'] else 4)
    for v in wave['voices']:q=copy.deepcopy(v);q['start']+=wave_offset;p['voices'].append(q)
    p['wave_end']=p['seconds'];p['light_at']=wave_offset
    for id in ['4-05','4-06','4-07']:legacy(id,4)
    for id in ['5-01','5-02']:legacy(id,5)
    hero=plan_trials(read(spec['inherits']),out)[2];hero_offset=p['seconds'];p['dio_at']=hero_offset;p['hero_at']=hero_offset+hero['hero_entry'];p['hero_peak']=hero_offset+hero['peak_at']
    for s in hero['segments']:add(s,5)
    for v in hero['voices']:q=copy.deepcopy(v);q['start']+=hero_offset;p['voices'].append(q)
    # The beam already includes the victory window: avoid showing it twice.
    byid['5-06']['layers']=[l for l in byid['5-06']['layers'] if l['layer']!='G']
    legacy('5-06',5,trim=.60)
    for id in ['6-01','6-02','6-03','6-04']:legacy(id,6)
    for id in ['7-01','7-02','7-03','7-04']:legacy(id,7)
    for s in p['segments']:
        if s.get('shot',{}).get('id')=='3-03':
            # Actual trap-card quote, separate from TTS. Timings are source windows.
            for ref,a,b,at,text in [('sore',154.50,157.30,.10,'那可不一定。'),('cylinder',37.95,40.75,2.95,'陷阱发动——魔法筒！')]:
                voice('QUOTE-'+ref,ROOT/read('episodes/ep008-r3-film.json')['references'][ref]['file'],s['start']+at,text,a,b-a)
    validate(p);return p


def validate(p):
    if set(p['chapters'])!=set('1234567'):raise ValueError('Missing story chapter')
    voices=sorted(p['voices'],key=lambda v:v['start'])
    if any(a['start']+a['seconds']>b['start']+.04 for a,b in zip(voices,voices[1:])):raise ValueError('Overlapping foreground dialogue')
    if any(v['start']<0 or v['start']+v['seconds']>p['seconds']+.03 for v in voices):raise ValueError('Dialogue outside movie')
    if next(v['text'] for v in voices if v['id']=='CREATE-A')!='到我创造了，三格气的大招！':raise ValueError('Exact requested bridge changed')
    if any('我的反弹呢' in v['text'] or '那……三格气呢' in v['text'] or v['id'].startswith('3-04D') for v in voices):raise ValueError('Removed old dialogue returned')
    if sum(v['id']=='JP-HADOUKEN' for v in voices)!=1:raise ValueError('Hadouken shout duplicated')


def opening_audio(s,out):
    sr=24000;n=round(s['seconds']*sr);t=np.arange(n)/sr
    if s['mode']=='intro':return np.zeros((n,2),np.float32)
    pulse=np.zeros(n,np.float32)
    for a,b in [(.14,.38),(.44,.70),(.97,1.19),(1.26,1.42)]:
        x=int(a*sr);y=min(n,int(b*sr));pulse[x:y]=np.sin(np.linspace(0,np.pi,y-x))**.3
    pulse[t>.77]*=.23
    v=(np.sin(2*np.pi*(180*t+4*np.sin(t*50)))+.4*np.sin(2*np.pi*540*t))*pulse*.20
    return np.stack([v,v],axis=1).astype(np.float32)


def signal_envelope(a,seconds):
    return [float(np.sqrt(np.mean(a[round(n*24000/30):max(round((n+1)*24000/30),round(n*24000/30)+1)]**2))) for n in range(round(seconds*30))]


def render_segments(p,out):
    oldspec=read('episodes/ep008-r3-film.json');bank=p['bank']
    for s in p['segments']:
        if s['kind']=='OPEN':
            fx=opening_audio(s,out);worker=np.zeros_like(fx)
            if s['mode']=='boss':
                v=next(v for v in p['voices'] if v['id']=='1-01-0');a=pcm(v['path'],0,v['seconds']);x=round(.78*24000);worker[x:x+len(a)]+=a
            s['boss_envelope']=signal_envelope(fx,s['seconds']);s['worker_envelope']=signal_envelope(worker,s['seconds'])
            target=out/'segments'/(s['id']+'.mp4');draw_opening(target,s['mode'],s['seconds'],worker=s['worker_envelope'],boss=s['boss_envelope'])
        elif s['kind']=='FILM':
            shot=s['shot'];resolved={}
            for i,l in enumerate(shot['layers']):
                if l['layer']=='G':
                    r=bank['game'][shot['id']+'_'+str(i)];resolved[i]={'path':out/'full-inputs'/r['file'],'in':0,'cropped':r['cropped']}
            scratch=out/'legacy';(scratch/'segments').mkdir(parents=True,exist_ok=True);(scratch/'r-animation').mkdir(exist_ok=True);(scratch/'logs').mkdir(exist_ok=True)
            path=oldfilm.visual_shot(shot,oldspec,scratch,layer_inputs=resolved);dest=out/'segments'/(s['id']+'.mp4')
            if s['trim']:
                run(['ffmpeg','-v','error','-y','-ss',s['trim'],'-i',path,'-t',s['seconds'],'-an','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p',dest])
            else:shutil.copyfile(path,dest)
        elif s['kind']=='MATCH':
            match.draw_match(out/'segments'/(s['id']+'.mp4'),s['phase'],s['seconds'],action_at=s.get('action_at',0),envelope=s.get('envelope'),previous=s.get('previous'))
        else:dialogue.segment(out,s)
        print('Rendered full',s['id'],s['kind'],round(s['seconds'],2),flush=True)


def score(p,spec,out,voice_ranges):
    sr=24000;n=math.ceil(p['seconds']*sr);result=np.zeros((n,2),np.float32);music=out/'music';music.mkdir(exist_ok=True);sf=ROOT/read(spec['inherits'])['music']['soundfont_path']
    title=next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='7-04')
    sections=[('deadpan',0,p['chapters']['2'],None),('warm',p['chapters']['2'],p['chapters']['3'],None),('battle',p['chapters']['3'],p['villain_at'],None),('villain',p['villain_at'],p['rock_at'],None),('rock',p['rock_at'],p['dio_at'],p['wave_peak']),('heroic',p['hero_at'],p['chapters']['6'],p['hero_peak']),('reprise',p['chapters']['6'],title,None)]
    cues=[]
    for i,(style,start,end,peak) in enumerate(sections):
        length=end-start;path=compose(music/(str(i)+'-'+style+'.wav'),sf,style,length,None if peak is None else peak-start);a=pcm(path)[:round(length*sr)]
        gain=.13 if style in ['deadpan','warm','reprise'] else .27
        if style=='deadpan':gain=.045
        x=round(start*sr);result[x:x+len(a)]+=a*gain;cues.append({'style':style,'in':start,'out':end,'peak':peak,'source':'Original same-motif arrangement with MIT FluidR3 GM samples'})
    # Quiet reply after the actual first hit, before the next AT reversal.
    end_game=next(s['start']+s['seconds'] for s in p['segments'] if s['kind']=='G' and s.get('round')==8)
    result[round(end_game*sr):round(p['wave_end']*sr)]*=.12
    # Short original phrase resolves to E at the film title, with a real release.
    events=[]
    for i,key in enumerate([76,71,69,67,64]):
        t=.08+i*.17;events.extend([(t,1,7,key,62),(t+.18,-1,7,key,0)])
    for key in [52,56,59,64]:events.extend([(.77,1,7,key,44),(1.17,-1,7,key,0)])
    a=Synth(sf).perform(events,p['seconds']-title);a*=.30/max(.001,np.max(np.abs(a)));a[-min(len(a),9600):]*=np.linspace(1,0,min(len(a),9600))[:,None];x=round(title*sr);result[x:x+len(a)]+=a
    # Look-ahead ducking with a short release; quiet holds and one DIO hard stop.
    t=np.arange(n)/sr;duck=np.ones(n,np.float32)
    for start,end in voice_ranges:duck=np.minimum(duck,1-.74*np.minimum(np.clip((t-(start-.04))/.04,0,1),1-np.clip((t-end)/.18,0,1)))
    result*=duck[:,None];write(music/'design.json',{'sections':cues,'DIO_music_silence':[p['dio_at'],p['hero_at']],'reply_duck':[end_game,p['wave_end']],'final_cadence':title,'same_motif':'E G A B E, major reprise raises G','user_music_review':'pending'})
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','aac','-b:a','128k',str(music/'full-score.m4a')],input=result.astype('<f4').tobytes(),check=True)
    return result


def mix(p,spec,out):
    sr=24000;n=math.ceil(p['seconds']*sr);master=np.zeros((n,2),np.float32);ranges=[]
    def add(a,start,gain=1):
        x=round(start*sr);count=min(len(a),n-x)
        if count>0:master[x:x+count]+=a[:count]*gain
    def tone(length,hz,gain=.15):
        t=np.arange(round(length*sr))/sr;v=np.sin(2*np.pi*hz*t)*np.exp(-t*10)*gain;return np.stack([v,v],axis=1).astype(np.float32)
    for v in p['voices']:
        a=pcm(v['path'],v['source_in'],v['seconds'])
        if v['id']=='5-06-1':
            older=oldfilm.pcm(v['path'],v['source_in'],v['seconds'],pitch=.88);count=min(len(a),len(older));ramp=np.clip((np.arange(count)-(count-.4*sr))/(.4*sr),0,1);a[:count]=a[:count]*(1-ramp[:,None])+older[:count]*ramp[:,None]
        add(a,v['start'],.85 if v['id'].startswith('QUOTE') else 1);ranges.append((v['start'],v['start']+v['seconds']))
    clap1=pcm(out/'extra/clap1.wav');clap2=pcm(out/'extra/clap2.wav')
    for s in p['segments']:
        if s['kind']=='OPEN':add(opening_audio(s,out),s['start']);continue
        if s['kind']=='G':add(pcm(s['source'],s['in'],s['seconds']),s['start'],.62);continue
        if s['kind']!='FILM':continue
        shot=s['shot'];start=s['start']-s['trim'];id=shot['id']
        for i,l in enumerate(shot['layers']):
            if l['layer']!='G':continue
            r=p['bank']['game'][id+'_'+str(i)];gain=.18 if id=='3-03' else .45 if shot['scheduled_lines'] else .70
            a=pcm(out/'full-inputs'/r['file'],0,l['seconds'])
            if id=='4-07':
                before=max(0,p['original']['capture']['rounds'][14]['launch']-l['in']);a[:round(before*sr)]*=.12
            add(a,start+l['at'],gain)
        effect=shot.get('sfx')
        if effect in ['clap2','clap-end']:add(clap1,start+.02,.75)
        if effect=='clap2':add(clap2,start+.62,.75)
        if effect=='ding':add(tone(.35,1900)+tone(.35,2837,.08),start+.02)
        if effect=='poweroff':
            for j,hz in enumerate([880,550,220]):add(tone(.16,hz),start+.05+j*.1)
        if effect=='bell':add(tone(.7,2200,.12)+tone(.7,3103,.07),start+.70)
        if effect=='baby':
            t=np.arange(round(shot['seconds']*sr))/sr;phase=2*np.pi*(500*t+80*np.sin(2*np.pi*2.6*t)/(2*np.pi*2.6));v=(np.sin(phase)+.35*np.sin(phase*2))*(.5+.5*np.sin(2*np.pi*3*t))*.10;add(np.stack([v,v],axis=1),start)
    refs=read('episodes/ep008-r3-film.json')['references'];laugh=ROOT/refs['evil_laugh']['file'];add(pcm(laugh,0,3.8),p['light_at']+2.2,.6);ranges.append((p['light_at']+2.2,p['light_at']+6))
    ghost=next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='7-03')-.18
    for name,offset,gain in [('adult',0,.35),('child',.35,.20)]:add(pcm(out/'full-inputs'/p['bank']['voices']['ending-laugh-'+name]['file']),ghost+offset,gain)
    master+=score(p,spec,out,ranges);path=out/'mix.wav';subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','pcm_f32le',str(path)],input=master.astype('<f4').tobytes(),check=True);return path


def render(spec,out):
    for name in ['segments','logs']:(out/name).mkdir(exist_ok=True)
    p=plan(spec,out);render_segments(p,out);write(out/'storyboard.json',p)
    rows=[{'start':v['start'],'end':v['start']+v['seconds'],'cues':[{'start':v['start'],'end':v['start']+v['seconds'],'text':v['text']}],'emphasis':'','provenance_label':''} for v in p['voices']];ass_file(out/'subtitles.ass',{'display_chapters':False,'shots':rows})
    audio=mix(p,spec,out);f=out/'concat.txt';f.write_text(''.join(f"file '{out/'segments'/(s['id']+'.mp4')}'\n" for s in p['segments']));run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',f,'-c','copy',out/'joined.mp4'])
    movie=out/'final.mp4';run(['ffmpeg','-v','error','-y','-reinit_filter','0','-i',out/'joined.mp4','-i',audio,'-filter_complex',f'[0:v]setpts=PTS-STARTPTS,ass={out/"subtitles.ass"},fps=30,format=yuv420p[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=12,aresample=48000[a]','-map','[v]','-map','[a]','-t',p['seconds'],'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-color_range','tv','-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',movie],log=out/'logs/final.log',timeout=900)
    run(['ffmpeg','-v','error','-i',movie,'-f','null','-'],log=out/'logs/decode.log');checks=verify_final_shots(movie,p['segments'],out/'segments');write(out/'frame-checks.json',checks)
    if not all(c['passed'] for c in checks):raise ValueError('A full-film shot disappeared')
    info=probe(movie);v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio');metrics=audio_metrics(movie)
    if (v['width'],v['height'],v['avg_frame_rate'],v['codec_name'],a['codec_name'])!=(1920,1080,'30/1','h264','aac') or metrics['clipped_fraction']>.0001:raise ValueError('Full media gate failed')
    # Find opening audio lag after final mux; compare a downsampled waveform,
    # not just declared packet timestamps. Loudness normalization changes gain.
    expected=pcm(audio,p['boss_start'],1.55).mean(axis=1)[::8];actual=pcm(movie,p['boss_start']-.15,1.85).mean(axis=1)[::8];corr=np.correlate(actual,expected,'valid');lag=(int(np.argmax(corr))/3000-.15)*1000
    if abs(lag)>50:raise ValueError('Opening waveform offset exceeds50ms: '+str(lag))
    write(out/'opening-sync.json',{'measured_final_audio_lag_ms':lag,'threshold_ms':50,'method':'Final AAC waveform cross-correlation against pre-mux opening master, 3000Hz sample grid','boss_and_worker_envelopes':'Each mouth reads its own actual voice/SFX energy at the same30fps clock; no fixed-frequency mouth loop','subtitle_and_voice_start':{v['id']:v['start'] for v in p['voices'][:2]},'perceptual_lip_sync':'pending phone review'})
    scan=subprocess.run(['ffmpeg','-hide_banner','-i',str(movie),'-vf','blackdetect=d=0.8:pix_th=0.04,freezedetect=n=-50dB:d=3','-an','-f','null','-'],capture_output=True,text=True,check=True);(out/'logs/visual-scan.log').write_text(scan.stderr);events=[s for s in scan.stderr.splitlines() if 'black_start:' in s or 'freeze_start:' in s]
    if events:raise ValueError('Unexpected long black/freeze: '+str(events))
    write(out/'report.json',{'status':'technical_pass_pending_full_phone_review','duration':duration(movie),'sha256':sha(movie),'audio':metrics,'all_shots_present':True,'chapters':7,'opening_sync_ms':lag,'long_black_or_freeze_events':events,'exact_bridge':'到我创造了，三格气的大招！','new_opening':'日复一日的一天。','B_reaction':'还能这样？！','full_film':True,'git_head':run(['git','rev-parse','HEAD']).strip(),'creative_and_full_listening_review':'pending user','bilibili_or_toy_submission':False});print('FULL FILM READY',movie,duration(movie),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='build/episodes/ep008-v6-full');a=parser.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);spec=read('episodes/ep008-v6-full.json');prepare(spec,out);render(spec,out)
