from __future__ import annotations
import os
from pathlib import Path
import subprocess
import urllib.request
from urllib.parse import urlparse
from .common import ROOT, sha, write, probe, run, digest
from .history import git


def collect(repo, spec, output):
    """Read exact committed bytes; never mutate the game working tree."""
    repo, output = Path(repo), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    collected = []
    for asset in spec['assets']:
        origin=asset.get('origin','git')
        if origin == 'user_upload':
            from PIL import Image
            import shutil
            source = (ROOT / asset['path']).resolve()
            if not source.is_relative_to(ROOT / 'build' / 'inputs') or source.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                raise ValueError('User-uploaded images must stay inside build/inputs')
            if not source.exists() or sha(source) != asset['sha256']:
                raise ValueError('User-uploaded image missing or SHA256 mismatch: ' + asset['id'])
            with Image.open(source) as im:
                im.verify()
            dest = output / (asset['id'] + source.suffix.lower())
            shutil.copyfile(source, dest)
            collected.append(dict(asset, local_path=str(dest.resolve()), sha256=sha(dest),
                                  source_url='user-upload:' + asset['original_filename']))
            continue
        if origin=='recording':
            from .recording import capture
            source,receipt=capture(repo,asset)
            evidence_dir=output.parent/'recording-evidence';evidence_dir.mkdir(exist_ok=True)
            for name in ['trace.json','receipt.json','capture.log']:
                __import__('shutil').copyfile(source.parent/name,evidence_dir/(asset['case']+'-'+name))
            dest=output/(asset['id']+('.png' if 'frame_seconds' in asset else '.mp4'))
            if 'frame_seconds' in asset:
                run(['ffmpeg','-v','error','-y','-ss',str(asset['frame_seconds']),'-i',source,'-frames:v','1',dest],timeout=60)
            elif not dest.exists() or sha(dest)!=receipt['movie_sha256']:
                __import__('shutil').copyfile(source,dest)
            obj=dict(asset,local_path=str(dest.resolve()),sha256=sha(dest),recording_receipt=receipt,
                source_url=f'https://github.com/{spec["repository"]}/tree/{receipt["recipe"]["source_commit"]}')
            if dest.suffix=='.mp4':obj['ffprobe']=probe(dest)
            collected.append(obj)
            continue
        if origin in ('editorial','external'):
            suffix=Path(urlparse(asset['url']).path).suffix.lower() if origin=='external' else '.png'
            dest=output/(asset['id']+(suffix if suffix in ('.mp4','.webm') else '.png'))
            if origin=='editorial':
                from .graphics import graphic
                graphic(dest,asset['graphic'])
                obj=dict(asset,local_path=str(dest.resolve()),sha256=sha(dest),
                         source_url='original-editorial-graphic:'+asset['id'],generator_sha256=sha(ROOT/'video_rush/graphics.py'))
            else:
                url=asset['url']
                if urlparse(url).scheme!='https' or not asset.get('sha256'):
                    raise ValueError('External media requires HTTPS and a pinned SHA256')
                if not dest.exists() or sha(dest)!=asset['sha256']:
                    tmp=dest.with_suffix('.download')
                    with urllib.request.urlopen(url,timeout=60) as response,tmp.open('wb') as f:
                        total=0
                        while block:=response.read(1024*1024):
                            total+=len(block)
                            if total>50*1024*1024:raise ValueError('External media exceeds 50MiB')
                            f.write(block)
                    if sha(tmp)!=asset['sha256']:
                        tmp.unlink();raise ValueError('External asset SHA256 mismatch')
                    tmp.replace(dest)
                obj=dict(asset,local_path=str(dest.resolve()),source_url=asset['page_url'])
                if dest.suffix in ('.mp4','.webm'):
                    obj['ffprobe']=probe(dest)
                    if not any(s['codec_type']=='video' for s in obj['ffprobe']['streams']):
                        raise ValueError('External movie must contain a decodable video stream')
            collected.append(obj)
            continue
        if origin!='git':raise ValueError('Unsupported asset origin')
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
        if 'frame_seconds' in asset:
            # Cover/detail stills retain both the exact movie blob and the extraction recipe.
            import math
            from .render import crop_filter
            seconds = asset['frame_seconds']
            if (path.suffix.lower() not in ('.mp4', '.webm', '.avi') or
                    not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or
                    not 0 <= seconds < float(obj['ffprobe']['format']['duration'])):
                raise ValueError('Frame extraction requires a finite time inside a real source movie')
            filt = crop_filter(asset.get('frame_crop'), dest).rstrip(',')
            frame = output / (asset['id'] + '.png')
            args = ['ffmpeg', '-v', 'error', '-y', '-ss', str(seconds), '-i', dest,
                    '-frames:v', '1']
            if filt: args += ['-vf', filt]
            run([*args, frame], timeout=60)
            obj.update(source_local_path=str(dest.resolve()), source_sha256=obj['sha256'],
                       source_ffprobe=obj.pop('ffprobe'), local_path=str(frame.resolve()),
                       sha256=sha(frame), extraction={'seconds': seconds,
                       'crop': asset.get('frame_crop'), 'method': 'FFmpeg exact movie frame; optional crop only'})
        if asset.get('preserve_evidence'):
            import shutil
            evidence = output.parent / 'source-evidence' / (asset['id'] + dest.suffix)
            evidence.parent.mkdir(exist_ok=True)
            shutil.copyfile(dest, evidence)
            obj['preserved_evidence'] = str(evidence.relative_to(output.parent))
        collected.append(obj)
    # Preserve the exact five user originals for future recovery from delivery.
    for item in collected:
        if item.get('user_attachment'):
            if item['sha256'] != item.get('attachment_sha256', item['sha256']):
                raise ValueError('Original user attachment bytes do not match declared SHA256')
            original = Path(item['original_filename'])
            if original.name != str(original) or original.suffix.lower() not in {'.jpg','.jpeg','.png'}:
                raise ValueError('Upload original filename must be a basename')
            backup = output.parent / 'original_uploads' / original.name
            backup.parent.mkdir(exist_ok=True)
            __import__('shutil').copyfile(item['local_path'], backup)
            item['preserved_original'] = 'original_uploads/' + original.name
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
