"""V8: continuous acting, uninterrupted real victory, quiet matching age transition."""
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
import numpy as np
import requests
from video_rush.common import ROOT,read,write,sha,run,duration,digest
from video_rush.transfers import download_chunks
from tools import make_paipai_counterplay as prior,make_paipai_full as full
from tools.make_paipai_v2_review import envelope,pcm

SPEC='episodes/ep008-v8-continuity.json'
OUTPUT='build/episodes/ep008-v8-continuity'


def unpack(raw,out,allowed=None):
    z=zipfile.ZipFile(io.BytesIO(raw))
    if sum(i.file_size for i in z.infolist())>60_000_000:raise ValueError('Unexpected archive expansion')
    for name in z.namelist():
        if name.endswith('/') or (allowed and not allowed(name)):continue
        target=(out/name).resolve()
        if not target.is_relative_to(out.resolve()):raise ValueError('Unsafe input path')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))


def prepare(spec,out):
    out.mkdir(parents=True,exist_ok=True)
    if not (out/'full-inputs/manifest.json').exists():
        local=ROOT/'build/deliveries/paipai-counterplay-full-review-remote'
        allow=lambda n:n.startswith(('full-inputs/','portable/','extra/','licenses/')) or n in ['new-voice-receipts.json','counter-voice-receipts.json']
        if local.exists():
            for folder in ['full-inputs','portable','extra','licenses']:shutil.copytree(local/folder,out/folder,dirs_exist_ok=True)
            for name in ['new-voice-receipts.json','counter-voice-receipts.json']:shutil.copyfile(local/name,out/name)
        else:
            session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
            r=session.get('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/13163594844/zip',timeout=120);r.raise_for_status()
            if hashlib.sha256(r.content).hexdigest()!='e35600733be76881306c33e9b83b3380ddccc68005c32f2cab189a26bea4209f':raise ValueError('Preserved V7 archive differs')
            unpack(r.content,out,allow)
    if not all((out/n).exists() and sha(out/n)==h for n,h in spec['continuity_assets'].items()):
        session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
        raw=download_chunks(session,os.environ['GITHUB_REPOSITORY'],json.loads(os.environ['VR_CONTINUITY_ARTIFACTS']),spec['continuity_bundle_sha256']);unpack(raw,out)
    for name,h in spec['continuity_assets'].items():
        if sha(out/name)!=h:raise ValueError('V8 source/voice mismatch: '+name)
    prior.prepare(spec,out)


def patch(p,spec,out):
    segments=p['segments'];old_starts={s['id']:s['start'] for s in segments}
    def anchor(t):
        s=next(s for s in segments if s['start']-.0001<=t<s['start']+s['seconds']-.0001)
        return s['id'],t-s['start']
    keys=['boss_start','villain_at','wave_offset','rock_at','wave_peak','wave_end','light_at','dio_at','hero_at','hero_peak']
    markers={k:anchor(p[k]) for k in keys}
    for v in p['voices']:v['_anchor'],v['_at']=anchor(v['start'])
    def shot(id):return next(s for s in segments if s.get('shot',{}).get('id')==id)
    face=next(s for s in segments if s.get('mode')=='dio_face');an=segments[segments.index(face)+1]
    path=out/'extra/DIO-CONT-A.m4a';n=duration(path)
    p['voices']=[v for v in p['voices'] if v['id'] not in ['JOJO-A','K04-B']]
    face['seconds']=.60;face['envelope']=envelope(path)
    an['seconds']=2.30
    p['voices'].append({'id':'DIO-CONT-A','path':str(path),'source_in':0,'seconds':n,'text':'JOJO！我不做人了！','_anchor':face['id'],'_at':.03})
    # One performance spans the actor/anime cut without a gain dip or a restart.
    beam=next(s for s in segments if s['kind']=='G' and s.get('round')==21)
    beam.update(source=str(out/'extra/beam-complete.mp4'),**{'in':0,'seconds':full.match.round_frame(spec['new_game']['seconds']),'blue_in':False,'cropped':True})
    beam['native_foreground_duck']=.65
    markers['hero_peak']=(beam['id'],.32)
    king=shot('5-06');king['trim']=0;king['seconds']=2.0;ks=king['shot'];ks.update(seconds=2.0,game_first=0,victory_pose='jojo_point')
    ks['layers']=[{'layer':'AN','source':'jotaro','in':0,'out':1.6,'at':.08,'seconds':1.6,'alpha':.40,'soft_apparition':True,'rect':[700,80,620,800],'crop':[.42,0,.57,1]}]
    p['voices']=[v for v in p['voices'] if v['id']!='5-06-0']
    path=out/'extra/KING-FAST.m4a';n=duration(path)
    p['voices'].append({'id':'KING-FAST','path':str(path),'source_in':0,'seconds':n,'text':'叫大王！','_anchor':king['id'],'_at':.08})
    reply=next(v for v in p['voices'] if v['id']=='5-06-1');reply['_anchor']=king['id'];reply['_at']=1.43
    ks['scheduled_lines']=[{'id':'KING-FAST','speaker':'kidA','text':'叫大王！','start':.08,'end':.08+n},{'id':'5-06-1','speaker':'kidB','text':reply['text'],'start':1.43,'end':1.43+reply['seconds']}]
    ks['lines']=[{'speaker':l['speaker'],'text':l['text']} for l in ks['scheduled_lines']]
    back=shot('6-01');back['seconds']=1.1;back['shot'].update(seconds=1.1,memory_dissolve=True,sfx=None)
    phone=shot('7-02');phone['seconds']=2.9;phone['shot'].update(seconds=2.9,arena_top=True)
    layer=phone['shot']['layers'][0];layer.update(seconds=2.9,out=layer['in']+2.9,rect=[270,0,1380,690],crop=[0,210/844,1,220/844])
    # The original first guard is visible to recover; omit the next incomplete round.
    clock=0;p['chapters']={}
    for s in segments:s['start']=clock;clock+=s['seconds'];p['chapters'].setdefault(str(s['chapter']),s['start'])
    p['seconds']=clock;starts={s['id']:s['start'] for s in segments}
    for v in p['voices']:v['start']=starts[v.pop('_anchor')]+v.pop('_at')
    for k,(id,at) in markers.items():p[k]=starts[id]+at
    # Native audio in beam-complete contains the full 2.8-second victory sample.
    # It must not compete with the remaining half-second of the hero shout.
    p['native_victory']={**spec['new_game'],'timeline_start':beam['start'],'timeline_end':beam['start']+beam['seconds'],'truth':'Fresh legal21-round run at same pinned game source, normal speed; no native cut-in, complete original win declaration'}
    p['source_beds']=[{'id':'dio','file':spec['counter_references']['dio_audio']['file'],'source_in':37.7,'source_seconds':2.8,'start':face['start'],'end':p['hero_at']-.06,'gain':.43,'dialogue_duck':.62,'truth':'Corresponding source-scene music/effects mix; not isolated soundtrack'},{'id':'ultra','file':full.read('episodes/ep008-r3-film.json')['references']['ultra']['file'],'source_in':65.0,'start':next(s['start'] for s in segments if s['kind']=='AN' and 'BV1cZ4y1n7X2' in s.get('source','')),'end':p['hero_peak']+.65,'gain':.26,'truth':'Source scene mix, licensed status unchanged'}]
    full.validate(p);validate(p)
    return p


