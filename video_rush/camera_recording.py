"""Record matched controller probes against two immutable camera revisions."""
import os
import shutil
import subprocess
from pathlib import Path
from .common import ROOT,read,write,sha,digest,probe,run

SEGMENTS={'turn','jump','recoil','fall','look','corner'}
DRIVER=ROOT/'video_rush/drivers/camera_progress.gd'

def validate_trace(t):
    if t.get('failures')!=0 or t.get('position_writes_within_marked_clips') is not False:
        raise ValueError('Camera fixture failed or changed position inside a marked clip')
    if {s['id'] for s in t['segments']}!=SEGMENTS or not 1<=t['frames']<=7200:
        raise ValueError('Incomplete/beyond-budget camera recording')
    for s in t['segments']:
        rows=[r for r in t['rows'] if r['clip']==s['id']]
        if not 0<=s['start_frame']<s['end_frame']<=t['frames'] or len(rows)<40:
            raise ValueError('Missing actual motion observations')

def capture(repo,asset):
    from tools.current_gameplay_job import prepare
    from tools.record_current_gameplay import capture as native
    segment=asset['case'];commit=asset['commit']
    if segment not in SEGMENTS or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Unsupported camera case or unpinned source')
    recipe={'source_commit':commit,'driver_sha256':sha(DRIVER),'module_sha256':sha(Path(__file__)),
            'runner_sha256':sha(ROOT/'tools/record_current_gameplay.py'),'prepare_sha256':sha(ROOT/'tools/current_gameplay_job.py')}
    base=Path(os.environ.get('VIDEO_RUSH_CAMERA_CAPTURE_ROOT',ROOT/'build/recordings/camera')).resolve()/commit[:12]
    folder=base/('capture-'+digest(recipe)[:12]);master=folder/'master-receipt.json'
    if master.exists():
        r=read(master)
        if r.get('recipe')!=recipe or sha(folder/'gameplay.mp4')!=r['movie_sha256'] or sha(folder/'trace.json')!=r['trace_sha256']:
            raise ValueError('Cached camera source bytes changed')
        validate_trace(read(folder/'trace.json'))
    else:
        if (folder/'receipt.json').exists():raise ValueError('Preserved failed attempt; inspect before a fresh recording root')
        spec={'repository':asset['repository'],'main_commit':commit,'stages':{'camera':{'version':'main','driver':str(DRIVER.relative_to(ROOT))}}}
        work,engine,script,_=prepare(spec,'camera',base)
        with (base/'world-build.log').open('wb') as log:
            subprocess.run(['python',str(work/'tools/world/build.py')],cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        run([engine,'--headless','--path',work,'--check-only','--script',script],log=base/'script-check.log',timeout=60)
        r=native(work,engine,script,['--output='+str(folder/'trace.json')],folder,commit,timeout=1200)
        validate_trace(read(folder/'trace.json'))
        if not r['driver_completed_successfully']:raise ValueError('Native camera capture has engine/driver errors')
        r.update(recipe=recipe,trace_sha256=sha(folder/'trace.json'),camera_sha256=sha(work/'game/presentation/ui/world/world_camera.gd'))
        write(master,r)
        for name in ['preparation.json','import.log','world-build.log']:shutil.copyfile(base/name,folder/name)
    t=read(folder/'trace.json');part=next(x for x in t['segments'] if x['id']==segment)
    seconds=(part['end_frame']-part['start_frame'])/60;start=part['start_frame']/60
    movie=folder/(segment+'.mp4');receipt=folder/(segment+'-receipt.json')
    if not receipt.exists() or not movie.exists() or sha(movie)!=read(receipt)['movie_sha256']:
        run(['ffmpeg','-y','-v','error','-ss',str(start),'-i',folder/'gameplay.mp4','-t',str(seconds),
             '-vf','scale=in_range=auto:out_range=tv,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','18',
             '-threads','4','-color_range','tv','-c:a','aac','-ar','48000','-movflags','+faststart',movie],timeout=180)
        write(receipt,{'recipe':recipe,'segment':part,'seconds':seconds,'kind':'fresh_native_camera_fixture',
              'source_commit':commit,'movie_sha256':sha(movie),'trace_sha256':r['trace_sha256'],
              'master_movie_sha256':r['movie_sha256'],'native_receipt':r,'ffprobe':probe(movie),
              'scope':t['scope'],'playback':'normal 60fps capture; no simulation speedup or gameplay synthesis'})
    return movie,read(receipt)
