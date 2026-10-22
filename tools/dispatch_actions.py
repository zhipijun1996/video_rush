"""Transfer bounded user BGM/images through Actions, then dispatch production.

No media is committed. Each group is limited to768KB and temporary chunk
Artifacts expire in one day or are deleted after successful production.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import secrets
import subprocess
import time
import zipfile


def gh(*args):
    p=subprocess.run(['gh',*map(str,args)],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[:500])
    return p.stdout


def transfer_bytes(raw,folder,repository,label):
    if not 0<len(raw)<=16*48000:raise ValueError(f'{label} transport requires <=768KB')
    transfer=secrets.token_hex(6)
    parts=[raw[i:i+48000] for i in range(0,len(raw),48000)]
    def dispatch(item):
        i,b=item;payload=folder/f'{label}-{i:03}.json'
        payload.write_text(json.dumps({'ref':'main','inputs':{'transfer':transfer,'part':f'{i:03}',
            'label':label,'data_base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}}))
        gh('api',f'repos/{repository}/actions/workflows/receive-music.yml/dispatches','--method','POST','--input',payload)
        payload.unlink()
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(dispatch,enumerate(parts)))
    print(f'Dispatched {len(parts)} bounded {label} chunks; transfer {transfer}.',flush=True)
    deadline=time.time()+8*60
    while time.time()<deadline:
        runs=json.loads(gh('api',f'repos/{repository}/actions/workflows/receive-music.yml/runs?per_page=100'))['workflow_runs']
        runs=[r for r in runs if r['display_title'].startswith(label+' '+transfer+'-')]
        bad=[r for r in runs if r['status']=='completed' and r['conclusion']!='success']
        if bad:raise RuntimeError('Media transfer failed: '+bad[0]['html_url'])
        if len(runs)==len(parts) and all(r['conclusion']=='success' for r in runs):
            ids=[]
            for run in sorted(runs,key=lambda r:r['display_title']):
                artifacts=json.loads(gh('api',f'repos/{repository}/actions/runs/{run["id"]}/artifacts'))['artifacts']
                if len(artifacts)!=1:raise ValueError('Expected one media chunk per transfer run')
                ids.append(artifacts[0]['id'])
            return ids
        time.sleep(10)
    raise TimeoutError('Media transfer did not complete within8minutes')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('music',type=Path)
    p.add_argument('--spec',default='episodes/ep002.json')
    p.add_argument('--episode',default='ep002')
    p.add_argument('--repository',default='zhipijun1996/video_rush')
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text());assets=json.loads(Path(spec['asset_spec']).read_text())
    # Prepare and validate all user inputs before creating any remote artifacts.
    raw=a.music.read_bytes()
    if not 0<len(raw)<=768000:raise ValueError('BGM transport requires <=768KB')
    uploads=[item for item in assets['assets'] if item.get('origin')=='user_upload']
    images=None
    if uploads:
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for item in uploads:
                path=Path(item['path']).resolve()
                if not path.is_relative_to(Path('build/inputs').resolve()):raise ValueError('Upload paths must stay inside build/inputs')
                data=path.read_bytes()
                if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Upload SHA256 mismatch')
                archive.writestr(path.name,data)
        images=stream.getvalue()
        if len(images)>768000:raise ValueError('Upload pack exceeds768KB; reduce selected batch without silently recompressing originals')
    folder=Path('build/actions-transfer')/secrets.token_hex(6);folder.mkdir(parents=True)
    ids=transfer_bytes(raw,folder,a.repository,'BGM')
    image_ids=transfer_bytes(images,folder,a.repository,'IMAGES') if images else []
    inputs={'topic':spec['title'],'spec':a.spec,'episode':a.episode,
            'music_artifacts':json.dumps(ids),'music_sha256':hashlib.sha256(raw).hexdigest()}
    if images:inputs.update(images_artifacts=json.dumps(image_ids),images_sha256=hashlib.sha256(images).hexdigest())
    payload=folder/'produce.json';payload.write_text(json.dumps({'ref':'main','inputs':inputs}))
    gh('api',f'repos/{a.repository}/actions/workflows/produce.yml/dispatches','--method','POST','--input',payload)
    (folder/'receipt.json').write_text(json.dumps({'chunk_artifacts':ids,'image_chunk_artifacts':image_ids,
        'music_sha256':hashlib.sha256(raw).hexdigest(),'images_sha256':hashlib.sha256(images).hexdigest() if images else None,
        'status':'production_dispatched'},indent=2))
    print('Requested media transferred. Hosted production dispatched.',flush=True)

if __name__=='__main__':main()
