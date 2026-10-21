"""Batch required blobs in partial clones without checking out the game source."""
import subprocess
from pathlib import Path
from .common import run


def prefetch(repo, commit, paths):
    repo=Path(repo)
    promisor=subprocess.run(['git','-C',str(repo),'config','--get','remote.origin.promisor'],capture_output=True,text=True,check=False)
    if promisor.returncode or promisor.stdout.strip()!='true':return 0
    tree=run(['git','-C',repo,'ls-tree','-r','--format=%(objecttype) %(objectname)',commit,'--',*paths])
    needed={line.split()[1] for line in tree.splitlines() if line.startswith('blob ')}
    # Enumerating present objects never asks a promisor remote to fill missing ones.
    present=set(run(['git','-C',repo,'cat-file','--batch-all-objects','--batch-check=%(objectname)']).splitlines())
    missing=sorted(needed-present)
    if missing:
        # Same bounded protocol used by Git's lazy fetch, but with all wants together.
        p=subprocess.run(['git','-C',str(repo),'-c','fetch.negotiationAlgorithm=noop','fetch','origin','--no-tags',
                          '--no-write-fetch-head','--recurse-submodules=no','--filter=blob:none','--stdin'],
                         input='\n'.join(missing)+'\n',capture_output=True,text=True,timeout=300)
        if p.returncode:raise RuntimeError('Batched media fetch failed: '+p.stderr[-1000:])
        after=set(run(['git','-C',repo,'cat-file','--batch-all-objects','--batch-check=%(objectname)']).splitlines())
        if not needed<=after:raise RuntimeError('Batch fetch did not provide every requested blob')
    return len(missing)
