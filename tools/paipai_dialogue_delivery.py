"""Package revised dialogue with individually playable actual performances."""
from video_rush.common import ROOT,read,run,sha
from tools.paipai_matchcut_delivery import package


if __name__=='__main__':
    out=ROOT/'build/episodes/ep008-v5-lines';p=read(out/'timeline.json');reaction=next(s for s in p['segments'] if s.get('mode')=='surprise')
    run(['ffmpeg','-v','error','-y','-ss',reaction['start']+.30,'-i',out/'light_to_hadouken_MATCHCUT.mp4','-frames:v','1',out/'reaction.png'])
    spec=read('episodes/ep008-v5-lines.json')
    package(out,spec_path='episodes/ep008-v5-lines.json',notes='''# 创造三格气大招 → 波动拳 → 还能这样？！

先看 light_to_hadouken_MATCHCUT.mp4（带完整衔接和新反应）。hadouken_MATCH_ONLY.mp4 只看已认可的招式段。

A不再试探地问“那……三格气呢？”，而是讲“直到我创造了，三格气的大招！”，第二句抬起三根手指。将用户“到我创造了”按“直到我创造了”理解，前一轮末尾的夜神月狂笑直接接新招式的发现，不增加反弹规则确认。B被打中后不再喊“我的反弹呢”，改为小学生本音惊讶的“还能这样？！”；眼镜、瞳孔、眉毛、下巴、手臂都有独立动作，人物保持此前的蓝色圆眼镜设定。

新配音由实际Qwen3-TTS本地模型重新表演，非改字幕配旧声音。extra/CREATE-A.m4a和extra/SURPRISE-B.m4a可以单独试听，new-voice-receipts.json保存真实母带、波形、后端和哈希。字幕与镜头长度跟随实际新音频，不拉伸口播去迁就旧时长。

沿用已认可的V4波动拳：日语原声一次、12/9/6/4/3帧加速、脸部和推掌双重曝光、真实中波破反弹并命中；原片与实机取用窗口不改变。后续A的得意回应保留。B的惊讶仍留白，音乐按新台词结束点收束，music/score.m4a可试听。

这是独立短试剪，不是新全片。旧V4和原全片保留，未向B站或Toy投稿。请重点听两句是否顺、B的颜艺是否够惊讶。第三方动漫、日语录音授权仍未确认，技术报告不代表配音或喜剧效果已经通过用户审核。
''',extra_sources={'revision_of':'ep008-v4-accel','accepted_artifact':13153837962,'dialogue_changes':spec['dialogue_changes'],'new_voice_receipts':read(out/'new-voice-receipts.json'),'dialogue_art_sha256':sha(ROOT/'video_rush/paipai_dialogue_art.py'),'attack_recipe_unchanged':True,'score_cues':read(out/'music/cues.json'),'full_film_promoted':False})
