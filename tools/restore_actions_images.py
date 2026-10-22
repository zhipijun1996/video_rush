"""Restore the exact non-Git user originals; never regenerate or recompress."""
import json
import os
from pathlib import Path
import requests
from video_rush.transfers import download_chunks, restore_upload_pack

spec=json.loads(Path(os.environ['VR_SPEC']).read_text())
assets=json.loads(Path(spec['asset_spec']).read_text())
uploads=[a for a in assets['assets'] if a.get('origin')=='user_upload']
ids=json.loads(os.environ.get('VR_IMAGES_ARTIFACTS') or '[]')
if uploads:
    session=requests.Session()
    session.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    raw=download_chunks(session,os.environ['GITHUB_REPOSITORY'],ids,os.environ['VR_IMAGES_SHA256'])
    paths=restore_upload_pack(raw,uploads,Path.cwd())
    print('Original user images restored and individually SHA-verified:',len(paths))
elif ids:
    raise ValueError('Image chunks supplied but no user_upload assets were declared')
else:
    print('No additional user image transport required.')
