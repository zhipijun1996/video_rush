"""Bounded reconstruction using the original App/Router/Motor in an isolated archive."""
import os
from pathlib import Path
import selectors
import shutil
import subprocess
from .common import ROOT, read, write, run, sha, digest, probe

CASES={'jump_control','gun_up','gun_side','gun_empty','shuriken_side','fan_turn','laser_up','laser_stop','triple_up'}
SPECIAL={'boomerang_return','mine_ground','mine_air','singularity_launch'}
CASES |= SPECIAL
DRIVER=ROOT/'video_rush/drivers/weapon_showcase.gd'

def runtime_fingerprint(work):
    files=[]
    for name in ['scripts','resources','scenes','config','shaders','assets','project.godot']:
        p=work/name
        files.extend([p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file()))
    return digest({str(p.relative_to(work)):sha(p) for p in files})


def validate_trace(trace, case, frames):
    rows=trace.get('frames',[])
    if trace.get('case')!=case or len(rows)!=frames or trace.get('failures'):
        raise ValueError('Recording trace failed or incomplete')
    if not trace.get('no_midflight_position_health_resource_injection'):
        raise ValueError('Recording does not preserve real motion/resources')
    if any(r['hp']<=0 or r['epoch']!=rows[0]['epoch'] or r['actor_epoch']!=rows[0]['actor_epoch'] for r in rows):
        raise ValueError('Death or respawn invalidates this demonstration')
    if len({tuple(r['position']) for r in rows})<10:
        raise ValueError('No real movement in recording')
    if (case=='jump_control' and trace['accepted_shots']!=0) or (case!='jump_control' and trace['accepted_shots']<1):
        raise ValueError('Expected attack/control not observed')

    kinds={e['kind'] for e in trace.get('events',[])}
    if case=='boomerang_return' and not {'returning','caught'}<=kinds:
        raise ValueError('Recall and actual catch were not observed')
    if case=='mine_ground' and not {'attached','blast'}<=kinds:
        raise ValueError('Mine attachment and detonation were not observed')
    if case=='mine_air' and 'blast' not in kinds:
        raise ValueError('Air detonation was not observed')
    if case=='singularity_launch' and not any(r.get('phase')=='singularity' for r in rows):
        raise ValueError('Singularity hold was not observed')


