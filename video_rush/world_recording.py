"""Bounded PR142 recording through the existing source-owned native route helpers."""
import os
import shutil
import subprocess
from pathlib import Path
from .common import ROOT, digest, read, sha, write

DRIVER = ROOT / 'video_rush/drivers/fixed_world_intro.gd'


def validate_trace(trace):
    if trace.get('failures') != 0 or trace.get('player_position_health_progress_writes') is not False:
        raise ValueError('Fixed-world route failed its bounded checks')
    entered = [m['room'] for m in trace['markers'] if m['event'] == 'room_enter']
    if entered[:2] != ['P-R03', 'P-R21']:
        raise ValueError('Actual P-R03 to P-R21 crossing was not observed')
    events = {m['event']: m['frame'] for m in trace['markers']}
    if events.get('map_close', 0) - events.get('map_open', 0) != 240:
        raise ValueError('Explored-map capture interval missing')
    if not 1 <= trace['frames'] <= 3600 or len(trace.get('rows', [])) < 20:
        raise ValueError('Missing or out-of-budget gameplay trace')
    if 'recoil_end' not in events or events['recoil_end'] <= events.get('recoil_start',3600) or 'P-R22' not in entered:
        raise ValueError('Actual canal entry and recoil landing are missing')


def capture(repo, asset):
    from tools.current_gameplay_job import prepare
    from tools.record_current_gameplay import capture as native_capture
    if asset['case'] != 'pr142-intro-map':
        raise ValueError('Unsupported fixed-world case')
    commit = asset['commit']
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Exact full source commit required')
    recipe = {'source_commit': commit, 'case': asset['case'], 'driver_sha256': sha(DRIVER),
              'module_sha256': sha(Path(__file__)), 'runner_sha256': sha(ROOT/'tools/record_current_gameplay.py'),
              'preparation_sha256': sha(ROOT/'tools/current_gameplay_job.py')}
    base = Path(os.environ.get('VIDEO_RUSH_WORLD_CAPTURE_ROOT', ROOT/'build/recordings/fixed-world')).resolve()/commit[:12]
    target = base/('capture-'+digest(recipe)[:12])
    receipt = target/'receipt.json'
    if receipt.exists():
        value = read(receipt)
        if value.get('recipe') == recipe and value.get('status') == 'captured':
            if sha(target/'gameplay.mp4') != value['movie_sha256'] or sha(target/'trace.json') != value['trace_sha256']:
                raise ValueError('Cached capture bytes changed')
            validate_trace(read(target/'trace.json'))
            return target/'gameplay.mp4', value
        raise ValueError('Preserved failed capture exists; inspect it before selecting a fresh recording root')
    spec = {'repository': asset['repository'], 'main_commit': commit,
            'stages': {'intro': {'version': 'main', 'driver': str(DRIVER.relative_to(ROOT))}}}
    work, engine, driver, _ = prepare(spec, 'intro', base)
    # The authored scenes consume an ignored derived bundle, never the raw docs.
    with (base/'world-build.log').open('wb') as log:
        subprocess.run(['python', str(work/'tools/world/build.py')], cwd=work,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    value = native_capture(work, engine, driver, ['--output='+str(target/'trace.json')], target, commit, timeout=900)
    validate_trace(read(target/'trace.json'))
    if not value['driver_completed_successfully']:
        raise ValueError('Native recording has engine or driver errors')
    value.update(recipe=recipe,trace_sha256=sha(target/'trace.json'),truth=read(target/'trace.json')['scope'])
    write(receipt,value)
    shutil.copyfile(base/'preparation.json',target/'preparation.json')
    shutil.copyfile(base/'import.log',target/'import.log')
    shutil.copyfile(base/'world-build.log',target/'world-build.log')
    return target/'gameplay.mp4',value
