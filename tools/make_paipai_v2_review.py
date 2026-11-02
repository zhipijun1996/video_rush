"""Audit V1 and render ONLY three V2 trials for user creative review.

There deliberately is no command to render a new full film. Existing movies,
scripts and voices are never overwritten by this review workflow.
"""
import argparse
import array
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave
import numpy as np
from video_rush.common import ROOT,read,write,sha,digest,duration,probe,run
from video_rush.narration import audio_metrics
from video_rush.render import ass_file
from video_rush.paipai_v2_art import render as act
from video_rush.paipai_v2_score import compose
from tools.make_paipai_film import pcm,validate_game_trace

OLD=ROOT/'build/episodes/ep008-r3'
CAPTURE=ROOT/'build/film-capture/ep008-r3'
REMOTE=ROOT/'build/deliveries/ep008-r3-remote/episodes/ep008-r3'


def audit(spec,out):
    baseline=ROOT/spec['baseline']
    if sha(baseline)!=spec['baseline_sha256']:raise ValueError('Baseline movie differs')
    previous=read(REMOTE/'storyboard.json');rows=[]
    for s in previous['shots']:
        for l in s['scheduled_lines']:
            rows.append({'type':'voice','shot':s['id'],'id':l['id'],'speaker':l['speaker'],'start':s['start']+l['start'],'end':s['start']+l['end'],'text':l['text'],'dry_source':str(OLD/'narration'/(l['id']+'.wav')),'source_status':'Previous production dry voice; baseline mix is the exact downloaded remote film'})
        for l in s['layers']:
            rows.append({'type':'native_game_sound' if l['layer']=='G' else 'anime_visual','shot':s['id'],'source':l['source'],'start':s['start']+l['at'],'end':s['start']+l['at']+l['seconds'],'source_in':l['in'],'source_out':l['out'],'source_truth':l['layer']})
    original=read('episodes/ep008-r3-film.json')
    flaws=[
        {'issue':'BGM arrangement does not follow the dramatic arc','evidence':'One fixed playground-battle-original.wav under all chapters; original soundtrack() primarily changes volume. Hero beam lacks a separate instrumental climax.','basis':'Inspected score and soundtrack code, not an independent human listening score'},
        {'issue':'Brief anime identity windows','evidence':'Light 0.45s inset; DIO 0.42s; first Street Fighter 0.30s apparition +0.48s full; Ultra 0.30s apparition +0.60s full.','basis':'Actual delivered storyboard layers'},
        {'issue':'Key shouts squeezed against old shot lengths','evidence':'4-02 fixed1.2s and5-04 fixed1.4s; flat speech rates generally +18% to +30%; no instruction-controlled acting backend.','basis':'Delivered narration receipts and renderer'},
        {'issue':'No smooth music duck release','evidence':'Previous envelope multiplies rectangular speech intervals, with few global style changes; abrupt BGM switches may be intentional jokes but ordinary dialogue needs a release ramp.','basis':'Actual original mix recipe; masking/aesthetics require user listening'},
        {'issue':'Source quotes and game voice can compete','evidence':'Native game includes copyrighted voice samples as well as effects. Previous magic quote already needed native gain0.2; new mix must similarly choose one foreground voice for each key shout.','basis':'Native audio manifest and actual source-window recipe'}
    ]
    p=subprocess.run(['ffmpeg','-hide_banner','-i',str(baseline),'-af','ebur128=peak=true','-vn','-f','null','-'],capture_output=True,text=True,check=True);(out/'audit-loudness.log').write_text(p.stderr)
    write(out/'sound-audit.json',{'baseline':str(baseline),'sha256':sha(baseline),'requested_filename':spec['requested_filename'],'requested_file_status':spec['requested_file_status'],'duration':duration(baseline),'tracks':rows,'findings':flaws,'audio_metrics':audio_metrics(baseline),'method':'Timeline/source inspection, decoded audio and loudness metering; no fabricated human listening approval'})
    with (out/'old-sound-timeline.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['type','shot','source_or_id','start','end','text']);w.writeheader()
        for r in rows:w.writerow({'type':r['type'],'shot':r['shot'],'source_or_id':r.get('id',r.get('source')),'start':r['start'],'end':r['end'],'text':r.get('text','')})
    cues=[
      (0,6,'成年疲惫','deadpan','80BPM，低音拨弦+稀疏木质音；主题只露两三个音','极轻进入；老板/宝宝和台词前景，断电处收音'),
      (6,8,'手机邀约','deadpan','同主题留白','手机叮后停配乐，让杯叮接棒'),
      (8,13.97,'老友重逢','warm','112BPM，尼龙吉他、钟琴，E大调主题','杯叮引入；两次拍手前抽掉旋律'),
      (13.97,16.87,'拍手回童年','battle','主题相同，改为164BPM复古方波与弹跳贝斯','拍手裸露，第二拍后加八分音符拾起'),
      (16.87,23.37,'小波与防御','battle','淘气街机律动，暂不用完整摇滚配器','连续律动，普通互怼时柔和侧链压低'),
      (23.37,29.57,'魔法筒','villain','低木管+减五度，五音主题变调','原片两句优先；吸收和反射使用真实游戏音效'),
      (29.57,38.3,'B规则宣言','villain','木管到弦乐渐强，给装腔和笑声留停顿','正义后急停；笑声尾音干切'),
      (38.3,45.3,'A夜神月失控','villain','嫌弃时干声；阴笑开始低音暗入，狂笑后短促上扬','清晰全屏原作表情；普通小孩吐槽到来前音乐硬停'),
      (45.3,49.67,'小孩互怼破功','battle','前半无配乐，后半同主题贝斯拾起','先让普通声线反差成立，再由拍手恢复主节奏'),
      (49.67,57.67,'三格气/首次波动拳','rock','176BPM，过载电吉他、贝斯、完整鼓组；五音主题第一次强奏','聚气鼓滚→原片蓝光→真实发射点崩出第一次高潮'),
      (57.67,62.5,'回小学生嚣张','battle','保留贝斯和鼓，收起主奏','台词前景，不能像新开一首歌'),
      (62.5,76.93,'AT与宇智波连续反转','battle','延续同一战斗主题，重击、90–160ms短留白','短停顿跟真实结算点走；不盖住破防/反弹音效'),
      (76.93,82.2,'五格气预告','villain','抽去主奏，保留紧张拨弦与低鼓','准备下一次跨番反转，不提前放英雄旋律'),
      (82.2,86.1,'DIO→奥特曼','heroic','DIO极简/静音，十字手势后铜管+弦乐，主题改为大调','我不做人了尾音→100–180ms留白→十字手势英雄配器炸开'),
      (86.1,93.6,'光线决胜与加冕','heroic','144BPM英雄主题，铜管、弦乐、定音鼓；强度高于首次波动拳','真实发射点全奏；到血量归零前不插普通吐槽'),
      (93.6,104.5,'回酒局与手机','warm','童年五音主题改尼龙吉他与轻木质节奏','杯叮切回；不使用煽情钢琴，不另开无关曲目'),
      (104.5,112.5,'两个老登与童年重影','reprise','轻盈大调再现，同一旋律与拍手节奏','笑声在前；标题最后350ms收尾')]
    with (out/'bgm-design.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['baseline_in','baseline_out','scene','arrangement','music','entry_exit','source','license']);w.writerows([(*c,'Video Rush新作《课间仍未结束》+FluidR3 GM','新作原创；采样音色库MIT，附原许可') for c in cues])
    md=['# 全片声音设计 · 审核版','',f"基准为上轮远端成片112.5秒，SHA `{sha(baseline)}`。工作区尚未收到1000061319.mp4，未冒称检查过该文件。下面是旧版时间锚点，试剪延长的表演将在用户审核后统一重排全片。",'', '统一旋律：E–G–A–B–E；结尾将G升半音，以同一轮廓做温暖大调再现。新作使用真实采样乐器离线编配，不是神经音乐生成器，也不是购买的商用曲库。','', '| 旧版时间 | 场景 | 配器/转场 |','|---|---|---|']
    md += [f'| {a:.2f}–{b:.2f}s | {scene} | {music}；{trans} |' for a,b,scene,style,music,trans in cues]
    md+=['','人声时配乐约压低8–12dB，攻击30ms、恢复220ms；高潮喊招保留鼓与低频冲击，主旋律适当避开人声频段。实际拟用混音在三个试剪中，自动技术检查不代表“足够好笑/帅气”。','', '素材：FluidR3 GM音色由Frank Wen、Toby Smithe制作，MIT；版权声明一同交付。动漫画面、另轨笑声和游戏自带作品录音的许可仍未确认，不因为重新混音而变成原创授权素材。']
    (out/'BGM设计表.md').write_text('\n'.join(md));return previous


def new_voice(out,id):
    portable=out/'portable/voices'/(id+'.m4a')
    return portable if portable.exists() else out/'voices'/(id+'.m4a')


def envelope(path,source_in=0,seconds=None):
    data=pcm(path,source_in,seconds);m=np.mean(data**2,axis=1);step=800
    return [float(np.sqrt(np.mean(m[i:i+step]))) for i in range(0,len(m),step)]


def segment(out,s):
    folder=out/'segments';folder.mkdir(exist_ok=True);target=folder/(s['id']+'.mp4');cache=target.with_suffix('.json')
    key=digest({'shot':s,'source_sha':sha(s['source']) if s.get('source') else None,'art':sha(ROOT/'video_rush/paipai_v2_art.py'),'recipe':1})
    if target.exists() and cache.exists() and read(cache).get('key')==key and read(cache)['sha256']==sha(target):return target
    if s['kind']=='R':act(target,s['mode'],s['seconds'],s.get('envelope'))
    else:
        if s['in']<0 or s['in']+s['seconds']>duration(s['source'])+.04:raise ValueError('Clip exceeds source')
        filt='setpts=PTS-STARTPTS'
        if s['kind']=='G' and not s.get('cropped'):filt+=',crop=1116:628:402:70'
        if s.get('flip'):filt+=',hflip'
        filt+=',scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xfaf5e8,setsar=1'
        if s.get('blue_out'):filt+=f",fade=t=out:st={s['seconds']-.1}:d=0.1:color=0x99eaff"
        if s.get('blue_in'):filt+=',fade=t=in:st=0:d=0.08:color=0x99eaff'
        run(['ffmpeg','-v','error','-y','-ss',s['in'],'-i',s['source'],'-t',s['seconds'],'-vf',filt,'-an','-r','30','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-color_range','tv',target],log=out/'logs'/(s['id']+'.log'),timeout=180)
    write(cache,{'key':key,'sha256':sha(target)});return target


def round_frame(t):return math.ceil(t*30)/30


def light_statement(out):
    """Find the spoken sentence after laughter; never use an unlabelled guess."""
    receipt=out/'alignments.json'
    if receipt.exists():return read(receipt)['K02-B']['statement_start']
    raise ValueError('Run audition alignment before composing the Light trial')


def plan_trials(spec,out):
    original=read('episodes/ep008-r3-film.json');refs=original['references']
    bank_path=out/'portable/game-bank.json';bank=read(bank_path) if bank_path.exists() else None
    trace=read(out/'portable/trace.json') if bank else read(CAPTURE/'trace.json');validate_game_trace(trace)
    trials=[]
    def trial(id,style):return {'id':id,'style':style,'segments':[],'voices':[],'effects':[],'seconds':0}
    def add(p,kind,seconds,**kwargs):
        if kind=='G' and bank:
            b=bank[str(kwargs['round'])];kwargs['source']=str(out/'portable'/b['file']);kwargs['in']-=b['source_in'];kwargs['cropped']=b.get('cropped',False)
        s={'id':p['id']+'-'+str(len(p['segments'])).zfill(2),'kind':kind,'seconds':round_frame(seconds),'start':p['seconds'],**kwargs};p['segments'].append(s);p['seconds']+=s['seconds'];return s
    def vo(p,id,at,text,source_in=0,seconds=None):
        path=new_voice(out,id);seconds=duration(path)-source_in if seconds is None else seconds
        p['voices'].append({'id':id,'path':str(path),'start':at,'source_in':source_in,'seconds':seconds,'text':text})
    # A: dislike -> grin -> clear original expressions -> moving R actor -> kid breaks the spell.
    p=trial('01_light','villain');n1=duration(new_voice(out,'N01-A'));add(p,'R',n1+.15,mode='light_disgust',envelope=envelope(new_voice(out,'N01-A')));vo(p,'N01-A',.04,'你动漫看傻了吧？')
    grin=p['seconds'];add(p,'R',.65,mode='light_grin');vo(p,'K02-B',grin+.10,'呵……',0,.45);p['anime_laugh_start']=p['seconds']
    add(p,'AN',1.0,source=str(ROOT/refs['light']['file']),**{'in':.9})
    add(p,'AN',2.8,source=str(ROOT/'build/research/ep008-v2/anime/light-laugh-maniac.mp4'),**{'in':0})
    statement=light_statement(out);spoken=duration(new_voice(out,'K02-B'))-statement
    begin=p['seconds'];add(p,'R',spoken+.15,mode='light_mad',envelope=envelope(new_voice(out,'K02-B'),statement));vo(p,'K02-B',begin,'事情……开始变得有趣了！！',statement)
    p['dry_break']=p['seconds'];b=duration(new_voice(out,'N02-B'));begin=p['seconds'];add(p,'R',b+.15,mode='light_break',envelope=envelope(new_voice(out,'N02-B')));vo(p,'N02-B',begin+.04,'你刚才不还骂我耍赖吗？')
    begin=p['seconds'];a=duration(new_voice(out,'N03-A'));add(p,'R',a+.1,mode='light_recover',envelope=envelope(new_voice(out,'N03-A')));vo(p,'N03-A',begin+.02,'少废话！反弹以后也算！')
    p['restore_battle']=begin;trials.append(p)
    # B: show the classic charge for long enough; trim only the native repeated
    # pre-launch hold. Actual projectile, break, hit and HP are not synthesized.
    p=trial('02_hadouken','rock')
    for number in (5,6,7):
        r=trace['rounds'][number-1];add(p,'G',.20,source=str(CAPTURE/'continuous.mp4'),**{'in':r['commit']-.05},round=number)
    begin=p['seconds'];add(p,'R',2.65,mode='hadoken_three');vo(p,'old-4-01-0',begin+.04,'一格能放波——那三格呢？');vo(p,'old-4-01-1',begin+1.95,'哈？！')
    add(p,'R',.80,mode='hadoken_charge');add(p,'AN',2.5,source=str(ROOT/refs['street']['file']),**{'in':191.65},flip=True,blue_out=True)
    r=trace['rounds'][7];start=p['seconds'];g=add(p,'G',r['commit']+.30-(r['launch']-.12),source=str(CAPTURE/'continuous.mp4'),**{'in':r['launch']-.12},round=8,blue_in=True);p['peak_at']=start+.12
    v=duration(new_voice(out,'K03-B'));vo(p,'K03-B',max(.15,p['peak_at']+.22-v),'波——动——拳！！！')
    begin=p['seconds'];p['boast_start']=begin
    # The supporting reply stays exactly as approved. Voice assets are a
    # separately verified old-role copy, not claimed as newly acted candidates.
    for id,text,mode in [('old-4-04-0','喂！我的反弹呢？！','hadoken_reply'),('old-4-04-1','三格气！你那一格的反弹接得住吗？！','hadoken_boast')]:
        begin=p['seconds'];add(p,'R',duration(new_voice(out,id))+.10,mode=mode,envelope=envelope(new_voice(out,id)));vo(p,id,begin+.02,text)
    trials.append(p)
    # C: no neutral-standing reset between DIO and the cross-arms reveal.
    p=trial('03_dio_ultra','heroic');add(p,'R',.95,mode='dio_setup');vo(p,'old-5-03-0',.02,'宇智波反弹！')
    begin=p['seconds'];v=duration(new_voice(out,'K04-B'));opening=max(.8,v-2.30+.12);add(p,'R',opening,mode='dio_face',envelope=envelope(new_voice(out,'K04-B')));add(p,'AN',2.30,source=str(ROOT/refs['dio']['file']),**{'in':.05});vo(p,'K04-B',begin+.02,'我不做人了！！！');p['hero_entry']=p['seconds']
    v=duration(new_voice(out,'K05-A'));cross=max(.60,v-2.5);add(p,'R',cross,mode='ultra_cross',envelope=envelope(new_voice(out,'K05-A')));add(p,'AN',1.40,source=str(ROOT/refs['ultra']['file']),**{'in':65.0},flip=True,blue_out=True)
    r=trace['rounds'][20];start=p['seconds'];add(p,'G',r['commit']+1.12-(r['launch']-.12),source=str(CAPTURE/'continuous.mp4'),**{'in':r['launch']-.12},round=21,blue_in=True);p['peak_at']=start+.12
    vo(p,'K05-A',p['hero_entry']+.10,'斯派修姆——光线！！！');p['seconds']=max(p['seconds'],max(x['start']+x['seconds'] for x in p['voices'])+.05)
    if p['seconds']>sum(s['seconds'] for s in p['segments'])+.04:raise ValueError('Hero line exceeds complete native victory window; do not silently freeze or loop gameplay')
    trials.append(p)
    return trials


def mix_trial(p,spec,out):
    sr=24000;mix=np.zeros((math.ceil(p['seconds']*sr),2),np.float32);voice_ranges=[]
    def add(a,start,gain=1):
        pos=round(start*sr);n=min(len(a),len(mix)-pos)
        if n>0:mix[pos:pos+n]+=a[:n]*gain
    for v in p['voices']:
        add(pcm(v['path'],v['source_in'],v['seconds']),v['start']);voice_ranges.append((v['start'],v['start']+v['seconds']))
    for s in p['segments']:
        if s['kind']=='G':
            fx=pcm(s['source'],s['in'],s['seconds']);gain=np.full(len(fx),.75,dtype=np.float32)
            for start,end in voice_ranges:
                a=max(0,round((start-s['start'])*sr));b=min(len(gain),round((end-s['start'])*sr))
                if b>a:
                    gain[a:b]=np.minimum(gain[a:b],.36)
                    release=min(len(gain),b+round(.12*sr));gain[b:release]=np.minimum(gain[b:release],np.linspace(.36,.75,release-b))
            add(fx*gain[:,None],s['start'])
    # Only original game's recording/samples supply action SFX.
    project=ROOT/'build/recordings/wave-film-c6f1326c824a'
    charge=out/'portable/game/charge.m4a' if (out/'portable/game/charge.m4a').exists() else project/'assets/audio/charge.wav'
    if charge.exists() and p['id']!='01_light':add(pcm(charge),.05,.32)
    if p['id']=='01_light':
        laugh=ROOT/read('episodes/ep008-r3-film.json')['references']['evil_laugh']['file'];add(pcm(laugh,0,3.8),p['anime_laugh_start'],.60);voice_ranges.append((p['anime_laugh_start'],p['anime_laugh_start']+3.8))
    score=out/'music'/(p['id']+'.wav');compose(score,ROOT/spec['music']['soundfont_path'],p['style'],p['seconds'],p.get('peak_at'))
    music=pcm(score);env=np.full(len(mix),.33,dtype=np.float32)
    # Gain automation has bounded attack/release and explicit story silences.
    for start,end in voice_ranges:
        a,b=max(0,round(start*sr)),min(len(env),round(end*sr));env[a:b]*=.28
        attack=max(0,a-round(.03*sr));env[attack:a]=np.minimum(env[attack:a],np.linspace(.33,.33*.28,a-attack))
        end_release=min(len(env),b+round(.22*sr));env[b:end_release]=np.minimum(env[b:end_release],np.linspace(.33*.28,.33,end_release-b))
    if p['id']=='01_light':
        start=round(p['anime_laugh_start']*sr);env[:start]=0;stop=round(p['dry_break']*sr);restore=round(p['restore_battle']*sr);env[max(0,stop-round(.10*sr)):restore]=0
        reprise=out/'music'/'01_light-battle-return.wav';compose(reprise,ROOT/spec['music']['soundfont_path'],'battle',max(.3,p['seconds']-p['restore_battle']))
        add(pcm(reprise),p['restore_battle'],.07)
    if p['id']=='03_dio_ultra':
        entry=round(p['hero_entry']*sr);env[:entry]=0
        n=min(round(.22*sr),len(env)-entry);env[entry:entry+n]*=np.linspace(0,1,n)
        dark=out/'music'/'03_dio-villain-before-cut.wav';compose(dark,ROOT/spec['music']['soundfont_path'],'villain',max(.2,p['hero_entry']-.18));add(pcm(dark),0,.04)
    add(music[:len(mix)]*env[:len(music),None],0)
    path=out/'audio'/(p['id']+'.wav');path.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(sr),'-ac','2','-i','-','-c:a','pcm_f32le',str(path)],input=mix.astype('<f4').tobytes(),check=True)
    return path


