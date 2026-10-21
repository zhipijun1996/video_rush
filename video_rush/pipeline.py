from __future__ import annotations
import json
import math
import re
import time
import traceback
from pathlib import Path
from .common import ROOT, read, write, sha, digest, run, duration
from .footage import collect
from .narration import narrate
from .render import subtitle_cues, ass_file, encode_shot, cover
from .quality import validate

STAGES=['Research','Story','Script','Shot Planning','Footage Collection','Narration','Timeline Composition','Rendering','Quality Validation','Delivery']


class Stages:
    def __init__(self, output):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.path=self.output/'state.json'
        self.state=read(self.path) if self.path.exists() else {'schema_version':1,'stages':{}}

    def execute(self, name, inputs, function):
        key=digest(inputs);old=self.state['stages'].get(name,{})
        if old.get('input_hash')==key and old.get('status')=='complete' and all(Path(p).exists() and sha(p)==h for p,h in old.get('outputs',{}).items()):
            print(f'[{name}] cached',flush=True);return
        print(f'[{name}] running',flush=True)
        entry={'status':'running','input_hash':key,'started_at':time.time()}
        self.state['stages'][name]=entry;write(self.path,self.state)
        try:
            outputs=function()
            entry.update(status='complete',outputs={str(Path(p).resolve()):sha(p) for p in outputs},finished_at=time.time())
        except Exception as e:
            entry.update(status='failed',error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc(),finished_at=time.time())
            write(self.path,self.state);raise
        write(self.path,self.state)


