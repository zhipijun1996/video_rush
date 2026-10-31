"""Record sound-bearing story fixtures; game source stays read-only."""
import argparse
import hashlib
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

from video_rush.common import ROOT, digest, probe, read, run, sha, write
from video_rush.narration import audio_metrics


def game_audio_metrics(path):
    return {**audio_metrics(path),'speech_identity':'Actual recorded game AudioBus output; voice identity/listening not independently verified.'}


def verify_runtime(source,project,commit):
    resolved=run(['git','-C',source,'rev-parse',commit+'^{commit}']).strip()
    records=[]
    tree=run(['git','-C',source,'ls-tree','-r',resolved,'--','src','public','data','index.html','package.json','package-lock.json','tsconfig.json','vite.config.ts','LICENSE'])
    for entry in tree.splitlines():
        metadata,name=entry.split('\t');blob=metadata.split()[2];path=project/name
        data=path.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual!=blob:raise ValueError('Runtime differs from pinned source: '+name)
        records.append({'path':name,'blob':blob})
    if len(records)<20:raise ValueError('Source snapshot unexpectedly incomplete')
    return {'commit':resolved,'files':records,'snapshot_hash':digest(records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Existing disposable runtime with dist and npm dependencies')
    parser.add_argument('--source',type=Path,default=Path('build/sources/wave-game'))
    parser.add_argument('--output', type=Path, default=Path('build/story-capture/ep008-r2'))
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.is_relative_to(ROOT/'build'):
        raise ValueError('Only disposable build runtimes are allowed')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    driver = ROOT/'video_rush/drivers/wave_story_capture.mjs'
    snapshot=verify_runtime(args.source,project,'f0bc228798600ed650bcd92bc8f415d7703484c4')
    recipe = {'driver':sha(driver),'source_commit':'f0bc228798600ed650bcd92bc8f415d7703484c4',
              'index':sha(project/'dist/index.html'),'audio':'Actual game WebAudio; music=0, sfx=.8'}
    receipt_path = output/'receipt.json'
    if receipt_path.exists():
        old=read(receipt_path)
        if old['recipe']==recipe and old['trace_sha256']==sha(output/'trace.json') and all(sha(output/n)==v for n,v in old['files'].items()):
            old['runtime_snapshot']=snapshot
            old['audio_metrics']={n:game_audio_metrics(output/n) for n in old['files']}
            if not all(a['audible_signal'] for a in old['audio_metrics'].values()):raise ValueError('Silent game audio recording')
            write(receipt_path,old)
            print('Verified cached story recordings and pinned source snapshot');return
    shutil.copyfile(driver,project/'video-rush-story.mjs')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(project/'dist')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        browser=os.getenv('VR_CHROMIUM_PATH') or shutil.which('chromium')
        if not browser:raise RuntimeError('Set VR_CHROMIUM_PATH to an installed Chromium executable')
        run(['node',project/'video-rush-story.mjs',server.server_port,output,browser],
            cwd=project,log=output/'capture.log',timeout=240)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    trace=read(output/'trace.json')
    rgb=subprocess.check_output(['ffmpeg','-v','error','-i',str(output/'raw.webm'),'-vf','crop=16:16:0:0,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-'])
    frames=[tuple(rgb[i:i+3]) for i in range(0,len(rgb),3)]
    starts=[i for i,(r,g,b) in enumerate(frames) if r>180 and g<90 and b>180]
    ends=[i for i,(r,g,b) in enumerate(frames) if r<90 and g>180 and b>180]
    if not starts or not ends:raise RuntimeError('Audio/video synchronization markers missing')
    start,end=starts[0]/25,ends[0]/25
    ratio=(end-start)/trace['audioSeconds']
    if not .8<ratio<1.35:raise RuntimeError(f'Unexpected video clock correction {ratio}')
    files={}
    for rec in trace['records']:
        name=rec['case']['id'];a,b=rec['start'],rec['end'];target=output/(name+'.mp4')
        filters=(f'[0:v]trim=start={start+a*ratio}:end={start+b*ratio},setpts=(PTS-STARTPTS)/{ratio},fps=30,format=yuv420p[v];'
                 f'[1:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a]')
        run(['ffmpeg','-v','error','-y','-i',output/'raw.webm','-i',output/'native-audio.webm',
             '-filter_complex',filters,'-map','[v]','-map','[a]','-t',b-a,
             '-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-c:a','aac','-b:a','128k','-movflags','+faststart',target],
            log=output/(name+'-mux.log'),timeout=120)
        run(['ffmpeg','-v','error','-i',target,'-f','null','-'],timeout=60)
        files[target.name]=sha(target)
    metrics={n:game_audio_metrics(output/n) for n in files}
    if not all(a['audible_signal'] for a in metrics.values()):raise ValueError('Silent game audio recording')
    write(receipt_path,{'recipe':recipe,'runtime_snapshot':snapshot,'files':files,'audio_metrics':metrics,'trace_sha256':sha(output/'trace.json'),
                        'sync':{'start':start,'end':end,'ratio':ratio},'truth':trace['truth']})
    print(json.dumps({'recordings':len(files),'output':str(output),'sync_ratio':ratio}))


if __name__=='__main__':main()
