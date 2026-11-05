"""Add source-verified equipment and chapter cards to an immutable progress film."""
from pathlib import Path
import argparse
import shutil
import json
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .common import read, write, sha, probe, font, run, digest
from .gameplay import load_capture, validate_gameplay


def seconds(value):
    cs=round(value*100);return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'


def ass(events):
    head='[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans CJK SC,29,&H00FFFFFF,&H00FFFFFF,&H0010181C,&H0010181C,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    for e in events:
        text=e['text'].replace('\n','\\N')
        head+=f'Dialogue: 0,{seconds(e["start"])},{seconds(e["end"])},Default,,0,0,0,,{{\\pos(92,986)\\fs31\\b1\\c&HAD DFF2&}}{text}\n'.replace('AD DFF2','ADDFF2')
    return head


def equipment_clips(capture):
    t=capture['trace']
    if t['failures']:raise ValueError('Incomplete equipment UI recording')
    cps=t['checkpoints'];find=lambda token:next(i for i,c in enumerate(cps) if token in c['phase'])
    indices=[find('原正式宝箱'),find('正式背包'),find('点击装备'),find('点击卸下')]
    results=[]
    notes=['道具先领进背包，还没有自动装上。','先选中看详情，再决定要不要装备。','装备后才生效；本例占用 2 / 8 负荷。','卸下后效果撤销，道具仍保留在背包。']
    frames=t['frames'];equipped=[r for r in frames if r.get('equipped')==['N01']]
    if not equipped or not any(abs(r.get('resolved_focus_scale',1)-.12)<1e-5 and r['gear']['used']==2 and r['gear']['capacity']==8 for r in equipped):raise ValueError('N01 actual resolver/gear evidence missing')
    if frames[-1]['equipped'] or frames[-1].get('effects') or frames[-1]['owned']!=['N01']:raise ValueError('Actual unequip evidence missing')
    for order,index in enumerate(indices):
        start=cps[index]['drawn_frame']/60;end=cps[indices[order+1]]['drawn_frame']/60 if order<3 else capture['duration']-.2
        results.append(dict(kind='equipment-ui',start=round(start*30)/30,end=round(end*30)/30,title='装备系统 · 原生背包操作',note=notes[order]+'  宝箱站位为演示设置。'))
    return results


def verify_base_coverage(parts,duration):
    chunks=[p for p in parts if p['kind']=='base']
    at=0.0
    for p in chunks:
        if abs(p['start']-at)>.001 or p['end']<=p['start']:raise ValueError('Base gameplay lost, repeated or reordered')
        at=p['end']
    if abs(at-duration)>.001:raise ValueError('Base gameplay tail missing')


def plan(base_timeline,base_duration,ui,action,spec):
    forest=next(c['timeline_start'] for c in base_timeline if c['stage']=='forest1')
    random=next(c['timeline_start'] for c in base_timeline if c['stage']=='random')
    parts=[]
    def card(name,source_time):parts.append(dict(kind='card',card=name,start=source_time,end=source_time+2,duration=2,title=spec['cards'][name][0],note=spec['cards'][name][1]))
    def base(a,b):parts.append(dict(kind='base',start=a,end=b,duration=b-a,title='',note=''))
    card('intro',0);base(0,4);card('plains',6);base(4,forest)
    card('forest',forest+8);base(forest,random);card('equipment',random-8)
    parts+=equipment_clips(ui)
    trace=action['trace'];start=trace['world_begin_drawn']/60;end=trace['world_end_drawn']/60
    if trace['failures'] or trace['setup']['training_objects_created']!=0:raise ValueError('Failed/non-native equipment combat')
    damaging=trace['damage_receipts']
    if not all(any('/'+item+'/' in r['event'] and r['damage']>0 for r in damaging) for item in ['P24','P14']):raise ValueError('Active/automatic actual enemy damage missing')
    parts.append(dict(kind='equipment-action',start=start,end=end,duration=end-start,title='装备实战 · 双向回环飞轮 + 三巡钟',note='按 R 释放主动装置；三巡钟自动攻击。指定装备与初始共鸣演示。'))
    card('random',random+5);base(random,base_duration);card('outro',base_duration-3)
    at=0
    for i,p in enumerate(parts):
        p['duration']=round((p['end']-p['start'])*30)/30;p.update(index=i,timeline_start=at,timeline_end=at+p['duration']);at=p['timeline_end']
    verify_base_coverage(parts,base_duration)
    return parts


