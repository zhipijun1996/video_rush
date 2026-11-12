"""Complete original-audio Windkeeper films; no narration or simulated audio."""
import argparse
import hashlib
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from .common import read, write, sha, probe, run, font
from .gameplay import load_capture, validate_gameplay
from .posting_policy import require_public_copy


def audit_fight(trace):
    rows=trace.get('rows',[]);shots=trace.get('shots',[])
    if trace.get('failure') or trace.get('victory_frame',-1)<0 or not rows:
        raise ValueError('A real complete successful fight is required')
    if {r['phase'] for r in rows}!={1,2,3}:
        raise ValueError('All three actual Boss phases must be present')
    if trace['initial_boss_hp']!=rows[0]['boss_capacity'] or rows[0]['boss_hp']!=rows[0]['boss_capacity'] or rows[-1]['boss_hp']!=0:
        raise ValueError('Boss must start at full source HP and actually die')
    if trace.get('invincible') is not False or trace.get('position_writes_in_recorded_fight') is not False or not rows[-1].get('battle_finished'):
        raise ValueError('Need ordinary vulnerability, unchanged positions and native encounter completion')
    if len({r['session'] for r in rows})!=1 or min(r['hp'] for r in rows)<=0:
        raise ValueError('Player died/restarted during claimed complete take')
    for a,b in zip(rows,rows[1:]):
        if b['frame']!=a['frame']+1 or b['boss_hp']>a['boss_hp']:
            raise ValueError('Omitted observations or Boss HP reset')
        if math.dist(a['player'],b['player'])>40:
            raise ValueError('Player position discontinuity; inspect hazard/fixture return')
    air=[s for s in shots if s['airborne']]
    if not air:raise ValueError('No actual airborne focus/recoil demonstrated')
    for shot in air:
        focus=shot.get('focus',{})
        if shot['flight_ordinal']>1 or not 30<=focus.get('frames',0)<=31:
            raise ValueError('Aerial chain or missing half-second focus')
        observed=[r for r in rows if focus['start']<=r['movie_frame']<focus['end']]
        if not observed or any(not r['focus'] or not 0<r['time_scale']<1 for r in observed):
            raise ValueError('Declared focus was not actually active in the original engine')
        if focus['end']-focus['start']!=focus['frames']:
            raise ValueError('Incorrect real-frame focus timing')
    events=trace.get('events',[])
    crosses=[]
    for landed in (e for e in events if e['event']=='cross_landed' and e['boosted']):
        cross_id=landed.get('cross_begin')
        begin=next((e for e in events if e['event']=='cross_begin' and e['frame']==cross_id),None)
        walk=next((e for e in events if e['event']=='walk_off' and e.get('cross_begin')==cross_id),None)
        shot=next((s for s in air if s['focus'].get('cross_begin')==cross_id),None)
        if not begin or not walk or not shot:
            raise ValueError('Landing is not linked to an actual walk-off and focused shot')
        segment=[r for r in rows if begin['frame']<r['frame']<=landed['frame']]
        if not segment or any(r['phase']!=3 or r['jump_held'] for r in segment):
            raise ValueError('Phase III crossing used a takeoff jump')
        if not begin['frame']<walk['frame']<shot['frame']<landed['frame']:
            raise ValueError('Incorrect walk-off, shot and landing order')
        origin=begin['origin_rect'];goal=begin['goal'];at=walk['position']
        if origin[0]<=at[0]<=origin[0]+origin[2] or at[1]+18<=origin[1]+10:
            raise ValueError('Player did not physically walk below and off the old shelf')
        end=next(r for r in rows if r['frame']==landed['frame'])
        if not end['grounded'] or abs(end['player'][0]-goal[0])>100 or abs(end['player'][1]-goal[1])>8:
            raise ValueError('No actual grounded arrival at the other shelf')
        if abs(goal[0]-(origin[0]+origin[2]/2))>330 or origin[0]<=goal[0]<=origin[0]+origin[2]:
            raise ValueError('Expected an adjacent actual shelf')
        crosses.append(landed)
    if not crosses:raise ValueError('No actual walk-off/recoil landing in phase III')
    return dict(complete=True,phases=[1,2,3],boss_initial_hp=trace['initial_boss_hp'],
                boss_final_hp=rows[-1]['boss_hp'],player_final_hp=rows[-1]['hp'],
                actual_shots=len(shots),airborne_shots=len(air),
                max_air_shots_per_flight=max(s['flight_ordinal'] for s in air),
                actual_air_focus_seconds=[s['focus']['frames']/60 for s in air],
                walk_off_recoil_landings=len(crosses),human_play=False,
                experience_quality='not inferred from successful automatic input')


