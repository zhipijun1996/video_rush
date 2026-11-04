"""Repair evidence-only metadata while preserving an already rendered film.

Refuses changed narration, shots, visuals, timing, soundtrack or posting copy.
Original failing content report stays in original-producer/; content is rechecked.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import requests
from video_rush.common import ROOT,read,write,sha,digest,run
from video_rush.footage import collect
from video_rush.quality import content_check,validate_evidence_registry
from video_rush.narration import audio_metrics


def comparable(spec):
    s=dict(spec);s.pop('evidence',None)
    if s.get('research_scope'):
        s['research_scope']={k:v for k,v in s['research_scope'].items() if k!='episode_evidence'}
    if s.get('music_asset'):
        s['music_asset']={k:v for k,v in s['music_asset'].items() if k not in ['path','source','transport','original_source']}
    return s


def repair():
    episode=os.environ['VR_EPISODE']
    if not episode or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in episode):raise ValueError('Unsafe episode')
    aid=int(os.environ['VR_REUSE_ARTIFACT']);expected=os.environ['VR_REUSE_SHA256']
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):raise ValueError('Need exact prior archive SHA256')
    spec=read(ROOT/os.environ['VR_SPEC']);validate_evidence_registry(spec)
    out=ROOT/'build/episodes'/episode;out.mkdir(parents=True,exist_ok=True)
    session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    r=session.get('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/'+str(aid)+'/zip',timeout=120);r.raise_for_status()
    if hashlib.sha256(r.content).hexdigest()!=expected:raise ValueError('Prior render archive differs')
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        if sum(i.file_size for i in z.infolist())>200_000_000:raise ValueError('Oversized prior delivery')
        for name in z.namelist():
            if not (out/name).resolve().is_relative_to(out.resolve()):raise ValueError('Unsafe archive path')
        z.extractall(out)
    delivery=read(out/'delivery.json')
    for name,h in delivery['files'].items():
        if sha(out/name)!=h:raise ValueError('Prior delivery member differs: '+name)
    old_spec=read(out/'script.json');sources=read(out/'sources.json');report=read(out/'report.json');timeline=read(out/'storyboard.json')
    if comparable(old_spec)!=comparable(spec):raise ValueError('Repair is evidence-only; render new audiovisual/posting changes normally')
    if not report['technical']['passed'] or sha(out/'final.mp4')!=report['final']['sha256']:raise ValueError('Need an exact technically valid prior movie')
    assets=read(ROOT/spec['asset_spec'])
    old_assets={a['id']:a for a in sources['assets']}
    for a in assets['assets']:
        if any(old_assets[a['id']].get(k)!=v for k,v in a.items()):raise ValueError('Authored visual source changed: '+a['id'])
    saved=out/'original-producer';saved.mkdir(exist_ok=True)
    for name in ['report.json','script.json','sources.json','research.json','state.json','delivery.json']:shutil.copyfile(out/name,saved/name)
    # Restore source media/quoted bytes from the same pinned recipes, without TTS or frame rendering.
    media=collect(ROOT/'build/source',assets,out/'media')
    if any(a['sha256']!=old_assets[a['id']]['sha256'] for a in media):raise ValueError('Restored source pixel/recording bytes differ')
    for name,h in delivery['files'].items():
        if name.startswith('source-evidence/') and sha(out/name)!=h:raise ValueError('Original source proof changed')
    repaired_spec={**old_spec,'evidence':spec['evidence']}
    if 'episode_evidence' in repaired_spec.get('research_scope',{}):
        repaired_spec['research_scope']={**repaired_spec['research_scope'],'episode_evidence':spec['evidence']}
    sources['evidence']=spec['evidence'];sources['assets']=media
    sources['document_sources']=read(out/'source-evidence/documents/document-manifest.json')
    research=read(out/'research.json');research['episode_evidence']=spec['evidence'];write(out/'research.json',research)
    write(out/'script.json',repaired_spec);write(out/'sources.json',sources)
    content=content_check(repaired_spec,timeline,sources)
    if not content['structural_pass']:raise ValueError('Content structure still fails: '+str(content['structural_checks']))
    run(['ffmpeg','-v','error','-xerror','-i',out/'final.mp4','-f','null','-'])
    metrics=audio_metrics(out/'final.mp4')
    if not metrics['audible_signal'] or metrics['clipped_fraction']>=.0001:raise ValueError('Preserved movie audio gate failed')
    receipt={'original_artifact':aid,'original_archive_sha256':expected,'original_content_pass':report['content']['structural_pass'],'repair':'Evidence alias ci-failure-api separated from numeric run_id; no narration/visual/timing/posting changes','new_content_checks':content['structural_checks'],'source_media_hashes_unchanged':True,'source_document_files_unchanged':True,'full_movie_decode_rechecked':True,'final_movie_sha256_unchanged':sha(out/'final.mp4'),'no_TTS_or_frame_rendering_repeated':True,'repair_commit':run(['git','rev-parse','HEAD']).strip(),'human_aesthetic_review':'pending'}
    report['content']=content;report['metadata_repair']=receipt;report['technical_proof_reuse']='Original full technical/motion audit retained for exact unchanged movie; source media and document hashes, full decode/audio and repaired content references freshly rechecked.'
    write(out/'report.json',report);write(out/'metadata-repair.json',receipt)
    state=read(out/'state.json');state['postprocess_metadata_repair']=receipt;write(out/'state.json',state)
    newfiles=set(delivery['files'])|{'metadata-repair.json'}|{str(p.relative_to(out)) for p in saved.iterdir() if p.is_file()}
    delivery['files']={n:sha(out/n) for n in sorted(newfiles)};delivery['metadata_repair']='metadata-repair.json';write(out/'delivery.json',delivery)
    print('REPAIRED SOURCE REGISTRY; original movie preserved:',receipt['final_movie_sha256_unchanged'],flush=True)


if __name__=='__main__':repair()