def capture(repo, asset):
    repo=Path(repo);commit=run(['git','-C',repo,'rev-parse',asset['commit']+'^{commit}']).strip()
    case=asset['case'];frames=asset.get('frames',480)
    driver=ROOT/'video_rush/drivers/special_weapons.gd' if case in SPECIAL else DRIVER
    if case not in CASES or type(frames) is not int or not 120<=frames<=600:
        raise ValueError('Unsupported/beyond-budget recording recipe')
    game_toolchain=__import__('json').loads(run(['git','-C',repo,'show',commit+':config/toolchain.json']))['godot']
    local=ROOT/'build/tools/godot'/('Godot_v'+game_toolchain['version']+'-stable_linux.x86_64')
    engine=os.getenv('VIDEO_RUSH_GODOT') or (str(local) if local.exists() else shutil.which('godot'))
    if not engine:raise RuntimeError('Pinned Godot binary unavailable')
    version=run([engine,'--version']).strip()
    if not version.startswith(game_toolchain['version_prefix']):
        raise ValueError('Godot version mismatch; recording blocked before rendering')
    folder=ROOT/'build/recordings'/('weapons-'+commit[:12]);work=folder/'project';folder.mkdir(parents=True,exist_ok=True)
    recipe={'source_commit':commit,'case':case,'frames':frames,'driver_sha256':sha(driver),'capture_implementation_sha256':sha(Path(__file__)),'engine':version,'seed':'level-design-v2-baseline/08'}
    key=digest(recipe);target=folder/(case+'-'+key[:10]);target.mkdir(exist_ok=True)
    movie=target/'movie.mp4';receipt=target/'receipt.json'
    if receipt.exists():
        r=read(receipt)
        if r.get('recipe')==recipe and movie.exists() and sha(movie)==r.get('movie_sha256') and (target/'trace.json').exists() and sha(target/'trace.json')==r.get('trace_sha256'):
            validate_trace(read(target/'trace.json'),case,frames)
            return movie,r
    for old in sorted(folder.glob(case+'-*/receipt.json')):
        previous=read(old);old_recipe=previous.get('recipe',{})
        comparable=lambda value:{k:v for k,v in value.items() if k!='capture_implementation_sha256'}
        old_movie=old.parent/'movie.mp4';old_trace=old.parent/'trace.json'
        if comparable(old_recipe)==comparable(recipe) and old_movie.exists() and old_trace.exists() and sha(old_movie)==previous.get('movie_sha256') and sha(old_trace)==previous.get('trace_sha256'):
            validate_trace(read(old_trace),case,frames)
            if previous.get('source_repo_unchanged') and runtime_fingerprint(work)==previous.get('runtime_fingerprint_after'):
                return old_movie,previous
    if not (folder/'archive.json').exists():
        work.mkdir(exist_ok=True)
        names=run(['git','-C',repo,'ls-tree','--name-only',commit]).splitlines()
        names=[n for n in names if n not in {'.agents','.github','.gitignore','docs','preview','build'}]
        from .git_media import prefetch
        fetched=prefetch(repo,commit,names)
        if fetched:print(f'  batch-fetched {fetched} source blobs without checkout',flush=True)
        arch=subprocess.Popen(['git','-C',str(repo),'archive',commit,'--',*names],stdout=subprocess.PIPE)
        subprocess.run(['tar','-x','-C',str(work)],stdin=arch.stdout,check=True,timeout=120);arch.stdout.close()
        if arch.wait():raise RuntimeError('Source archive failed')
        run([engine,'--headless','--path',work,'--editor','--import'],log=folder/'import.log',timeout=240)
        write(folder/'archive.json',{'commit':commit,'excluded':['docs','preview','build'],'source_repo_readonly':True})
    shutil.copyfile(driver,work/'tools/video_rush_weapon.gd')
    before=runtime_fingerprint(work)
    repo_before=run(['git','-C',repo,'status','--porcelain'])
    display=None;env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='4')
    xvfb=os.getenv('VIDEO_RUSH_XVFB') or shutil.which('Xvfb') or str(ROOT/'build/tools/root/usr/bin/Xvfb')
    try:
        display=subprocess.Popen([xvfb,'-displayfd','1','-screen','0','1280x720x24','-nolisten','tcp','-ac'],stdout=subprocess.PIPE,stderr=(target/'display.log').open('wb'))
        with selectors.DefaultSelector() as sel:
            sel.register(display.stdout,selectors.EVENT_READ)
            if not sel.select(20):raise RuntimeError('Virtual display did not start')
            number=display.stdout.readline().decode().strip()
        if not number.isdigit():raise RuntimeError('Invalid virtual display')
        env['DISPLAY']=':'+number
        avi=target/'raw.avi';trace=target/'trace.json'
        run([engine,'--path',work,'--rendering-method','gl_compatibility','--audio-driver','Dummy','--fixed-fps','60','--write-movie',avi,
             '--script','tools/video_rush_weapon.gd','--','--case='+case,'--frames='+str(frames),'--output='+str(trace)],
            log=target/'capture.log',timeout=240,env=env)
        log=(target/'capture.log').read_text()
        if any(e in log for e in ['SCRIPT ERROR:','Parse Error:','SHADER ERROR:','ERROR:']):
            raise RuntimeError('Engine error in capture; see capture.log')
        value=read(trace);validate_trace(value,case,frames)
        after=runtime_fingerprint(work)
        if before!=after or repo_before!=run(['git','-C',repo,'status','--porcelain']):
            raise RuntimeError('Runtime or read-only source working tree changed during recording')
        run(['ffmpeg','-v','error','-y','-i',avi,'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',movie],log=target/'encode.log',timeout=120)
        run(['ffmpeg','-v','error','-xerror','-i',movie,'-f','null','-'],timeout=90)
        r={'recipe':recipe,'kind':'historical_reconstruction','movie_sha256':sha(movie),'trace_sha256':sha(trace),'ffprobe':probe(movie),
           'manifest_hash':value['manifest_hash'],'runtime_fingerprint_before':before,'runtime_fingerprint_after':after,'initialization':value['initialization'],'accepted_attacks':value['accepted_shots'],
           'scope':value['scope'],'source_repo_unchanged':True,'rendering':'Xvfb + Mesa software; not physical-device FPS',
           'driver_source':str(driver.relative_to(ROOT))}
        write(receipt,r);avi.unlink();return movie,r
    except Exception as e:
        write(target/'failure.json',{'recipe':recipe,'error':str(e),'status':'failed_no_recording_success_claim'})
        raise
    finally:
        if display:
            display.terminate()
            try:display.wait(timeout=5)
            except subprocess.TimeoutExpired:display.kill();display.wait()
