"""V7 full-film action dialogue, native scene music and a matched victory pose."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import requests
import numpy as np
from video_rush.common import ROOT,read,write,sha,run,duration
from video_rush.transfers import download_chunks
from tools import make_paipai_full as full
from tools.make_paipai_v2_review import pcm,envelope


def prepare(spec,out):
    old=ROOT/'build/deliveries/paipai-full-av-review-remote'
    if not (out/'full-inputs/manifest.json').exists():
        if old.exists():
            for folder in ['full-inputs','portable','extra','licenses']:shutil.copytree(old/folder,out/folder,dirs_exist_ok=True)
            shutil.copyfile(old/'new-voice-receipts.json',out/'new-voice-receipts.json')
        else:
            session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
            r=session.get('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/13158489126/zip',timeout=120);r.raise_for_status()
            if hashlib.sha256(r.content).hexdigest()!='4123b661a8a02af80fd2eaef4ff3fdd24c1ef055391a8b65448735cd3fc6a22d':raise ValueError('Accepted full-film input archive differs')
            for name in (z:=zipfile.ZipFile(io.BytesIO(r.content))).namelist():
                if not name.startswith(('full-inputs/','portable/','extra/','licenses/')) and name!='new-voice-receipts.json':continue
                dest=(out/name).resolve()
                if not dest.is_relative_to(out.resolve()):raise ValueError('Unsafe preserved input path')
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    if not all((out/path).exists() for path in spec['counter_assets']):
        session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
        raw=download_chunks(session,os.environ['GITHUB_REPOSITORY'],json.loads(os.environ['VR_COUNTER_ARTIFACTS']),spec['counter_bundle_sha256'])
        for name in (z:=zipfile.ZipFile(io.BytesIO(raw))).namelist():
            dest=(out/name).resolve()
            if not dest.is_relative_to(out.resolve()):raise ValueError('Unsafe new voice path')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    for path,h in spec['counter_assets'].items():
        if sha(out/path)!=h:raise ValueError('Counterplay performance differs: '+path)
    full.prepare(spec,out)
    for id,ref in spec['counter_references'].items():
        path=ROOT/ref['file'];path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and sha(path)==ref['sha256']:continue
        if ref.get('bvid'):
            from tools.collect_anime_reference import collect
            collect(ref['bvid'],path.parent,cid=ref['cid'],metadata=ref)
        else:
            r=requests.get(ref['url'],timeout=45);r.raise_for_status();path.write_bytes(r.content)
        if sha(path)!=ref['sha256']:raise ValueError('New reference differs: '+id)
    # Editorial anime freeze, never a synthetic or stretched gameplay window.
    ref=spec['counter_references']['jotaro_pose'];dest=out/'extra/jotaro-pose.mp4'
    run(['ffmpeg','-v','error','-y','-i',ROOT/ref['file'],'-vf','trim=start=0:end=0.35,setpts=PTS-STARTPTS,fps=30,tpad=stop_mode=clone:stop_duration=1.75,scale=1920:1080,setsar=1,format=yuv420p','-t','2.1','-an','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-color_range','tv',dest])


def patch(p,spec,out):
    segments=p['segments'];old_starts={s['id']:s['start'] for s in segments}
    def anchor(t):
        s=next(s for s in segments if s['start']-.0001<=t<s['start']+s['seconds']-.0001)
        return (s['id'],t-s['start'])
    marker_names=['boss_start','villain_at','wave_offset','rock_at','wave_peak','wave_end','light_at','dio_at','hero_at','hero_peak']
    markers={key:anchor(p[key]) for key in marker_names}
    for v in p['voices']:v['_anchor'],v['_at']=anchor(v['start'])
    def shot(id):return next(s for s in segments if s.get('shot',{}).get('id')==id)
    def add(s,id,text,at,speaker):
        path=out/'extra'/(id+'.m4a');n=duration(path)
        p['voices'].append({'id':id,'path':str(path),'source_in':0,'seconds':n,'text':text,'_anchor':s['id'],'_at':at})
        s['shot']['scheduled_lines'].append({'id':id,'speaker':speaker,'text':text,'start':at,'end':at+n})
        return at+n
    s=shot('4-05');s['shot']['scheduled_lines']=[]
    add(s,'RETRY-A','再来！',.06,'kidA');add(s,'AT-B','AT力场！防住！',.95,'kidB')
    s['shot']['lines']=[{'speaker':l['speaker'],'text':l['text']} for l in s['shot']['scheduled_lines']]
    # Retain the real launch/defence window; only fill the previous empty dialogue.
    s=shot('4-06');p['voices']=[v for v in p['voices'] if v['id']!='4-06-1']
    s['shot']['scheduled_lines']=[l for l in s['shot']['scheduled_lines'] if l['id']!='4-06-1']
    at=s['shot']['scheduled_lines'][0]['end']+.10;end=add(s,'TURN-B','到我了！',at,'kidB')
    s['seconds']=full.match.round_frame(end+.18);s['shot']['seconds']=s['seconds'];s['shot']['lines']=[{'speaker':l['speaker'],'text':l['text']} for l in s['shot']['scheduled_lines']]
    s=shot('4-07');s['shot']['angry_counter']=True
    old=next(v for v in p['voices'] if v['id']=='4-07-2');p['voices'].remove(old)
    lines=s['shot']['scheduled_lines'];s['shot']['scheduled_lines']=[l for l in lines if l['id']!='4-07-2']
    end=add(s,'ANGER-B','你把我的反弹升级了？！',3.25,'kidB')
    for id in ['4-07-3','4-07-4']:
        v=next(v for v in p['voices'] if v['id']==id);v['_at']=end+.10;end=v['_at']+v['seconds']
        l=next(l for l in s['shot']['scheduled_lines'] if l['id']==id);l.update(start=v['_at'],end=end)
    s['seconds']=full.match.round_frame(end+.15);s['shot']['seconds']=s['seconds'];s['shot']['scheduled_lines'].sort(key=lambda l:l['start']);s['shot']['lines']=[{'speaker':l['speaker'],'text':l['text']} for l in s['shot']['scheduled_lines']]
    v=next(v for v in p['voices'] if v['id']=='K04-B');path=out/'extra/JOJO-A.m4a';prefix=duration(path)
    face=next(s for s in segments if s.get('mode')=='dio_face');v['_at']=.02+prefix+.10
    p['voices'].append({'id':'JOJO-A','path':str(path),'source_in':0,'seconds':prefix,'text':'JOJO！','_anchor':face['id'],'_at':.02})
    face['seconds']=full.match.round_frame(face['seconds']+prefix+.10);face['envelope']=envelope(path)+[0]*3+face['envelope']
    s=shot('5-06');s['trim']=0;s['seconds']=3.30;s['shot'].update(seconds=3.30,victory_pose='jojo_point')
    for l in s['shot']['layers']:
        if l['layer']=='AN':l.update(**{'in':0,'out':2.1,'at':.50,'seconds':2.1})
    for id,at in [('5-06-0',.12),('5-06-1',2.65)]:
        v=next(v for v in p['voices'] if v['id']==id);v['_at']=at
        l=next(l for l in s['shot']['scheduled_lines'] if l['id']==id);l.update(start=at,end=at+v['seconds'])
    shot('7-04')['shot']['end_url']=spec['end_url']
    clock=0;p['chapters']={}
    for s in segments:s['start']=clock;clock+=s['seconds'];p['chapters'].setdefault(str(s['chapter']),s['start'])
    p['seconds']=clock;new_starts={s['id']:s['start'] for s in segments}
    for v in p['voices']:v['start']=new_starts[v.pop('_anchor')]+v.pop('_at')
    for key,(id,at) in markers.items():p[key]=new_starts[id]+at
    p['source_beds']=[{'id':'dio','file':spec['counter_references']['dio_audio']['file'],'source_in':37.7,'source_seconds':5.0,'start':face['start'],'end':p['hero_at']-.08,'gain':.32,'truth':'Original scene music/effects mix, not claimed as isolated licensed BGM'},{'id':'ultra','file':full.read('episodes/ep008-r3-film.json')['references']['ultra']['file'],'source_in':65.0,'start':next(s['start'] for s in segments if s['kind']=='AN' and 'BV1cZ4y1n7X2' in s.get('source','')),'end':p['hero_peak']+1.55,'gain':.28,'truth':'Original corresponding Ultraman scene audio with music and effects; not Tiga-labelled or isolated BGM'}]
    full.validate(p);validate_counterplay(p)
    return p


def validate_counterplay(p):
    voices={v['id']:v for v in p['voices']}
    ids=['RETRY-A','AT-B','TURN-B','4-07-0','4-07-1','ANGER-B']
    if not all(id in voices for id in ids+['JOJO-A','K04-B']):raise ValueError('Missing action dialogue')
    if any(voices[a]['start']>=voices[b]['start'] for a,b in zip(ids,ids[1:])):raise ValueError('Counterplay cause and reaction order changed')
    if voices['JOJO-A']['start']+voices['JOJO-A']['seconds']>voices['K04-B']['start']+.02:raise ValueError('JOJO prefix overlaps the preserved performance')
    if any('想起舞' in v['text'] for v in p['voices']):raise ValueError('Unmotivated dance line returned')


def plan(spec,out):return patch(full.plan(spec,out),spec,out)


def render_segments(p,out):
    ref={'file':str((out/'extra/jotaro-pose.mp4').relative_to(ROOT)),'sha256':sha(out/'extra/jotaro-pose.mp4'),'truth':'0.35s normal anime action followed by editorial pose freeze, total2.1s'}
    full.render_segments(p,out,reference_overrides={'jotaro':ref})


def score(p,spec,out,voices):
    result=full.score(p,spec,out,voices);sr=24000;t=np.arange(len(result))/sr
    for bed in p['source_beds']:
        n=bed['end']-bed['start'];source_seconds=bed.get('source_seconds',n);rate=source_seconds/n;bed['tempo_ratio']=rate
        raw=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-ss',str(bed['source_in']),'-i',str(ROOT/bed['file']),'-af',f'atrim=duration={source_seconds},asetpts=PTS-STARTPTS,atempo={rate}','-ar','24000','-ac','2','-f','f32le','-']),dtype='<f4').reshape(-1,2).copy()
        if abs(len(raw)/sr-n)>.04:raise ValueError('Source music retiming truncated the intended bed')
        bed['actual_decoded_seconds']=len(raw)/sr;raw*=.70/max(.001,float(np.max(np.abs(raw))));count=len(raw);gain=np.full(count,bed['gain'],np.float32)
        for start,end in voices:
            a=max(0,round((start-bed['start']-.03)*sr));b=min(count,round((end-bed['start']+.08)*sr))
            if b>a:gain[a:b]*=.38
        fade=min(round(.08*sr),count);gain[:fade]*=np.linspace(0,1,fade);gain[-fade:]*=np.linspace(1,0,fade)
        x=round(bed['start']*sr);available=min(count,round(n*sr),len(result)-x);result[x:x+available]*=.35;result[x:x+available]+=raw[:available]*gain[:available,None]
        subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','aac','-b:a','96k',str(out/'extra'/('bgm-'+bed['id']+'.m4a'))],input=raw.astype('<f4').tobytes(),check=True)
        bed['extracted_sha256']=sha(out/'extra'/('bgm-'+bed['id']+'.m4a'))
    design=read(out/'music/design.json');design.update(DIO_music_silence=[p['hero_at']-.08,p['hero_at']],source_audio_beds=p['source_beds']);write(out/'music/design.json',design)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','aac','-b:a','128k',str(out/'music/full-score.m4a')],input=result.astype('<f4').tobytes(),check=True);return result


def mix(p,spec,out):return full.mix(p,spec,out,score_fn=score)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='build/episodes/ep008-v7-counterplay');a=parser.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);spec=read('episodes/ep008-v7-counterplay.json');prepare(spec,out);full.render(spec,out,plan_fn=plan,segments_fn=render_segments,mix_fn=mix)
    report=read(out/'report.json');report.update(counterplay_lines=['再来！','AT力场！防住！','到我了！','你把我的反弹升级了？！','JOJO！我不做人了！！！'],dance_line_removed=True,source_audio_beds=True,victory_reference_seconds=2.1,end_url=spec['end_url']);write(out/'report.json',report)