def render_trial(p,spec,out):
    files=[segment(out,s) for s in p['segments']];concat=out/(p['id']+'-concat.txt');concat.write_text(''.join("file '"+str(f)+"'\n" for f in files));joined=out/(p['id']+'-joined.mp4')
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',concat,'-c','copy',joined],log=out/'logs'/(p['id']+'-join.log'))
    audio=mix_trial(p,spec,out);captions=[]
    for v in p['voices']:captions.append({'start':v['start'],'end':v['start']+v['seconds'],'cues':[{'start':v['start'],'end':v['start']+v['seconds'],'text':v['text']}],'provenance_label':'','emphasis':''})
    ass=out/(p['id']+'.ass');ass_file(ass,{'display_chapters':False,'shots':captions});target=out/(p['id']+'_NEW.mp4')
    run(['ffmpeg','-v','error','-y','-reinit_filter','0','-i',joined,'-i',audio,'-filter_complex',f'[0:v]setpts=PTS-STARTPTS,ass={ass},fps=30,format=yuv420p[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=14,aresample=48000[a]','-map','[v]','-map','[a]','-t',p['seconds'],'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',target],log=out/'logs'/(p['id']+'-render.log'),timeout=300)
    run(['ffmpeg','-v','error','-i',target,'-f','null','-'],log=out/'logs'/(p['id']+'-decode.log'),timeout=180)
    from tools.make_wave_story import verify_final_shots
    frame_checks=verify_final_shots(target,p['segments'],out/'segments');write(out/(p['id']+'-frame-checks.json'),frame_checks)
    if not all(c['passed'] for c in frame_checks):raise ValueError('A review shot disappeared during composition')
    info=probe(target);v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio');metrics=audio_metrics(target)
    if not ((v['width'],v['height'])==(1920,1080) and v['avg_frame_rate']=='30/1' and v['codec_name']=='h264' and a['codec_name']=='aac' and metrics['audible_signal'] and metrics['clipped_fraction']<.0001):raise ValueError('Trial media validation failed')
    return {'file':target.name,'seconds':duration(target),'sha256':sha(target),'full_decode':True,'all_planned_shots_survive':True,'audio':metrics,'acting_humor_and_impact':'pending human review'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',default='episodes/ep008-v2-av-review.json');p.add_argument('--output',default='build/episodes/ep008-v2-review');p.add_argument('--stage',choices=['audit','clips'],default='clips');a=p.parse_args();spec=read(a.spec);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    if out in (OLD.resolve(),REMOTE.resolve()):raise ValueError('Review must use an independent output folder')
    audit(spec,out)
    if a.stage=='audit':return
    trials=plan_trials(spec,out);validate_trials(trials);write(out/'trial-timelines.json',trials);reports=[]
    for trial in trials:reports.append(render_trial(trial,spec,out));print('TRIAL READY',reports[-1],flush=True)
    if sha(ROOT/spec['baseline'])!=spec['baseline_sha256']:raise ValueError('Baseline was altered')
    write(out/'report.json',{'scope':'Only three trials; full film intentionally not rendered','trials':reports,'status':'technical_checks_pass_pending_user_direction','baseline_sha256':spec['baseline_sha256'],'no_full_film':not (out/'final.mp4').exists(),'no_bilibili_or_toy_submission':True})


def validate_trials(trials):
    if {t['id'] for t in trials}!={'01_light','02_hadouken','03_dio_ultra'}:raise ValueError('Exactly the three approved trials are expected')
    for t in trials:
        voices=sorted(t['voices'],key=lambda v:v['start'])
        for v in voices:
            if v['start']<0 or v['start']+v['seconds']>t['seconds']+.04:raise ValueError('Speech outside trial')
        if any(a['start']+a['seconds']>b['start']+.03 for a,b in zip(voices,voices[1:])):raise ValueError('Overlapping foreground character lines')
        if abs(sum(s['seconds'] for s in t['segments'])-t['seconds'])>.04:raise ValueError('Visual timeline gap')


if __name__=='__main__':main()
