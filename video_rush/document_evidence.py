"""Preserve exact repository documents behind editorial quotations and diagrams."""
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit
import requests
from .common import sha,write


def collect_documents(documents,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[]
    for d in documents:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',d['id']):raise ValueError('Unsafe document ID')
        path=Path(d['path'])
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe source document path')
        commit=d['commit']
        if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Full document commit required')
        expected='https://raw.githubusercontent.com/'+d['repository']+'/'+commit+'/'+path.as_posix()
        if d['url']!=expected:raise ValueError('Document URL must match pinned repository/commit/path')
        dest=output/d['id']/path.name
        if not dest.exists() or sha(dest)!=d['sha256']:
            r=requests.get(expected,timeout=45);r.raise_for_status()
            if len(r.content)>8_000_000:raise ValueError('Source document exceeds8MB')
            if hashlib.sha256(r.content).hexdigest()!=d['sha256']:raise ValueError('Source document bytes differ: '+d['id'])
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(r.content)
        data=dest.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=d['blob_sha']:raise ValueError('Source document Git blob differs: '+d['id'])
        for quote in d.get('verified_quotes',[]):
            if quote not in data.decode('utf-8'):raise ValueError('Displayed quote absent from document: '+d['id'])
        records.append({**d,'local_path':str(dest.resolve()),'sha256':sha(dest),'quoted_document_not_browser_screenshot':True})
    write(output/'document-manifest.json',records);return records