def produce(spec_path, repo, *, output=None, backend='edge', piper_model=None, music=None, music_license=None):
    spec_path=Path(spec_path).resolve();spec=read(spec_path)
    output=Path(output or ROOT/'build'/'episodes'/spec['episode']).resolve()
    runner=Stages(output);logs=output/'logs';logs.mkdir(exist_ok=True)
    a_path=Path(spec['asset_spec']);a_path=a_path if a_path.is_absolute() else ROOT/a_path
    a_spec=read(a_path)
    stages=runner.execute
    def research():
        scope=ROOT/'build/research/scope.json'
        snapshot=read(scope) if scope.exists() else {'status':'using_frozen_authored_sources','repository':spec['repository'],'coverage':'episode assets and authored claims only; run research for a new complete scan'}
        write(output/'research.json',snapshot);return [output/'research.json']
    stages('Research',{'asset_spec':a_spec,'story_ids':spec['story_ids']},research)
    def story():
        stories=read(ROOT/'research/stories.json')
        selected=[s for s in stories if s['id'] in spec['story_ids']]
        write(output/'story.json',selected);return [output/'story.json']
    stages('Story',{'ids':spec['story_ids'],'index':sha(ROOT/'research/stories.json')},story)
    def script():
        (output/'script.md').write_text('# '+spec['title']+'\n\nAI 配音；第一人称为经证据整理的开发者叙述，未冒称用户逐句签收。\n\n'+''.join(f'## {s["id"]} · {s["title"]}\n\n{s["narration"]}\n\n来源：'+', '.join(f'PR #{p}' for p in s['prs'])+'；'+s['claim_type']+'\n\n' for s in spec['shots']))
        write(output/'script.json',spec);return [output/'script.md',output/'script.json']
    stages('Script',spec,script)
    def planning():
        for s in spec['shots']:
            if not s.get('narration') or not s.get('assets') or not s.get('prs'):
                raise ValueError('Every shot needs narration, source media, PR claims')
        write(output/'shot-plan.json',spec['shots']);return [output/'shot-plan.json']
    stages('Shot Planning',spec['shots'],planning)
    def footage():
        media=collect(repo,a_spec,output/'media')
        return [output/'media/manifest.json',*[a['local_path'] for a in media]]
    stages('Footage Collection',{'assets':a_spec,'implementation':sha(ROOT/'video_rush/footage.py')},footage)
    media=read(output/'media/manifest.json');assets={x['id']:x for x in media}
    def narration():
        paths=[];(output/'narration').mkdir(exist_ok=True)
        for s in spec['shots']:
            p=output/'narration'/(s['id']+'.wav')
            narrate(s['narration'],p,backend=backend,voice=spec['voice'],rate=spec['rate'],model=piper_model)
            paths.extend([p,p.with_suffix('.json')])
        return paths
    stages('Narration',{'texts':[s['narration'] for s in spec['shots']],'backend':backend,'voice':spec['voice'],'rate':spec['rate'],'model':sha(piper_model) if piper_model else None,'code':sha(ROOT/'video_rush/narration.py')},narration)
    def compose():
        speed=spec.get('playback_speed',1.0);t=0;shots=[]
        for s in spec['shots']:
            audio=output/'narration'/(s['id']+'.wav');raw_d=duration(audio);spoken=raw_d/speed
            d=math.ceil((spoken+.3)*30)/30
            x=dict(s,start=round(t,6),end=round(t+d,6),audio=str(audio),spoken_duration=spoken,playback_speed=speed)
            labels=[]
            for asset_id in s['assets']:
                a=assets[asset_id];kind=a['kind']
                typ={'concept_art':'AI 母版','composite_preview_not_gameplay':'合屏预览','original_game_recording':'历史原片','original_game_screenshot':'历史截图','positioned_game_screenshot':'实机定位图','technical_fixture':'技术样板','original_game_comparison':'比较实验'}.get(kind,'开发实验')
                labels.append(f'{typ} PR{a["pr"]} · {(a.get("runtime_commit") or a["commit"])[:8]}')
            x['provenance_label']=' | '.join(labels)
            boundaries=audio.with_suffix('.raw.boundaries.jsonl')
            cues=[]
            if backend=='edge' and boundaries.exists():
                for line in boundaries.read_text().splitlines():
                    b=json.loads(line)
                    if b['type']!='SentenceBoundary':continue
                    st=b['offset']/1e7/speed;du=b['duration']/1e7/speed
                    cues.extend(subtitle_cues(b['text'],t+st,min(du,spoken-st)))
                x['subtitle_alignment']='Edge sentence boundaries; phrase subdivisions proportional within sentence'
            else:
                cues=list(subtitle_cues(s['narration'],t,spoken));x['subtitle_alignment']='duration-proportional estimate; phone timing review required'
            x['cues']=cues;shots.append(x);t+=d
        timeline={'fps':30,'width':1920,'height':1080,'duration':round(t,6),'shots':shots,'music':music,'music_license':music_license}
        write(output/'storyboard.json',timeline);ass_file(output/'subtitles.ass',timeline)
        sources={'repository':spec['repository'],'assets':media,'story_ids':spec['story_ids'],'claims':[{k:s[k] for k in ['id','narration','prs','fact_check','claim_type']} for s in spec['shots']],
                 'rights':read(ROOT/'research/rights.json'),'audio':{'backend':backend,'voice':spec['voice'],'synthesized':True,'playback_speed':speed,'music':music,'music_license':music_license},
                 'comparison':'Different stages, not a controlled same-seed before/after benchmark'}
        write(output/'sources.json',sources)
        return [output/'storyboard.json',output/'subtitles.ass',output/'sources.json']
    stages('Timeline Composition',{'spec':spec,'narration':[sha(output/'narration'/(s['id']+'.wav')) for s in spec['shots']],'media':sha(output/'media/manifest.json'),'code':sha(Path(__file__)),'music':sha(music) if music else None,'music_license':music_license},compose)
    timeline=read(output/'storyboard.json');sources=read(output/'sources.json')
    def rendering():
        cuts=output/'cuts';cuts.mkdir(exist_ok=True)
        muxed=[]
        for s in timeline['shots']:
            p=cuts/(s['id']+'.mp4');k=digest({'shot':s,'sources':[assets[x]['sha256'] for x in s['assets']],'render':sha(ROOT/'video_rush/render.py')})
            cache=p.with_suffix('.json')
            if not (p.exists() and cache.exists() and read(cache).get('key')==k and read(cache).get('sha256')==sha(p)):
                raw=cuts/(s['id']+'.silent.mp4');encode_shot(s,assets,raw,logs/(s['id']+'-visual.log'))
                run(['ffmpeg','-y','-v','warning','-i',raw,'-i',s['audio'],'-map','0:v','-map','1:a','-c:v','copy','-af',f'atempo={s["playback_speed"]},apad','-t',str(s['end']-s['start']),'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',p],log=logs/(s['id']+'-audio.log'))
                raw.unlink();write(cache,{'key':k,'sha256':sha(p)})
            muxed.append(p)
            print(f'  rendered {s["id"]}',flush=True)
        lst=cuts/'concat.txt';lst.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in muxed))
        joined=output/'joined.mp4'
        run(['ffmpeg','-y','-v','warning','-f','concat','-safe','0','-i',lst,'-c','copy',joined],log=logs/'concat.log',timeout=180)
        cmd=['ffmpeg','-y','-v','warning','-threads','4','-i',joined]
        if music:
            if not music_license:raise ValueError('--music requires --music-license')
            cmd+=['-stream_loop','-1','-i',music,'-filter_complex','[1:a]volume=0.08[bg];[bg][0:a]sidechaincompress=threshold=0.025:ratio=10:attack=20:release=300[duck];[0:a][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[mix]','-map','0:v','-map','[mix]']
        cmd+=['-vf',f'ass={output}/subtitles.ass','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',output/'final.mp4']
        run(cmd,log=logs/'final-render.log',timeout=1200)
        cover(output/'cover.png',assets[spec['cover_assets'][0]]['local_path'],assets[spec['cover_assets'][1]]['local_path'])
        return [output/'final.mp4',output/'cover.png']
    stages('Rendering',{'timeline':sha(output/'storyboard.json'),'ass':sha(output/'subtitles.ass'),'renderer':sha(ROOT/'video_rush/render.py'),'music':sha(music) if music else None},rendering)
    def validation():
        report=validate(output,spec,timeline,sources)
        if not report['technical']['passed']:raise RuntimeError('Technical quality failed; inspect report.json and logs')
        return [output/'report.json',output/'phone-review.md']
    stages('Quality Validation',{'final':sha(output/'final.mp4'),'sources':sha(output/'sources.json'),'validator':sha(ROOT/'video_rush/quality.py')},validation)
    def delivery():
        titles=[spec['title'],'概念图很美，实机像贴皮？我用AI做游戏的美术返工记录','独自用AI做Godot游戏：素材越画越多，为什么画面还是不对？']
        body='# B站上传建议\n\n'+''.join(f'- {x}\n' for x in titles)+'\n分区建议：游戏 → 单机游戏（开发记录）；或知识 → 野生技能协会，以投稿页实际可选分区为准。\n\n标签：AI开发、独立游戏、Godot、游戏开发、Codex、美术、失序之钟\n\n简介：\n\n独自用 AI 制作《失序之钟》，这次复盘概念图到实机的反复返工。包含历史实机、失败候选和有限进展，不代表游戏美术问题已解决。中文AI配音；母版、预览、实验与正式入口分别标注。不同阶段画面对比不是同Seed受控实验。\n\n素材来源：本人项目 gunman-rush 的 Git/PR/历史录像。Underworld Tileset by Asouris，采用作者许可声明；中文字体 Noto Sans CJK，SIL OFL。其余许可状态见 sources.json。\n\n'+''.join(f'- https://github.com/{spec["repository"]}/pull/{p}\n' for p in sorted({n for s in spec['shots'] for n in s['prs']}))+'\n上传前完整观看 phone-review.md 清单；未自动发布到B站。\n'
        (output/'bilibili.md').write_text(body)
        files=['final.mp4','cover.png','script.md','storyboard.json','subtitles.ass','bilibili.md','sources.json','report.json','phone-review.md']
        write(output/'delivery.json',{'episode':spec['episode'],'files':{p:sha(output/p) for p in files},'technical_pass':True,'human_review':'pending','bilibili_published':False})
        return [output/'bilibili.md',output/'delivery.json']
    stages('Delivery',{'report':sha(output/'report.json'),'title':spec['title'],'delivery_schema':1},delivery)
    return output
