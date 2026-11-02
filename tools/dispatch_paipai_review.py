"""Reuse bounded Actions transport for exact performances and real footage.

Media stays in build/ and temporary one-day Artifacts. It never enters Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
from tools.dispatch_actions import transfer_bytes,gh


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--repository',default='zhipijun1996/video_rush');p.add_argument('--ref',default='ep008-v2-av-director');a=p.parse_args()
    raw=a.bundle.read_bytes()
    if not 0<len(raw)<=48*48000:raise ValueError('Review bundle exceeds bounded transport capacity')
    folder=Path('build/actions-transfer')/('v2-'+secrets.token_hex(6));folder.mkdir(parents=True);ids=[]
    for group in range(0,len(raw),16*48000):ids+=transfer_bytes(raw[group:group+16*48000],folder,a.repository,'VOICES')
    h=hashlib.sha256(raw).hexdigest();payload={'ref':a.ref,'inputs':{'review_artifacts':json.dumps(ids),'review_sha256':h}}
    f=folder/'review-dispatch.json';f.write_text(json.dumps(payload));gh('api',f'repos/{a.repository}/actions/workflows/paipai-v2-review.yml/dispatches','--method','POST','--input',f)
    (folder/'receipt.json').write_text(json.dumps({'ids':ids,'bundle_sha256':h,'bytes':len(raw),'ref':a.ref,'status':'review workflow dispatched; no full-film render requested'},indent=2));print('Three-trial review dispatched. Receipt:',folder/'receipt.json',flush=True)


if __name__=='__main__':main()
