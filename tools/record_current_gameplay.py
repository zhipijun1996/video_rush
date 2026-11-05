"""Record exact source-owned drivers in disposable projects; preserve game AV.

No gameplay edits, health grants, synthetic hits or silent replacement audio.
The source repo is never checked out or written by this runner.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import selectors
import shutil
import subprocess
import time

from video_rush.common import probe, sha, write
from video_rush.narration import audio_metrics


def fingerprint(work):
    result={}
    for directory in ('game','scripts','scenes','resources','config','shaders','assets','addons','experiments','tools','tests'):
        for p in sorted((work/directory).rglob('*')):
            if p.is_file() and not p.name.endswith(('.import','.uid')) and not p.name.startswith('video_rush_'):
                result[str(p.relative_to(work))]=sha(p)
    result['project.godot']=sha(work/'project.godot')
    return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()


def capture(work,engine,script,arguments,out,commit,*,headless=False,timeout=1200):
    work=Path(work).resolve();engine=Path(engine).resolve();out=Path(out).resolve()
    if out.exists():
        raise ValueError('Use a fresh output directory; failed originals are immutable')
    out.mkdir(parents=True)
    config=json.loads((work/'config/toolchain.json').read_text())['godot']
    if sha(engine)!=config['linux_x86_64']['binary_sha256']:
        raise ValueError('Exact patched engine SHA mismatch')
    version=subprocess.check_output([str(engine),'--version'],text=True).strip()
    if version!=config['version_exact']:raise ValueError('Engine version mismatch')
    before=fingerprint(work);display=None
    env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='4',
             XDG_DATA_HOME=str(out/'userdata'),XDG_CACHE_HOME=str(out/'cache'),XDG_CONFIG_HOME=str(out/'config'))
    avi=out/'original.avi';movie=out/'gameplay.mp4'
    record=dict(source_commit=commit,source_project=str(work),driver=script,
                driver_sha256=sha(work/script),arguments=arguments,engine=version,
                capture_implementation_sha256=sha(Path(__file__)),
                engine_sha256=sha(engine),runtime_fingerprint_before=before,
                human_play=False,device_performance='unverified',
                kind='headless_input_diagnostic' if headless else 'fresh_real_game_recording',
                status='running',started_at=time.time(),rendering='headless; no video' if headless else 'Xvfb/Mesa software, original Godot MovieMaker AV')
    write(out/'receipt.json',record)
    shutil.copyfile(work/script,out/'recording_driver.gd')
    try:
        cmd=[str(engine),'--path',str(work),'--audio-driver','Dummy','--fixed-fps','60']
        if headless:cmd+=['--headless']
        else:
            xvfb=Path(shutil.which('Xvfb') or 'build/tools/root/usr/bin/Xvfb').resolve()
            display=subprocess.Popen([str(xvfb),'-displayfd','1','-screen','0','1280x720x24','-nolisten','tcp','-ac'],stdout=subprocess.PIPE,stderr=(out/'display.log').open('wb'))
            with selectors.DefaultSelector() as sel:
                sel.register(display.stdout,selectors.EVENT_READ)
                if not sel.select(20):raise RuntimeError('Xvfb readiness timeout')
                number=display.stdout.readline().decode().strip()
            if not number.isdigit():raise RuntimeError('Xvfb display invalid')
            env['DISPLAY']=':'+number
            cmd+=['--rendering-method','gl_compatibility','--resolution','1280x720','--write-movie',str(avi)]
        cmd+=['--script',script,'--',*arguments]
        if not headless:cmd+=['--capture-movie']
        record['command']=cmd;write(out/'receipt.json',record)
        with (out/'native.log').open('wb') as f:
            child=subprocess.Popen(cmd,cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT)
            started=time.monotonic()
            while child.poll() is None:
                if time.monotonic()-started>timeout:
                    child.terminate();child.wait(timeout=10);raise TimeoutError('Bounded game recording exceeded wall budget')
                if not headless and __import__('shutil').disk_usage(out).free<500_000_000:
                    child.terminate();child.wait(timeout=10);raise RuntimeError('Recording stopped before exhausting RAM-backed media workspace')
                time.sleep(1)
        record['exit_code']=child.returncode
        record['runtime_fingerprint_after']=fingerprint(work)
        if before!=record['runtime_fingerprint_after']:raise RuntimeError('Original runtime source changed in disposable project')
        record['driver_sha256_after']=sha(work/script)
        if record['driver_sha256_after']!=record['driver_sha256']:
            record['driver_file_drift']=True
            # The original AV remains useful as an explicitly provisional
            # capture; never silently recertify it against the new source file.
        text=(out/'native.log').read_text(errors='replace')
        record['engine_error_lines']=[line for line in text.splitlines() if line.startswith(('ERROR:','SCRIPT ERROR:'))]
        record['driver_completed_successfully']=child.returncode==0 and not record['engine_error_lines'] and not record.get('driver_file_drift',False)
        if not headless:
            if not avi.exists() or avi.stat().st_size<1000:raise RuntimeError('No actual recorded AVI')
            record['raw_avi_sha256']=sha(avi);record['raw_media']=probe(avi)
            with (out/'encode.log').open('wb') as f:
                subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(avi),'-map','0:v:0','-map','0:a:0','-vf','scale=in_range=auto:out_range=tv,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','18','-color_range','tv','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(movie)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
            with (out/'decode.log').open('wb') as f:subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
            metrics=audio_metrics(movie)
            metrics.pop('speech_identity',None)
            metrics['source_type']='Original Godot MovieMaker engine audio; no TTS or substitute soundtrack'
            record.update(movie_sha256=sha(movie),media=probe(movie),original_game_audio=metrics)
            if not record['original_game_audio']['audible_signal']:raise RuntimeError('Actual game recording has no audible original track')
            # Source AVI is removed only after its digest, full stream metadata,
            # matching original audio, MP4 and complete decode have been checked.
            avi.unlink();record['raw_avi_retention']='encoded original frames/audio; source AVI digest and metadata retained'
        record['status']='captured' if record['driver_completed_successfully'] else 'captured_incomplete_or_failed_driver'
    except Exception as e:
        record.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        record['finished_at']=time.time();write(out/'receipt.json',record)
        if display:
            display.terminate()
            try:display.wait(timeout=5)
            except subprocess.TimeoutExpired:display.kill();display.wait()
    print(json.dumps({k:record.get(k) for k in ('status','exit_code','movie_sha256','driver_completed_successfully')},ensure_ascii=False),flush=True)
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True);p.add_argument('--engine',required=True)
    p.add_argument('--script',required=True);p.add_argument('--out',required=True);p.add_argument('--commit',required=True)
    p.add_argument('--headless',action='store_true');p.add_argument('--timeout',type=int,default=1200)
    args,extra=p.parse_known_args()
    capture(args.work,args.engine,args.script,extra,args.out,args.commit,headless=args.headless,timeout=args.timeout)


if __name__=='__main__':main()
