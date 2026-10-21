from __future__ import annotations
import os
from pathlib import Path
import subprocess
from .common import sha, write, probe, run
from .history import git


def collect(repo, spec, output):
    """Read exact committed bytes; never mutate the game working tree."""
    repo, output = Path(repo), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    collected = []
    for asset in spec['assets']:
        sha_full = git(repo, 'rev-parse', f'{asset["commit"]}^{{commit}}').strip()
        path = Path(asset['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Asset paths must be repository-relative')
        dest = output / (asset['id'] + path.suffix.lower())
        blob = f'{sha_full}:{path.as_posix()}'
        blob_sha = git(repo, 'rev-parse', blob).strip()
        # Stream large media directly; do not load video blobs into RAM.
        if not dest.exists() or run(['git', 'hash-object', dest]).strip() != blob_sha:
            tmp = dest.with_suffix(dest.suffix + '.tmp')
            with tmp.open('wb') as f:
                subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', blob], stdout=f, check=True)
            tmp.replace(dest)
        obj = dict(asset, commit=sha_full, blob_sha=blob_sha, local_path=str(dest.resolve()), sha256=sha(dest),
                   source_url=f'https://github.com/{spec["repository"]}/blob/{sha_full}/{path.as_posix()}')
        if path.suffix.lower() in ('.mp4', '.webm', '.avi'):
            obj['ffprobe'] = probe(dest)
        collected.append(obj)
    write(output / 'manifest.json', collected)
    return collected


def record(repo, commit, args, output, *, godot='godot', display=':99', timeout=240):
    """Re-run a committed recording driver in a disposable, reduced git archive.

    This is an explicit tool for ShotSpecs after checking the source's CLI/help.
    No synthetic inputs or unknown driver options are invented.
    """
    output = Path(output).resolve()
    work = output / 'project'
    if work.exists():
        raise ValueError('Recording workspace exists; choose a fresh output directory')
    work.mkdir(parents=True)
    head = git(repo, 'rev-parse', f'{commit}^{{commit}}').strip()
    roots = git(repo, 'ls-tree', '--name-only', head).splitlines()
    excludes = {'.agents', '.github', 'docs', 'preview', 'build', '.gitignore'}
    paths = [p for p in roots if p not in excludes]
    arch = subprocess.Popen(['git', '-C', str(repo), 'archive', head, '--', *paths], stdout=subprocess.PIPE)
    subprocess.run(['tar', '-x', '-C', str(work)], stdin=arch.stdout, check=True)
    arch.stdout.close()
    if arch.wait():
        raise RuntimeError('git archive failed')
    env = dict(os.environ, DISPLAY=display, LIBGL_ALWAYS_SOFTWARE='1', LP_NUM_THREADS='4')
    receipt = {'source_commit': head, 'kind': 'historical_reconstruction', 'driver_args': args,
               'engine': run([godot, '--version']).strip(), 'rendering': 'Mesa software / virtual display',
               'warning': 'New recording of old source; not contemporaneous original footage'}
    try:
        run([godot, '--headless', '--path', work, '--editor', '--import'], log=output/'import.log', timeout=180, env=env)
        run([godot, '--path', work, '--rendering-method', 'gl_compatibility', *args],
            log=output/'record.log', timeout=timeout, env=env)
        receipt['status'] = 'driver_completed_requires_media_validation'
    except Exception as e:
        receipt.update(status='failed', error=str(e))
        write(output/'receipt.json', receipt)
        raise
    write(output/'receipt.json', receipt)
    return receipt
