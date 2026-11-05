"""Original-audio progress films from verified complete native recordings.

No narration stage exists in this mode. Source AV, native outcome and human
viewing judgement remain separate; an audible waveform is never called speech.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont
from .common import read, write, sha, digest, probe, font, run
from .narration import audio_metrics


def load_capture(root, stage, expected_commit, *, allow_partial=False):
    folder=Path(root)/stage
    r=read(folder/'receipt.json');t=read(folder/'trace.json');movie=folder/'gameplay.mp4'
    if r['source_commit']!=expected_commit:raise ValueError('Wrong game source commit: '+stage)
    if r.get('kind')!='fresh_real_game_recording':raise ValueError('Headless diagnostics are not footage')
    if r.get('runtime_fingerprint_before')!=r.get('runtime_fingerprint_after'):raise ValueError('Source runtime changed')
    if r.get('driver_file_drift'):raise ValueError('Recording driver drifted')
    if r.get('movie_sha256')!=sha(movie):raise ValueError('Capture digest mismatch: '+stage)
    if not r.get('original_game_audio',{}).get('audible_signal'):raise ValueError('Missing real game audio: '+stage)
    if not allow_partial and not r.get('driver_completed_successfully'):raise ValueError('Complete recording required: '+stage)
    seconds=float(probe(movie)['format']['duration'])
    if seconds<=1:raise ValueError('Empty recording')
    return dict(folder=folder,receipt=r,trace=t,movie=movie,duration=seconds)


def assert_boss_clear(stage, trace):
    if stage.startswith('plains'):
        if trace.get('failures') or trace.get('boss_defeat_process_frame',-1)<0:
            raise ValueError('Full live route + Boss defeat missing: '+stage)
    else:
        combat=trace.get('combat',{})
        if trace.get('failures') or combat.get('defeats')!=1 or combat.get('final',{}).get('boss_hp')!=0:
            raise ValueError('Full forest Boss defeat missing: '+stage)


def plan(spec, captures):
    clips=[]
    def add(stage,start,end,title,note):
        start=round(max(0,start)*30)/30;end=round(min(end,captures[stage]['duration'])*30)/30
        if end-start<.2:raise ValueError('Invalid clip duration')
        clips.append(dict(stage=stage,start=start,end=end,title=title,note=note,speed=1))
    # A brief actual-action hook; its repeat is disclosed rather than a fake loop.
    c=captures['plains1'];boss=c['trace']['boss_start_process_frame']/60
    add('plains1',boss+12,boss+16,'失序之钟 · 现阶段实机记录','这次少说两句，直接看关卡。开场为下文 Boss 战摘录。')
    for stage in ['plains1','plains2']:
        c=captures[stage];t=c['trace'];s=spec['stages'][stage];begin=t['boss_start_process_frame']/60;end=t['boss_defeat_process_frame']/60
        for a,b in [(0,16),(24,38),(max(38,begin-14),begin)]:
            if b>a:add(stage,a,b,s['label'],'跑图节选 · 独立关卡自动输入录像 · main '+spec['main_commit'][:7])
        add(stage,begin,min(c['duration'],end+3),s['label']+' / '+s['boss'],'完整 Boss 战 · 原速 · 游戏原声')
    for stage in ['forest1','forest2']:
        c=captures[stage];t=c['trace'];s=spec['stages'][stage];frames=t['combat']['frames']
        kill=next(r['physics_frame']/60 for r in frames if r.get('boss_hp')==0)
        end=min(c['duration'],kill+1.2)
        note='完整路线与 Boss · 独立关卡自动输入录像 · forest-bible-world-v15'
        if stage=='forest2':
            # This source-owned test really reloads a saved checkpoint. Cut its
            # pause/reload frames, never misrepresent uninterrupted live play.
            before=[r for r in frames if r.get('segment')=='before_reload']
            after=[r for r in frames if r.get('segment')=='after_reload']
            cut_a=(before[-1]['physics_frame']+1)/60;cut_b=after[0]['physics_frame']/60
            fixture=t.get('gold_effect_probe',{}).get('before',{}).get('physics_frame')
            if fixture:end=min(end,fixture/60-.05)
            add(stage,0,cut_a,s['label']+' / '+s['boss'],note+' · 同场战斗分段记录')
            add(stage,cut_b,end,s['label']+' / '+s['boss'],'同一 Boss 战续段 · 已剪掉测试读档等待 · 原速')
        else:add(stage,0,end,s['label']+' / '+s['boss'],note)
    c=captures['random'];t=c['trace'];s=spec['stages']['random'];overview=t.get('overview_process_frames',[])
    if len(overview)==2:
        add('random',overview[0]/60,overview[1]/60,s['label'],'静止场景镜头巡览（非游玩） · PR136 '+spec['random_commit'][:7])
        begin=overview[1]/60+.1
    else:begin=t.get('ready_process_frame',0)/60
    add('random',begin,min(begin+45,c['duration']-.5),s['label'],
        '正常输入尝试 · 自动路线尚未跑通，不能当作关卡已验收' if not t.get('route_complete') else '正常输入实机路线 · 开发版本')
    last=clips[-1];last['note']+=' · 还在打磨，欢迎提建议'
    at=0
    for index,c in enumerate(clips):
        c.update(index=index,timeline_start=at,duration=round((c['end']-c['start'])*30)/30)
        at+=c['duration'];c['timeline_end']=at
    return clips


def render_cut(clip,capture,out):
    key=digest(dict(clip=clip,source=sha(capture['movie']),format='1080p30-originalaudio-v1'))
    path=out/'cuts'/f'{clip["index"]:03d}.mp4';receipt=path.with_suffix('.json')
    if path.exists() and receipt.exists() and read(receipt).get('input_hash')==key and read(receipt).get('sha256')==sha(path):return path
    path.parent.mkdir(exist_ok=True)
    # Raster text avoids shell/filter escaping and keeps original full field of
    # view. Native 720p is honestly upscaled; the footer covers no game pixels.
    overlay=path.with_suffix('.png');im=Image.new('RGBA',(1920,1080),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rectangle((0,980,1920,1080),fill=(16,24,28,255))
    d.text((92,985),clip['title'],font=ImageFont.truetype(font(True),31),fill='#f2dfad')
    d.text((92,1030),clip['note'],font=ImageFont.truetype(font(),24),fill='#d8e0df')
    im.save(overlay)
    filt='[0:v]fps=30,scale=1742:980:flags=lanczos:in_range=auto:out_range=tv,pad=1920:1080:89:0:color=0x10181c,setsar=1[v];[v][1:v]overlay=0:0:format=auto,format=yuv420p[out]'
    run(['ffmpeg','-nostdin','-y','-v','error','-ss',clip['start'],'-t',clip['duration'],'-i',capture['movie'],'-i',overlay,
         '-filter_complex_threads','2','-filter_complex',filt,'-map','[out]','-map','0:a:0','-t',clip['duration'],
         '-af',f'afade=t=in:d=0.025,afade=t=out:st={max(0,clip["duration"]-.025)}:d=0.025',
         '-c:v','libx264','-preset','veryfast','-crf','20','-threads','4','-color_range','tv',
         '-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',path],log=path.with_suffix('.log'),timeout=600)
    write(receipt,dict(input_hash=key,sha256=sha(path)))
    return path


def validate_gameplay(out,*,rehash_sources=True):
    out=Path(out);movie=out/'final.mp4';timeline=read(out/'storyboard.json');sources=read(out/'sources.json')
    media=probe(movie);v=next(s for s in media['streams'] if s['codec_type']=='video');a=next(s for s in media['streams'] if s['codec_type']=='audio')
    total=float(media['format']['duration']);expected=timeline[-1]['timeline_end']
    run(['ffmpeg','-v','error','-xerror','-i',movie,'-f','null','-'],log=out/'logs/decode.log',timeout=600)
    # Detect accidental render black/freeze. A frozen-world camera survey is
    # separately declared; all ordinary gameplay remains subject to detection.
    detect=run(['ffmpeg','-hide_banner','-i',movie,'-vf','blackdetect=d=2:pix_th=.08,freezedetect=n=-50dB:d=10','-an','-f','null','-'],log=out/'logs/visual-scan.log',timeout=600)
    scan=(out/'logs/visual-scan.log').read_text();black=re.findall(r'black_start:([\d.]+) black_end:([\d.]+)',scan)
    freeze=re.findall(r'freeze_start: ([\d.]+)',scan)
    audio=audio_metrics(movie);audio.pop('speech_identity',None);audio['source_type']='actual captured game AV, narration intentionally disabled'
    hashes=all(sha(out/s['delivered_recording'])==s['movie_sha256'] for s in sources['captures']) if rehash_sources else None
    checks=dict(full_decode=True,mp4=media['format']['format_name'].startswith('mov,mp4'),dimensions=[v['width'],v['height']]==[1920,1080],fps=v['avg_frame_rate']=='30/1',video_codec=v['codec_name']=='h264',pixel_format=v['pix_fmt']=='yuv420p',limited_range=v.get('color_range')=='tv',audio_codec=a['codec_name']=='aac',sample_rate=a['sample_rate']=='48000',duration=abs(total-expected)<.15,original_game_audio_audible=audio['audible_signal'],clipping=audio['clipped_fraction']<.0001,subtitle_bounds=all(0<=c['timeline_start']<c['timeline_end']<=total+.1 for c in timeline),source_hashes=hashes is not False,no_long_black=not black,no_unexplained_freeze=not freeze)
    report=dict(mode='original_game_audio/no_narration',technical=dict(passed=all(checks.values()),checks=checks,media=media,audio=audio,black_intervals=black,freeze_starts=freeze),content=dict(status='source/coverage checked; human enjoyment and final phone listening unverified',independent_human_review='pending',random_clear=sources['random_route_complete'],limitations=sources['limitations']),movie_sha256=sha(movie))
    write(out/'report.json',report)
    return report


def produce_gameplay(spec_path,captures_root,output):
    spec=read(spec_path);out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    captures={}
    for name,s in spec['stages'].items():
        commit=spec['main_commit' if s['version']=='main' else 'random_commit']
        captures[name]=load_capture(captures_root,name,commit,allow_partial=name=='random')
        if name!='random':assert_boss_clear(name,captures[name]['trace'])
    clips=plan(spec,captures);write(out/'storyboard.json',clips)
    paths=[render_cut(c,captures[c['stage']],out) for c in clips]
    listing=out/'cuts/concat.txt';listing.write_text(''.join("file '"+p.as_posix().replace("'","'\\''")+"'\n" for p in paths))
    run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',listing,'-t',clips[-1]['timeline_end'],
         '-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','18','-threads','4','-color_range','tv',
         '-af','aresample=async=1:first_pts=0','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out/'final.mp4'],log=out/'logs/compose.log',timeout=600)
    source_rows=[]
    for name,c in captures.items():
        target=out/'recordings'/name;target.mkdir(parents=True,exist_ok=True)
        for file in ['gameplay.mp4','receipt.json','trace.json','native.log','decode.log','encode.log','recording_driver.gd']:
            if (c['folder']/file).exists():shutil.copyfile(c['folder']/file,target/file)
        r=c['receipt'];source_rows.append(dict(stage=name,commit=r['source_commit'],url=f'https://github.com/{spec["repository"]}/commit/{r["source_commit"]}',seed=spec['stages'][name]['seed'],driver=r['driver'],driver_sha256=r['driver_sha256'],engine_sha256=r['engine_sha256'],runtime_fingerprint=r['runtime_fingerprint_before'],movie_sha256=r['movie_sha256'],delivered_recording=f'recordings/{name}/gameplay.mp4',driver_success=r['driver_completed_successfully'],audio='original native game music + sound effects'))
    limitations=['各关独立进入，自动玩家正常输入，不是人工一命完整战役。','森林按源测试独立进入，初始能力采用其森林入场配置，并非从新存档自然解锁。第二图源测试含战中读档；原片保留，精剪标记为同场分段。战后金装资源测试不进入精剪。','随机地图巡览冻结世界并自由移动镜头，始终标为非游玩；实际操作尝试另列。','软件渲染离线 720p60 原片，成片放大为 1080p30；没有目标设备性能结论。','配乐来自游戏的用户提供 MP3；保留实际来源，不宣称原创、CC0 或广泛商用许可。']
    sources=dict(repository=spec['repository'],captures=source_rows,random_pr=spec['random_pr'],random_route_complete=captures['random']['trace'].get('route_complete',False),limitations=limitations,rights=dict(game='User-owned project recording requested by project owner',music='In-game user-supplied tracks; project-specific authorization, broader license unspecified',font='Noto Sans CJK / SIL Open Font License'))
    write(out/'sources.json',sources);write(out/'script.json',dict(narration=False,on_screen_only=True,claims=spec['claims']))
    (out/'script.md').write_text('# 现阶段关卡记录（无配音）\n\n'+ '\n\n'.join(f'{c["timeline_start"]:.2f}–{c["timeline_end"]:.2f}s：{c["title"]}\n{c["note"]}' for c in clips)+'\n')
    def ass_time(value):
        cs=round(value*100);return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'
    # Footer is burnt into the video; the ASS is a sidecar, never double-burnt.
    ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans CJK SC,24,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,80,80,15,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    for c in clips:ass+=f'Dialogue: 0,{ass_time(c["timeline_start"])},{ass_time(c["timeline_end"])},Default,,0,0,0,,{c["title"]}：{c["note"]}\n'
    (out/'subtitles.ass').write_text(ass)
    title=spec['title']+' | 【失序之钟】独游折腾记 '+spec['public_episode']+'【B站AI创造公开赛】'
    description='这次不讲方法论，直接留一份现阶段的实机记录。风铃平原两图、荆棘森林两图，以及最新随机平原开发分支。原声、原速；跑图有节选，四场 Boss 战保留完整战斗过程。\n\n各关独立录制，由自动输入操作。森林第二图含同场战斗分段。随机平原仍在开发，自动路线尚未跑通；地图巡览已标为非游玩，不代表已经通过可玩性验收。\n\n还在打磨中，欢迎大家挑毛病、提建议。\n\n#B站AI创造公开赛 #独立游戏 #Godot #失序之钟 #游戏开发'
    (out/'bilibili.md').write_text('推荐标题：\n'+title+'\n\n简介：\n'+description+'\n\n分区建议：游戏 / 单机游戏\n活动话题：#B站AI创造公开赛（实际投稿仍须选择平台活动入口）\n')
    (out/'phone-review.md').write_text('请用手机完整观看：\n\n- 四场 Boss 从开战到击败是否完整、动作是否清楚。\n- 原声是否舒适，剪切处是否突兀。\n- 字幕、血条和高跳是否可读且没有被裁掉。\n- 随机地图巡览和未跑通的尝试是否区分清楚。\n- 本片是阶段记录，不代表手感、美术或可玩性已通过人工验收。\n')
    # Cover uses only actual footage, with no invented scenery or gameplay.
    stills=[]
    for name,time in [('plains1',8),('forest1',18)]:
        path=out/f'cover-{name}.png';run(['ffmpeg','-y','-v','error','-ss',time,'-i',captures[name]['movie'],'-frames:v','1',path]);stills.append(Image.open(path).convert('RGB'))
    im=Image.new('RGB',(1920,1080));im.paste(stills[0].resize((1920,1080)).crop((0,0,960,1080)),(0,0));im.paste(stills[1].resize((1920,1080)).crop((480,0,1440,1080)),(960,0))
    layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer);d.rectangle((0,0,1920,200),fill=(12,20,25,220));d.rectangle((0,840,1920,1080),fill=(12,20,25,225));d.text((90,46),'失序之钟 · 现阶段实机',font=ImageFont.truetype(font(True),88),fill='#f8e4ab');d.text((90,870),'平原 × 森林 × 随机地图',font=ImageFont.truetype(font(True),82),fill='white');d.text((95,986),'关卡与 BOSS 记录 / 游戏原声 / 开发中',font=ImageFont.truetype(font(),40),fill='#d4dfd8');im=Image.alpha_composite(im.convert('RGBA'),layer);im.convert('RGB').save(out/'cover.png')
    report=validate_gameplay(out)
    # Cover extraction frames are a render cache, not delivery requirements.
    for name in ['plains1','forest1']:(out/f'cover-{name}.png').unlink(missing_ok=True)
    write(out/'delivery-manifest.json',{'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and ('cuts' not in p.relative_to(out).parts) and p.name!='delivery-manifest.json'}})
    if not report['technical']['passed']:raise RuntimeError('Gameplay film technical checks failed; see report.json')
    return out
