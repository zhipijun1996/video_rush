"""Exact committed-file snapshots for partial clones without git archive."""
import os
from pathlib import Path, PurePosixPath
import subprocess
import threading
from .common import run
from .git_media import prefetch


def snapshot(repo,commit,paths,output):
    repo=Path(repo);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    fetched=prefetch(repo,commit,paths)
    if fetched:print(f'  batch-fetched {fetched} source blobs without checkout',flush=True)
    raw=subprocess.check_output(['git','-C',str(repo),'ls-tree','-rz',commit,'--',*paths])
    entries=[]
    for entry in raw.split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,oid=meta.decode().split();name=name.decode()
        if kind!='blob':raise ValueError('Snapshot requires ordinary committed files, not submodule entries')
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Invalid committed path')
        entries.append((mode,oid,name))
    if not entries:raise ValueError('Empty snapshot request')
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
    proc=subprocess.Popen(['git','-C',str(repo),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    timer=threading.Timer(180,proc.kill);timer.daemon=True;timer.start();total=0
    try:
        for mode,oid,name in entries:
            proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
            header=proc.stdout.readline().decode().strip().split()
            if len(header)!=3 or header[:2]!=[oid,'blob']:raise RuntimeError('Missing/unexpected snapshot object: '+oid)
            size=int(header[2]);total+=size;p=output/name;p.parent.mkdir(parents=True,exist_ok=True)
            if mode=='120000':
                target=proc.stdout.read(size).decode()
                if PurePosixPath(target).is_absolute():raise ValueError('Absolute symlink unsupported in game snapshot')
                if p.is_symlink() or p.exists():p.unlink()
                p.symlink_to(target)
            else:
                if p.is_symlink():p.unlink()
                with p.open('wb') as f:
                    remaining=size
                    while remaining:
                        block=proc.stdout.read(min(1024*1024,remaining))
                        if not block:raise RuntimeError('Snapshot object stream ended early')
                        f.write(block);remaining-=len(block)
                p.chmod(0o755 if mode=='100755' else 0o644)
            if proc.stdout.read(1)!=b'\n':raise RuntimeError('Invalid snapshot stream delimiter')
        proc.stdin.close()
        if proc.wait(timeout=10):raise RuntimeError('Git snapshot reader failed')
    finally:
        timer.cancel()
        if proc.poll() is None:proc.kill();proc.wait()
        proc.stdout.close();proc.stderr.close()
    return {'files':len(entries),'bytes':total,'prefetched_blobs':fetched,'method':'exact git ls-tree + cat-file --batch; no checkout or archive attribute walk'}
