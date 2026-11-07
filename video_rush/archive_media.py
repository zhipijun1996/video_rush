"""Hash-pinned public ZIP members, never executable imports or game installs."""
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import urllib.request
from urllib.parse import urlparse
import zipfile
from .common import sha

MAX_ARCHIVE=150*1024*1024
MAX_MEMBER=32*1024*1024
MAX_UNPACKED=512*1024*1024
SUFFIXES={'.png','.jpg','.jpeg','.json','.md','.txt'}


def _hash(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):
        raise ValueError('Archive and member require full SHA256')
    return value


def collect(asset, archive, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if not re.fullmatch('[A-Za-z0-9_-]+',asset['id']):raise ValueError('Unsafe archive asset ID')
    expected=_hash(archive['sha256']);member_hash=_hash(asset['sha256'])
    parsed=urlparse(archive['url'])
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.query:
        raise ValueError('Archive URL must be public HTTPS without credentials/query')
    member=asset['member'];path=PurePosixPath(member)
    if path.is_absolute() or '..' in path.parts or '\\' in member or path.suffix.lower() not in SUFFIXES:
        raise ValueError('Unsafe or unsupported archive member')
    cache=output/'.archives';cache.mkdir(exist_ok=True)
    source=cache/(expected+'.zip')
    if source.exists() and source.stat().st_size>MAX_ARCHIVE:raise ValueError('Archive exceeds size limit')
    if not source.exists() or sha(source)!=expected:
        tmp=source.with_suffix('.download')
        try:
            with urllib.request.urlopen(archive['url'],timeout=90) as response,tmp.open('wb') as f:
                total=0
                while block:=response.read(1024*1024):
                    total+=len(block)
                    if total>MAX_ARCHIVE:raise ValueError('Archive exceeds size limit')
                    f.write(block)
            if sha(tmp)!=expected:raise ValueError('Archive SHA256 mismatch')
            tmp.replace(source)
        finally:
            if tmp.exists():tmp.unlink()
    with zipfile.ZipFile(source) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if len(names)>10000 or len(names)!=len(set(names)):raise ValueError('Too many or duplicate ZIP members')
        if sum(i.file_size for i in infos)>MAX_UNPACKED:raise ValueError('ZIP unpacked size exceeds limit')
        info=z.getinfo(member)
        if info.is_dir() or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Archive member must be an ordinary file')
        if info.file_size>MAX_MEMBER:raise ValueError('Archive member exceeds size limit')
        with z.open(info) as f:data=f.read(MAX_MEMBER+1)
        if len(data)>MAX_MEMBER:raise ValueError('Archive member exceeds size limit')
        import hashlib
        if hashlib.sha256(data).hexdigest()!=member_hash:raise ValueError('Archive member SHA256 mismatch')
    dest=output/(asset['id']+path.suffix.lower())
    if not dest.exists() or sha(dest)!=member_hash:dest.write_bytes(data)
    extra={}
    if dest.suffix in {'.png','.jpg','.jpeg'}:
        from PIL import Image
        with Image.open(dest) as im:
            if im.width*im.height>60_000_000:raise ValueError('Archive image exceeds pixel limit')
            extra['dimensions']=[im.width,im.height];im.verify()
    else:
        data.decode('utf-8')
        if dest.suffix=='.json':__import__('json').loads(data)
    receipt={'archive_url':archive['url'],'archive_sha256':expected,'archive_bytes':source.stat().st_size,
             'member':member,'member_bytes':len(data),'member_sha256':member_hash,
             'method':'Exact ZIP member bytes; CRC and SHA256 checked; no scripts executed or project imported'}
    result=dict(asset,local_path=str(dest.resolve()),sha256=member_hash,archive_receipt=receipt,
                source_url=archive['page_url'],**extra)
    if asset.get('preserve_evidence'):
        evidence=output.parent/'source-evidence'/'archive-members'/dest.name
        evidence.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dest,evidence)
        result['preserved_evidence']=str(evidence.relative_to(output.parent))
    return result
