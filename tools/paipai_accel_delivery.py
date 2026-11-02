"""Package V4 without replacing earlier review artifacts."""
from video_rush.common import ROOT,read,run,sha
from tools.paipai_matchcut_delivery import package


if __name__=='__main__':
    out=ROOT/'build/episodes/ep008-v4-accel';p=read(out/'timeline.json');merged=next(s for s in p['segments'] if s['kind']=='BLEND')
    run(['ffmpeg','-v','error','-y','-ss',merged['start']+merged['seconds']*.65,'-i',out/'light_to_hadouken_MATCHCUT.mp4','-frames:v','1',out/'double-exposure.png'])
    package(out,spec_path='episodes/ep008-v4-accel.json',notes='''# 越闪越快 → 火柴人和原片叠画；配乐重新收尾

先看 light_to_hadouken_MATCHCUT.mp4；hadouken_MATCH_ONLY.mp4 只看动作。double-exposure.png 是实际导出视频的叠画截图。

在上一版方向上继续：对应动作每个镜头从12帧、9帧、6帧、4帧缩短到3帧，然后停止来回切，用12帧脸部双重曝光和3帧推掌叠画接真实游戏发射。叠画将原创小学生画层与原片对齐，保留原角色与红头带；不会把动画合成贴进实机。仅一处短暂加速段，无白场频闪。日语原声仍连续喊一次。

上一版命中后整条摇滚声部还在两句互怼下继续，末尾主要依靠短淡出。本版让战斗音乐在命中后150毫秒内退出，给“喂！我的反弹呢？”留白。最后一句说完，以原主题倒序的五个音做轻巧吉他收尾，预留释放尾音的时间，避免突然截断乐句。music/score.m4a 可独立试听，music/cues.json 可核对进入和退出时间。

夜神月到三格气的衔接、日语配音、游戏音效与真实第8回合结果延用。没有推广全片，没有重配其他台词，没有覆盖V2/V3或向B站/Toy投稿。此处收尾只服务试剪，合入全片时应接下一次反转的音乐。

手机重点审核：加速是否足够自然？叠画是否像小学生进入角色而非两张画随意重叠？命中后留白和最后短收尾是否合适？自动检查不代表观感通过。第三方原片、日语录音授权状态沿用此前未确认状态，素材来源见sources.json。
''',extra_sources={'revision_of':'ep008-v3-matchcut','previous_transition_artifact':13148973511,'accelerating_frames':[12,9,6,4,3],'overlay_art_sha256':sha(ROOT/'video_rush/paipai_double_exposure.py'),'score_cues':read(out/'music/cues.json'),'truth':'Editorial original drawing over anime only; game footage is unaltered'})
