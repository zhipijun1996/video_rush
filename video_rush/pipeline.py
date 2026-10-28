from __future__ import annotations
import json
import inspect
import math
import re
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from .common import ROOT, read, write, sha, digest, run, duration
from .footage import collect
from .narration import narrate
from .render import subtitle_cues, ass_file, encode_shot, cover, montage_spans, concatenate_cuts
from .quality import validate
from .publish import posting_copy
from .subtitles import narration_cues

STAGES=['Research','Story','Script','Shot Planning','Footage Collection','Narration','Timeline Composition','Rendering','Quality Validation','Delivery']


def cut_source_fingerprints(shot, assets):
    # An animation's flat preview can be byte-identical after timing or group
    # edits. Include its actual recipe, not just the PNG's file hash.
    return [{'sha256':assets[x]['sha256'],
             'animation':assets[x].get('graphic') if shot.get('presentation')=='animated_diagram' else None}
            for x in shot['assets']]


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


@contextmanager
def production_lock(output):
    """One writer per episode, including validation and delivery manifests."""
    import fcntl
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'.production.lock').open('a') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Episode production already running: '+str(output)) from exc
        try:
            yield
        finally:
            fcntl.flock(handle,fcntl.LOCK_UN)


def produce(spec_path, repo, *, output=None, backend='edge', piper_model=None, music=None, music_license=None):
    spec=read(Path(spec_path).resolve())
    output=Path(output or ROOT/'build'/'episodes'/spec['episode']).resolve()
    with production_lock(output):
        return _produce(spec_path,repo,output=output,backend=backend,piper_model=piper_model,
                        music=music,music_license=music_license)


