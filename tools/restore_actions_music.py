"""Restore bounded BGM transfer artifacts in the hosted producer, then remove them."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import requests
import zipfile

repo=os.environ['GITHUB_REPOSITORY']
ids=json.loads(os.environ['VR_MUSIC_ARTIFACTS'])
expected=os.environ['VR_MUSIC_SHA256']
assert isinstance(ids,list) and 0<len(ids)<=16 and all(type(i) is int and i>0 for i in ids)
assert re.fullmatch('[a-f0-9]{64}',expected)
session=requests.Session();session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
chunks={}
for artifact_id in ids:
    r=session.get(f'https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip',timeout=120)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert len(z.namelist())==1
        name=z.namelist()[0]
        assert re.fullmatch(r'[0-9]{3}\.bin',name) and name not in chunks
        assert z.getinfo(name).file_size<=48000
        chunks[name]=z.read(name)
assert sorted(chunks)==[f'{i:03}.bin' for i in range(len(chunks))]
raw=b''.join(chunks[n] for n in sorted(chunks))
assert hashlib.sha256(raw).hexdigest()==expected
music=Path('build/music/the_kindred_hearth-actions.ogg');music.parent.mkdir(parents=True,exist_ok=True);music.write_bytes(raw)
spec=json.loads(Path(os.environ['VR_SPEC']).read_text())
original=spec['music_asset'].copy()
spec['music_asset'].update(path=str(music),sha256=expected,
    source='User-uploaded original, compressed for Actions transfer; first 145 seconds, mono Opus 20kbps',
    original_sha256=original['sha256'],original_source=original['source'],
    transport='temporary Actions chunk artifacts; not committed to Git')
Path('build/actions-episode.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
print('Requested BGM derivative restored and hash-verified.')
