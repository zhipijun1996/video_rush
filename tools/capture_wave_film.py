"""Capture the user-approved v1 screenplay as a continuous legal game battle."""
import argparse
import functools
import http.server
import shutil
import os
from pathlib import Path
import subprocess
import threading

from video_rush.common import ROOT, read, write, sha, run
from video_rush.browser_movie import PATHS
from video_rush.snapshot import snapshot
from tools.capture_wave_story import verify_runtime, game_audio_metrics


COMMIT='c6f1326c824a4b5c8489b0918285d9063f9d1db6'


def capture(source,output):
    source=Path(source).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    project=ROOT/'build/recordings'/('wave-film-'+COMMIT[:12]);driver=ROOT/'video_rush/drivers/wave_film_capture.mjs'
    if not (project/'dist/index.html').exists():
        snap=snapshot(source,COMMIT,PATHS,project);write(project/'snapshot.json',snap)
        run(['npm','ci','--no-audit','--no-fund'],cwd=project,log=output/'npm.log',timeout=180)
        run(['npm','run','build'],cwd=project,log=output/'build.log',timeout=180)
    snap=verify_runtime(source,project,COMMIT);recipe={'commit':COMMIT,'driver':sha(driver),'runtime':snap['snapshot_hash']}
    receipt=output/'receipt.json';movie=output/'continuous.mp4'
    if movie.exists() and receipt.exists() and read(receipt).get('recipe')==recipe and read(receipt).get('sha256')==sha(movie):return read(receipt)
    shutil.copyfile(driver,project/'video-rush-film.mjs')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(project/'dist')))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        browser=os.getenv('VR_CHROMIUM_PATH') or shutil.which('chromium')
        if not browser:raise RuntimeError('Chromium required')
        run(['npx','tsx',project/'video-rush-film.mjs',server.server_port,output,browser],cwd=project,log=output/'capture.log',timeout=240)
    finally:server.shutdown();server.server_close();worker.join(timeout=2)
    trace=read(output/'trace.json');raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(output/'raw.webm'),'-vf','crop=16:16:0:0,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-'])
    starts=[i for i in range(len(raw)//3) if raw[i*3]>180 and raw[i*3+1]<90 and raw[i*3+2]>180]
    ends=[i for i in range(len(raw)//3) if raw[i*3]<90 and raw[i*3+1]>180 and raw[i*3+2]>180]
    if not starts or not ends:raise ValueError('Sync markers missing')
    start,end=starts[0]/25,ends[0]/25;ratio=(end-start)/trace['audioSeconds']
    if not .8<ratio<1.35:raise ValueError('Unbounded capture clock drift')
    run(['ffmpeg','-v','error','-y','-i',output/'raw.webm','-i',output/'native-audio.webm','-filter_complex',
         f'[0:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{ratio},fps=30,format=yuv420p[v];[1:a]asetpts=PTS-STARTPTS[a]',
         '-map','[v]','-map','[a]','-t',trace['audioSeconds'],'-c:v','libx264','-preset','veryfast','-threads','2','-crf','21','-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',movie],log=output/'mux.log',timeout=240)
    metrics=game_audio_metrics(movie)
    if not metrics['audible_signal']:raise ValueError('Real game audio missing')
    rec={'recipe':recipe,'sha256':sha(movie),'trace_sha256':sha(output/'trace.json'),'snapshot':snap,'audio':metrics,'sync_ratio':ratio,'truth':trace['truth']};write(receipt,rec);return rec


def capture_mobile(output):
    output=Path(output).resolve();project=ROOT/'build/recordings'/('wave-film-'+COMMIT[:12]);driver=ROOT/'video_rush/drivers/wave_mobile_capture.mjs'
    movie=output/'mobile.mp4';receipt=output/'mobile-receipt.json';recipe={'commit':COMMIT,'driver_sha256':sha(driver)}
    if movie.exists() and receipt.exists():
        old=read(receipt)
        if old.get('driver_sha256')==recipe['driver_sha256'] and old.get('sha256')==sha(movie):return old
    shutil.copyfile(driver,project/'video-rush-mobile.mjs')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(project/'dist')));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        browser=os.getenv('VR_CHROMIUM_PATH') or shutil.which('chromium')
        if not browser:raise RuntimeError('Chromium required')
        run(['npx','tsx',project/'video-rush-mobile.mjs',server.server_port,output,browser],cwd=project,log=output/'mobile-capture.log',timeout=120)
    finally:server.shutdown();server.server_close();worker.join(timeout=2)
    trace=read(output/'mobile-trace.json');raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(output/'mobile-raw.webm'),'-vf','crop=16:16:0:0,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-'])
    starts=[i for i in range(len(raw)//3) if raw[3*i]>180 and raw[3*i+1]<90 and raw[3*i+2]>180];ends=[i for i in range(len(raw)//3) if raw[3*i]<90 and raw[3*i+1]>180 and raw[3*i+2]>180]
    if not starts or not ends:raise ValueError('Mobile sync markers missing')
    start,end=starts[0]/25,ends[0]/25;ratio=(end-start)/trace['audioSeconds']
    if not .8<ratio<1.35:raise ValueError('Unbounded mobile capture drift')
    run(['ffmpeg','-v','error','-y','-i',output/'mobile-raw.webm','-i',output/'mobile-audio.webm','-filter_complex',f'[0:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{ratio},fps=30,format=yuv420p[v];[1:a]asetpts=PTS-STARTPTS[a]','-map','[v]','-map','[a]','-t',trace['audioSeconds'],'-c:v','libx264','-preset','veryfast','-threads','2','-crf','21','-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',movie],log=output/'mobile-mux.log',timeout=120)
    metrics=game_audio_metrics(movie)
    if not metrics['audible_signal']:raise ValueError('Mobile actual game sound missing')
    result={**recipe,'sha256':sha(movie),'trace_sha256':sha(output/'mobile-trace.json'),'sync_ratio':ratio,'audio':metrics};write(receipt,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',default='build/sources/wave-game');p.add_argument('--output',default='build/film-capture/ep008-r3');a=p.parse_args();print(capture(a.source,a.output));print(capture_mobile(a.output))
