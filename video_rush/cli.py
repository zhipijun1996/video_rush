from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
from .common import ROOT, read, write, run
from .history import research, git
from .pipeline import produce


def source_path(value):
    path=Path(value).expanduser().resolve()
    if not (path/'.git').exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        run(['git','clone','https://github.com/zhipijun1996/gunman-rush.git',path],timeout=1200)
    return path


def director_brief(args, repo):
    stories=read(ROOT/'research/stories.json');selected=[]
    if args.story:selected=[s for s in stories if s['id']==args.story]
    elif args.pr:selected=[s for s in stories if s['pr']==args.pr]
    elif args.commits:
        commits=set(git(repo,'rev-list',args.commits).splitlines())
        selected=[s for s in stories if s['commit'] in commits]
    elif args.since or args.until:
        selected=[s for s in stories if (not args.since or s['date']>=args.since) and (not args.until or s['date'][:10]<=args.until)]
    else:
        query=set(args.topic or '')
        selected=sorted(stories,key=lambda s:len(query&set(s['event']+s['conflict'])),reverse=True)[:5]
    if not selected:raise ValueError('No evidence-backed story matches the selector; run research, then author new stories')
    out=Path(args.output or ROOT/'build/briefs'/args.episode);out.mkdir(parents=True,exist_ok=True)
    write(out/'director-brief.json',{'status':'awaiting_codex_editorial','topic':args.topic,'selected_stories':selected,'selector':{'pr':args.pr,'commits':args.commits,'since':args.since,'until':args.until},'next_action':'Codex reads video-director and footage-producer skills, writes an evidence-backed episode spec + assets JSON, then resumes produce --spec <path>. Never auto-pad thin evidence.'})
    print(f'Prepared {out}/director-brief.json; creative script needs the Codex host. No video claimed.',file=sys.stderr)
    return 3


def main(argv=None):
    p=argparse.ArgumentParser(prog='python -m video_rush',description='可追溯的中文游戏开发视频生产。素材仓库只读；首期完整预设可直接运行。')
    sub=p.add_subparsers(dest='command',required=True)
    doc=sub.add_parser('doctor',help='检查依赖与运行能力')
    hist=sub.add_parser('research',help='扫描全部Git引用与分页PR正文、文件和讨论')
    hist.add_argument('--source',default='/workspace/gunman-rush');hist.add_argument('--output',default=str(ROOT/'build/research'));hist.add_argument('--repository',default='zhipijun1996/gunman-rush');hist.add_argument('--refresh',action='store_true')
    pr=sub.add_parser('produce',help='从已编写分镜生产；新主题生成可恢复的Codex创作任务')
    pr.add_argument('--source',default='/workspace/gunman-rush');pr.add_argument('--spec');pr.add_argument('--topic');pr.add_argument('--story');pr.add_argument('--pr',type=int);pr.add_argument('--commits',help='Git range，例如 SHA1..SHA2');pr.add_argument('--since');pr.add_argument('--until');pr.add_argument('--episode',default='ep002');pr.add_argument('--output');pr.add_argument('--tts',choices=['edge','piper'],default='edge');pr.add_argument('--piper-model');pr.add_argument('--music');pr.add_argument('--music-license')
    pub=sub.add_parser('deliver',help='把已验收成片直接上传GitHub预发布，不经过Actions')
    pub.add_argument('output');pub.add_argument('--tag');pub.add_argument('--repository',default='zhipijun1996/video_rush')
    pr.add_argument('--local-only',action='store_true',help='只生成本地文件；默认完成后直接交付GitHub预发布')
    val=sub.add_parser('validate',help='重新验证成片与来源；不代签人类审美')
    val.add_argument('output')
    args=p.parse_args(argv)
    try:
        if args.command=='doctor':
            checks={x:shutil.which(x) for x in ['git','gh','ffmpeg','ffprobe','piper','godot','Xvfb']}
            from .common import font
            checks['chinese_font']=font();checks['proxy_configured']=bool(__import__('os').getenv('HTTPS_PROXY'))
            checks['notes']='Existing committed media can render without Godot/Xvfb; Edge requires network, Piper requires model.'
            print(json.dumps(checks,ensure_ascii=False,indent=2));return 0
        if args.command=='research':
            print(json.dumps(research(source_path(args.source),args.output,args.repository,args.refresh),ensure_ascii=False,indent=2));return 0
        if args.command=='deliver':
            from .publish import publish
            print(publish(args.output,args.repository,args.tag)['url']);return 0
        if args.command=='validate':
            from .quality import validate
            out=Path(args.output);r=validate(out,read(out/'script.json'),read(out/'storyboard.json'),read(out/'sources.json'))
            print(r['status']);return 0 if r['technical']['passed'] else 1
        if args.music and not args.music_license:raise ValueError('--music requires explicit --music-license')
        repo=source_path(args.source)
        spec=args.spec
        # The authored preset matches only its actual theme. Other selectors create a director handoff.
        if not spec and args.topic in ['枪是用来赶路的？我的游戏靠反冲跳跃','反冲跳跃与六把武器']:
            spec=ROOT/'episodes/ep003-r2.json'
        if not spec and args.topic and any(w in args.topic for w in ['初心','介绍视频','圆梦','开坑','自我介绍']):
            spec=ROOT/'episodes/ep002.json'
        if not spec and not any([args.pr,args.story,args.commits,args.since,args.until]) and (not args.topic or any(w in args.topic for w in ['概念图','美术落差','首期'])):
            spec=ROOT/'episodes/ep001.json'
        if not spec:return director_brief(args,repo)
        output=produce(spec,repo,output=args.output,backend=args.tts,piper_model=args.piper_model,music=args.music,music_license=args.music_license)
        print(output)
        if not args.local_only:
            from .publish import publish
            print(publish(output)['url'])
        return 0
    except Exception as e:
        print(f'Video Rush failed: {e}',file=sys.stderr);return 1

if __name__=='__main__':
    raise SystemExit(main())
