"""Collect an anonymous public Bilibili reference with provenance and bounded retries.

Does not remove watermarks, use login cookies, alter signed URLs or access paid media.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

import requests


def collect(bvid,folder):
    if not re.fullmatch(r'BV[A-Za-z0-9]{10}',bvid):raise ValueError('Expected a Bilibili BV identifier')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    target=folder/(bvid+'.mp4');receipt=folder/(bvid+'.json')
    if target.exists() and receipt.exists():
        old=json.loads(receipt.read_text())
        if hashlib.sha256(target.read_bytes()).hexdigest()==old['sha256']:return old
    target.unlink(missing_ok=True)
    page='https://www.bilibili.com/video/'+bvid+'/'
    headers={'User-Agent':'Mozilla/5.0','Referer':page}
    r=requests.get(page,headers=headers,timeout=25);r.raise_for_status()
    (folder/(bvid+'.page.html')).write_text(r.text)
    m=re.search(r'__INITIAL_STATE__\s*=\s*',r.text)
    if not m:raise ValueError('Public page lacks video metadata')
    data=json.JSONDecoder().raw_decode(r.text[m.end():])[0]['videoData']
    r=requests.get('https://api.bilibili.com/x/player/playurl',
                   params={'bvid':bvid,'cid':data['cid'],'qn':32,'fnval':0},headers=headers,timeout=25)
    r.raise_for_status();play=r.json()
    if play.get('code')!=0:raise RuntimeError('Anonymous playback unavailable: '+str(play.get('code')))
    streams=play['data'].get('durl',[])
    if len(streams)!=1:raise ValueError('Expected single anonymous progressive stream')
    stream=streams[0];size=stream['size']
    if not 0<size<=60*1024*1024:raise ValueError('Reference exceeds bounded download size')
    # Select the API-provided backup on ordinary CDN errors, not invented hosts.
    urls=[stream['url']]+(stream.get('backup_url') or [])
    failures=[];chunk=524288;parts=folder/(bvid+'-parts');parts.mkdir(exist_ok=True)
    for url in urls:
        try:
            with requests.get(url,headers={**headers,'Range':'bytes=0-0'},timeout=12,stream=True) as check:
                if check.status_code in (401,403):raise PermissionError('Public media access denied; stop collection')
                check.raise_for_status()
        except PermissionError:raise
        except requests.RequestException as exc:
            failures.append({'stage':'cdn_availability','error':type(exc).__name__});continue
        def fetch(i):
            a=i*chunk;b=min(size,a+chunk)-1;f=parts/str(i)
            if f.exists() and f.stat().st_size==b-a+1:return True
            for attempt in range(2):
                try:
                    resp=requests.get(url,headers={**headers,'Range':f'bytes={a}-{b}'},timeout=18)
                    if resp.status_code in (401,403):
                        raise PermissionError('Access denied; do not retry or change destinations to bypass')
                    resp.raise_for_status()
                    if resp.status_code==200 and a==0 and len(resp.content)==size:
                        target.write_bytes(resp.content);return True
                    if resp.status_code!=206 or len(resp.content)!=b-a+1:raise ValueError('Invalid partial response')
                    f.write_bytes(resp.content);return True
                except PermissionError:raise
                except Exception as exc:
                    if attempt:failures.append({'part':i,'error':type(exc).__name__})
            return False
        with ThreadPoolExecutor(max_workers=3) as pool:ok=list(pool.map(fetch,range((size+chunk-1)//chunk)))
        if target.exists() or all(ok):
            if not target.exists():
                with target.open('wb') as out:
                    for i in range(len(ok)):out.write((parts/str(i)).read_bytes())
            break
    if not target.exists():
        (folder/(bvid+'.failure.json')).write_text(json.dumps(failures,indent=2));raise RuntimeError('Public CDN download incomplete')
    obj={'bvid':bvid,'page':page,'title':data['title'],'uploader':data['owner']['name'],
         'uploader_description':data.get('desc'),'cid':data['cid'],'bytes':target.stat().st_size,
         'duration_reported':data['duration'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
         'rights_status':'Copyrighted reference, permission not established; public availability is not a license.',
         'download_failures':failures}
    receipt.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    for f in parts.iterdir():f.unlink()
    parts.rmdir();return obj


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bvid');p.add_argument('--output',default='build/research/ep008-r2/anime')
    a=p.parse_args();print(json.dumps(collect(a.bvid,a.output),ensure_ascii=False,indent=2))