def validate(p):
    voices={v['id']:v for v in p['voices']}
    if any(id in voices for id in ['K04-B','JOJO-A','5-06-0']):raise ValueError('Spliced villain or old slow king returned')
    face=next(s for s in p['segments'] if s.get('mode')=='dio_face');an=p['segments'][p['segments'].index(face)+1];v=voices['DIO-CONT-A']
    if not v['start']<an['start']<v['start']+v['seconds']:raise ValueError('Continuous performance must cross DIO cut')
    g=next(s for s in p['segments'] if s['kind']=='G' and s.get('round')==21)
    if g.get('blue_in') or g['seconds']<4:raise ValueError('Clean complete game victory missing')
    king=next(s for s in p['segments'] if s.get('shot',{}).get('id')=='5-06')
    if voices['KING-FAST']['start']<g['start']+g['seconds']-.02:raise ValueError('King interrupts native victory')
    if any(not l.get('alpha') or l['rect'][2]>=1000 for l in king['shot']['layers']):raise ValueError('Victory apparition became fullscreen')
    if voices['KING-FAST']['seconds']>1.2:raise ValueError('King call is still slow')


def plan(spec,out):return patch(prior.plan(spec,out),spec,out)


def render_segments(p,out):
    # Reuse unchanged shot pixels only with a content/source hash, never an ID alone.
    full.render_segments(p,out,reference_overrides={'jotaro':{'file':str((out/'extra/jotaro-pose.mp4').relative_to(ROOT)),'sha256':sha(out/'extra/jotaro-pose.mp4')}})


def score(p,spec,out,voices):
    result=prior.score(p,spec,out,voices)
    # The source's victory declaration owns the foreground, with subdued backing.
    sr=24000;g=next(s for s in p['segments'] if s['kind']=='G' and s.get('round')==21)
    start=g['start']+p['native_victory']['victory_offset'];result[round(start*sr):round((g['start']+g['seconds'])*sr)]*=.23
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','aac','-b:a','128k',str(out/'music/full-score.m4a')],input=result.astype('<f4').tobytes(),check=True)
    return result


def mix(p,spec,out):return full.mix(p,spec,out,score_fn=score)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default=OUTPUT);a=parser.parse_args();out=Path(a.output).resolve();spec=read(SPEC);prepare(spec,out);full.render(spec,out,plan_fn=plan,segments_fn=render_segments,mix_fn=mix)
    report=read(out/'report.json');report.update(continuity='Single new generated villain performance across actor/anime cut; clean real beam; full native victory; side apparition; memory dissolve; complete first mobile defence',new_game={**spec['new_game'],'receipt':'extra/new-game-receipt.json','receipt_sha256':sha(out/'extra/new-game-receipt.json')},end_url=spec['end_url']);write(out/'report.json',report)
