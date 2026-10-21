"""Install the game's hash-pinned Godot only when an episode needs reconstruction."""
from pathlib import Path
import hashlib
import io
import json
import os
import requests
import subprocess
import zipfile

spec=json.loads(Path(os.environ['VR_SPEC']).read_text())
assets=json.loads(Path(spec['asset_spec']).read_text())['assets']
recordings=[a for a in assets if a.get('origin')=='recording']
if recordings:
    commits={a['commit'] for a in recordings}
    if len(commits)!=1:raise ValueError('One frozen runtime per recorded episode')
    config=json.loads(subprocess.check_output(['git','-C','build/source','show',next(iter(commits))+':config/toolchain.json']))['godot']
    target=Path('build/engine');target.mkdir(parents=True,exist_ok=True)
    release=config['linux_x86_64']
    response=requests.get(release['url'],timeout=120);response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest()!=release['sha256']:raise ValueError('Godot download hash mismatch')
    name='Godot_v'+config['version']+'-stable_linux.x86_64'
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        (target/name).write_bytes(z.read(name))
    (target/name).chmod(0o755)
    with open(os.environ['GITHUB_ENV'],'a') as f:f.write('VIDEO_RUSH_GODOT='+str((target/name).resolve())+'\n')
    print('Hash-pinned Godot installed for real gameplay reconstruction.')
else:print('No reconstruction needed; using existing footage.')
