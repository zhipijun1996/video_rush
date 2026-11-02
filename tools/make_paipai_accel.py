"""Bounded V4 trial: accelerating pose cuts, double exposure and a real cadence."""
import argparse
import copy
import math
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
from video_rush.common import ROOT,read,write,sha,digest,run
from video_rush.paipai_double_exposure import composite
from video_rush.paipai_v2_score import Synth,arrange,midi_file
from tools import make_paipai_matchcut as base
from tools.make_paipai_v2_review import pcm


PAIRS=[('hands',12,189.35),('torso',9,191.58),('mouth',6,192.90),('face',4,193.65),('face',3,193.65+4/30)]


def plan(spec,out):
    old=base.plan(spec,out);p=copy.deepcopy(old)
    prefix=[s for s in p['segments'] if s['start']<p['action_start']-.001]
    suffix=[s for s in p['segments'] if s['start']>=p['game_start']-.001]
    actions=[];clock=p['action_start'];matches=[];mouth_at=None
    source=next(s['source'] for s in p['segments'] if s.get('match_phase') and s['kind']=='AN')
    for phase,frames,at in PAIRS:
        if phase=='mouth':mouth_at=clock
        for kind in ['MATCH','AN']:
            s={'kind':kind,'start':clock,'seconds':frames/30,'match_phase':phase,'phase':phase,'action_at':clock-p['action_start']}
            if kind=='AN':s.update(source=source,**{'in':at},flip=True)
            actions.append(s);matches.append({'performer':kind,'phase':phase,'source_in':at if kind=='AN' else None,'seconds':frames/30});clock+=frames/30
    p['merge_at']=clock
    for phase,at,frames in [('face',193.65+7/30,12),('palm',194.50,3)]:
        actions.append({'kind':'BLEND','start':clock,'seconds':frames/30,'phase':phase,'source':source,'in':at,'flip':True,'enter':phase=='face','match_phase':'merged_'+phase});clock+=frames/30
    shift=clock-p['game_start']
    for s in suffix:s['start']+=shift
    for v in p['voices']:
        if v['id']=='JP-HADOUKEN':v['start']=mouth_at
        elif v['start']>=p['game_start']-.001:v['start']+=shift
    p['game_start']+=shift;p['peak_at']+=shift;p['seconds']+=shift
    p['speech_end']=max(v['start']+v['seconds'] for v in p['voices'])
    # A short punctuation after the last word, rather than slicing an unfinished bar.
    extra=base.round_frame(max(0,p['speech_end']+.82-p['seconds']))
    suffix[-1]['seconds']+=extra;p['seconds']+=extra
    p['segments']=prefix+actions+suffix;p['matches']=matches;p['required_match_phases']=['hands','torso','mouth','face']
    for i,s in enumerate(p['segments']):s['id']=f'ac-{i:02}'
    base.validate(p);validate(p);return p


def validate(p):
    pairs=p['matches'];frames=[round(pairs[i]['seconds']*30) for i in range(0,len(pairs),2)]
    if frames!=[12,9,6,4,3]:raise ValueError('Acceleration schedule changed')
    for a,b in zip(pairs[::2],pairs[1::2]):
        if a['phase']!=b['phase'] or a['seconds']!=b['seconds']:raise ValueError('Unpaired action')
    sources=[s for s in p['segments'] if s['kind'] in ('AN','BLEND') and s['start']>=p['action_start']]
    if any(a['in']+a['seconds']>b['in']+.001 for a,b in zip(sources,sources[1:])):raise ValueError('Source motion goes backwards')
    if p['speech_end']+.65>p['seconds']:raise ValueError('No room for musical resolution')
    if p['segments'][next(i for i,s in enumerate(p['segments']) if s['kind']=='G' and s['start']==p['game_start'])-1]['kind']!='BLEND':raise ValueError('Merge must lead into real game')


def segment(out,s):
    if s['kind']!='BLEND':return base.segment(out,s)
    dest=out/'segments'/(s['id']+'.mp4');receipt=dest.with_suffix('.json')
    key=digest({'shot':s,'source':sha(s['source']),'art':sha(ROOT/'video_rush/paipai_double_exposure.py'),'parent_art':sha(ROOT/'video_rush/paipai_match_art.py')})
    if dest.exists() and receipt.exists() and read(receipt).get('key')==key and read(receipt).get('sha256')==sha(dest):return dest
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(s['in']),'-i',s['source'],'-t',str(s['seconds']),'-vf','hflip,fps=30,scale=1280:720','-f','rawvideo','-pix_fmt','rgb24','-'])
    frames=np.frombuffer(raw,np.uint8).reshape((-1,720,1280,3));count=round(s['seconds']*30)
    if len(frames)<count:raise ValueError('Insufficient original frames for merge')
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-','-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-color_range','tv',str(dest)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(count):enc.stdin.write(composite(Image.fromarray(frames[n]),s['phase'],n/30,s['seconds'],enter=s['enter']).tobytes())
        enc.stdin.close();error=enc.stderr.read();rc=enc.wait(timeout=90)
        if rc:raise RuntimeError(error.decode()[-1000:])
    finally:
        if enc.poll() is None:enc.kill();enc.wait()
    write(receipt,{'key':key,'sha256':sha(dest),'truth':'Original child drawing double-exposed over anime, never game footage'});return dest


