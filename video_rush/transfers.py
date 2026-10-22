"""Bounded Actions media transport and exact user-upload restoration."""
import hashlib
import io
import re
import zipfile
from pathlib import Path


def download_chunks(session, repo, ids, expected):
    if not isinstance(ids, list) or not 0 < len(ids) <= 16 or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError('Expected 1–16 media chunk Artifact IDs')
    if not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Media transport needs an exact SHA256')
    chunks = {}
    for aid in ids:
        response = session.get(f'https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip', timeout=120)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
            if len(names) != 1 or not re.fullmatch(r'[0-9]{3}\.bin', names[0]):
                raise ValueError('Invalid media chunk archive')
            name = names[0]
            if name in chunks or archive.getinfo(name).file_size > 48000:
                raise ValueError('Duplicate or oversized media chunk')
            chunks[name] = archive.read(name)
    if sorted(chunks) != [f'{i:03}.bin' for i in range(len(chunks))]:
        raise ValueError('Missing or unordered media chunks')
    raw = b''.join(chunks[n] for n in sorted(chunks))
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Media transfer SHA256 mismatch')
    return raw


def restore_upload_pack(raw, uploads, root):
    root = Path(root).resolve()
    expected = {Path(a['path']).name: a for a in uploads}
    if len(expected) != len(uploads):
        raise ValueError('Upload basenames must be unique')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError('Upload ZIP must contain exactly the declared images')
        pending = []
        for name, asset in expected.items():
            dest = (root / asset['path']).resolve()
            if not dest.is_relative_to(root / 'build' / 'inputs') or Path(name).suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                raise ValueError('Uploads must be images inside build/inputs')
            if archive.getinfo(name).file_size > 50 * 1024 * 1024:
                raise ValueError('Upload image is oversized')
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != asset['sha256']:
                raise ValueError('Upload image SHA256 mismatch: ' + name)
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            pending.append((dest, data))
    for dest, data in pending:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return [str(dest) for dest, _ in pending]
