"""Reconstruct and record one exact native game stage on a hosted runner."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import zipfile
import requests

from video_rush.common import read, write, sha
from video_rush.snapshot import snapshot
from tools.record_current_gameplay import capture

ROOTS = ['project.godot', 'export_presets.cfg', 'game', 'assets', 'scripts',
         'scenes', 'resources', 'config', 'shaders', 'tools', 'tests', 'addons',
         'experiments', 'docs/data', 'docs/bible', 'docs/project', 'AGENTS.md']
ROOTS += ['art/world-art-v2/assets/pixel']


def prepare(spec, stage_id, base):
    base=Path(base).resolve();base.mkdir(parents=True,exist_ok=True)
    stage=spec['stages'][stage_id]
    commit=spec['main_commit' if stage['version']=='main' else 'random_commit']
    repo=base/'source.git';work=base/'project'
    if not repo.exists():
        subprocess.run(['git','init','--bare',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'remote','add','origin','https://github.com/'+spec['repository']+'.git'],check=True)
    subprocess.run(['git','-C',str(repo),'fetch','--no-tags','--filter=blob:none','--depth=1','origin',commit],check=True,timeout=300)
    # A bare partial repository is a separate source cache, never the user's
    # active game worktree. prefetch batches runtime objects before extraction.
    subprocess.run(['git','-C',str(repo),'config','remote.origin.promisor','true'],check=True)
    subprocess.run(['git','-C',str(repo),'config','remote.origin.partialclonefilter','blob:none'],check=True)
    info=snapshot(repo,commit,ROOTS,work)
    lock=read(work/'config/toolchain.json')['godot'];platform=lock['linux_x86_64']
    engine=base/'engine'/platform['binary'];engine.parent.mkdir(exist_ok=True)
    if not engine.exists() or sha(engine)!=platform['binary_sha256']:
        archive=base/'engine.zip'
        with requests.get(platform['url'],stream=True,timeout=(30,120)) as r:
            r.raise_for_status()
            with archive.open('wb') as f:
                for block in r.iter_content(1024*1024):f.write(block)
        if sha(archive)!=platform['sha256']:raise ValueError('Pinned engine ZIP digest mismatch')
        with zipfile.ZipFile(archive) as z:
            members=[n for n in z.namelist() if Path(n).name==platform['binary']]
            if len(members)!=1:raise ValueError('Pinned engine archive must contain exactly one named binary')
            with z.open(members[0]) as source,engine.open('wb') as target:shutil.copyfileobj(source,target)
        if sha(engine)!=platform['binary_sha256']:raise ValueError('Pinned engine binary digest mismatch')
        engine.chmod(0o755);archive.unlink()
    if stage.get('compile_world',False):
        # Execute the snapshot's own compiler. Only generated build/world is
        # written; authored game files are never patched for the recording.
        import sys
        with (base/'world-build.log').open('wb') as log:
            subprocess.run([sys.executable,str(work/'tools/world/build.py')],cwd=work,
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1',LP_NUM_THREADS='4',
             XDG_DATA_HOME=str(base/'import-userdata'),XDG_CACHE_HOME=str(base/'import-cache'),XDG_CONFIG_HOME=str(base/'import-config'))
    with (base/'import.log').open('wb') as log:
        subprocess.run([str(engine),'--headless','--path',str(work),'--editor','--import'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    script=stage['driver']
    if script.startswith('video_rush/'):
        local=Path(script);name='tools/video_rush_'+sha(local)[:12]+'.gd'
        shutil.copyfile(local,work/name);script=name
    write(base/'preparation.json',dict(commit=commit,snapshot=info,engine=lock['version_exact'],engine_sha256=sha(engine),driver=script,driver_sha256=sha(work/script)))
    return work,engine,script,commit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',default='episodes/ep011-gameplay.json');p.add_argument('--stage',required=True)
    p.add_argument('--base',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();spec=read(a.spec);s=spec['stages'][a.stage]
    work,engine,driver,commit=prepare(spec,a.stage,a.base)
    out=Path(a.output).resolve()
    capture(work,engine,driver,[f'--seed={s["seed"]}',*s['args'],f'--output={out}/trace.json'],out,commit,timeout=1500)
    # A failed player is retained and advertised as an incomplete attempt.
    # It is not an infrastructure error, nor a fabricated successful clear.
    if not (out/'gameplay.mp4').exists():raise RuntimeError('No game recording produced')


if __name__=='__main__':main()
