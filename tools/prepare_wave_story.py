"""Fetch pinned source/reference inputs for reproducible story preview production."""
from pathlib import Path
import argparse
import shutil
import requests

from video_rush.browser_movie import PATHS
from video_rush.common import ROOT, read, run, sha, write
from video_rush.snapshot import snapshot
from tools.collect_anime_reference import collect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('build/source'))
    parser.add_argument('--project',type=Path,default=Path('build/story-runtime'))
    args=parser.parse_args()
    if not args.project.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('Runtime must stay in disposable build/')
    spec=read('episodes/ep008-r2-story.json')
    for ref in spec['references'].values():
        p=Path(ref['file'])
        if p.exists() and sha(p)==ref['sha256']:continue
        p.parent.mkdir(parents=True,exist_ok=True)
        if ref.get('bvid'):
            collected=collect(ref['bvid'],'build/research/ep008-r2/anime')
            src=Path('build/research/ep008-r2/anime')/(ref['bvid']+'.mp4')
            if src!=p:shutil.copyfile(src,p)
        elif ref.get('url'):
            r=requests.get(ref['url'],timeout=45);r.raise_for_status();p.write_bytes(r.content)
        else:raise ValueError('No public source for '+str(p))
        if sha(p)!=ref['sha256']:raise ValueError('Public reference differs from pinned bytes: '+str(p))
    source=args.source;project=args.project
    if not (source/'.git').exists():
        source.mkdir(parents=True,exist_ok=True);run(['git','init',source])
        run(['git','-C',source,'remote','add','origin','https://github.com/zhipijun1996/wave-game.git'])
    if run(['git','-C',source,'remote','get-url','origin']).strip()!='https://github.com/zhipijun1996/wave-game.git':
        raise ValueError('Source directory belongs to a different repository')
    run(['git','-C',source,'fetch','--no-tags','--depth=1','--filter=blob:none','origin',spec['source_commit']],timeout=120)
    if not (project/'dist/index.html').exists():
        snap=snapshot(source,spec['source_commit'],PATHS,project)
        run(['npm','ci','--no-audit','--no-fund'],cwd=project,timeout=180)
        run(['npm','run','build'],cwd=project,timeout=180);write(project/'snapshot.json',snap)
    print('Pinned inputs and disposable web runtime prepared')


if __name__=='__main__':main()