def music_events(p):
    """No busy lead underneath the last exchange; cadence begins after speech."""
    seconds=p['seconds'];start=p['idea_at']-.1;stop=p['game_start']+next(s['seconds'] for s in p['segments'] if s['start']==p['game_start'])
    events=[]
    villain,_=arrange('villain',start+.2)
    events += [(t,k,ch,key,v) for t,k,ch,key,v in villain]
    rock,_=arrange('rock',stop-start,peak_at=p['peak_at']-start)
    events += [(t+start,k,ch,key,v) for t,k,ch,key,v in rock]
    # Five-note E-minor theme backwards, played softly on nylon guitar.
    tail=p['speech_end']+.02
    for j,key in enumerate([76,71,69,67,64]):
        t=tail+j*.09;events += [(t,1,7,key,57),(t+(.25 if j==4 else .075),-1,7,key,0)]
    for key in [52,59,64]:events += [(tail+.36,1,7,key,42),(tail+.64,-1,7,key,0)]
    return events,{'rock_start':start,'rock_stop':stop,'reaction_dry':True,'cadence_start':tail,'cadence_end':tail+.64,'cadence_notes':[76,71,69,67,64]}


def mix(p,spec,out):
    sr=24000;total=math.ceil(p['seconds']*sr);master=np.zeros((total,2),np.float32)
    def add(a,start,gain=1):
        x=round(start*sr);n=min(len(a),total-x)
        if n>0:master[x:x+n]+=a[:n]*gain
    voices=[]
    for v in p['voices']:add(pcm(v['path'],v['source_in'],v['seconds']),v['start']);voices.append((v['start'],v['start']+v['seconds']))
    for s in p['segments']:
        if s['kind']=='G':add(pcm(s['source'],s['in'],s['seconds']),s['start'],.60)
    laugh=ROOT/read('episodes/ep008-r3-film.json')['references']['evil_laugh']['file'];add(pcm(laugh,0,3.8),p['anime_laugh_start'],.6);voices.append((p['anime_laugh_start'],p['anime_laugh_start']+3.8))
    sf=ROOT/read(spec['inherits'])['music']['soundfont_path'];music=out/'music';music.mkdir(exist_ok=True)
    events,cues=music_events(p);score=Synth(sf).perform(events,p['seconds']);score*=.70/max(.001,float(np.max(np.abs(score))))
    t=np.arange(total)/sr;gain=np.full(total,.34,np.float32)
    gain[t<p['anime_laugh_start']]=0
    # Deliberately remove the attack score before the first ordinary-boy reaction.
    stop=cues['rock_stop'];gain*=1-np.clip((t-(stop-.15))/.15,0,1)
    tail=cues['cadence_start'];gain[t>=tail]=.25
    end=cues['cadence_end'];gain*=1-np.clip((t-end)/.18,0,1)
    for a,b in voices:
        attack=np.clip((t-(a-.05))/.05,0,1);release=1-np.clip((t-b)/.18,0,1)
        gain*=1-.72*np.minimum(attack,release)
    add(score*gain[:,None],0);path=out/'mix.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','pcm_f32le',str(path)],input=master.astype('<f4').tobytes(),check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','aac','-b:a','128k',str(music/'score.m4a')],input=(score*gain[:,None]).astype('<f4').tobytes(),check=True)
    midi_file(music/'score.mid',events,176);write(music/'cues.json',{**cues,'source':'Original E G A B E theme; FluidR3 GM MIT instruments','speech_end':p['speech_end'],'seconds':p['seconds'],'human_musical_review':'pending'})
    return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='build/episodes/ep008-v4-accel');args=parser.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);spec=read('episodes/ep008-v4-accel.json');base.prepare(spec,out);p=base.render(spec,out,plan_fn=plan,segment_fn=segment,mix_fn=mix)
    report=read(out/'report.json');report.update(acceleration_frames=[12,9,6,4,3],double_exposure=True,ending=read(out/'music/cues.json'),game_unaltered=True);write(out/'report.json',report)