def _produce(spec_path, repo, *, output=None, backend='edge', piper_model=None, music=None, music_license=None):
    spec_path=Path(spec_path).resolve();spec=read(spec_path)
    output=Path(output or ROOT/'build'/'episodes'/spec['episode']).resolve()
    if spec.get('music_asset') and not music:
        m=spec['music_asset'];music=str(ROOT/m['path'])
        if not Path(music).exists() or sha(music)!=m['sha256']:
            raise ValueError('Requested BGM missing or changed; restore the user-supplied file with its pinned SHA256')
        music_license=m['license_status']
    if spec.get('original_music') and not music:
        from .graphics import score
        music=str(output/'original-score.wav');output.mkdir(parents=True,exist_ok=True)
        if not Path(music).exists():score(music,seconds=240)
        music_license='Original Video Rush synthesized score; no samples; user project use authorized'
    runner=Stages(output);logs=output/'logs';logs.mkdir(exist_ok=True)
    a_path=Path(spec['asset_spec']);a_path=a_path if a_path.is_absolute() else ROOT/a_path
    a_spec=read(a_path)
    stages=runner.execute
    def research():
        scope=ROOT/'build/research/scope.json'
        snapshot=spec.get('research_scope') or (read(scope) if scope.exists() else {'status':'using_frozen_authored_sources','repository':spec['repository'],'coverage':'episode assets and authored claims only; run research for a new complete scan'})
        snapshot['episode_evidence']=spec.get('evidence',[])
        write(output/'research.json',snapshot);return [output/'research.json']
    stages('Research',{'asset_spec':a_spec,'story_ids':spec['story_ids'],'evidence':spec.get('evidence',[]),'scope':spec.get('research_scope')},research)
    def story():
        stories=read(ROOT/'research/stories.json')
        selected=[s for s in stories if s['id'] in spec['story_ids']]
        write(output/'story.json',selected);return [output/'story.json']
    stages('Story',{'ids':spec['story_ids'],'index':sha(ROOT/'research/stories.json')},story)
    def script():
        (output/'script.md').write_text('# '+spec['title']+'\n\nAI 配音；第一人称为经证据整理的开发者叙述，未冒称用户逐句签收。\n\n'+''.join(f'## {s["id"]} · {s["title"]}\n\n{s["narration"]}\n\n来源：'+', '.join([*(f'PR #{p}' for p in s['prs']),*s.get('evidence',[])])+'；'+s['claim_type']+'\n\n' for s in spec['shots']))
        write(output/'script.json',spec);return [output/'script.md',output/'script.json']
    stages('Script',spec,script)
    def planning():
        for s in spec['shots']:
            if not s.get('narration') or not s.get('assets') or not (s.get('prs') or s.get('evidence')):
                raise ValueError('Every shot needs narration, media and PR/document/user evidence')
            if s.get('presentation') == 'montage' and spec.get('game_audio_gain', 0) > 0:
                raise ValueError('Montage currently supports narration/BGM only; set game_audio_gain=0 to avoid mismatched source audio')
        write(output/'shot-plan.json',spec['shots']);return [output/'shot-plan.json']
    stages('Shot Planning',spec['shots'],planning)
    def footage():
        media=collect(repo,a_spec,output/'media')
        return [output/'media/manifest.json',*[a['local_path'] for a in media],*sorted((output/'recording-evidence').glob('*')),*sorted((output/'original_uploads').glob('*')),*sorted((output/'source-evidence').glob('*')),*sorted((output/'browser-evidence').glob('*'))]
    recording_code=[sha(ROOT/'video_rush/recording.py'),sha(ROOT/'video_rush/git_media.py'),sha(ROOT/'video_rush/snapshot.py'),[sha(ROOT/'video_rush/drivers/weapon_showcase.gd'),sha(ROOT/'video_rush/drivers/special_weapons.gd'),sha(ROOT/'video_rush/drivers/route_weapons.gd')]] if any(a.get('origin')=='recording' for a in a_spec['assets']) else None
    stages('Footage Collection',{'assets':a_spec,'implementation':sha(ROOT/'video_rush/footage.py'),'recording_code':recording_code,'browser_code':sha(ROOT/'video_rush/browser_capture.py') if any(a.get('origin')=='browser_capture' for a in a_spec['assets']) else None,'editorial_generator':sha(ROOT/'video_rush/graphics.py') if any(a.get('origin')=='editorial' for a in a_spec['assets']) else None},footage)
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
                if a.get('display_label'):
                    labels.append(a['display_label'])
                else:
                    labels.append(f'{typ} PR{a.get("pr", "")} · {(a.get("runtime_commit") or a.get("commit", ""))[:8]}')
            x['provenance_label']=s.get('display_source',' | '.join(labels))
            if s.get('presentation') == 'montage':
                x['source_cues'] = [
                    {'start': round(t + cut['start'], 6), 'end': round(t + cut['end'], 6),
                     'text': labels[cut['index']]}
                    for cut in montage_spans(x)]
            boundaries=audio.with_suffix('.raw.boundaries.jsonl')
            metadata=[json.loads(line) for line in boundaries.read_text().splitlines()] if backend=='edge' and boundaries.exists() else []
            cues,x['subtitle_alignment']=narration_cues(s['narration'],metadata,t,spoken,speed,s.get('subtitle_mode','sentence'))
            x['cues']=cues;shots.append(x);t+=d
        timeline={'fps':30,'width':1920,'height':1080,'duration':round(t,6),'shots':shots,'music':music,'music_license':music_license,'display_chapters':spec.get('display_chapters',True)}
        write(output/'storyboard.json',timeline);ass_file(output/'subtitles.ass',timeline)
        sources={'repository':spec['repository'],'assets':media,'story_ids':spec['story_ids'],'claims':[{k:s[k] for k in ['id','narration','prs','fact_check','claim_type']} | {'evidence':s.get('evidence',[])} for s in spec['shots']],
                 'evidence':spec.get('evidence',[]),
                 'rights':spec.get('rights',read(ROOT/'research/rights.json')),'audio':{'backend':backend,'voice':spec['voice'],'synthesized':True,'playback_speed':speed,'music':music,'music_license':music_license,'music_sha256':sha(music) if music else None,'music_provenance':spec.get('music_asset'),'game_audio_gain':spec.get('game_audio_gain',0),'game_audio_policy':'Original matching clip window; comparison uses selected side only; narration foreground'},
                 'comparison':spec.get('comparison','Different stages, not a controlled same-seed before/after benchmark')}
        write(output/'sources.json',sources)
        return [output/'storyboard.json',output/'subtitles.ass',output/'sources.json']
    stages('Timeline Composition',{'spec':spec,'narration':[sha(output/'narration'/(s['id']+'.wav')) for s in spec['shots']],'media':sha(output/'media/manifest.json'),'code':sha(Path(__file__)),'subtitle_timing':sha(ROOT/'video_rush/subtitles.py'),'subtitle_generator':inspect.getsource(ass_file),'music':sha(music) if music else None,'music_license':music_license,'rights':sha(ROOT/'research/rights.json')},compose)
    timeline=read(output/'storyboard.json');sources=read(output/'sources.json')
    animation_code=[sha(ROOT/'video_rush/animation.py'),sha(ROOT/'video_rush/graphics.py')] if any(s.get('presentation')=='animated_diagram' for s in spec['shots']) else None
    def rendering():
        cuts=output/'cuts';cuts.mkdir(exist_ok=True)
        muxed=[]
        for s in timeline['shots']:
            p=cuts/(s['id']+'.mp4');k=digest({'shot':s,'sources':cut_source_fingerprints(s,assets),'game_audio_gain':spec.get('game_audio_gain',0),'audio_schema':2,'animation':animation_code,'render':digest({'encode_shot':inspect.getsource(encode_shot),'module':sha(ROOT/'video_rush/render.py'),'resolution':[1920,1080,30]})})
            cache=p.with_suffix('.json')
            if not (p.exists() and cache.exists() and read(cache).get('key')==k and read(cache).get('sha256')==sha(p)):
                raw=cuts/(s['id']+'.silent.mp4');encode_shot(s,assets,raw,logs/(s['id']+'-visual.log'))
                mux=['ffmpeg','-y','-v','warning','-i',raw,'-i',s['audio']]
                audio_index=s.get('game_audio_index',0);game=assets[s['assets'][audio_index]]
                if spec.get('game_audio_gain',0)>0 and Path(game['local_path']).suffix in ('.mp4','.webm','.avi'):
                    mux+=['-ss',str(s.get('offsets',[0]*len(s['assets']))[audio_index]),'-i',game['local_path'],
                          '-filter_complex',f'[1:a]atempo={s["playback_speed"]},apad[voice];[2:a]volume={spec["game_audio_gain"]},apad[game];[voice][game]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[audio]',
                          '-map','0:v','-map','[audio]']
                else:
                    mux+=['-map','0:v','-map','1:a','-af',f'atempo={s["playback_speed"]},apad']
                mux+=['-c:v','copy','-t',str(s['end']-s['start']),'-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',p]
                run(mux,log=logs/(s['id']+'-audio.log'))
                raw.unlink();write(cache,{'key':k,'sha256':sha(p)})
            muxed.append(p)
            print(f'  rendered {s["id"]}',flush=True)
        joined,continuous=concatenate_cuts(muxed,timeline['shots'],output,logs)
        cmd=['ffmpeg','-y','-v','warning','-threads','4','-i',joined,'-i',continuous]
        if music:
            if not music_license:raise ValueError('--music requires --music-license')
            from .graphics import effects
            effects(output/'original-effects.wav',timeline)
            cmd+=['-stream_loop','-1','-i',music,'-i',output/'original-effects.wav','-filter_complex',
                  f'[1:a]asplit=2[voice][side];[2:a]volume={spec.get("music_gain",.16)},afade=t=in:st=0:d=1,afade=t=out:st={max(0,timeline["duration"]-3)}:d=3[bg];[bg][side]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=250[duck];[voice][duck][3:a]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.9[mix]',
                  '-map','0:v','-map','[mix]']
        else:
            cmd+=['-map','0:v','-map','1:a']
        cmd+=['-vf',f'scale=in_range=auto:out_range=tv,format=yuv420p,ass={output}/subtitles.ass','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-color_range','tv','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',output/'final.mp4']
        run(cmd,log=logs/'final-render.log',timeout=1200)
        cover(output/'cover.png',assets[spec['cover_assets'][0]]['local_path'],assets[spec['cover_assets'][1]]['local_path'],spec.get('cover'))
        return [output/'final.mp4',output/'cover.png']
    stages('Rendering',{'timeline':sha(output/'storyboard.json'),'media':sha(output/'media/manifest.json'),'ass':sha(output/'subtitles.ass'),'renderer':sha(ROOT/'video_rush/render.py'),'animation':animation_code,'composition_code':sha(Path(__file__)),'music':sha(music) if music else None,'game_audio_gain':spec.get('game_audio_gain',0),'audio_schema':3,'cover_design':spec.get('cover'),'cover_sources':[assets[x]['sha256'] for x in spec['cover_assets']]},rendering)
    def validation():
        report=validate(output,spec,timeline,sources)
        if not report['technical']['passed']:raise RuntimeError('Technical quality failed; inspect report.json and logs')
        return [output/'report.json',output/'phone-review.md',*sorted((output/'animation-evidence').glob('*'))]
    stages('Quality Validation',{'final':sha(output/'final.mp4'),'sources':sha(output/'sources.json'),'validator':sha(ROOT/'video_rush/quality.py'),'animation':animation_code},validation)
    def delivery():
        titles=spec.get('title_candidates') or [spec['title'],'概念图很美，实机像贴皮？我用AI做游戏的美术返工记录','独自用AI做Godot游戏：素材越画越多，为什么画面还是不对？']
        body='# B站上传建议\n\n'+''.join(f'- {x}\n' for x in titles)+'\n分区建议：游戏 → 单机游戏（开发记录）；或知识 → 野生技能协会，以投稿页实际可选分区为准。\n\n标签：AI开发、独立游戏、Godot、游戏开发、Codex、美术、失序之钟\n\n简介：\n\n独自用 AI 制作《失序之钟》，这次复盘概念图到实机的反复返工。包含历史实机、失败候选和有限进展，不代表游戏美术问题已解决。中文AI配音；母版、预览、实验与正式入口分别标注。不同阶段画面对比不是同Seed受控实验。\n\n素材来源：本人项目 gunman-rush 的 Git/PR/历史录像。Underworld Tileset by Asouris，采用作者许可声明；中文字体 Noto Sans CJK，SIL OFL。五风格比较另含 Retro Lines / VEXED、Basic Platformer / Ariel Pinana、Scribble Platformer / Kenney、Cavern Tile Set / ansimuz（CC0；Basic许可来自作者页面，原许可文件为空）。其余许可状态见 sources.json。\n\n'+''.join(f'- https://github.com/{spec["repository"]}/pull/{p}\n' for p in sorted({n for s in spec['shots'] for n in s['prs']}))+'\n上传前完整观看 phone-review.md 清单；未自动发布到B站。\n'
        if spec.get('bilibili_body'):
            body='# B站上传建议\n\n'+''.join('- '+t+'\n' for t in titles)+'\n'+spec['bilibili_body']+'\n\nAI配音；正式/开发演示/设计示意分别标注。完整来源与授权见sources.json。未上传B站。\n'
        # Use the authored description when present; keep the original source-rich fallback.
        description=spec.get('bilibili_body') or body.split('简介：\n\n',1)[-1]
        (output/'bilibili.md').write_text(posting_copy(spec,description))
        files=['final.mp4','cover.png','script.md','storyboard.json','subtitles.ass','bilibili.md','sources.json','report.json','phone-review.md']
        files += [str(p.relative_to(output)) for p in sorted((output/'original_uploads').glob('*')) if p.is_file()]
        files += [str(p.relative_to(output)) for p in sorted((output/'source-evidence').glob('*')) if p.is_file()]
        files += [str(p.relative_to(output)) for p in sorted((output/'browser-evidence').glob('*')) if p.is_file()]
        files += [str(p.relative_to(output)) for p in sorted((output/'animation-evidence').glob('*')) if p.is_file()]
        write(output/'delivery.json',{'episode':spec['episode'],'files':{p:sha(output/p) for p in files},'technical_pass':True,'human_review':'pending','bilibili_published':False})
        return [output/'bilibili.md',output/'delivery.json']
    stages('Delivery',{'report':sha(output/'report.json'),'title':spec['title'],'delivery_schema':7,'bilibili_body':spec.get('bilibili_body'),'titles':spec.get('title_candidates')},delivery)
    return output
