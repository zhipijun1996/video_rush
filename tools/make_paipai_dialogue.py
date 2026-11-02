"""Apply new acted lines to the accepted V4 short, preserving its attack shots."""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import zipfile
import requests
from video_rush.common import ROOT,read,write,sha,digest,duration
from video_rush.paipai_dialogue_art import render as draw_dialogue
from video_rush.transfers import download_chunks
from tools import make_paipai_matchcut as base,make_paipai_accel as accepted


def prepare(spec,out):
    # One bounded transport contains the two new performances and the old bridge
    # needed only to reconstruct the previous edit's timing.
    if not all((out/path).exists() for path in spec['new_voice_assets']):
        session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
        raw=download_chunks(session,os.environ['GITHUB_REPOSITORY'],json.loads(os.environ['VR_DIALOGUE_ARTIFACTS']),spec['voice_bundle_sha256'])
        archive=zipfile.ZipFile(io.BytesIO(raw))
        for name in archive.namelist():
            dest=(out/name).resolve()
            if not dest.is_relative_to(out.resolve()):raise ValueError('Unsafe voice path')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(archive.read(name))
    for path,expected in spec['new_voice_assets'].items():
        if sha(out/path)!=expected:raise ValueError('New performance changed: '+path)
    base.prepare(spec,out)


def retime(p,shot,new_seconds):
    end=shot['start']+shot['seconds'];shift=new_seconds-shot['seconds'];shot['seconds']=new_seconds
    for s in p['segments']:
        if s is not shot and s['start']>=end-.001:s['start']+=shift
    for v in p['voices']:
        if v['start']>=end-.001:v['start']+=shift
    for key in ['action_start','game_start','peak_at','merge_at','speech_end']:
        if p[key]>=end-.001:p[key]+=shift
    p['seconds']+=shift


def apply_lines(p,spec,out):
    for change in spec['dialogue_changes']:
        v=next(v for v in p['voices'] if v['id']==change['replace'])
        shot=next(s for s in p['segments'] if s['start']-.001<=v['start']<s['start']+s['seconds'])
        audio=out/'extra'/(change['id']+'.m4a');n=duration(audio)
        retime(p,shot,base.round_frame(n+.25))
        shot.update(kind='DIALOGUE',mode=change['mode'],envelope=base.envelope(audio))
        v.update(id=change['id'],path=str(audio),seconds=n,text=change['text'],start=shot['start']+.08,source_in=0)
    p['speech_end']=max(v['start']+v['seconds'] for v in p['voices'])
    return p


def plan(spec,out):
    p=apply_lines(accepted.plan(spec,out),spec,out)
    base.validate(p);accepted.validate(p)
    if any('我的反弹呢' in v['text'] or v['id']=='IDEA-A' for v in p['voices']):raise ValueError('Old lines returned')
    return p


def segment(out,s):
    if s['kind']!='DIALOGUE':return accepted.segment(out,s)
    dest=out/'segments'/(s['id']+'.mp4');receipt=dest.with_suffix('.json');key=digest({'shot':s,'art':sha(ROOT/'video_rush/paipai_dialogue_art.py'),'parent_art':sha(ROOT/'video_rush/paipai_match_art.py')})
    if not dest.exists() or not receipt.exists() or read(receipt).get('key')!=key or read(receipt).get('sha256')!=sha(dest):
        draw_dialogue(dest,s['mode'],s['seconds'],envelope=s.get('envelope'),previous=s.get('previous'));write(receipt,{'key':key,'sha256':sha(dest),'truth':'Original school-story dialogue animation'})
    return dest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',default='episodes/ep008-v5-lines.json');parser.add_argument('--output',default='build/episodes/ep008-v5-lines');a=parser.parse_args();spec=read(a.spec);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);prepare(spec,out)
    p=base.render(spec,out,plan_fn=plan,segment_fn=segment,mix_fn=accepted.mix)
    report=read(out/'report.json');report.update(dialogue_changes=spec['dialogue_changes'],accepted_attack_visual_plan='V4 unchanged source windows, frame counts, poses and overlay',new_voice_receipts=read(out/'new-voice-receipts.json'),surprise_animation=True,ending=read(out/'music/cues.json'));write(out/'report.json',report)