def cue_plan(trace,seconds):
    cues=[]
    def add(at,length,text,kind):
        at=max(0,float(at));end=min(seconds,at+length)
        if end>at:cues.append(dict(start=round(at,3),end=min(seconds,round(end,3)),text=text,kind=kind))
    add(.3,5.5,'牧风者 · 三阶段完整战斗 / 独立 Boss 测试入口','intro')
    add(6,5,'常规移动为主 · 每次空中开枪前慢时瞄准 0.5 秒','style')
    for phase in [2,3]:
        row=next(e for e in trace['events'] if e['event']=='phase' and e['phase']==phase)
        text='第二阶段：看预警、留空间，再找还手的机会' if phase==2 else '第三阶段：走下台阶躲跳扑，再反冲换台'
        add(row['movie_frame']/60+.15,5.5,text,'phase')
    air=next(s for s in trace['shots'] if s['airborne'])
    add(air['focus']['start']/60,4.5,'空中开枪前：游戏内慢时瞄准 0.5 秒','focus')
    walks=[e for e in trace['events'] if e['event']=='walk_off']
    if walks:add(walks[0]['movie_frame']/60,5,'Boss 跳过来 → 离开原台阶 → 反冲到邻台','walk_off')
    healed=next((b for a,b in zip(trace['rows'],trace['rows'][1:]) if b['hp']>a['hp']),None)
    if healed:add(healed['movie_frame']/60-1,4,'拉开距离，使用游戏内的蓄力回血','heal')
    add(trace['victory_frame']/60,2,'牧风者击败 · 当前版本完整实机记录','victory')
    add(max(0,seconds-1.3),1.3,'仍在打磨，欢迎提建议','ending')
    # Keep one readable explanation at a time. Phase cues have priority over
    # nearby details; no instruction rewrites or manufactured action frames.
    priority={'phase':0,'intro':1,'victory':0,'ending':1,'focus':2,'walk_off':2,'heal':2,'style':3}
    selected=[]
    for c in sorted(cues,key=lambda c:(priority[c['kind']],c['start'])):
        if not any(min(c['end'],x['end'])-max(c['start'],x['start'])>.05 for x in selected):selected.append(c)
    return sorted(selected,key=lambda c:c['start'])


def ass_text(cues,seconds):
    def at(t):
        cs=round(t*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Explain,Noto Sans CJK SC,38,&H00FFFFFF,&H00FFFFFF,&H0010181C,&H8010181C,-1,0,0,0,100,100,0,0,1,2,0,2,75,75,13,1
Style: Title,Noto Sans CJK SC,29,&H00ADDFF2,&H00FFFFFF,&H0010181C,&H8010181C,-1,0,0,0,100,100,0,0,1,1,0,1,70,70,65,1
Style: Source,Noto Sans CJK SC,22,&H00DFE0D8,&H00FFFFFF,&H0010181C,&H8010181C,0,0,0,0,100,100,0,0,1,1,0,3,70,70,65,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    header+=f'Dialogue: 0,0:00:00.00,{at(seconds)},Title,,0,0,0,,失序之钟 · 牧风者完整战斗\n'
    header+=f'Dialogue: 0,0:00:00.00,{at(seconds)},Source,,0,0,0,,PR150 开发实机 · 程序输入 · 无配音\n'
    for c in cues:header+=f'Dialogue: 1,{at(c["start"])},{at(c["end"])},Explain,,0,0,0,,{c["text"]}\n'
    return header


def make_cover(movie,begin,out,spec):
    # Stable original ground view keeps the guardian's head and feet visible.
    run(['ffmpeg','-v','error','-y','-ss',begin+10,'-i',movie,'-frames:v','1',out/'cover-source.png'])
    im=Image.open(out/'cover-source.png').convert('RGB').resize((1920,1080),Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,690,1080),fill='#10181c')
    draw.text((55,65),'失序之钟',font=ImageFont.truetype(font(True),73),fill='#f2dfad')
    draw.text((60,175),'独游折腾记 '+spec['public_episode'],font=ImageFont.truetype(font(True),38),fill='#d8e0df')
    draw.text((45,315),'牧风者',font=ImageFont.truetype(font(True),157),fill='white')
    draw.text((45,500),'开打！',font=ImageFont.truetype(font(True),157),fill='white')
    draw.line((60,770,620,770),fill='#f2dfad',width=3)
    draw.text((60,825),'三阶段完整战斗',font=ImageFont.truetype(font(True),48),fill='#f2dfad')
    draw.text((60,920),'游戏原声 · 开发中',font=ImageFont.truetype(font(True),39),fill='#d8e0df')
    im.save(out/'cover.png')


