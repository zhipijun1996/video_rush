"""One continuous revised transition: Light's idea -> Japanese Hadouken.

V2 stays intact. R/AN use ordered phases of one action; game results are real.
"""
import argparse
import copy
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import zipfile
import numpy as np
import requests
from video_rush.common import ROOT,read,write,sha,digest,duration,run,probe
from video_rush.narration import audio_metrics
from video_rush.render import ass_file
from video_rush.paipai_match_art import render as draw_match
from video_rush.paipai_v2_score import compose
from tools.make_paipai_v2_review import plan_trials,segment,round_frame,pcm,envelope,new_voice
from tools.make_wave_story import verify_final_shots


CUTS=[
    ('MATCH','hands',.30,None),('AN','hands',.40,189.35),
    ('MATCH','torso',.23,None),('AN','torso',.55,191.58),
    ('MATCH','mouth',.17,None),('AN','mouth',.30,192.90),
    ('MATCH','face',.17,None),('AN','face',.32,193.65),
    ('MATCH','palm',.17,None),('AN','palm',.15,194.40)]


def prepare(spec,out):
    """Reuse the previous approved audition bank; only the new bridge is new."""
    from tools.paipai_v2_assets import prepare as prepare_base
    previous=ROOT/'build/deliveries/paipai-v2-final-review-remote'
    if not (out/'portable/manifest.json').exists():
        if (previous/'portable/manifest.json').exists():shutil.copytree(previous/'portable',out/'portable',dirs_exist_ok=True)
        else:
            import os,hashlib
            session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
            url=f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/actions/artifacts/{spec["previous_review_artifact"]}/zip'
            r=session.get(url,timeout=90);r.raise_for_status()
            if hashlib.sha256(r.content).hexdigest()!=spec['previous_review_zip_sha256']:raise ValueError('Previous review archive differs')
            z=zipfile.ZipFile(io.BytesIO(r.content))
            for n in z.namelist():
                if n.startswith('portable/'):
                    target=(out/n).resolve()
                    if not target.is_relative_to(out.resolve()):raise ValueError('Unsafe archive path')
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(n))
    for n,h in read(out/'portable/manifest.json').items():
        if sha(out/'portable'/n)!=h:raise ValueError('Preserved bank hash mismatch')
    shutil.copyfile(out/'portable/alignments.json',out/'alignments.json')
    base=read(spec['inherits']);prepare_base(base,out)
    extra=out/'extra';extra.mkdir(exist_ok=True);jp=extra/'hadouken-original.wav';ref=spec['japanese_hadouken']
    if not jp.exists() or sha(jp)!=ref['sha256']:
        r=requests.get(ref['url'],timeout=30);r.raise_for_status();jp.write_bytes(r.content)
    if sha(jp)!=ref['sha256']:raise ValueError('Japanese source hash mismatch')
    run(['ffmpeg','-v','error','-y','-i',jp,'-af','loudnorm=I=-17:TP=-1.5:LRA=11','-ar','48000','-ac','1','-c:a','aac','-b:a','96k',extra/'hadouken-jp.m4a'])
    bridge=extra/'idea-bridge.m4a'
    if not bridge.exists():
        import os
        from video_rush.transfers import download_chunks
        session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
        raw=download_chunks(session,os.environ['GITHUB_REPOSITORY'],json.loads(os.environ['VR_BRIDGE_ARTIFACTS']),spec['bridge_voice']['sha256']);bridge.write_bytes(raw)
    if sha(bridge)!=spec['bridge_voice']['sha256']:raise ValueError('New idea performance differs')


