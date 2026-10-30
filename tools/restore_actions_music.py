"""Restore bounded BGM transfer artifacts in the hosted producer, then remove them."""
import json
import os
from pathlib import Path
import re
import requests

repo=os.environ['GITHUB_REPOSITORY']
ids=json.loads(os.environ['VR_MUSIC_ARTIFACTS'])
expected=os.environ['VR_MUSIC_SHA256']
assert isinstance(ids,list) and 0<len(ids)<=16 and all(type(i) is int and i>0 for i in ids)
assert re.fullmatch('[a-f0-9]{64}',expected)
session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
from video_rush.transfers import download_chunks
raw=download_chunks(session,repo,ids,expected)
music=Path('build/music/the_kindred_hearth-actions.ogg');music.parent.mkdir(parents=True,exist_ok=True);music.write_bytes(raw)
spec=json.loads(Path(os.environ['VR_SPEC']).read_text())
original=spec['music_asset'].copy()
spec['music_asset'].update(path=str(music),sha256=expected,
    source=(original['source']+'; exact transferred Opus derivative restored'
            if original.get('origin')=='procedural_original' else 'User-uploaded original, compressed for Actions transfer; first 145 seconds, mono Opus 20kbps'),
    original_sha256=original.get('original_sha256',original['sha256']),original_source=original['source'],
    transport='temporary Actions chunk artifacts; not committed to Git')
Path('build/actions-episode.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
print('Requested BGM derivative restored and hash-verified.')