def compose(spec_path,capture_folder,output,*,source_evidence=None,source_manifest=None):
    spec=read(spec_path);out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    capture_folder=Path(capture_folder).resolve()
    c=load_capture(capture_folder.parent,capture_folder.name,spec['main_commit'])
    audit=audit_fight(c['trace']);trace=c['trace']
    begin=trace['start_movie_frame']/60
    seconds=math.floor(min(trace['rows'][-1]['movie_frame']/60,c['duration']-begin)*30)/30
    cues=cue_plan(trace,seconds);(out/'subtitles.ass').write_text(ass_text(cues,seconds))
    timeline=[dict(stage='windkeeper',start=begin,end=begin+seconds,index=0,timeline_start=0,timeline_end=seconds,duration=seconds,speed=1,title='牧风者三阶段完整战斗',note='游戏原声，无配音；慢时来自真实游戏能力，非后期变速')]
    write(out/'storyboard.json',timeline);write(out/'text-cues.json',cues);write(out/'script.json',spec)
    target=out/'recordings/windkeeper';target.mkdir(parents=True,exist_ok=True)
    for name in ['gameplay.mp4','trace.json','receipt.json','recording_driver.gd','native.log','display.log','encode.log','decode.log']:
        if (capture_folder/name).exists():shutil.copyfile(capture_folder/name,target/name)
    source_project=Path(source_evidence) if source_evidence else Path(c['receipt']['source_project']);documents=[]
    original_documents={}
    if source_evidence:
        if not source_manifest:raise ValueError('Recovery requires the original source manifest')
        original=read(source_manifest)
        if original['commit']!=spec['main_commit']:raise ValueError('Recovered source commit mismatch')
        original_documents={d['path']:d for d in original['documents']}
    for path in spec['source_files']:
        p=source_project/path
        if source_evidence:
            expected=original_documents.get(path,{})
            raw=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if expected.get('sha256')!=sha(p) or expected.get('git_blob')!=blob or expected.get('commit')!=spec['main_commit']:
                raise ValueError('Recovered original source document mismatch: '+path)
        dest=out/'source-evidence'/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);raw=p.read_bytes()
        documents.append(dict(path=path,commit=spec['main_commit'],sha256=sha(dest),git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),delivered_path=str(dest.relative_to(out))))
    sources=dict(repository=spec['repository'],commit=spec['main_commit'],pr=150,recording_kind='fresh_original_native_recording',human_play=False,narration=False,captures=[dict(stage='windkeeper',source_commit=spec['main_commit'],movie_sha256=sha(c['movie']),delivered_recording='recordings/windkeeper/gameplay.mp4',receipt=c['receipt'])],documents=documents,combat_audit=audit,random_route_complete=None,limitations=['Declared isolated local Boss entry with base profile; not full-game progression or human gameplay.','Original source AI/HP/physics/resources are unchanged; software-rendered capture does not measure phone FPS.','Source aiming/occlusion helpers are reused read-only; floor forecasting is a recording input policy, not the game AI. One declared right-side local placement precedes the recorded live fight.','Successful automatic play does not certify player difficulty, fun, balance or aesthetic approval.'],rights=spec['rights'])
    write(out/'sources.json',sources)
    filt='fps=30,scale=1742:980:flags=lanczos:in_range=auto:out_range=tv,pad=1920:1080:89:0:color=0x10181c,setsar=1,ass='+str(out/'subtitles.ass')+',format=yuv420p'
    run(['ffmpeg','-nostdin','-y','-v','warning','-ss',begin,'-i',c['movie'],'-t',seconds,'-map','0:v:0','-map','0:a:0','-vf',filt,'-c:v','libx264','-preset','veryfast','-crf','20','-threads','4','-color_range','tv','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',out/'final.mp4'],log=out/'logs/render.log',timeout=1500)
    make_cover(c['movie'],begin,out,spec)
    require_public_copy(spec['title'],spec['description'])
    (out/'bilibili.md').write_text('# B站投稿资料\n\n## 标题\n\n'+spec['title']+'\n\n## 简介\n\n'+spec['description']+'\n\n分区：游戏 → 单机游戏\n标签：B站AI创造公开赛、失序之钟、独立游戏、Godot、游戏开发、Boss战\n\n尚未投稿。活动需在获准投稿时核对真实话题关联。\n')
    (out/'script.md').write_text('# 无配音文字提示\n\n'+'\n'.join(f'- {c["start"]:.2f}–{c["end"]:.2f}s：{c["text"]}' for c in cues)+'\n')
    (out/'phone-review.md').write_text('请完整观看：开战到死亡是否连续；慢时瞄准是否可读；三阶段走下台阶再反冲换台是否清楚；血条/脚下/字幕在手机上是否可读；原声是否舒适。程序输入不是真人操作，技术通过不代表好玩或难度合格。\n')
    report=validate_gameplay(out);report['combat_audit']=audit;report['publication']={'bilibili_published':False}
    report['technical']['checks']['explanatory_cue_bounds']=all(0<=c['start']<c['end']<=seconds for c in cues)
    report['technical']['passed']=all(report['technical']['checks'].values());write(out/'report.json',report)
    if not report['technical']['passed']:raise RuntimeError('Technical media checks failed')
    write(out/'delivery-manifest.json',{'episode':spec['episode'],'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='delivery-manifest.json' and 'logs' not in p.relative_to(out).parts}})
    print('DELIVERED',out,'seconds',seconds,flush=True)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',required=True);parser.add_argument('--capture',required=True);parser.add_argument('--output',required=True);parser.add_argument('--source-evidence');parser.add_argument('--source-manifest');a=parser.parse_args();compose(a.spec,a.capture,a.output,source_evidence=a.source_evidence,source_manifest=a.source_manifest)


if __name__=='__main__':main()