def plan(spec,out):
    base=read(spec['inherits']);old=plan_trials(base,out);light=old[0];wave=old[1]
    p={'id':'light_to_hadouken','segments':[],'voices':[],'seconds':0,'matches':[]}
    def add(kind,seconds,**kwargs):
        s={'id':'mc-'+str(len(p['segments'])).zfill(2),'kind':kind,'start':p['seconds'],'seconds':round_frame(seconds),**kwargs};p['segments'].append(s);p['seconds']+=s['seconds'];return s
    for s in light['segments']:
        if s['start']>=light['dry_break']-.01:break
        q=copy.deepcopy(s);q['id']='mc-'+str(len(p['segments'])).zfill(2);p['segments'].append(q);p['seconds']=q['start']+q['seconds']
    p['voices']=[copy.deepcopy(v) for v in light['voices'] if v['start']<light['dry_break']-.01]
    p['anime_laugh_start']=light['anime_laugh_start'];p['idea_at']=p['seconds'];last=p['segments'][-1]
    bridge=out/'extra/idea-bridge.m4a';n=duration(bridge)
    add('MATCH',n+.25,phase='idea',action_at=0,previous={'seconds':last['seconds'],'envelope':last.get('envelope')})
    p['voices'].append({'id':'IDEA-A','path':str(bridge),'start':p['idea_at']+.10,'source_in':0,'seconds':n,'text':'那……三格气呢？'})
    # A short surprised response takes the place of a second rule discussion.
    start=p['seconds'];b=new_voice(out,'old-4-01-1');add('R',duration(b)+.10,mode='light_break',envelope=envelope(b));p['voices'].append({'id':'old-4-01-1','path':str(b),'start':start+.02,'source_in':0,'seconds':duration(b),'text':'哈？！'})
    for s in wave['segments']:
        if s['kind']=='G' and s.get('round') in (5,6,7):
            a=copy.deepcopy(s);a.update(id='mc-'+str(len(p['segments'])).zfill(2),start=p['seconds']);p['segments'].append(a);p['seconds']+=a['seconds']
    p['action_start']=p['seconds'];jp=out/'extra/hadouken-jp.m4a';mouth_at=None;refs=read('episodes/ep008-r3-film.json')['references']
    for kind,phase,seconds,source_in in CUTS:
        at=p['seconds']-p['action_start']
        if phase=='mouth' and mouth_at is None:mouth_at=p['seconds']
        if kind=='MATCH':
            kwargs={'phase':phase,'action_at':at}
            if phase=='mouth':kwargs['envelope']=envelope(jp,0,seconds)
            s=add(kind,seconds,**kwargs)
        else:s=add(kind,seconds,source=str(ROOT/refs['street']['file']),**{'in':source_in},flip=True,blue_out=phase=='palm')
        s['match_phase']=phase;p['matches'].append({'segment':s['id'],'performer':kind,'phase':phase,'action_at':at,'source_in':source_in,'seconds':s['seconds']})
    p['voices'].append({'id':'JP-HADOUKEN','path':str(jp),'start':mouth_at,'source_in':0,'seconds':duration(jp),'text':'波動拳！'})
    s=next(s for s in wave['segments'] if s['kind']=='G' and s.get('round')==8);q=copy.deepcopy(s);q.update(id='mc-'+str(len(p['segments'])).zfill(2),start=p['seconds']);p['segments'].append(q);p['peak_at']=p['seconds']+.12;p['seconds']+=q['seconds'];p['game_start']=q['start']
    for s in wave['segments']:
        if s.get('mode') in ('hadoken_reply','hadoken_boast'):
            old_start=s['start'];new_start=p['seconds'];q=copy.deepcopy(s);q.update(id='mc-'+str(len(p['segments'])).zfill(2),start=new_start);p['segments'].append(q);p['seconds']+=q['seconds']
            for v in wave['voices']:
                if old_start-.01<=v['start']<old_start+s['seconds']:
                    a=copy.deepcopy(v);a['start']=new_start+v['start']-old_start;p['voices'].append(a)
    validate(p);return p


def validate(p):
    lines=sorted(p['voices'],key=lambda v:v['start'])
    if any(a['start']+a['seconds']>b['start']+.03 for a,b in zip(lines,lines[1:])):raise ValueError('Foreground voice overlap')
    if any(v['start']+v['seconds']>p['seconds']+.03 for v in lines):raise ValueError('Voice out of bounds')
    if any('反弹以后也算' in v['text'] or '骂我耍赖' in v['text'] for v in lines):raise ValueError('Removed rule discussion reappeared')
    if sum(v['id']=='JP-HADOUKEN' for v in lines)!=1 or any(v['id']=='K03-B' for v in lines):raise ValueError('Japanese shout must occur once with no Chinese duplicate')
    last=-1
    for m in p['matches']:
        if m['performer']=='AN':
            if m['source_in']<last:raise ValueError('Anime motion restarted')
            last=m['source_in']+m['seconds']
    if not all(any(m['performer']=='MATCH' and m['phase']==phase for m in p['matches']) for phase in p.get('required_match_phases',['hands','torso','mouth','face','palm'])):raise ValueError('Missing real matched R acting phase')


