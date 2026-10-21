"""Send a verified local ZIP to a GitHub-hosted Actions Artifact, without rerendering.

The runner publishes only an encrypted, one-blob upload capability. Its runtime
token never leaves GitHub. No media or private keys are committed to Git.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from video_rush.common import ROOT, read, write, sha
from video_rush.publish import verified_files


def gh(*args):
    # Capture output, never log capability URLs or credentials.
    p = subprocess.run(['gh', *map(str, args)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('GitHub API command failed: ' + p.stderr[:500])
    return p.stdout


def decrypt_capsule(capsule, private):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    payload = json.loads(base64.b64decode(capsule))
    key = private.decrypt(base64.b64decode(payload['key']), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    url = AESGCM(key).decrypt(base64.b64decode(payload['nonce']),
                             base64.b64decode(payload['data']), None).decode()
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname.endswith('.blob.core.windows.net'):
        raise ValueError('Unexpected artifact storage destination')
    return url


def main():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import requests
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--repository', default='zhipijun1996/video_rush')
    args = p.parse_args()
    out = args.output.resolve()
    files = verified_files(out)
    episode = read(out/'script.json')['episode']
    name = 'video-rush-' + episode
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', name):
        raise ValueError('Invalid episode artifact name')
    bundle = out/(episode+'-actions-delivery.zip')
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for filename in [*files, 'delivery.json', 'script.json', 'state.json']:
            z.write(out/filename, filename)
    expected = sha(bundle)
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    keyfile = out/'.actions-bridge-key.pem'
    with keyfile.open('wb') as f:
        keyfile.chmod(0o600)
        f.write(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    public = base64.b64encode(private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    # These dispatch inputs contain no private credentials.
    payload = out/'actions-dispatch.json'
    write(payload, {'ref':'main', 'inputs':{'artifact_name':name, 'public_key':public,
        'byte_size':str(bundle.stat().st_size), 'sha256':expected}})
    head = gh('api', f'repos/{args.repository}/commits/main', '--jq', '.sha').strip()
    started = time.time()
    gh('api', f'repos/{args.repository}/actions/workflows/deliver-existing.yml/dispatches',
       '--method', 'POST', '--input', payload)
    print('Actions delivery dispatched; waiting for the encrypted upload destination.', flush=True)
    run = None
    deadline = time.time()+12*60
    while time.time()<deadline:
        if not run:
            runs = json.loads(gh('api', f'repos/{args.repository}/actions/workflows/deliver-existing.yml/runs?event=workflow_dispatch&per_page=10'))
            run = next((r for r in runs['workflow_runs'] if r['head_sha']==head
                        and r['display_title']=='Deliver '+name
                        and __import__('datetime').datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).timestamp()>=started-5), None)
            if not run:
                time.sleep(5);continue
            write(out/'actions-delivery.pending.json', {'run_id':run['id'],'url':run['html_url'],
                  'zip_sha256':expected,'status':'waiting_for_upload','movie_sha256':files['final.mp4']})
            print(run['html_url'], flush=True)
        jobs = json.loads(gh('api',f'repos/{args.repository}/actions/runs/{run["id"]}/jobs'))['jobs']
        job = next((j for j in jobs if j['name']=='Receive verified episode'),None)
        if job:
            check = json.loads(gh('api', job['check_run_url']))
            match = re.search(r'VR_CAPSULE:([A-Za-z0-9+/=]+)',check['output'].get('summary') or '')
            if match:
                url = decrypt_capsule(match[1], private)
                # Preserve inherited proxy/TLS settings. No GitHub credential is
                # forwarded to blob storage; the capability authorizes this ZIP.
                with bundle.open('rb') as f:
                    response = requests.put(url, data=f, headers={
                        'x-ms-blob-type':'BlockBlob', 'Content-Type':'application/zip'}, timeout=180)
                if response.status_code not in (200,201):
                    raise RuntimeError(f'Artifact blob upload failed: HTTP {response.status_code}; capability URL withheld')
                print('Verified delivery ZIP uploaded; waiting for GitHub finalization.', flush=True)
                keyfile.unlink(missing_ok=True)
                write(out/'actions-delivery.pending.json', {'run_id':run['id'],'url':run['html_url'],
                      'zip_sha256':expected,'status':'blob_uploaded_awaiting_finalization','movie_sha256':files['final.mp4']})
                return
            if job['status']=='completed':
                raise RuntimeError('Receiver job completed before accepting the ZIP: '+str(job['conclusion']))
        time.sleep(5)
    raise TimeoutError('Actions did not request the upload within 12 minutes')


if __name__=='__main__':
    try:
        main()
    except Exception as e:
        print(str(e),file=sys.stderr)
        raise SystemExit(1)
