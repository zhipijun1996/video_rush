"""Record all showcase takes from one immutable source snapshot."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse

from tools.current_gameplay_job import prepare
from tools.record_current_gameplay import capture
from video_rush.common import read, sha
from video_rush.demo_showcase import audit_take
from video_rush.gameplay import load_capture


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',default='episodes/ep016-showcase.json')
    p.add_argument('--base',default='build/native-demo-showcase')
    p.add_argument('--captures',default='build/captures')
    p.add_argument('--workers',type=int,default=2,choices=[1,2])
    a=p.parse_args();spec=read(a.spec)
    work,engine,driver,commit=prepare(spec,'p10',Path(a.base))
    root=Path(a.captures).resolve()
    def record(case):
        name='demo-'+case;out=root/name
        arguments=[*spec['stages'][case]['args'],f'--output={out}/trace.json']
        if out.exists():
            retained=load_capture(root,name,commit)
            receipt=retained['receipt']
            if receipt['driver_sha256']!=sha(work/driver) or receipt['arguments']!=arguments:
                raise ValueError('Retained input recipe changed; use a fresh --captures directory: '+case)
            audit_take(retained['trace'],case)
            print('REUSED verified native take:',case,flush=True)
            return
        capture(work,engine,driver,arguments,out,commit,timeout=900)
        audit_take(read(out/'trace.json'),case)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(record,spec['stages']))


if __name__=='__main__':main()
