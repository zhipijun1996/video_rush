"""Paginated GitHub snapshot + all local refs, with exact immutable provenance."""
from __future__ import annotations
import datetime
import json
from pathlib import Path
import subprocess
import urllib.request
from .common import run, write, sha


def git(repo, *args):
    return run(['git', '-C', repo, *args], timeout=180)


def api(endpoint):
    # gh retains the platform's injected authentication and proxy configuration.
    try:
        return json.loads(run(['gh', 'api', endpoint], timeout=120))
    except RuntimeError as e:
        if '401' not in str(e) and '403' not in str(e):
            raise
        # Public read fallback retains proxy, never changes or prints credentials.
        req = urllib.request.Request('https://api.github.com/' + endpoint,
                                     headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'VideoRush/0.1'})
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)


def pages(endpoint):
    out = []
    for n in range(1, 1000):
        batch = api(f'{endpoint}{"&" if "?" in endpoint else "?"}per_page=100&page={n}')
        out.extend(batch)
        if len(batch) < 100:
            return out
    raise RuntimeError('Pagination safety bound reached; snapshot incomplete')


def research(repo, output, remote='zhipijun1996/gunman-rush', refresh=False):
    repo, output = Path(repo), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Fetch is opt-in: the pipeline uses a frozen source snapshot on resume.
    if refresh:
        git(repo, 'fetch', '--all', '--prune')
    refs = git(repo, 'for-each-ref', '--format=%(refname)|%(objectname)', 'refs/remotes/').splitlines()
    log = git(repo, 'log', '--all', '--format=%H%x09%aI%x09%P%x09%s').splitlines()
    commits = [dict(zip(['sha', 'date', 'parents', 'subject'], x.split('\t', 3))) for x in log]
    write(output / 'commits.json', commits)
    write(output / 'refs.json', [dict(zip(['ref', 'sha'], x.split('|', 1))) for x in refs])
    pulls = json.loads((output / 'pulls.json').read_text()) if (output / 'pulls.json').exists() and not refresh else pages(f'repos/{remote}/pulls?state=all')
    write(output / 'pulls.json', pulls)
    errors = []
    for p in pulls:
        num = p['number']
        dest = output / 'prs' / f'{num}.json'
        if dest.exists() and not refresh:
            continue
        try:
            detail = api(f'repos/{remote}/pulls/{num}')
            detail['files_complete'] = pages(f'repos/{remote}/pulls/{num}/files')
            detail['github_files_truncated'] = len(detail['files_complete']) >= 3000 or len(detail['files_complete']) < detail.get('changed_files', 0)
            detail['issue_comments_complete'] = pages(f'repos/{remote}/issues/{num}/comments') if detail.get('comments', 0) else []
            detail['review_comments_complete'] = pages(f'repos/{remote}/pulls/{num}/comments') if detail.get('review_comments', 0) else []
            detail['reviews_complete'] = pages(f'repos/{remote}/pulls/{num}/reviews')
            write(dest, detail)
        except Exception as e:
            errors.append({'pr': num, 'error': str(e)})
    # GitHub's files API caps at 3000. Recover all changed paths locally and disclose it.
    capped = []
    for p in pulls:
        dest = output / 'prs' / f'{p["number"]}.json'
        if not dest.exists():
            continue
        detail = json.loads(dest.read_text())
        detail['github_files_truncated'] = len(detail.get('files_complete', [])) >= 3000 or len(detail.get('files_complete', [])) < detail.get('changed_files', 0)
        if detail['github_files_truncated']:
            capped.append(p['number'])
            try:
                detail['local_changed_paths_complete'] = git(repo, 'diff', '--name-only', detail['base']['sha'] + '...' + detail['head']['sha']).splitlines()
            except Exception as error:
                detail['local_diff_error'] = str(error)
        write(dest, detail)
    # Catalog paths from EVERY remote tip, not just HEAD/README.
    catalog = {}
    for item in refs:
        ref, head = item.split('|', 1)
        paths = git(repo, 'ls-tree', '-r', '--name-only', head).splitlines()
        catalog[ref] = {'sha': head, 'documents': [p for p in paths if p.endswith(('.md', '.json')) and ('docs/' in p or 'report' in p)],
                        'media': [p for p in paths if p.lower().endswith(('.png', '.jpg', '.webm', '.mp4', '.avi'))]}
    write(output / 'branch_catalog.json', catalog)
    report = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'repository': remote,
              'head': git(repo, 'rev-parse', 'HEAD').strip(), 'main': git(repo, 'rev-parse', 'origin/main').strip(),
              'shallow': git(repo, 'rev-parse', '--is-shallow-repository').strip() == 'true',
              'commit_count': len(commits), 'ref_count': len(refs), 'pr_count': len(pulls),
              'pr_detail_count': len(list((output / 'prs').glob('*.json'))), 'github_file_list_capped_prs': capped, 'errors': errors,
              'earliest_commit': min(x['date'] for x in commits), 'latest_commit': max(x['date'] for x in commits),
              'coverage': 'All fetched refs metadata and media/doc paths; all PR bodies/API files/discussions; API file caps disclosed, full local changed paths recovered; curated stories require separate evidence reading.'}
    write(output / 'scope.json', report)
    return report
