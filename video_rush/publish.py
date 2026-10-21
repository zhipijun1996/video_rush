"""Validated deliverables -> GitHub prerelease. Never publishes to Bilibili."""
from pathlib import Path
import json
import re
import zipfile
from .common import ROOT, read, write, sha, run

REQUIRED_FILES = {'final.mp4', 'cover.png', 'bilibili.md', 'script.md',
                  'storyboard.json', 'subtitles.ass', 'sources.json',
                  'report.json', 'phone-review.md'}


def posting_copy(spec, description):
    """Phone-copyable submission materials, also shown in the release body."""
    title=spec['title'].strip()
    if not title or not description.strip():
        raise ValueError('Submission materials require a title and description')
    alternatives=[t for t in spec.get('title_candidates',[]) if t!=title]
    return ('# B站投稿资料\n\n## 推荐标题\n\n'+title+
            '\n\n## 备选标题\n\n'+(''.join('- '+t+'\n' for t in alternatives) or '无\n')+
            '\n## 简介（可复制）\n\n'+description.strip()+
            '\n\nAI配音；正式/开发演示/设计示意分别标注。完整来源与授权见sources.json。\n'
            '\n投稿前请按phone-review.md完整试听；本系统未自动上传B站。\n')


def verified_files(output):
    output=Path(output)
    report=read(output/'report.json');delivery=read(output/'delivery.json')
    if not report['technical']['passed'] or not report['content']['structural_pass']:
        raise ValueError('Prerelease requires technical and content-structure checks; human review may remain pending')
    if sha(output/'final.mp4')!=report['final']['sha256']:
        raise ValueError('Final movie changed after validation')
    missing=REQUIRED_FILES-set(delivery['files'])
    if missing:
        raise ValueError('Missing required delivery files: '+', '.join(sorted(missing)))
    for name,expected in delivery['files'].items():
        p=(output/name).resolve()
        if not p.is_relative_to(output.resolve()) or sha(p)!=expected:
            raise ValueError('Delivery manifest mismatch: '+name)
    return delivery['files']


def publish(output, repository='zhipijun1996/video_rush', tag=None):
    output=Path(output).resolve();files=verified_files(output);spec=read(output/'script.json')
    tag=tag or spec['episode']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,80}',tag):raise ValueError('Unsafe release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Unsafe repository')
    commit=run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
    if run(['git','-C',ROOT,'status','--porcelain']).strip():
        raise ValueError('Commit episode specs/code before prerelease so the release target is reproducible')
    remote=run(['git','-C',ROOT,'ls-remote','origin','refs/heads/main']).split()[0]
    if remote!=commit:raise ValueError('Push this commit before creating a prerelease')
    bundle=output/(tag+'-delivery.zip')
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name in [*files,'delivery.json','state.json','script.json']:
            if (output/name).exists():z.write(output/name,name)
    uploads=[output/'final.mp4',output/'cover.png',output/'bilibili.md',bundle]
    receipt=output/'prerelease.json';input_hashes={p.name:sha(p) for p in uploads}
    # Existing stable releases must never be converted or overwritten.
    try:
        current=json.loads(run(['gh','api',f'repos/{repository}/releases/tags/{tag}']))
    except RuntimeError as e:
        if '404' not in str(e):raise
        current=None
    if not current:
        # The by-tag API may omit drafts; list owned releases before creating a duplicate.
        listed=json.loads(run(['gh','api',f'repos/{repository}/releases?per_page=100']))
        current=next((r for r in listed if r.get('tag_name')==tag),None)
    if current:
        if not current.get('prerelease'):raise ValueError('Refusing to overwrite a stable release')
        existing={a['name']:a for a in current.get('assets',[])}
        for name,h in input_hashes.items():
            if name in existing and existing[name].get('digest')!='sha256:'+h:
                raise ValueError('Existing prerelease differs; use a new revision tag, e.g. ep002-v2')
        if not current.get('draft') and all(name in existing for name in input_hashes):
            result={'url':current['html_url'],'tag':tag,'commit':current['target_commitish'],'prerelease':True,'files':input_hashes,'status':'already_uploaded_and_verified'}
            write(receipt,result);return result
    notes=output/'release-notes.md'
    notes.write_text('# '+spec['title']+'\n\n附件：\n\n- `final.mp4`：完整成片，手机观看/投稿使用。\n- `cover.png`：B站封面。\n- `bilibili.md`：推荐标题、备选标题和可复制简介。\n- `'+bundle.name+'`：上述文件及脚本、字幕、来源和验收报告。\n\n技术验收通过；这是预发布，完整试听与最终审美仍待用户审核。未向B站上传。\n\n'+(output/'bilibili.md').read_text()+'\n\n生产代码提交：'+commit+'\n')
    try:
        if not current:
            # Keep partial/failed uploads out of the public prerelease list.
            run(['gh','release','create',tag,'--repo',repository,'--prerelease','--draft','--target',commit,
                 '--title',spec['title'],'--notes-file',notes],log=output/'logs/prerelease-create.log',timeout=120)
            listed=json.loads(run(['gh','api',f'repos/{repository}/releases?per_page=100']))
            current=next(r for r in listed if r.get('tag_name')==tag)
        elif current.get('draft'):
            run(['gh','release','edit',tag,'--repo',repository,'--title',spec['title'],
                 '--notes-file',notes],log=output/'logs/prerelease-notes.log',timeout=120)
        existing={a['name']:a for a in current.get('assets',[])}
        for p in uploads:
            if p.name not in existing:
                run(['gh','release','upload',tag,str(p),'--repo',repository],log=output/'logs'/('upload-'+p.name+'.log'),timeout=600)
        observed=json.loads(run(['gh','api',f'repos/{repository}/releases/{current["id"]}']))
        actual={a['name']:a for a in observed.get('assets',[])}
        for p in uploads:
            a=actual.get(p.name,{})
            if a.get('size')!=p.stat().st_size or a.get('digest')!='sha256:'+sha(p):
                raise ValueError('Uploaded asset size/digest verification failed: '+p.name)
        if observed.get('draft'):
            run(['gh','release','edit',tag,'--repo',repository,'--draft=false','--prerelease'],timeout=120)
        result={'url':observed['html_url'],'tag':tag,'commit':observed['target_commitish'],'prerelease':True,'status':'uploaded_and_digest_verified',
                'files':{a['name']:{'sha256':a['digest'],'download_url':a['browser_download_url'],'bytes':a['size']} for a in actual.values()}}
        write(receipt,result);return result
    except Exception as error:
        write(output/'prerelease.failure.json',{'tag':tag,'error':str(error),'status':'failed_or_partial_no_success_claim',
              'local_delivery_valid':True,'resume':'Repair GitHub attachment authorization, then rerun deliver with the same output/tag; no rerender needed.'})
        raise
