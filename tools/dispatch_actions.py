"""Transfer a compact user soundtrack through Actions inputs and dispatch production.

No media is committed to Git and no third-party file host is used. Temporary
chunks are removed after successful production (otherwise expire in one day).
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time


def gh(*args):
    p=subprocess.run(['gh',*map(str,args)],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[:500])
    return p.stdout


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('music',type=Path)
    p.add_argument('--spec',default='episodes/ep002.json')
    p.add_argument('--episode',default='ep002')
    p.add_argument('--repository',default='zhipijun1996/video_rush')
    a=p.parse_args()
    raw=a.music.read_bytes()
    if not 0<len(raw)<=16*48000:raise ValueError('BGM transport requires <=768KB; encode a low-volume derivative first')
    transfer=secrets.token_hex(6);folder=Path('build/actions-transfer')/transfer;folder.mkdir(parents=True)
    parts=[raw[i:i+48000] for i in range(0,len(raw),48000)]
    def dispatch(item):
        i,b=item;payload=folder/f'{i:03}.json'
        payload.write_text(json.dumps({'ref':'main','inputs':{'transfer':transfer,'part':f'{i:03}',
            'data_base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}}))
        gh('api',f'repos/{a.repository}/actions/workflows/receive-music.yml/dispatches','--method','POST','--input',payload)
        payload.unlink()
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(dispatch,enumerate(parts)))
    print(f'Dispatched {len(parts)} bounded BGM chunks; transfer {transfer}.',flush=True)
    deadline=time.time()+8*60;ids=None
    while time.time()<deadline:
        runs=json.loads(gh('api',f'repos/{a.repository}/actions/workflows/receive-music.yml/runs?per_page=100'))['workflow_runs']
        runs=[r for r in runs if r['display_title'].startswith('BGM '+transfer+'-')]
        if any(r['status']=='completed' and r['conclusion']!='success' for r in runs):
            raise RuntimeError('Soundtrack transfer failed: '+next(r['html_url'] for r in runs if r['status']=='completed' and r['conclusion']!='success'))
        if len(runs)==len(parts) and all(r['conclusion']=='success' for r in runs):
            ids=[]
            for run in sorted(runs,key=lambda r:r['display_title']):
                artifacts=json.loads(gh('api',f'repos/{a.repository}/actions/runs/{run["id"]}/artifacts'))['artifacts']
                assert len(artifacts)==1
                ids.append(artifacts[0]['id'])
            break
        time.sleep(10)
    if ids is None:raise TimeoutError('Soundtrack transfer did not complete within 8 minutes')
    payload=folder/'produce.json'
    data={'ref':'main','inputs':{'topic':json.loads(Path(a.spec).read_text())['title'],'spec':a.spec,'episode':a.episode,
          'music_artifacts':json.dumps(ids),'music_sha256':hashlib.sha256(raw).hexdigest()}}
    payload.write_text(json.dumps(data))
    gh('api',f'repos/{a.repository}/actions/workflows/produce.yml/dispatches','--method','POST','--input',payload)
    (folder/'receipt.json').write_text(json.dumps({'transfer':transfer,'chunk_artifacts':ids,'music_sha256':hashlib.sha256(raw).hexdigest(),'status':'production_dispatched'},indent=2))
    print('Soundtrack transferred. Hosted production dispatched.',flush=True)

if __name__=='__main__':main()
