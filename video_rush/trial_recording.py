"""Continuous original-controller V-R12 trial, including its real return latch."""
import os
import shutil
import subprocess
from pathlib import Path
from .common import ROOT, read, write, sha, digest

DRIVER = ROOT/'video_rush/drivers/stargate_trial.gd'


def validate_trace(t):
    if t.get('failures') != 0 or t.get('position_writes_after_entry') is not False:
        raise ValueError('Trial failed or has undeclared position writes')
    if not t.get('finish_latch') or not t.get('returned_to_entry'):
        raise ValueError('The actual finish latch and return to entry are required')
    rows = t.get('rows', [])
    if t.get('capabilities') != {'H':True,'W':True,'D':True,'Q':True}:
        raise ValueError('The actual all-ability entry preset was not observed')
    if not {'jump_edge','shoot_release','grapple'} <= {a['action'] for a in t.get('inputs',[])}:
        raise ValueError('No original action requests recorded')
    if not 100 < t['frames'] <= 15000 or len(rows) < 100:
        raise ValueError('Missing/beyond-budget continuous trial trace')
    if len({r['session'] for r in rows}) != 1 or min(r['hp'] for r in rows) <= 0:
        raise ValueError('Player died or session changed during purported continuous clear')
    if len({r['hp'] for r in rows}) != 1:
        raise ValueError('Hazard recovery may reposition within the same session; do not certify it as an uninterrupted clear')
    if any(sum((x-y)**2 for x,y in zip(b['p'],a['p'])) > 40**2 for a,b in zip(rows,rows[1:])):
        raise ValueError('A frame contains a position discontinuity beyond original traversal speed')
    if any(b['frame'] != a['frame']+1 for a,b in zip(rows,rows[1:])):
        raise ValueError('Trial trace contains omitted frames')
    labels = [e['phase'] for e in t['events']]
    expected = ['entry','entry_to_w1','w1_to_h1','h1_to_w3','w3_to_relay',
                'relay','relay_to_w4','w4_to_h2','h2_to_w5','w5_to_w6',
                'w6_to_finish','finish_platform','return_bridge','return_chute','returned']
    if labels != expected:
        raise ValueError('Missing original-input route stages')
    if not rows[-1]['floor'] or rows[-1]['p'][1] < 1800 or not rows[-1]['latch']:
        raise ValueError('No observed supported return to entry after real latch')


def capture(repo, asset):
    from tools.current_gameplay_job import prepare
    from tools.record_current_gameplay import capture as native
    commit = asset['commit']
    if asset['case'] != 'stargate-v12-hwdq' or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Supported trial and immutable source commit required')
    recipe = dict(source_commit=commit, driver_sha256=sha(DRIVER), module_sha256=sha(Path(__file__)),
                  runner_sha256=sha(ROOT/'tools/record_current_gameplay.py'),
                  preparation_sha256=sha(ROOT/'tools/current_gameplay_job.py'))
    base = Path(os.environ.get('VIDEO_RUSH_TRIAL_CAPTURE_ROOT', ROOT/'build/recordings/stargate')).resolve()/commit[:12]
    target = base/('capture-'+digest(recipe)[:12]);receipt = target/'receipt.json'
    if receipt.exists():
        r = read(receipt)
        if r.get('recipe') != recipe or r.get('status') != 'captured' or sha(target/'gameplay.mp4') != r['movie_sha256'] or sha(target/'trace.json') != r['trace_sha256']:
            raise ValueError('Preserved trial is failed or changed; inspect it before a new attempt')
        validate_trace(read(target/'trace.json'))
        return target/'gameplay.mp4', r
    spec = dict(repository=asset['repository'],main_commit=commit,
                stages={'trial':{'version':'main','driver':str(DRIVER.relative_to(ROOT))}})
    work,engine,driver,_ = prepare(spec,'trial',base)
    with (base/'world-build.log').open('wb') as log:
        subprocess.run(['python','tools/world/build.py'],cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        code = "from pathlib import Path;import json,sys;sys.path.insert(0,'tools/world');from workbench_seed import preview_catalog;p=Path('build/workbench/preview-world.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(preview_catalog(Path.cwd()),ensure_ascii=False)+'\\n')"
        subprocess.run(['python','-c',code],cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    r = native(work,engine,driver,['--output='+str(target/'trace.json')],target,commit,timeout=1500)
    validate_trace(read(target/'trace.json'))
    if not r['driver_completed_successfully']:
        raise ValueError('Native engine/driver error in trial')
    r.update(recipe=recipe,trace_sha256=sha(target/'trace.json'),truth=read(target/'trace.json')['scope'])
    write(receipt,r)
    for name in ['preparation.json','import.log','world-build.log']:
        shutil.copyfile(base/name,target/name)
    return target/'gameplay.mp4',r
