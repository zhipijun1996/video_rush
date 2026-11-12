"""A compact, trace-audited native Demo showcase with original game audio."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

from PIL import Image, ImageDraw, ImageFont

from .common import read, write, sha, run, font
from .gameplay import load_capture, render_cut, validate_gameplay
from .posting_policy import require_public_copy


def audit_take(trace, case):
    if trace.get('case') != case or not trace.get('complete') or trace.get('failures'):
        raise ValueError('Incomplete native take: '+case)
    rows = trace['frames']
    if not rows or any(r['hp'] <= 0 for r in rows):
        raise ValueError('Missing live trajectory: '+case)
    sessions = {r['session'] for r in rows}
    expected = 2 if case == 'clockheart' else 1
    if len(sessions) != expected or max(sessions)-min(sessions) != expected-1:
        raise ValueError('Unexpected session/reset in take: '+case)
    events = trace['events']
    start = next(e for e in events if e['event'] == 'take_start')
    if start['invincible']:
        raise ValueError('Invincible footage not declared for this film')
    result = dict(complete=True, frames=len(rows), initial_pose=trace['initial_pose'],
                  human_play=False, min_hp=min(r['hp'] for r in rows),
                  actual_rooms=sorted({r['room'] for r in rows}),
                  session_changes=expected-1)
    if case == 'clockheart':
        if set(result['actual_rooms']) != {'P-R33','Z-R01'}:
            raise ValueError('Expected actual clockheart doorway transition')
        lines = [e for e in events if e['event']=='dialogue']
        if [e['index'] for e in lines] != [0,1,2]:
            raise ValueError('Clockheart native dialogue missing')
    if case == 'p10':
        shots = [e for e in events if e['event'] == 'native_shot']
        refills = [e for e in events if e['event'] == 'check'
                   and e.get('ok') and e['label'].startswith('native hit refills air shot:')]
        if start['stage'] != 'base' or len(shots) != 10 or len(refills) != 5:
            raise ValueError('Actual base-gun hits/refills missing')
        if {r['room'] for r in rows} != {'P-R10'} or not rows[-1]['grounded'] or rows[-1]['position'][1] > 160:
            raise ValueError('P10 continuous summit missing')
        # Count true shots while continuously airborne using sampled contacts.
        counts = []
        flight = 0
        for i, row in enumerate(rows):
            if row['grounded']:
                if flight: counts.append(flight)
                flight = 0
            end = rows[i+1]['frame'] if i+1 < len(rows) else row['frame']+1
            flight += sum(row['frame'] <= s['movie_frame'] < end for s in shots)
        if flight: counts.append(flight)
        if max(counts, default=0) != 4:
            raise ValueError('No actual four-shot single-flight chain')
        result.update(native_shots=10, actual_hit_refills=5, max_shots_single_flight=4,
                      summit_y=rows[-1]['position'][1], no_hook_or_double_jump=True)
    return result


def plan(captures):
    titles = {
        'p10': ('Demo 中的 Demo / P10 · 只用基础枪登高', '命中补弹，再接反冲；不用钩索和二段跳，也能一路上去。'),
        'street': ('先在钟外小站，喘口气', '一路跳跳乐，也需要能停下来看看、逛逛的地方。'),
        'clockheart': ('去钟心看看：这座世界，为什么停摆了？', '从塔前庭实际进门，播放游戏里已有的钟心剧情。'),
        'meadow': ('风铃岔路 / 不只一条向前的路', '上下错开的平台，希望让移动、选路和探索连在一起。'),
        'carrier': ('旧风车内廊 / 枪也能启动机关', '先上吊台，射铃启动；升到高处，再反冲换岸。'),
        'sluice': ('退潮渠畔 / 开门和赶路，用同一枪', '先走下落岸，回身射铃；开闸的同时，反冲穿过去。'),
        'repair': ('最后，让风鸣钟重新响起来', '这是 Demo 中的 Demo；还在搭路、补内容、磨体验，先往下做。'),
    }
    clips = []
    at = 0
    for case in ['p10', 'street', 'clockheart', 'meadow', 'carrier', 'sluice', 'repair']:
        t = captures[case]['trace']
        begin = next(e['movie_frame']/60 for e in t['events'] if e['event'] == 'take_start')
        end = next(e['movie_frame']/60 for e in t['events'] if e['event'] == 'take_end')
        # A native map panel is useful evidence in the retained raw take, but
        # omit the review-mode full-map detour from this short highlights edit.
        if case == 'street':
            end = next(e['movie_frame']/60 for e in t['events'] if e['event'] == 'native_explored_map')
        start = round(begin*30)/30
        end = round(end*30)/30
        if end > captures[case]['duration'] or end-start < .5:
            raise ValueError('Native take bounds invalid')
        title, note = titles[case]
        clips.append(dict(index=len(clips), stage=case, start=start, end=end,
                          duration=end-start, timeline_start=at,
                          timeline_end=at+end-start, title=title, note=note,
                          speed=1, type='fresh_native_gameplay',
                          scope='independent room; one disclosed initial pose, then native inputs'))
        at = clips[-1]['timeline_end']
    return clips


def compose(spec_path, captures_root, output, source_project):
    spec = read(spec_path)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out/'logs').mkdir(exist_ok=True)
    captures = {name: load_capture(captures_root, 'demo-'+name, spec['main_commit'])
                for name in spec['stages']}
    audits = {name: audit_take(c['trace'], name) for name,c in captures.items()}
    clips = plan(captures)
    write(out/'storyboard.json', clips)
    paths = [render_cut(c, captures[c['stage']], out) for c in clips]
    listing = out/'cuts/concat.txt'
    listing.write_text(''.join("file '"+str(p)+"'\n" for p in paths))
    run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',listing,
         '-t',clips[-1]['timeline_end'],'-vf','fps=30,format=yuv420p',
         '-c:v','libx264','-preset','veryfast','-crf','19','-threads','4',
         '-color_range','tv','-af','aresample=async=1:first_pts=0',
         '-c:a','aac','-b:a','192k','-ar','48000',
         '-bsf:v','h264_metadata=video_format=5:video_full_range_flag=0',
         '-movflags','+faststart',out/'final.mp4'],log=out/'logs/compose.log',timeout=600)
    source_rows = []
    for case,c in captures.items():
        dest = out/'recordings'/case
        dest.mkdir(parents=True,exist_ok=True)
        for name in ['gameplay.mp4','receipt.json','trace.json','native.log','recording_driver.gd']:
            shutil.copyfile(c['folder']/name, dest/name)
        r = c['receipt']
        source_rows.append(dict(stage=case,commit=spec['main_commit'],
                                movie_sha256=r['movie_sha256'],
                                delivered_recording=f'recordings/{case}/gameplay.mp4',
                                driver_sha256=r['driver_sha256'],
                                engine_sha256=r['engine_sha256'], audit=audits[case]))
    documents = []
    for relative in spec['source_files']:
        raw = (Path(source_project)/relative).read_bytes()
        dest = out/'source-evidence'/relative
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        documents.append(dict(path=relative,commit=spec['main_commit'],sha256=sha(dest),
                              git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
                              url=f'https://github.com/{spec["repository"]}/blob/{spec["main_commit"]}/{relative}',
                              delivered_path=str(dest.relative_to(out))))
    limits = ['分房逐房试玩，每段只有一个声明的初始站位，其后为普通Router输入；不是一命新档连续流程。',
              'P10基础枪连续登顶，不用H/D、途中传送、资源或血量注入。',
              'P15采用已有H的原生逐房试玩配置，并非本片内自然获得；敌人、机关、剧情和游戏规则保持。',
              '软件渲染720p60原片，剪辑1080p30；不宣称目标设备性能或完整游戏已验收。',
              '这是Demo中的Demo；自动操作成功不代表手感、美术、平衡或完整探索已经满意。']
    write(out/'sources.json',dict(repository=spec['repository'],commit=spec['main_commit'],
                                 source_ref=spec['source_ref'],captures=source_rows,
                                 documents=documents,random_route_complete=None,
                                 limitations=limits,rights=spec['rights']))
    write(out/'script.json',spec)
    (out/'script.md').write_text('# Demo 中的 Demo（无配音，游戏原声）\n\n'+
        '\n\n'.join(f'{c["timeline_start"]:.2f}–{c["timeline_end"]:.2f}s：{c["title"]}\n{c["note"]}' for c in clips))
    from .gameplay_revision import seconds
    ass = '[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans CJK SC,26,&H00FFFFFF,&H00FFFFFF,&H0010181C,&H0010181C,0,0,0,0,100,100,0,0,1,1,0,1,92,92,15,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    for c in clips:
        ass += f'Dialogue: 0,{seconds(c["timeline_start"])},{seconds(c["timeline_end"])},Default,,0,0,0,,{c["title"]}\\N{c["note"]}\n'
    (out/'subtitles.ass').write_text(ass)
    require_public_copy(spec['title'],spec['description'])
    (out/'bilibili.md').write_text('# 推荐标题\n\n'+spec['title']+'\n\n# 简介\n\n'+spec['description']+
        '\n\n分区：游戏 / 单机游戏\n标签：B站AI创造公开赛、失序之钟、独立游戏、类银河恶魔城、Godot、游戏开发\n\n尚未投稿；获准后核对真实活动话题与产品合集。\n')
    (out/'phone-review.md').write_text('完整用手机看一次：P10命中补弹与四枪是否看清；钟心原生对白是否来得及读；分房切换是否顺畅；机关及修钟声音是否舒适；字幕、人物和高处落点是否可读；Demo中的Demo是否表达清楚。技术验收不代替观感审核。\n')
    # An unchanged native scene, only resized and framed, forms the cover.
    run(['ffmpeg','-y','-v','error','-ss','8','-i',captures['p10']['movie'],
         '-frames:v','1',out/'cover-source.png'])
    frame = Image.open(out/'cover-source.png').convert('RGB').resize((1280,720))
    cover = Image.new('RGB',(1920,1080),'#101b23');cover.paste(frame,(640,220))
    draw = ImageDraw.Draw(cover)
    draw.text((55,65),'失序之钟',font=ImageFont.truetype(font(True),78),fill='#f2dfad')
    draw.text((55,235),'Demo',font=ImageFont.truetype(font(True),142),fill='white')
    draw.text((55,420),'中的',font=ImageFont.truetype(font(True),100),fill='#f2dfad')
    draw.text((55,565),'Demo',font=ImageFont.truetype(font(True),142),fill='white')
    draw.text((55,860),'先把能玩的拿出来',font=ImageFont.truetype(font(True),43),fill='white')
    draw.text((55,950),'当前实机 / 开发中',font=ImageFont.truetype(font(),38),fill='#d8e0df')
    draw.text((705,93),'只用枪，也能登顶',font=ImageFont.truetype(font(True),70),fill='#f2dfad')
    cover.save(out/'cover.png');(out/'cover-source.png').unlink()
    report = validate_gameplay(out)
    report.update(episode=spec['episode'],native_take_audits=audits,
                  publication={'bilibili_published':False},
                  user_request='最新版当前玩法与钟心剧情精彩片段；Demo中的Demo')
    write(out/'report.json',report)
    if not report['technical']['passed']:
        raise RuntimeError('Technical verification failed; retain report/logs')
    write(out/'state.json',dict(status='complete_pending_phone_review',
                               stages={k:('disabled_no_narration' if k=='Narration' else 'completed')
                                       for k in ['Research','Story','Script','Shot Planning','Footage Collection','Narration','Timeline Composition','Rendering','Quality Validation','Delivery']}))
    write(out/'delivery-manifest.json',{'episode':spec['episode'],'files':{
        str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
        if p.is_file() and 'cuts' not in p.relative_to(out).parts
        and 'logs' not in p.relative_to(out).parts and p.name!='delivery-manifest.json'}})
    print(json.dumps(dict(output=str(out),seconds=clips[-1]['timeline_end'],passed=True)),flush=True)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',default='episodes/ep016-showcase.json')
    p.add_argument('--captures',required=True);p.add_argument('--output',required=True)
    p.add_argument('--source-project',required=True)
    a=p.parse_args();compose(a.spec,a.captures,a.output,a.source_project)


if __name__=='__main__':main()
