"""Deliver the complete V8 film, review cut and truthful new-capture receipts."""
from video_rush.common import ROOT,read,write,run,sha
from tools.paipai_full_delivery import package
from tools.make_paipai_continuity import OUTPUT,SPEC


def deliver():
    out=ROOT/OUTPUT;spec=read(SPEC);p=read(out/'storyboard.json');package(out,spec_path=SPEC)
    sources=read(out/'sources.json');sources.update(continuity_voice_receipts=read(out/'extra/continuity-voice-receipts.json'),new_real_game=read(out/'extra/new-game-receipt.json'),source_audio_beds=read(out/'music/design.json')['source_audio_beds'],end_url=spec['end_url'])
    sources['packaging_commit']=sources['production_commit'];sources['production_commit']=read(out/'report.json')['git_head']
    sources['references']['jotaro']={**spec['counter_references']['jotaro_pose'],'derived_sha256':sha(out/'extra/jotaro-pose.mp4'),'appearance':'Only beside the child as feathered40% opacity apparition; first0.35s normal action then editorial pose freeze, no full-screen anime victory cut'}
    sources['voice_selection']={'villain':'DIO-CONT-A; one generated performance spanning stick/anime cut; DIO-CONT-B alternate audition included','king':'KING-FAST,0.88sec, not accelerated old audio','hero':'K05-A retained; overlapping native shout ducked at start; win declaration uncut native game sound'}
    sources['music']='Original same-motif score and short documented DIO/Ultraman source-scene mixes, third-party permissions unconfirmed; quieter during complete native victory declaration.'
    write(out/'sources.json',sources)
    (out/'changes.md').write_text('''# V8连贯性修订

- “JOJO！我不做人了！”重新生成同一次连续表演，0.60秒火柴人后切DIO，声音不断、不换表演、不随画面切换压低。原片底声在角色下保留，不再过度避让到听不见。
- 保留一次奥特曼原片接实机光线；从真实发射动作开始取游戏画面，省掉原生起手的重复奥特曼切入。旧的斯派修姆配音保留一次，实机最前0.65秒原声音轨压低避免双喊，之后恢复实际发射、破防、胜利音效。
- 之前实录只在获胜后等待1.65秒便退出，装不下2.8秒原生胜利声音。新实录使用同一精确游戏SHA、原规则和原渲染，从零气五血合法完成21轮，只把胜利后停留延长至3.5秒。最后光线到胜利宣言正常速度连续播放，没有插小孩/动漫全屏、补帧或伪造胜负。
- 实机宣言完整结束才回小孩，0.88秒“叫大王！”一口气喊完。承太郎在小孩右侧以40%透明、柔边叠影出现，保持小孩画面，不再实机/原画/小孩来回闪。
- B“你就赢这一把”后半搭在0.85秒童年走廊与成年酒局溶解上，保留原台词与轻微成年音色过渡；去掉旧切换的叮声与局部突切。
- 末尾手机实机由手中小窗改为上方清楚展示，连续保留第一轮防守至恢复，再接结尾，去掉第二轮尚未放完的开头。
- 片尾和简介继续使用https://b23.tv/yCut8r4。旧版保留，未投稿B站/Toy。

表演、节奏、幽默和叠影位置仍待用户手机审片。原片及游戏内第三方录音的转载许可未确认。
''')
    (out/'phone-review.md').write_text('''# 手机审核待用户

- [ ] JOJO与我不做人是同一人、同一速度，切DIO时喊声是否仍有爆发力。
- [ ] 实机光线开始没有奥特曼闪回，也没有重复喊招。
- [ ] 实机胜利宣言是否完整、清楚，期间没有其他画面打断。
- [ ] 叫大王是否够利落，承太郎像旁边替身而非全屏插片。
- [ ] 你就赢这一把到中年酒局是否自然，成年回答是否顺。
- [ ] 最后防守完整播完再结束，手机画面是否清楚。

技术检查不代替审美/听感验收；未自动公开投稿。
''')
    start=next(s['start'] for s in p['segments'] if s.get('mode')=='dio_face')-.95
    end=next(s['start']+s['seconds'] for s in p['segments'] if s.get('shot',{}).get('id')=='6-02')
    run(['ffmpeg','-v','error','-y','-ss',start,'-i',out/'final.mp4','-t',end-start,'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',out/'continuity-review.mp4'])
    for name,at in [('victory-apparition.png',next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='5-06')+.45),('memory-transition.png',next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='6-01')+.525),('complete-defence.png',next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='7-02')+1.5)]:run(['ffmpeg','-v','error','-y','-ss',at,'-i',out/'final.mp4','-frames:v','1',out/name])
    manifest=read(out/'delivery-manifest.json')
    for f in [*out.glob('*.json'),*out.glob('*.md'),*out.glob('*.png'),*out.glob('*review.mp4'),*out.joinpath('extra').glob('*')]:
        if f.is_file() and f.name!='delivery-manifest.json':manifest[str(f.relative_to(out))]=sha(f)
    write(out/'delivery-manifest.json',manifest)


if __name__=='__main__':deliver()
