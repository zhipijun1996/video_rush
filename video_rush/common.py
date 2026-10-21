from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run(args, *, cwd=None, log=None, timeout=300, env=None):
    started = time.time()
    p = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                       text=True, timeout=timeout, env=env)
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_text('$ ' + ' '.join(map(str, args)) + '\n' + p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError(f'{args[0]} exited {p.returncode}: {(p.stderr or p.stdout)[-1800:]}')
    return p.stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]))


def duration(path):
    return float(probe(path)['format']['duration'])


def font(bold=False):
    p = os.getenv('VIDEO_RUSH_FONT') or ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if not Path(p).exists():
        raise RuntimeError('Install fonts-noto-cjk or set VIDEO_RUSH_FONT')
    return p
