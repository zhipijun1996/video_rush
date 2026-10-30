"""Record the pinned web game through its existing localhost fixture/DOM API."""
from pathlib import Path
import functools
import http.server
import shutil
import threading
from .common import ROOT,run,sha,digest,read,write,probe
from .snapshot import snapshot

PATHS=['src','public','data','index.html','package.json','package-lock.json','tsconfig.json','vite.config.ts','LICENSE']


def capture(repo,asset):
    commit=run(['git','-C',repo,'rev-parse',asset['commit']+'^{commit}']).strip()
    driver=ROOT/'video_rush/drivers/wave_capture.mjs'
    browser=next((shutil.which(x) for x in ['chromium','google-chrome','google-chrome-stable'] if shutil.which(x)),None)
    if not browser:raise RuntimeError('Web game recording requires Chromium')
    recipe={'commit':commit,'case':asset['case'],'driver_sha256':sha(driver),'module_sha256':sha(Path(__file__)),
            'viewport':[1920,1080],'browser':run([browser,'--version']).strip()}
    key=digest(recipe);folder=ROOT/'build/browser-movies'/key[:20];folder.mkdir(parents=True,exist_ok=True)
    movie=folder/'movie.mp4';receipt=folder/'receipt.json'
    if movie.exists() and receipt.exists():
        old=read(receipt)
        if old.get('key')==key and old.get('movie_sha256')==sha(movie):return movie,old
    project=ROOT/'build/browser-runtime'/commit[:16]
    if not (project/'dist/index.html').exists():
        snap=snapshot(repo,commit,PATHS,project)
        run(['npm','ci','--no-audit','--no-fund'],cwd=project,log=folder/'install.log',timeout=180)
        run(['npm','run','build'],cwd=project,log=folder/'build.log',timeout=180)
        write(project/'snapshot.json',snap)
    # The source already depends on Playwright; use its recording encoder and API.
    run(['npx','playwright','install','ffmpeg'],cwd=project,log=folder/'encoder.log',timeout=120)
    shutil.copyfile(driver,project/'video-rush-capture.mjs')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(project/'dist')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        run(['node',project/'video-rush-capture.mjs',str(server.server_port),asset['case'],folder,browser],
            cwd=project,log=folder/'capture.log',timeout=150)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    raw=folder/'raw.webm';trace=read(folder/'trace.json')
    if trace['page_errors']:raise RuntimeError('Recorded game runtime errors; see trace')
    # Source's capture.ts/mux_capture.py also use visible start/end markers to
    # calibrate Playwright's constant-25fps recording against actual wall time.
    import subprocess
    rgb=subprocess.check_output(['ffmpeg','-v','error','-i',raw,'-vf','crop=16:16:0:0,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-'])
    starts=[i for i in range(len(rgb)//3) if rgb[3*i]>180 and rgb[3*i+1]<90 and rgb[3*i+2]>180]
    ends=[i for i in range(len(rgb)//3) if rgb[3*i]<90 and rgb[3*i+1]>180 and rgb[3*i+2]>180]
    if not starts or not ends:raise RuntimeError('Recording synchronization marker missing')
    start,end=starts[0]/25,ends[0]/25
    ratio=(end-start)/trace['wall_seconds'];trim=.25;seconds=trace['wall_seconds']-trim
    # The upstream v2.1 receipt measured 1.158877 with this recorder. Correct
    # to the measured wall clock instead of claiming the raw 25fps is real time.
    if not .8<ratio<1.35:raise RuntimeError('Browser recording clock drift exceeds bounded calibration range')
    run(['ffmpeg','-v','error','-y','-i',raw,'-vf',
         f'trim=start={start+trim*ratio}:end={end},setpts=(PTS-STARTPTS)/{ratio},fps=30,scale=in_range=auto:out_range=tv,format=yuv420p',
         '-an','-t',str(seconds),'-c:v','libx264','-preset','veryfast','-crf','20','-threads','4','-color_range','tv','-movflags','+faststart',movie],
         log=folder/'encode.log',timeout=180)
    obj={'key':key,'recipe':recipe,'movie_sha256':sha(movie),'trace_sha256':sha(folder/'trace.json'),
         'ffprobe':probe(movie),'sync':{'start':start,'end':end,'ratio':ratio,'trimmed_seconds':trim},
         'truth':'New actual browser rendering; original source/physics untouched. Preset action scenes explicitly labelled; normal case uses sealed native AI. Source audio omitted; final narration/music are editorial.'}
    write(receipt,obj);raw.unlink();return movie,obj
