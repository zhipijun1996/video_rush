"""Package the V7 full film and its new source/acting evidence."""
from video_rush.common import ROOT,read,write,run,sha
from tools.paipai_full_delivery import package


if __name__=='__main__':
    out=ROOT/'build/episodes/ep008-v7-counterplay';spec=read('episodes/ep008-v7-counterplay.json');p=read(out/'storyboard.json')
    package(out,spec_path='episodes/ep008-v7-counterplay.json')
    sources=read(out/'sources.json');sources.update(counter_voice_receipts=read(out/'counter-voice-receipts.json'),counter_references=spec['counter_references'],source_music_beds=read(out/'music/design.json')['source_audio_beds'],end_url=spec['end_url'])
    sources['references']['jotaro']={**spec['counter_references']['jotaro_pose'],'derived_sha256':sha(out/'extra/jotaro-pose.mp4'),'recipe':'first0.35s normal action plus1.75s editorial anime pose freeze; not continuous original motion and never fake gameplay'}
    sources['music']='Original five-note theme with MIT FluidR3 GM, plus short corresponding DIO/Ultraman source-scene music/effects mixes. Third-party music permissions unconfirmed; not claimed as isolated BGM.';write(out/'sources.json',sources)
    notes='''

# 本轮反转段和胜利镜头修订

- A第二次出中波补“再来！”，B开盾补“AT力场！防住！”。字幕采用通用译名力场，生成输入立场与其读音一致，配音回执保留真实输入。
- 删除A“你也想起舞吗”，B紧接着说“到我了！”再出波，原有中波和宇智波反弹实机时间窗口保留。
- B被反弹后用气愤语气说“你把我的反弹升级了？！”；变小的瞳孔、斜眉和指向A的手势替换原来的单纯惊讶。
- A新增“JOJO！”呼喊，主体沿用已认可的“我不做人了”表演，声线从压低到爆发，DIO画面仍承接部分喊声。加入同一DIO原片场景的音乐/效果混音底声，5秒源片音频保留音高后适配段落长度，不冒称原画同期声；硬切奥特曼前仅留0.08秒停顿，奥特曼画面恢复对应原片声音并衔接实机光线，AI对白下自动压低。
- 原声底不是分离出的纯伴奏，也不宣称有商业许可。DIO转贴来源BV114411r7Cr；现有奥特曼镜头仍是上版实际初代片段，未将其错标成迪迦。
- 更换承太郎为前指造型，火柴人也改为前指、另一手叉腰；原片0.35秒动作后漫画式停帧，总显示2.1秒。不是循环原片，也没有用替身/其他人物画面凑时长。
- 片尾和投稿简介试玩链接按用户最新要求改为https://b23.tv/yCut8r4；不擅自替换成重定向后的长参数URL。云端访问落地页412，不声称试玩加载成功。

本次仍交完整七章。旧版保留，未投稿B站/Toy。配音表演、配乐冲击和姿势匹配由用户手机审片，不由技术检查代签。
'''
    current=(out/'changes.md').read_text().replace('DIO段抽掉音乐，奥特曼进入英雄配器','DIO段补原片底声，跨番前仅短暂停顿，奥特曼衔接原片底声与英雄配器')
    (out/'changes.md').write_text(current+notes)
    with (out/'phone-review.md').open('a') as f:f.write('\n重点：再来→AT防住→到我了→反弹后怒问是否连贯；JOJO和原片底声是否有冲击；前指姿势是否对应；片尾短链接是否正确。\n')
    posting=(out/'bilibili.md').read_text();posting=posting.replace('火柴人、剪辑与主题配乐由Video Rush制作；短引用及游戏原声来源、许可状态见sources.json。','火柴人、剪辑与主题配乐由Video Rush制作；DIO/奥特曼段另含短原片混音引用。各来源与许可状态见sources.json。');(out/'bilibili.md').write_text(posting)
    for name,at in [('counter-angry.png',next(v['start'] for v in p['voices'] if v['id']=='ANGER-B')+.4),('victory-pose.png',next(s['start'] for s in p['segments'] if s.get('shot',{}).get('id')=='5-06')+1.2),('ending-link.png',p['segments'][-1]['start']+.65)]:run(['ffmpeg','-v','error','-y','-ss',at,'-i',out/'final.mp4','-frames:v','1',out/name])
    manifest=read(out/'delivery-manifest.json')
    for f in [*out.glob('*.json'),*out.glob('*.md'),*out.glob('*.png'),*out.joinpath('extra').glob('*.m4a'),out/'extra/jotaro-pose.mp4']:
        if f.name!='delivery-manifest.json':manifest[str(f.relative_to(out))]=sha(f)
    write(out/'delivery-manifest.json',manifest)