def base_events(part,timeline):
    events=[];a,b=part['start'],part['end']
    for c in timeline:
        start=max(a,c['timeline_start']);end=min(b,c['timeline_end'])
        if end<=start:continue
        title=c['title'];stage=c['stage'];original=c['note']
        if c['index']==0:note='四场 Boss、两片区域，再补上装备。开场为下文节选。'
        elif stage.startswith('plains'):note='普通跳跃 + 射击反冲，把赶路和战斗接在一起。' if '跑图' in original else 'Boss 战完整保留 · 原速 · 游戏原声'
        elif stage=='forest1':note='钩索和高低差，开始变成路线的一部分。独立关卡自动输入记录。'
        elif stage=='forest2':note='荆冠女王 · 同场战斗分段记录 · 独立关卡自动输入'
        elif '非游玩' in original:note='生成地图镜头巡览（非游玩） · PR136 开发版本'
        else:note='正常输入尝试 · 自动路线还没跑通，继续调。'
        events.append(dict(start=start-a,end=end-a,text=title+'\n{\\fs28\\b0\\c&HFFFFFF&}'+note))
    return events


def render(part,sources,timeline,out):
    path=out/'pieces'/f'{part["index"]:02d}.mp4';path.parent.mkdir(exist_ok=True)
    src=sources['base' if part['kind']=='card' else part['kind']]
    key=digest(dict(part=part,source_sha256=sha(src),format='revision-ep10-v1',base_timeline=timeline if part['kind']=='base' else None))
    r=path.with_suffix('.json')
    if path.exists() and r.exists() and read(r).get('input_hash')==key and read(r).get('sha256')==sha(path):return path
    d=part['duration'];args=['ffmpeg','-nostdin','-y','-v','error']
    if part['kind']=='card':
        still=path.with_suffix('.source.png');run(['ffmpeg','-y','-v','error','-ss',part['start'],'-i',src,'-frames:v','1',still])
        im=Image.open(still).convert('RGB').filter(ImageFilter.GaussianBlur(18));base=Image.new('RGB',im.size,'#263e47');im=Image.blend(base,im,.28);draw=ImageDraw.Draw(im)
        draw.rectangle((125,320,300,326),fill='#f2dfad');draw.text((125,235),'失序之钟  /  阶段记录  /  EP10',font=ImageFont.truetype(font(),30),fill='#d8e0df')
        draw.text((120,390),part['title'],font=ImageFont.truetype(font(True),86),fill='#f2dfad');draw.text((125,525),part['note'],font=ImageFont.truetype(font(),43),fill='white');im.save(path.with_suffix('.png'))
        args+=['-loop','1','-framerate','30','-i',path.with_suffix('.png'),'-ss',part['start'],'-t',d,'-i',src]
        vf=f"scale=1920:1080:in_range=auto:out_range=tv,format=yuv420p,fade=t=in:d=0.12,fade=t=out:st={d-.12}:d=0.12"
        args+=['-map','0:v:0','-map','1:a:0','-vf',vf,'-af',f'volume=.7,afade=t=in:d=0.06,afade=t=out:st={d-.06}:d=0.06']
    else:
        args+=['-ss',part['start'],'-t',d,'-i',src]
        events=base_events(part,timeline) if part['kind']=='base' else [dict(start=0,end=d,text=part['title']+'\n{\\fs28\\b0\\c&HFFFFFF&}'+part['note'])]
        captions=path.with_suffix('.ass');captions.write_text(ass(events))
        vf='fps=30,'+('' if part['kind']=='base' else 'scale=1742:980:flags=lanczos:in_range=auto:out_range=tv,pad=1920:1080:89:0:color=0x10181c,')+f'drawbox=x=0:y=980:w=1920:h=100:color=0x10181c:t=fill,subtitles={captions},format=yuv420p'
        args+=['-map','0:v:0','-map','0:a:0','-vf',vf,'-af',f'afade=t=in:d=0.025,afade=t=out:st={max(0,d-.025)}:d=0.025']
    args+=['-t',d,'-r','30','-c:v','libx264','-preset','ultrafast','-crf','19','-threads','4','-color_range','tv','-bsf:v','h264_metadata=video_format=5:video_full_range_flag=0','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',path]
    run(args,log=path.with_suffix('.log'),timeout=900);write(r,dict(input_hash=key,sha256=sha(path)))
    return path


