"""Package the continuous transition trial, without promoting it to a full film."""
import csv
import io
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from video_rush.common import ROOT, read, write, sha, run


def package(out):
    spec=read('episodes/ep008-v3-matchcut.json');p=read(out/'timeline.json')
    (out/'修改说明.md').write_text('''# 夜神月 → 日语波动拳：连续试剪

先看 light_to_hadouken_MATCHCUT.mp4（完整衔接），再看 hadouken_MATCH_ONLY.mp4（只看动作互切）。

旧版在“事情开始变得有趣了”之后，重新讨论反弹规则，打断了新招式的念头。新版删除这轮确认，恢复小学生本音，用“那……三格气呢？”和三指手势接起手。保留命中后的互怼。

旧版火柴人和原片各演一遍。新版按双手聚气、上身架势、喊招嘴部、面部、前景推掌五组对应镜头交替，原片时间顺序向前。一句日语“波動拳！”连续跨镜，不叠加中文喊声。深色背景减轻快速切换时的亮暗跳动，原片翻转朝向实机敌方；音乐峰值对准真实游戏发射。

火柴人为原创解释性动画；实机仍来自同一场真实连续对局，第8回合中波击碎低级反弹并造成伤害，没有改写结果。日语音效来自游戏仓库保存的街霸录音，动漫片段和该录音授权未确认。沿用配音、游戏音效和原创音乐主题，出处见 sources.json。

这次只验收连续衔接和动作互切，不是新版全片。旧版未覆盖，未向B站或Toy投稿。

手机审核：笑完之后想到三格气是否顺畅？日语喊招是否更带感？火柴人与原片是否像同一动作？切换是否过密？技术通过不代表观感通过。
''')
    pairs=[p['segments'][i:i+2] for i,s in enumerate(p['segments']) if s.get('match_phase') and s['kind']=='MATCH']
    canvas=Image.new('RGB',(960,len(pairs)*295),'#ddd');draw=ImageDraw.Draw(canvas)
    for row,pair in enumerate(pairs):
        for col,s in enumerate(pair):
            raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(s['seconds']*.5),'-i',str(out/'segments'/(s['id']+'.mp4')),'-frames:v','1','-f','image2pipe','-vcodec','png','-'])
            image=Image.open(io.BytesIO(raw));image.thumbnail((480,270));x=col*480;y=row*295;canvas.paste(image,(x,y));draw.text((x+5,y+272),s['kind']+' '+s['match_phase']+' '+s['id'],fill='black')
    canvas.save(out/'pose-match.png')
    with (out/'shot-list.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['id','start','duration','performer','phase','source_in','source'])
        for s in p['segments']:writer.writerow([s['id'],s['start'],s['seconds'],s['kind'],s.get('match_phase',s.get('mode',s.get('phase',''))),s.get('in',''),s.get('source','original stick animation')])
    head=run(['git','rev-parse','HEAD']).strip()
    write(out/'sources.json',{'git_head':head,'spec_sha256':sha(ROOT/'episodes/ep008-v3-matchcut.json'),'previous_artifact':spec['previous_review_artifact'],'previous_zip_sha256':spec['previous_review_zip_sha256'],'japanese_shout':spec['japanese_hadouken'],'new_bridge_voice':spec['bridge_voice'],'preserved_inputs':read(out/'portable/manifest.json'),'real_game_derivatives':read(out/'portable/game-bank.json'),'anime_and_soundfont_licenses':'licenses/; unchanged pinned V2 sources','rights_review':'third-party anime/shout not cleared; private review, no public submission','full_film_promoted':False})
    editable=out/'editable';editable.mkdir(exist_ok=True)
    run(['git','archive','--format=zip','--output',editable/'video-rush-project.zip','HEAD'])
    files=[*out.glob('*.md'),*out.glob('*.json'),*out.glob('*.csv'),*out.glob('*.ass'),*out.glob('*.png'),out/'light_to_hadouken_MATCHCUT.mp4',out/'hadouken_MATCH_ONLY.mp4',out/'extra/idea-bridge.m4a',out/'extra/hadouken-jp.m4a',*out.joinpath('portable').rglob('*'),*out.joinpath('licenses').rglob('*'),*editable.rglob('*'),*out.joinpath('logs').rglob('*')]
    write(out/'delivery-manifest.json',{str(f.relative_to(out)):sha(f) for f in sorted(set(files)) if f.is_file() and f.name!='delivery-manifest.json'})


if __name__=='__main__':package(ROOT/'build/episodes/ep008-v3-matchcut')
