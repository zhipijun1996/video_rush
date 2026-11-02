"""Prepare bounded review inputs without committing audio/video to Git."""
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import zipfile
import requests
from video_rush.common import ROOT,read,write,sha,run,duration


def export_portable(out):
    p=out/'portable';(p/'voices').mkdir(parents=True,exist_ok=True);(p/'game').mkdir(exist_ok=True)
    records=[]
    for src in sorted((out/'voices').glob('*.m4a')):
        target=p/'voices'/src.name
        run(['ffmpeg','-v','error','-y','-i',src,'-c:a','aac','-ar','48000','-ac','1','-b:a','64k',target],timeout=60)
        old=read(src.with_suffix('.json'));rec={**old,'parent_master_sha256':sha(src),'sha256':sha(target),'duration':duration(target),'portable_processing':'Same generated performance, AAC-LC mono64kbps transport derivative; original WAV and96kbps master retained locally'};write(target.with_suffix('.json'),rec);records.append(rec)
    write(p/'voice-candidates.json',[r for r in records if not r['id'].startswith('old-')])
    capture=ROOT/'build/film-capture/ep008-r3';trace=read(capture/'trace.json');bank={}
    for n in [5,6,7,8,21]:
        r=trace['rounds'][n-1]
        a=r['commit']-.05 if n in [5,6,7] else r['reveal']-.025
        b=a+.24 if n in [5,6,7] else r['commit']+(.4 if n==8 else 1.24)
        target=p/'game'/f'round-{n}.mp4'
        run(['ffmpeg','-v','error','-y','-ss',a,'-i',capture/'continuous.mp4','-t',b-a,'-vf','crop=1116:628:402:70','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-c:a','aac','-b:a','96k','-movflags','+faststart',target],timeout=120)
        bank[str(n)]={'file':str(target.relative_to(p)),'source_in':a,'source_out':b,'sha256':sha(target),'cropped':True,'crop':[402,70,1116,628],'original_continuous_sha256':sha(capture/'continuous.mp4'),'truth':'Normal-speed cropped derivative of the preserved continuous legal battle; no replay, state injection or synthetic game frames'}
    charge=ROOT/'build/recordings/wave-film-c6f1326c824a/public/assets/audio/charge.wav'
    run(['ffmpeg','-v','error','-y','-i',charge,'-ac','1','-c:a','aac','-b:a','64k',p/'game/charge.m4a'])
    for name in ['trace.json','receipt.json']:shutil.copyfile(capture/name,p/name)
    audio_manifest=ROOT/'build/recordings/wave-film-c6f1326c824a/data/audio-manifest.json';shutil.copyfile(audio_manifest,p/'game-native-audio-manifest.json')
    write(p/'game-bank.json',bank)
    for name in ['local-model-receipt.json','qwen-probe-response.json','qwen-custom-diagnostic.json']:
        src=ROOT/'build/research/ep008-v2'/name
        if src.exists():shutil.copyfile(src,p/name)
    # Word timings belong to the preserved master performance. Codec transport
    # can change sample padding by a few milliseconds; that is not an ASR pass.
    aligned=read(out/'alignments.json')
    for id,r in aligned.items():r['portable_sha256']=sha(p/'voices'/(id+'.m4a'));r['transport_timing']='Inherited from identical performance; AAC derivative padding can differ <=24ms'
    write(p/'alignments.json',aligned)
    write(p/'manifest.json',{str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() and f.name!='manifest.json'})
    archive=out/'portable-review-inputs.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p.rglob('*')):
            if f.is_file():z.write(f,str(Path('portable')/f.relative_to(p)))
    print('Portable input ZIP',archive.stat().st_size,'bytes',sha(archive),flush=True);return archive


