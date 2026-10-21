"""Validated deliverables -> GitHub prerelease. Never publishes to Bilibili."""
from pathlib import Path
import json
import re
import zipfile
from .common import ROOT, read, write, sha, run


def verified_files(output):
    output=Path(output)
    report=read(output/'report.json');delivery=read(output/'delivery.json')
    if not report['technical']['passed'] or not report['content']['structural_pass']:
        raise ValueError('Prerelease requires technical and content-structure checks; human review may remain pending')
    if sha(output/'final.mp4')!=report['final']['sha256']:
        raise ValueError('Final movie changed after validation')
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
    uploads=[output/'final.mp4',output/'cover.png',bundle]
    receipt=output/'prerelease.json';input_hashes={p.name:sha(p) for p in uploads}
    # Existing stable releases must never be converted or overwritten.
    try:
        current=json.loads(run(['gh','api',f'repos/{repository}/releases/tags/{tag}']))
    except RuntimeError as e:
        if '404' not in str(e):raise
        current=None
    if current:
        if not current.get('prerelease'):raise ValueError('Refusing to overwrite a stable release')
        assets={a['name']:a for a in current.get('assets',[])}
        if not all(name in assets and assets[name].get('digest')=='sha256:'+h for name,h in input_hashes.items()):
            raise ValueError('Existing prerelease differs; use a new revision tag, e.g. ep002-v2')
        result={'url':current['html_url'],'tag':tag,'commit':commit,'prerelease':True,'files':input_hashes,'status':'already_uploaded_and_verified'}
        write(receipt,result);return result
    notes=output/'release-notes.md'
    notes.write_text('# '+spec['title']+'\n\n直接下载 final.mp4 即可手机观看；cover.png 为B站封面；ZIP包含脚本、字幕、投稿文案、来源和验收报告。\n\n技术验收通过；这是预发布，完整试听与最终审美仍待用户审核。未向B站上传。\n\n'+spec.get('bilibili_body','素材来源和许可见ZIP中sources.json。')+'\n\n生产代码提交：'+commit+'\n')
    command=['gh','release','create',tag,'--repo',repository,'--prerelease','--target',commit,'--title',spec['title'],'--notes-file',notes,*uploads]
    try:
        run(command,log=output/'logs/prerelease-upload.log',timeout=600)
        observed=json.loads(run(['gh','api',f'repos/{repository}/releases/tags/{tag}']))
        actual={a['name']:a for a in observed.get('assets',[])}
        for p in uploads:
            a=actual.get(p.name,{})
            if a.get('size')!=p.stat().st_size or a.get('digest')!='sha256:'+sha(p):
                raise ValueError('Uploaded asset size/digest verification failed: '+p.name)
        result={'url':observed['html_url'],'tag':tag,'commit':commit,'prerelease':observed['prerelease'],'status':'uploaded_and_digest_verified',
                'files':{a['name']:{'sha256':a['digest'],'download_url':a['browser_download_url'],'bytes':a['size']} for a in actual.values()}}
        write(receipt,result);return result
    except Exception as error:
        write(output/'prerelease.failure.json',{'tag':tag,'error':str(error),'status':'failed_or_partial_no_success_claim'})
        raise