def mix(p,spec,out):
    sr=24000;mix=np.zeros((math.ceil(p['seconds']*sr),2),np.float32)
    def add(a,start,gain=1):
        pos=round(start*sr);n=min(len(a),len(mix)-pos)
        if n>0:mix[pos:pos+n]+=a[:n]*gain
    voices=[]
    for v in p['voices']:add(pcm(v['path'],v['source_in'],v['seconds']),v['start']);voices.append((v['start'],v['start']+v['seconds']))
    for s in p['segments']:
        if s['kind']!='G':continue
        a=pcm(s['source'],s['in'],s['seconds']);gain=np.full(len(a),.75,np.float32)
        for start,end in voices:
            x=max(0,round((start-s['start'])*sr));y=min(len(gain),round((end-s['start'])*sr))
            if y>x:gain[x:y]=.36
        add(a*gain[:,None],s['start'])
    laugh=ROOT/read('episodes/ep008-r3-film.json')['references']['evil_laugh']['file'];add(pcm(laugh,0,3.8),p['anime_laugh_start'],.6);voices.append((p['anime_laugh_start'],p['anime_laugh_start']+3.8))
    base=read(spec['inherits']);sf=ROOT/base['music']['soundfont_path'];music=out/'music';music.mkdir(exist_ok=True)
    villain=compose(music/'villain.wav',sf,'villain',p['seconds']);rock=compose(music/'rock.wav',sf,'rock',p['seconds'],p['peak_at']);t=np.arange(len(mix))/sr
    blend=np.clip((t-(p['idea_at']-.10))/.22,0,1);env=np.full(len(mix),.33,np.float32);env[:round(p['anime_laugh_start']*sr)]=0
    for a,b in voices:
        x=round(a*sr);y=min(len(env),round(b*sr));env[x:y]*=.28
        end=min(len(env),y+round(.18*sr));env[y:end]=np.minimum(env[y:end],np.linspace(.33*.28,.33,end-y))
    a=pcm(villain)[:len(mix)];b=pcm(rock)[:len(mix)];add((a*(1-blend[:,None])+b*blend[:,None])*env[:,None],0)
    path=out/'mix.wav';subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','pcm_f32le',str(path)],input=mix.astype('<f4').tobytes(),check=True);return path


def render(spec,out,*,plan_fn=plan,segment_fn=segment,mix_fn=mix):
    p=plan_fn(spec,out);write(out/'timeline.json',p);(out/'segments').mkdir(exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    for s in p['segments']:
        if s['kind']=='MATCH':
            target=out/'segments'/(s['id']+'.mp4');receipt=target.with_suffix('.json');key=digest({'s':s,'art':sha(ROOT/'video_rush/paipai_match_art.py')})
            if not target.exists() or not receipt.exists() or read(receipt).get('key')!=key or read(receipt).get('sha256')!=sha(target):
                draw_match(target,s['phase'],s['seconds'],action_at=s.get('action_at',0),envelope=s.get('envelope'),previous=s.get('previous'));write(receipt,{'key':key,'sha256':sha(target)})
        else:segment_fn(out,s)
    f=out/'concat.txt';f.write_text(''.join(f"file '{out/'segments'/(s['id']+'.mp4')}'\n" for s in p['segments']));joined=out/'joined.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',f,'-c','copy',joined])
    captions=[{'start':v['start'],'end':v['start']+v['seconds'],'cues':[{'start':v['start'],'end':v['start']+v['seconds'],'text':v['text']}],'provenance_label':'','emphasis':''} for v in p['voices']];ass_file(out/'subtitles.ass',{'display_chapters':False,'shots':captions});audio=mix_fn(p,spec,out);movie=out/'light_to_hadouken_MATCHCUT.mp4'
    run(['ffmpeg','-v','error','-y','-reinit_filter','0','-i',joined,'-i',audio,'-filter_complex',f'[0:v]setpts=PTS-STARTPTS,ass={out/"subtitles.ass"},fps=30,format=yuv420p[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=14,aresample=48000[a]','-map','[v]','-map','[a]','-t',p['seconds'],'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',movie],log=out/'logs/render.log',timeout=300)
    run(['ffmpeg','-v','error','-i',movie,'-f','null','-'],log=out/'logs/decode.log');checks=verify_final_shots(movie,p['segments'],out/'segments');write(out/'frame-checks.json',checks)
    if not all(c['passed'] for c in checks):raise ValueError('Missing shot in final match cut')
    metrics=audio_metrics(movie);info=probe(movie);v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    if not (metrics['audible_signal'] and metrics['clipped_fraction']<.0001 and (v['width'],v['height'],v['avg_frame_rate'],v['codec_name'],a['codec_name'])==(1920,1080,'30/1','h264','aac')):raise ValueError('Media gate failed')
    run(['ffmpeg','-v','error','-y','-ss',p['action_start'],'-i',movie,'-t',p['game_start']+p['segments'][next(i for i,s in enumerate(p['segments']) if s['start']==p['game_start'])]['seconds']-p['action_start'],'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-c:a','aac','-b:a','160k',out/'hadouken_MATCH_ONLY.mp4'],timeout=180)
    write(out/'report.json',{'status':'technical_pass_pending_user_edit_review','duration':duration(movie),'sha256':sha(movie),'audio':metrics,'all_shots_present':True,'japanese_shout_count':1,'old_reflection_agreement_removed':True,'no_full_film':not (out/'final.mp4').exists(),'human_fluency_and_match_quality':'pending','git_head':run(['git','rev-parse','HEAD']).strip()})
    print('MATCHCUT READY',movie,duration(movie),flush=True);return p


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='build/episodes/ep008-v3-matchcut');p.add_argument('--spec',default='episodes/ep008-v3-matchcut.json');a=p.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);spec=read(a.spec);prepare(spec,out);render(spec,out)
