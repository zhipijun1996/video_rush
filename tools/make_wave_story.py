"""Render the reviewed first-person story as a sound-bearing dynamic rough cut.

Explicit silent/dialogue-free shots are intentional editing holds. No generated
speech is replaced with silence, no game frames are synthesized or looped.
"""
import argparse
import array
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

from video_rush.common import ROOT, digest, duration, font, probe, read, run, sha, write
from video_rush.narration import narrate, audio_metrics
from video_rush.render import ass_file
from video_rush.stick_story import render as animate, frame


def clink(path,seconds):
    """Original short glass-like cue, not a sampled film/game sound."""
    sr=24000;data=array.array('h',[0])*round(seconds*sr)
    for i in range(round(.3*sr)):
        t=i/sr;v=sum(g*math.sin(2*math.pi*f*t) for f,g in ((1900,.6),(2837,.3),(4313,.1)))
        at=round(.67*sr)+i
        if at<len(data):data[at]=round(v*math.exp(-t*17)*7500)
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(data.tobytes())


def source_window(path,offset,seconds):
    if not math.isfinite(offset+seconds) or offset<0 or seconds<=0 or offset+seconds>duration(path)+.06:
        raise ValueError(f'Source window outside actual footage: {path}: {offset}+{seconds}')


def verify_final_shots(movie,timeline,segments):
    """Check final body pixels against each encoded shot, excluding captions."""
    def pixels(path,at):
        return subprocess.check_output(['ffmpeg','-v','error','-ss',str(max(0,at)),'-i',str(path),'-frames:v','1',
            '-vf','crop=1600:650:160:250,scale=96:40','-f','rawvideo','-pix_fmt','rgb24','-'])
    results=[]
    for s in timeline:
        t=s['seconds']*.55;actual=pixels(movie,s['start']+t);errors=[];deltas=[]
        # Frame-rate conversion and AAC container priming can shift a sampled
        # animation drawing by a few frames. This checks visual presence, not lip sync.
        for delta in (0,-1/30,1/30,-2/30,2/30):
            expected=pixels(Path(segments)/(s['id']+'.mp4'),t+delta)
            errors.append(sum(abs(a-b) for a,b in zip(actual,expected))/len(actual) if len(actual)==len(expected)>0 else 255)
            deltas.append(delta)
            if errors[-1]<2:break
        err=min(errors);results.append({'id':s['id'],'body_pixel_mean_absolute_error':round(err,3),'comparison_time_delta':deltas[errors.index(err)],'threshold':18,'passed':err<18})
    return results


