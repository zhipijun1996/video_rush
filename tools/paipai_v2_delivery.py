"""Create phone auditions, exact old excerpts, evidence and honest review notes."""
import argparse
import html
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from video_rush.common import ROOT,read,write,sha,run,duration
from video_rush.paipai_v2_score import compose
from tools.make_paipai_v2_review import pcm
from video_rush.narration import audio_metrics


def finish(spec,out):
    report=read(out/'report.json');p=out/'portable';candidates=read(p/'voice-candidates.json');timelines=read(out/'trial-timelines.json');baseline=ROOT/spec['baseline']
    for k in range(1,6):
        if not {f'K{k:02}-A',f'K{k:02}-B'}.issubset({c['id'] for c in candidates}):raise ValueError('Missing a required A/B voice performance')
    for c in candidates:
        path=p/'voices'/(c['id']+'.m4a')
        if sha(path)!=c['sha256'] or not audio_metrics(path)['audible_signal']:raise ValueError('Bad audition file '+c['id'])
    compare=out/'comparison';compare.mkdir(exist_ok=True);evidence=out/'evidence';evidence.mkdir(exist_ok=True)
    old=read(ROOT/'build/deliveries/ep008-r3-remote/episodes/ep008-r3/storyboard.json')['shots']
    ranges=[('01_light','3-04C','3-04D'),('02_hadouken','4-01','4-04'),('03_dio_ultra','5-03','5-05')]
    for id,first,last in ranges:
        a=next(s['start'] for s in old if s['id']==first);b=next(s['end'] for s in old if s['id']==last)
        run(['ffmpeg','-v','error','-y','-ss',a,'-i',baseline,'-t',b-a,'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',compare/(id+'_OLD.mp4')],timeout=180)
    bank=read(p/'game-bank.json');shutil.copyfile(p/bank['8']['file'],evidence/'native-medium-original.mp4')
    sf=ROOT/spec['music']['soundfont_path'];music=out/'music'
    for style in ['deadpan','warm','battle','villain','rock','heroic','reprise']:
        wav=compose(music/(style+'-theme.wav'),sf,style,8,3.0 if style in ('rock','heroic') else None)
    for wav in music.glob('*.wav'):
        run(['ffmpeg','-v','error','-y','-i',wav,'-c:a','aac','-b:a','128k','-movflags','+faststart',wav.with_suffix('.m4a')],timeout=90)
    md=['# 配音候选 · 先听表演，再决定全片','', '五组重点台词各有A/B两种真实模型表演；另有N01–N03普通小学生声线。候选独立音频位于portable/voices/，均可单独播放。是同一组新表演的AAC-LC单声道64kbps传输副本；原始WAV与96kbps母版保留在本地。不是把同一句复制后调大音量。','', '| 编号 | 台词 | 时长 | 表演方向 |','|---|---|---|---|']
    for c in candidates:md.append(f"| {c['id']} | {c['text']} | {c['duration']:.2f}s | {c['direction']} |")
    md+=['','导演暂选：B宣言K01-B；夜神月K02-B；波动拳K03-B；DIO K04-B；光线K05-A。波动拳A约5.8秒、B约1.6秒，是长聚气与瞬间爆发的两种节奏，试剪暂选B。光线B长吼更极端，自动转写对尾字有疑义，不能冒称咬字验收已过，暂选清晰的A。','', '文本/波形和部分自动转写已检查。笑声、招式专名、破音容易被ASR认错；它不能代替你听出好不好笑、是不是同一个小学生、喊得够不够帅。旧版支持性台词以old-开头，未冒充新演出。']
    (out/'配音试听说明.md').write_text('\n'.join(md))
    (out/'关键差异与审核.md').write_text('''# 看声音和节奏，不只看文件

先看三个*_NEW.mp4，再到comparison/看对应*_OLD.mp4。旧版完整成片没有被覆盖。这轮没有新的全片final.mp4。

| 桥段 | 旧版实际表现 | 本次试剪 |
|---|---|---|
| 夜神月 | 0.45秒小叠影；表情主要靠背景和固定手势 | 嫌弃干声→嘴角上扬并低笑→约3.8秒清楚的原作镜头组合→头、肩、手臂分别运动的火柴人狂喜→普通小孩吐槽前音乐急停；普通/中二声线分开生成 |
| 第一次波动拳 | 0.30秒叠影+0.48秒全幅，音乐没有发射重拍 | 真实攒气跳剪和三指铺垫；经典原片约2.5秒，镜像匹配向右出招；蓝光遮挡交接真实发射，电吉他/鼓组重拍落在发射时刻，再让小学生回来口胡 |
| DIO→奥特曼 | DIO仅0.42秒，原片间多次经过普通姿势 | 低声到爆喊的角色演出；DIO约2.3秒；直接切十字姿势，短抽空后铜管/弦乐进入，光线发射再全奏。发射到胜负不插普通吐槽 |

夜神月画面是两段可辨识的原作GIF来源，笑声来自另一条转载录音，经重新剪接；未核实它们原本音画同期，不能叫授权原盘。所有动漫短引用与游戏内作品录音的许可状态仍未确认。

为了避免把“动漫发招”和“游戏再起手”完整重复两遍，试剪剪去了游戏的重复蓄力停留，完整保留真实发射、破防、命中、扣血与胜负，没有加一场假战斗。evidence/native-medium-original.mp4单独保留原生中波特写，便于判断游戏本体。

## 手机审核

- [ ] 夜神月是否真正疯起来？普通小孩一句话打断，反差是否成立？是否要更短/更长？
- [ ] 波动拳起手看得清吗？蓝光接到真实发射那一下，音乐有没有一起炸开？
- [ ] DIO声线够不够疯狂？硬切十字手势时是否有意外感？光线是否真燃？
- [ ] 五组配音喜欢A还是B？特别是波动拳长聚气版与短爆发版、光线B的咬字。
- [ ] 人声是否始终压得住配乐与效果声？原片风格/音色是否接受？

以上由你审核，技术检查不签审美PASS。收到三段反馈后才把通过的方案推广到七章全片，未投稿B站/Toy。
''')
    trace=read(p/'trace.json');r=trace['rounds'][7]
    (out/'游戏端单独改进建议.md').write_text(f'''# 中波原生演出：单独建议，不在试剪伪造

素材来自wave-game `c6f1326c824a4b5c8489b0918285d9063f9d1db6` 的已保存连续合法对局。原生完整样本见evidence/native-medium-original.mp4。

- 当前中波独立特写的revealing→launch约{r['launch']-r['reveal']:.2f}秒，发射→结算约{r['commit']-r['launch']:.2f}秒。游戏已经有独立肖像、速度线、能量形状、破防碎片、受击姿态与震屏开关；不是完全没做反馈。
- 源码spectacle.ts的cutin主要在固定底色上绘制肖像、速度线与文字；renderer.ts已有受击姿态过渡和约35ms肢体滞后；main.ts在伤害结算时触发stage-wrap.shake。建议围绕这些已有能力做A/B调参，而不是再堆无差别特效。
- 建议实验一：蓄力最后100–150ms让身体、掌心和能量球的收缩/膨胀产生更明确对比，把发射首帧的方向与速度读出来。
- 建议实验二：破筒碎片、受击重心、伤害数字/血条和短促重击集中到同一结算节拍；可单独评估命中停顿，区分于已有蓄力特写冻结，不把两者混为一谈。
- 建议实验三：针对强度差做反馈等级对照，先保证小波/中波/大波的体量、音色和受击反应差异，再考虑加更多粒子。

本轮只提出建议，未修改wave-game。试剪中的蓝光遮挡属于剪辑转场，音乐高潮属于视频后期；没有把后期强化冒称为游戏已经实现的新打击反馈。
''')
    parts=['<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>拍拍波V2视听试剪</title><style>body{font:17px sans-serif;background:#faf5e8;color:#242b30;max-width:900px;margin:auto;padding:20px}video{width:100%;background:#111}audio{width:100%}section{padding:16px;background:#fff9;margin:18px 0;border-radius:12px}p{line-height:1.6}a{color:#3d7f9a}</style><h1>拍拍波 V2 · 先审三段</h1><p>这里只交付试剪和试听，不是新全片。解压后音视频可分别打开。若手机文件预览器不支持网页控件，直接打开MP4/M4A。</p>']
    names=['夜神月：从嫌弃到失控','首次波动拳：三格气的第一次高潮','DIO→奥特曼：跨番硬切']
    for r,name in zip(report['trials'],names):parts.append(f'<section><h2>{html.escape(name)}</h2><video controls preload="metadata" src="{r["file"]}"></video><p>新版 {r["seconds"]:.2f}秒 · <a href="comparison/{r["file"].replace("_NEW","_OLD")}">对照旧版片段</a></p></section>')
    parts.append('<h2>配音A/B试听</h2>')
    for c in candidates:parts.append(f'<section><b>{c["id"]} · {html.escape(c["key"])}</b><p>{html.escape(c["text"])}</p><audio controls preload="none" src="portable/voices/{c["id"]}.m4a"></audio></section>')
    parts.append('<p><a href="BGM设计表.md">全片BGM设计表</a> · <a href="关键差异与审核.md">关键差异与审核</a> · <a href="游戏端单独改进建议.md">游戏端建议</a></p></html>');(out/'index.html').write_text(''.join(parts))
    source={'baseline':{'requested_name':spec['requested_filename'],'actual_file':spec['baseline'],'sha256':sha(baseline),'identity_status':spec['requested_file_status']},'voices':{'model':'Qwen3-TTS-12Hz-1.7B-VoiceDesign','model_revision':spec['voice_model_revision'],'license':'Apache-2.0 model declaration','generation':'Actual local CPU bfloat16 inference; invented child characters, no actor/user voice clone','portable_performances':[(c['id'],c['sha256']) for c in candidates]},'music':{**spec['music'],'soundfont_sha256':sha(sf),'notice':'licenses/FluidR3-copyright.txt'},'anime':{**read('episodes/ep008-r3-film.json')['references'],**spec['new_references']},'game':{'commit':'c6f1326c824a4b5c8489b0918285d9063f9d1db6','bank':bank,'rights':'Native effects include original samples and franchise recordings; see portable/game-native-audio-manifest.json'},'full_film_policy':'Blocked pending user review of these three trials; no final.mp4 produced'}
    source['production']={'git_head':run(['git','rev-parse','HEAD']).strip(),'recipe_sha256':{f:sha(ROOT/f) for f in ['tools/make_paipai_v2_review.py','tools/paipai_v2_delivery.py','video_rush/paipai_v2_score.py','video_rush/paipai_v2_art.py','episodes/ep008-v2-av-review.json']}}
    write(out/'sources.json',source);write(out/'review-state.json',{'three_trial_approval':'pending_user','voice_choices':'pending_user','promote_to_full_film':False,'bilibili_submission':False})
    editable=out/'editable';editable.mkdir(exist_ok=True);run(['git','archive','--format=zip','HEAD','--output',editable/'video-rush-source.zip'])
    hashes={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and (f.parent==out or f.is_relative_to(p) or f.is_relative_to(compare) or f.is_relative_to(evidence) or f.is_relative_to(editable) or f.parent==music and f.suffix in ('.m4a','.mid','.json')) and not f.name.endswith('-joined.mp4') and f.suffix not in ('.wav','.txt') and f.name!='delivery-manifest.json'}
    write(out/'delivery-manifest.json',hashes)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',default='episodes/ep008-v2-av-review.json');p.add_argument('--output',default='build/episodes/ep008-v2-review');a=p.parse_args();finish(read(a.spec),Path(a.output).resolve())
