"""Reuse exact original media from a verified prior delivery, never its edit."""
import os
import re
import stat
import zipfile
from pathlib import Path,PurePosixPath
import requests
from .common import sha,run,probe

MAX_ZIP=160*1024*1024
MAX_UNPACKED=512*1024*1024


def archive(delivery,output):
    repository=delivery['repository'];aid=delivery['artifact_id'];expected=delivery['sha256']
    if not re.fullmatch('[A-Za-z0-9_-]+',delivery['episode']):raise ValueError('Unsafe source episode ID')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) or type(aid) is not int or aid<=0 or not re.fullmatch('[a-f0-9]{64}',expected):
        raise ValueError('Prior delivery requires repository, Artifact ID and full SHA256')
    cache=Path(os.environ.get('VIDEO_RUSH_EPISODE_ARCHIVES',Path(output)/'.episode-archives'));cache.mkdir(parents=True,exist_ok=True)
    dest=cache/(expected+'.zip')
    if not dest.exists() or sha(dest)!=expected:
        token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:raise ValueError('Restore the hash-pinned prior delivery cache or provide the authorized Actions token')
        url=f'https://api.github.com/repos/{repository}/actions/artifacts/{aid}/zip';tmp=dest.with_suffix('.download')
        try:
            with requests.get(url,headers={'Authorization':'Bearer '+token},stream=True,timeout=(30,120)) as r:
                r.raise_for_status()
                with tmp.open('wb') as f:
                    size=0
                    for block in r.iter_content(1024*1024):
                        size+=len(block)
                        if size>MAX_ZIP:raise ValueError('Prior delivery exceeds ZIP size limit')
                        f.write(block)
            if sha(tmp)!=expected:raise ValueError('Prior delivery ZIP hash mismatch')
            tmp.replace(dest)
        finally:tmp.unlink(missing_ok=True)
    if dest.stat().st_size>MAX_ZIP:raise ValueError('Prior delivery exceeds ZIP size limit')
    return dest


def collect(asset,delivery,output):
    output=Path(output);source=archive(delivery,output)
    if not re.fullmatch('[A-Za-z0-9_-]+',asset['id']):raise ValueError('Unsafe prior-media ID')
    with zipfile.ZipFile(source) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if len(names)>10000 or len(names)!=len(set(names)) or sum(i.file_size for i in infos)>MAX_UNPACKED:raise ValueError('Invalid/oversized delivery archive')
        for i in infos:
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe delivery member')
        import json,hashlib
        original=json.loads(z.read('sources.json'));matched=[a for a in original['assets'] if a['id']==asset['source_asset']]
        if len(matched)!=1:raise ValueError('Prior media ID not unique/present')
        prior=matched[0]
        if prior['sha256']!=asset['sha256'] or prior.get('commit')!=asset.get('commit') or prior['kind']!=asset['kind']:
            raise ValueError('Prior media identity or provenance mismatch')
        member='media/'+Path(prior['local_path']).name
        if Path(member).suffix not in {'.mp4','.png','.jpg','.jpeg'}:raise ValueError('Unsupported prior media')
        data=z.read(member)
        if hashlib.sha256(data).hexdigest()!=asset['sha256']:raise ValueError('Prior media member hash mismatch')
        dest=output/(asset['id']+Path(member).suffix);dest.write_bytes(data)
        # Preserve original evidence verbatim, including its actual producer and date.
        for name in names:
            if name.startswith('recording-evidence/') and not name.endswith('/'):
                p=output.parent/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
        evidence=output.parent/'source-evidence'/('delivery-'+delivery['episode']+'-sources.json');evidence.parent.mkdir(exist_ok=True);evidence.write_bytes(z.read('sources.json'))
    extra={k:prior[k] for k in ['recording_receipt','source_url','truth','rights'] if k in prior}
    if dest.suffix=='.mp4':extra['ffprobe']=probe(dest)
    if 'frame_seconds' in asset:
        seconds=asset['frame_seconds']
        if not isinstance(seconds,(int,float)) or not 0<=seconds<float(extra['ffprobe']['format']['duration']):raise ValueError('Prior-media frame outside clip')
        frame=output/(asset['id']+'.png');run(['ffmpeg','-v','error','-y','-ss',str(seconds),'-i',dest,'-frames:v','1',frame],timeout=60)
        extra.update(source_movie_sha256=sha(dest),extraction={'seconds':seconds,'method':'Exact original recording frame'});extra.pop('ffprobe');dest=frame
    return dict(asset,**extra,local_path=str(dest.resolve()),sha256=sha(dest),prior_delivery={'repository':delivery['repository'],'artifact_id':delivery['artifact_id'],'archive_sha256':delivery['sha256'],'episode':delivery['episode'],'source_asset':asset['source_asset'],'member':member,'member_sha256':asset['sha256'],'method':'Reuse exact source media, not prior edited final. Original provenance/evidence retained.'})