def build(spec_path,output,stage='all'):
    spec=read(spec_path);output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    for name in ('narration','segments','logs','animation-evidence','recording-evidence'):(output/name).mkdir(exist_ok=True)
    def voice(s):
        if not s['text']:return None
        return narrate(s['text'],output/'narration'/(s['id']+'.wav'),voice=spec['friend_voice'] if s.get('speaker')=='friend' else spec['voice'],rate=spec['rate'])
    with ThreadPoolExecutor(max_workers=3) as pool:voices=list(pool.map(voice,spec['shots']))
    if stage=='narration':print('Verified narration',sum(x is not None for x in voices));return
    capture=ROOT/'build/story-capture/ep008-r2';receipt=read(capture/'receipt.json')
    if receipt['recipe']['source_commit']!=spec['source_commit']:raise ValueError('Game revision mismatch')
    for name,h in receipt['files'].items():
        if sha(capture/name)!=h:raise ValueError('Game recording SHA mismatch')
    for key,ref in spec['references'].items():
        if not ref.get('sha256') or sha(ROOT/ref['file'])!=ref['sha256']:raise ValueError('Unpinned or changed reference '+key)
    animation_hash=sha(ROOT/'video_rush/stick_story.py');timeline=[];clock=0
    for s,vo in zip(spec['shots'],voices):
        seconds=round(max(s['seconds'],vo['duration']+.25 if vo else 0)*30)/30
        shot={**s,'seconds':seconds,'start':round(clock,6),'end':round(clock+seconds,6),'narration_receipt':vo}
        if s['kind'] in ('game','anime','phone'):
            path=capture/(s['case']+'.mp4') if s['kind'] in ('game','phone') else ROOT/spec['references'][s['reference']]['file']
            source_window(path,s.get('offset',0),seconds);shot['visual_source']=str(path.relative_to(ROOT));shot['visual_sha256']=sha(path)
        else:
            path=output/'animation-evidence'/(s['id']+'.mp4');shot['visual_source']=str(path.relative_to(ROOT));shot['visual_sha256']=animation_hash
        timeline.append(shot);clock+=seconds
    write(output/'storyboard.json',{'status':spec['status'],'duration':clock,'shots':timeline})
    for shot in timeline:
        sid=shot['id'];out=output/'segments'/(sid+'.mp4');key=digest({'shot':{k:v for k,v in shot.items() if k not in ('start','end')},'segment_renderer_version':2 if shot.get('sound') else 1,'animation':animation_hash if shot['kind'] in ('animation','phone') else None});cache=out.with_suffix('.json')
        if out.exists() and cache.exists() and read(cache).get('key')==key and read(cache).get('sha256')==sha(out):continue
        path=ROOT/shot['visual_source'];seconds=shot['seconds'];offset=shot.get('offset',0)
        if shot['kind'] in ('animation','phone'):animate(output/'animation-evidence'/(sid+'.mp4'),shot['scene'],seconds)
        if shot['kind']=='animation':path=output/'animation-evidence'/(sid+'.mp4')
        args=['ffmpeg','-v','error','-y','-ss',str(offset if shot['kind']!='animation' else 0),'-i',str(path)]
        filters=[];video='0:v';idx=1
        if shot['kind']=='game':filters.append('[0:v]crop=1116:628:402:97,scale=1920:1080,setsar=1[v]');video='v'
        elif shot['kind']=='phone':
            args+=['-i',str(output/'animation-evidence'/(sid+'.mp4'))]
            filters+=['[0:v]crop=1116:410:402:259,scale=1468:540,pad=1920:540:226:0:color=0xf7f4eb[top]',
                      '[1:v]scale=1920:1080,crop=1920:540:0:430[bottom]','[top][bottom]vstack=inputs=2[v]'];video='v';idx=2
        else:filters.append('[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v]');video='v'
        audio=[]
        if shot.get('audio_from'):
            a=shot['audio_from'];native=capture/(a['case']+'.mp4');clip_seconds=min(seconds,a.get('clip_seconds',seconds));source_window(native,a['offset'],clip_seconds)
            args+=['-ss',str(a['offset']),'-t',str(clip_seconds),'-i',str(native)];filters.append(f'[{idx}:a]volume=1.1[native]');audio.append('native');idx+=1
        elif shot['kind'] in ('game','phone') or (shot['kind']=='anime' and shot.get('native_gain',0)>0):
            gain=shot.get('native_gain',1.1)*(.45 if shot['text'] else 1)
            filters.append(f'[0:a]volume={gain}[native]');audio.append('native')
        if shot['text']:
            args+=['-i',str(output/'narration'/(sid+'.wav'))];filters.append(f'[{idx}:a]volume=1[voice]');audio.append('voice');idx+=1
        if shot.get('sound'):
            from video_rush.graphics import effects
            sound=output/'segments'/(sid+'-effect.wav')
            if shot['sound']=='clink':clink(sound,seconds)
            else:effects(sound,{'duration':seconds,'shots':[{'start':.02,'sfx':'bell'}]})
            args+=['-i',str(sound)];filters.append(f'[{idx}:a]volume=.45[effect]');audio.append('effect');idx+=1
        if audio:filters.append(''.join('['+a+']' for a in audio)+f'amix=inputs={len(audio)}:duration=longest:normalize=0,apad,atrim=duration={seconds},alimiter=limit=.95,aresample=48000[a]')
        else:filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={seconds}[a]')
        args+=['-filter_complex',';'.join(filters),'-map','['+video+']','-map','[a]','-t',str(seconds),'-r','30','-c:v','libx264','-preset','veryfast','-crf','23','-threads','2',
               '-pix_fmt','yuv420p','-color_range','tv','-c:a','aac','-ar','48000','-ac','2','-b:a','128k','-movflags','+faststart',str(out)]
        run(args,log=output/'logs'/(sid+'.log'),timeout=180);write(cache,{'key':key,'sha256':sha(out)})
        print('Rendered',sid,seconds,flush=True)
    # Subtitles correspond only to actual TTS; short anime translations are editorial.
    captions=[]
    for s in timeline:
        cues=[]
        if s['text']:cues=[{'start':s['start'],'end':s['start']+s['narration_receipt']['duration'],'text':s['text']}]
        if s.get('caption'):cues.append({'start':s['start'],'end':s['end'],'text':s['caption']})
        captions.append({'start':s['start'],'end':s['end'],'cues':cues,
                         'emphasis':s.get('label',''),'provenance_label':'动态粗剪 v2'})
    ass_file(output/'subtitles.ass',{'display_chapters':False,'shots':captions})
    concat=output/'segments.txt';concat.write_text(''.join("file 'segments/"+s['id']+".mp4'\nduration "+str(s['seconds'])+"\n" for s in timeline))
    joined=output/'joined.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',concat,'-c','copy',joined],log=output/'logs/join.log')
    score=ROOT/'build/music/playground-battle-original.wav'
    if not score.exists():
        run(['python','tools/make_playground_score.py'],timeout=120)
    end_bar=next(s['start'] for s in timeline if s['id']=='s43');begin_battle=next(s['start'] for s in timeline if s['id']=='s09')
    music=f"volume='if(lt(t,{begin_battle}),0.025,if(gt(t,{end_bar}),0.055,0.16))':eval=frame,afade=t=in:d=0.7,afade=t=out:st={clock-2}:d=2"
    final=output/'roughcut.mp4'
    filters=f'[0:v]ass={output/"subtitles.ass"},fps=30,format=yuv420p[v];[0:a]asplit=2[main][control];[1:a]{music}[music];[music][control]sidechaincompress=threshold=.025:ratio=5:attack=8:release=180[duck];[main][duck]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]'
    # All cuts have the same raster/pixel format. Their original color metadata
    # differs; reinitializing this combined AV graph discards buffered short cuts.
    run(['ffmpeg','-v','error','-y','-reinit_filter','0','-i',joined,'-i',score,'-filter_complex',filters,'-map','[v]','-map','[a]','-t',clock,
         '-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-pix_fmt','yuv420p','-color_range','tv',
         '-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-movflags','+faststart',final],log=output/'logs/final-render.log',timeout=900)
    run(['ffmpeg','-v','error','-i',final,'-f','null','-'],log=output/'logs/full-decode.log',timeout=180)
    meta=probe(final);metrics=audio_metrics(final)
    if not metrics['audible_signal'] or metrics['clipped_fraction']>.0001:raise ValueError('Invalid final soundtrack')
    shot_checks=verify_final_shots(final,timeline,output/'segments');write(output/'frame-checks.json',shot_checks)
    if not all(s['passed'] for s in shot_checks):raise ValueError('Final film differs from intended shots; see frame-checks.json')
    video=next(s for s in meta['streams'] if s['codec_type']=='video')
    if video['avg_frame_rate']!='30/1':raise ValueError('Final video must have constant 30 FPS')
    for name in ('receipt.json','trace.json'):shutil.copyfile(capture/name,output/'recording-evidence'/name)
    sources={'game':receipt,'references':spec['references'],'original_animation_module_sha256':animation_hash,
             'music':{'path':str(score.relative_to(ROOT)),'sha256':sha(score),'origin':'Original procedural score, no original anime BGM sampled.'},
             'rights':'Anime excerpts and original franchise sounds remain copyrighted with redistribution permission unconfirmed; not project MIT. Existing source subtitles and watermarks retained.',
             'truth':'Fictional first-person narrative requested by user. Game scenes are real new recordings with legal starting-resource/action fixtures; not natural campaign completion or live multiplayer.'}
    write(output/'sources.json',sources)
    (output/'script.md').write_text('# 第一人称动态粗剪\n\n'+ '\n\n'.join(s['id']+' '+('老友：' if s.get('speaker')=='friend' else '我：')+s['text'] for s in timeline if s['text']))
    (output/'bilibili.md').write_text('# 标题候选\n\n'+spec['title']+'\n\n# 简介草案\n\n小时候一下课，就和同学充气、放波、防御。长大后，借助 AI 把这场课间决斗做成了小游戏《拍拍波》。\n\n手机试玩：https://zhipijun1996.github.io/wave-game/\n\n你们小时候管它叫什么？还发明过哪些离谱招式？\n\n#B站AI创造公开赛#\n\n当前交付是动态粗剪，尚未通过用户审核，不自动投稿。开头家庭/职场和酒桌为剧情演绎；游戏当前是单机对 AI。游戏王、街霸、EVA、火影、奥特曼与 JOJO 的短引用及游戏原带作品录音权利归各原权利方，来源见 sources.json，未确认再发布授权。Toy 尚未发布，不宣称已上架。\n')
    cover=frame('crown',1,4).resize((1920,1080));d=ImageDraw.Draw(cover);d.text((100,95),'人到中年',font=ImageFont.truetype(font(True),95),fill='#282b2a');d.text((100,220),'我又当上了',font=ImageFont.truetype(font(True),95),fill='#282b2a');d.text((100,350),'拍拍波大王',font=ImageFont.truetype(font(True),110),fill='#bf5146');cover.save(output/'cover.png')
    (output/'phone-review.md').write_text('这是动态粗剪，不是审美验收通过的成片。\n\n- 第一人称是否连贯；酒桌与童年转场是否自然。\n- 翻卡和反弹是否看懂；原片喊招是否切完整；字幕是否对齐。\n- 实际游戏音量和两位 TTS 对白是否自然，是否有压住喊招。\n- 动画表情、梗与整体节奏是否成立。\n- 部分动漫源仅 360/480p，带原水印和字幕；原片引用与权利状态仍需最终审核。\n- 未自动投稿。\n')
    report={'status':'rendered_dynamic_roughcut','technical':{'full_decode':'passed','ffprobe':meta,'audio_metrics':metrics,
             'tts_verified':sum(v is not None for v in voices),'intentional_dialogue_free_shots':sum(v is None for v in voices),
             'source_windows':'All visual/audio windows bounded against actual media; no gameplay loops.',
             'final_shot_frame_checks':shot_checks,
             'subtitle_bounds':all(s['start']+(s['narration_receipt']['duration'] if s['narration_receipt'] else 0)<=s['end']+.01 for s in timeline)},
             'content_review':'User review pending; automated checks do not certify humor, listening or aesthetics.',
             'final_sha256':sha(final),'duration':duration(final),'files':{p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='report.json'}}
    write(output/'report.json',report);print('ROUGH CUT READY',final,report['duration'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,default=Path('episodes/ep008-r2-story.json'));p.add_argument('--output',type=Path,default=Path('build/episodes/ep008-r2-roughcut'));p.add_argument('--stage',choices=['all','narration'],default='all')
    a=p.parse_args();build(a.spec,a.output,a.stage)