def produce(base,captures,output,spec_path='episodes/ep011-r2.json'):
    base=Path(base).resolve();out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    spec=read(spec_path)
    if sha(base/'final.mp4')!=spec['base_sha256']:raise ValueError('Wrong base revision')
    ui=load_capture(captures,'equipment-ui',spec['source_commit']);action=load_capture(captures,'equipment-action',spec['source_commit'])
    timeline=read(base/'storyboard.json');parts=plan(timeline,float(probe(base/'final.mp4')['format']['duration']),ui,action,spec)
    sources={'base':base/'final.mp4','equipment-ui':ui['movie'],'equipment-action':action['movie']}
    write(out/'storyboard.json',parts);paths=[render(p,sources,timeline,out) for p in parts]
    listing=out/'pieces/concat.txt';listing.write_text(''.join("file '"+p.as_posix()+"'\n" for p in paths))
    run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',listing,'-t',parts[-1]['timeline_end'],'-vf','setpts=PTS-STARTPTS,fps=30:start_time=0,format=yuv420p','-fps_mode','cfr','-r','30','-c:v','libx264','-preset','veryfast','-crf','19','-threads','4','-color_range','tv','-bsf:v','h264_metadata=video_format=5:video_full_range_flag=0','-af','asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out/'final.mp4'],log=out/'logs/compose.log',timeout=1200)
    original=out/'original';original.mkdir(exist_ok=True);shutil.copyfile(base/'final.mp4',original/'base.mp4')
    for n in ['sources.json','storyboard.json','report.json']:shutil.copyfile(base/n,original/('base-'+n))
    rows=[dict(stage='base',kind='previous_verified_edit',delivered_recording='original/base.mp4',movie_sha256=spec['base_sha256'],source_manifest='original/base-sources.json',url=spec['base_artifact'])]
    for name,c in [('equipment-ui',ui),('equipment-action',action)]:
        target=out/'recordings'/name;target.mkdir(parents=True,exist_ok=True)
        for n in ['gameplay.mp4','trace.json','receipt.json','recording_driver.gd','native.log']:
            shutil.copyfile(c['folder']/n,target/n)
        rows.append(dict(stage=name,kind='fresh_real_game_recording',source_commit=spec['source_commit'],delivered_recording=f'recordings/{name}/gameplay.mp4',movie_sha256=c['receipt']['movie_sha256'],driver=c['receipt']['driver'],driver_sha256=c['receipt']['driver_sha256']))
    limits=read(base/'sources.json')['limitations']+['装备UI使用真实宝箱，初始宝箱站位为演示设置；没有注入道具、金币、血量或替代奖励结算。','飞轮/三巡钟实战采用固定装备、初始共鸣和一次站位；敌人、地形、输入与伤害结算为原生。','文字章节为后期编辑卡，所有原成片游戏段落按原速完整保留。']
    write(out/'sources.json',dict(captures=rows,base_sources=read(base/'sources.json'),random_route_complete=False,limitations=limits))
    write(out/'script.json',dict(narration=False,on_screen_only=True,authorization=spec['authorization']));all_events=[]
    for p in parts:
        ev=base_events(p,timeline) if p['kind']=='base' else [dict(start=0,end=p['duration'],text=p['title']+'\n'+p['note'])]
        all_events += [dict(start=e['start']+p['timeline_start'],end=e['end']+p['timeline_start'],text=e['text']) for e in ev]
    (out/'subtitles.ass').write_text(ass(all_events));(out/'script.md').write_text('# ep10 阶段成果记录（无配音）\n\n'+'\n\n'.join(f'{e["start"]:.2f}–{e["end"]:.2f}s\n'+re.sub(r'\{\\[^}]*\}','',e['text']) for e in all_events))
    shutil.copyfile(base/'cover.png',out/'cover.png')
    im=Image.open(out/'cover.png').convert('RGB');draw=ImageDraw.Draw(im);draw.rectangle((0,840,1920,1080),fill='#10181c');draw.text((90,865),'关卡 · BOSS · 装备',font=ImageFont.truetype(font(True),86),fill='white');draw.text((95,987),'阶段性成果记录 / 游戏原声 / EP10',font=ImageFont.truetype(font(),40),fill='#d4dfd8');im.save(out/'cover.png')
    description='这期少说两句，直接看《失序之钟》现阶段的实机。\n\n风铃平原和荆棘森林各两张图、四场Boss；补上道具领取、装备与卸下，以及飞轮、三巡钟参与战斗的效果。最后是最新随机平原的生成地图巡览和一次没跑通的尝试。\n\n分关录制、原速、游戏原声，无额外配音。跑图有节选，Boss战保留；森林第二场为同场分段。装备UI的宝箱站位、实战装备与初始共鸣采用固定演示设置，原生操作和伤害结算不变。巡览单独标明，不代表已经完成可玩性验收。\n\n游戏与视频使用AI辅助开发/制作，实机由自动输入录制。还在打磨，欢迎各位指出哪里别扭、怎么能更好玩。\n\n#B站AI创造公开赛#\n#独立游戏 #Godot #失序之钟 #游戏开发\n\n制作与来源：https://github.com/zhipijun1996/video_rush/blob/main/docs/ep011-r2.md'
    write(out/'posting.json',dict(title=spec['title'],description=description,topic_id=1340873,topic_name='B站AI创造公开赛',tags=['B站AI创造公开赛','失序之钟','独立游戏','游戏开发','Godot','AI开发','游戏实机','肉鸽']))
    (out/'bilibili.md').write_text('标题：\n'+spec['title']+'\n\n简介：\n'+description+'\n')
    (out/'phone-review.md').write_text('用户已授权补装备、字幕和转场后直接投稿。本片技术检查与来源核验独立执行，不冒称另外完成手机人工审美审核。\n')
    report=validate_gameplay(out);write(out/'delivery-manifest.json',{'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and 'pieces' not in p.relative_to(out).parts and p.name!='delivery-manifest.json'}})
    if not report['technical']['passed']:raise RuntimeError('Revision technical gate failed; see report.json')
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True);p.add_argument('--captures',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(produce(a.base,a.captures,a.output))


if __name__=='__main__':main()
