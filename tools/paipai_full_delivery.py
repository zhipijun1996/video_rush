"""Full phone-review delivery: film, cover, posting copy and source receipts."""
import csv
from PIL import Image,ImageDraw,ImageFont
from video_rush.common import ROOT,read,write,sha,run,font
from video_rush.paipai_film_art import image as original_frame


def package(out,*,spec_path='episodes/ep008-v6-full.json'):
    spec=read(spec_path);p=read(out/'storyboard.json');head=run(['git','rev-parse','HEAD']).strip();title=read('episodes/ep008-r3-film.json')['title']
    cover=Image.new('RGB',(1920,1080),'#faf5e8');d=ImageDraw.Draw(cover);king=next(s['shot'] for s in p['segments'] if s.get('shot',{}).get('id')=='5-06');cover.paste(original_frame(king,1.45,king['seconds']).resize((1200,675)),(700,390))
    for xy,text,size,color in [((90,120),'小时候的口胡',120,'#282529'),((90,290),'被我做成游戏了',120,'#d35c48'),((95,475),'拍拍波大王 · 申请出战',54,'#282529')]:d.text(xy,text,font=ImageFont.truetype(font(True),size),fill=color)
    cover.save(out/'cover.png')
    (out/'bilibili.md').write_text(f'''# 标题

{title}

# 简介

日复一日的一天，直到老朋友喊了一句：“拍拍波大王。”
小学课间口胡出来的波动拳、魔法筒、宇智波反弹……现在被我做成了小游戏。
这次用火柴人小剧场和真实游戏录屏，重打一场小时候的课间决战。

试玩：{spec.get('end_url','https://zhipijun1996.github.io/wave-game/')}
源码：https://github.com/zhipijun1996/wave-game

角色为AI配音，成年人和童年故事为剧情演绎；实机为单机AI对战。
火柴人、剪辑与主题配乐由Video Rush制作；短引用及游戏原声来源、许可状态见sources.json。

#B站AI创造公开赛#

建议分区：游戏 / 单机游戏
建议标签：B站AI创造公开赛，拍拍波，独立游戏，AI开发，童年，火柴人，游戏开发
投稿前核对账号公开期数；当前只交付完整审片，未自动上传或宣称已获得参赛资格。
''')
    lines=['# 拍拍波 · 完整视听修订版','',f"全片 {p['seconds']:.2f} 秒；七章结构保留，开头和过渡按本轮要求修改。",'']
    for v in sorted(p['voices'],key=lambda v:v['start']):lines.extend([f"- {v['start']:.2f} 秒 · {v['id']}：{v['text']}"])
    (out/'script.md').write_text('\n'.join(lines)+'\n')
    with (out/'shot-list.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','chapter','start','seconds','kind','scene','source_in'])
        for s in p['segments']:w.writerow([s['id'],s['chapter'],s['start'],s['seconds'],s['kind'],s.get('shot',{}).get('scene',s.get('mode',s.get('phase',''))),s.get('in','')])
    (out/'changes.md').write_text('''# 本轮完整审片

开头新增“日复一日的一天”，约2.6秒的疲惫上班日常建立情境，才进入老板训话。老板和主角嘴部各自读取实际声音的逐帧振幅，字幕、配音和视频使用一个时间轴；opening-sync.json记录最终AAC相对混音母带的实测偏移。

过渡保持“事情……开始变得有趣了”→“到我创造了，三格气的大招！”。严格保留到字，不再擅自加直到的直字。B中招后改为颜艺“还能这样？！”；原“我的反弹呢”和双方反弹确认删除。

夜神月完整表情、波动拳逐步加速互切和双重曝光、DIO硬切奥特曼三段推广到全片；B的规则宣言使用实际新表演。真人模仿声线不是原演员声音。七章情节、反转、实际游戏胜负、老友结尾保留。

整片使用同一五音主题不同配器，成年人疲惫、老友重逢、童年对战、反派、摇滚、英雄和温暖回归分别安排。短试剪结尾音型没有插进中途，波动拳后接AT连续反转；DIO段抽掉音乐，奥特曼进入英雄配器，最后在片名处收束。

游戏和手机画面复用之前保存的真实录像，并制作相同源窗口的正常速度副本；没有伪称本轮重新录制。火柴人及叠画属于剧情动画，不用于伪造实机结果。未覆盖旧全片，未向B站/Toy投稿。
''')
    (out/'phone-review.md').write_text('''# 手机完整审核（待用户）

- [ ] 日常旁白进入老板训话是否自然，开头嘴部与声音是否同步。
- [ ] 成年/小学生、普通互怼/故意模仿反派的声线反差是否清楚。
- [ ] 夜神月→“到我创造了”→波动拳是否顺，B惊讶是否够夸张。
- [ ] 波动拳加速叠画是否保留认可的效果，接AT与反弹是否自然。
- [ ] DIO跨番硬切奥特曼是否好笑，大波命中是否够燃。
- [ ] 整片BGM音量、留白、高潮和结尾是否合适。
- [ ] 七章和结尾是否顺畅；字幕、音效无漏听、漏看或重复。

自动技术检查不代表表演、幽默和审美通过。原片及部分游戏原声转载许可未确认，当前为审片交付，没有自动公开投稿。
''')
    references=read('episodes/ep008-r3-film.json')['references']
    write(out/'sources.json',{'production_commit':head,'spec_sha256':sha(ROOT/spec_path),'original_approved_storyboard':'episodes/briefs/ep008-r3-user-storyboard-v1.md','game_commit':spec['japanese_hadouken']['commit'],'original_capture_receipts':{n:read(out/'full-inputs'/n) for n in ['receipt.json','mobile-receipt.json']},'native_window_derivatives':p['bank']['game'],'original_voice_derivatives':p['bank']['voices'],'original_voice_receipts':'full-inputs/original-voice-receipts.json','new_voice_receipts':read(out/'new-voice-receipts.json'),'preserved_V2_input_manifest':read(out/'portable/manifest.json'),'references':references,'japanese_shout':spec['japanese_hadouken'],'native_claps':spec['native_claps'],'music':'Original five-note theme with MIT FluidR3 GM; licenses/ and music/design.json','animation':'Original procedural stick drawing; anime double exposure is editorial animation, not game footage','font':'Noto Sans CJK, SIL OFL 1.1','rights_status':'Anime references and some native franchise recordings unconfirmed; no claim of commercial permission','publication':'Full private review delivered only; no Bilibili/Toy submission'})
    run(['ffmpeg','-v','error','-y','-i',out/'final.mp4','-t',p['boss_start']+3.7,'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','128k','-movflags','+faststart',out/'opening-review.mp4'])
    for name,at in [('opening.png',.9),('boss-sync.png',p['boss_start']+.53),('wave.png',p['wave_peak']-.4),('hero.png',p['hero_peak'])]:run(['ffmpeg','-v','error','-y','-ss',at,'-i',out/'final.mp4','-frames:v','1',out/name])
    edit=out/'editable';edit.mkdir(exist_ok=True);run(['git','archive','--format=zip','--output',edit/'video-rush-project.zip','HEAD'])
    files=[*out.glob('*.json'),*out.glob('*.md'),*out.glob('*.csv'),*out.glob('*.ass'),*out.glob('*.png'),out/'final.mp4',out/'opening-review.mp4',*edit.rglob('*'),*out.joinpath('full-inputs').rglob('*'),*out.joinpath('portable').rglob('*'),*out.joinpath('extra').rglob('*.m4a'),*out.joinpath('extra').glob('clap*.wav'),*out.joinpath('licenses').rglob('*'),*out.joinpath('music').glob('*.json'),*out.joinpath('music').glob('*.m4a'),*out.joinpath('music').glob('*.mid'),*out.joinpath('logs').rglob('*')]
    write(out/'delivery-manifest.json',{str(f.relative_to(out)):sha(f) for f in sorted(set(files)) if f.is_file() and f.name!='delivery-manifest.json'})


if __name__=='__main__':package(ROOT/'build/episodes/ep008-v6-full')