def restore_portable(ids,expected,out,repository,token):
    if not isinstance(ids,list) or not 0<len(ids)<=48 or any(type(i) is not int or i<=0 for i in ids):raise ValueError('Expected1–48 bounded chunk IDs')
    if not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Exact bundle SHA required')
    session=requests.Session();session.headers['Authorization']='Bearer '+token
    pieces=[]
    for aid in ids:
        if not isinstance(aid,int):raise ValueError('Artifact IDs must be integers')
        r=session.get(f'https://api.github.com/repos/{repository}/actions/artifacts/{aid}/zip',timeout=60);r.raise_for_status()
        z=zipfile.ZipFile(io.BytesIO(r.content));names=z.namelist()
        if len(names)!=1 or not re.fullmatch(r'[0-9]{3}\.bin',names[0]) or z.getinfo(names[0]).file_size>48000:raise ValueError('Expected one bounded media chunk')
        part=z.read(names[0]);
        if len(part)>48000:raise ValueError('Chunk too large')
        pieces.append(part)
    raw=b''.join(pieces)
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Review input bundle SHA256 mismatch')
    z=zipfile.ZipFile(io.BytesIO(raw));root=out.resolve()
    if any(not (root/n).resolve().is_relative_to(root) or not n.startswith('portable/') for n in z.namelist()):raise ValueError('Unsafe review bundle paths')
    if sum(i.file_size for i in z.infolist())>20_000_000:raise ValueError('Unexpected input bundle expansion')
    z.extractall(root)
    for name,h in read(root/'portable/manifest.json').items():
        if sha(root/'portable'/name)!=h:raise ValueError('Portable input mismatch: '+name)
    shutil.copyfile(root/'portable/alignments.json',root/'alignments.json')
    return {'artifact_ids':ids,'bundle_sha256':expected,'source':'Existing generated voice performances and real recording derivatives, transferred without committing media'}


def prepare(spec,out):
    from tools.collect_anime_reference import collect
    old_refs=read('episodes/ep008-r3-film.json')['references'];refs={k:old_refs[k] for k in ['light','street','dio','ultra','evil_laugh']};refs.update(spec['new_references'])
    for id,r in refs.items():
        target=ROOT/r['file']
        if target.exists() and sha(target)==r['sha256']:continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if r.get('bvid'):
            collect(r['bvid'],'build/research/ep008-r2/anime',cid=r.get('cid'),metadata=r)
            src=ROOT/'build/research/ep008-r2/anime'/(r['bvid']+'.mp4')
            if src!=target:shutil.copyfile(src,target)
        else:
            response=requests.get(r['url'],timeout=45);response.raise_for_status();target.write_bytes(response.content)
        if sha(target)!=r['sha256']:raise ValueError('Reference differs from pinned source: '+id)
    sf=ROOT/spec['music']['soundfont_path']
    if not sf.exists():
        folder=ROOT/'build/tools/fluid-r3';folder.mkdir(parents=True,exist_ok=True);deb=folder/'bank.deb'
        with requests.get(spec['music']['soundfont_url'],stream=True,timeout=(20,120)) as response:
            response.raise_for_status()
            with deb.open('wb') as f:
                for b in response.iter_content(1_048_576):f.write(b)
        if sha(deb)!=spec['music']['soundfont_archive_sha256']:raise ValueError('SoundFont archive SHA mismatch')
        run(['dpkg-deb','-x',deb,folder]);deb.unlink()
    licenses=out/'licenses';licenses.mkdir(exist_ok=True)
    notice=ROOT/'build/tools/fluid-r3/usr/share/doc/fluid-soundfont-gm/copyright'
    shutil.copyfile(notice,licenses/'FluidR3-copyright.txt')
    write(licenses/'music-source.json',{**spec['music'],'actual_soundfont_sha256':sha(sf),'composition':'Original Video Rush five-note theme and arrangement; no third-party score recording'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['export','prepare','restore']);p.add_argument('--output',default='build/episodes/ep008-v2-review');p.add_argument('--spec',default='episodes/ep008-v2-av-review.json');a=p.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    if a.stage=='export':export_portable(out)
    elif a.stage=='prepare':prepare(read(a.spec),out)
    else:
        import os
        r=restore_portable(json.loads(os.environ['VR_REVIEW_ARTIFACTS']),os.environ['VR_REVIEW_SHA256'],out,os.environ['GITHUB_REPOSITORY'],os.environ['GH_TOKEN']);write(out/'transfer-receipt.json',r)
