"""Execute the user's complete 2026-11-02 screenplay with traceable R/AN/G layers."""
import argparse
import array
import csv
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

from video_rush.common import ROOT,read,write,run,sha,duration,probe,digest
from video_rush.narration import narrate,audio_metrics
from video_rush.paipai_film_art import render as draw_scene,image as draw_frame
from video_rush.render import ass_file,ass_time
from tools.make_wave_story import verify_final_shots

CAPTURE=ROOT/'build/film-capture/ep008-r3'


def validate_game_trace(trace):
    rounds=trace['rounds']
    if len(rounds)!=21:raise ValueError('The approved film needs one complete 21-round battle')
    if any(rounds[i]['result']['next']!=rounds[i+1]['initial'] for i in range(20)):
        raise ValueError('Discontinuous HP/energy: resource injection or missing battle round')
    returned=rounds[14]['result'];last=rounds[20]
    if returned['actions']!=['reflect2','wave2'] or returned['damage']!=[0,2]:
        raise ValueError('A must return B medium wave, not the opposite direction')
    if (last['initial']['players'][0]['energy']<5 or last['initial']['players'][1]['energy']<2
            or last['initial']['players'][1]['hp']>3 or last['result']['actions']!=['wave3','reflect2']
            or last['result']['winner']!=0):
        raise ValueError('Final beam must be legal and actually win against B reflection')


def plan(spec,voices):
    trace=read(CAPTURE/'trace.json');validate_game_trace(trace);mobile=read(CAPTURE/'mobile-trace.json');rounds=trace['rounds'];shots=[];clock=0
    for original in spec['shots']:
        s={**original};s['scheduled_lines']=[];id=s['id'];cursor=.06
        if s.get('game_first') and not s.get('first_two_on_game'):cursor=s['game_first']+.04
        if id=='1-03':cursor=.30
        for i,line in enumerate(s['lines']):
            v=voices[f'{id}-{i}']
            if id=='4-07' and i==2:cursor=max(cursor,3.25)
            s['scheduled_lines'].append({**line,'id':f'{id}-{i}','start':cursor,'end':cursor+v['duration']})
            cursor+=v['duration']+(.28 if i==0 and id=='3-04C' else .045)
        seconds=max(s['seconds'],cursor+.06)
        if id=='4-02':seconds=1.2  # shout tail crosses the blue-light hand-off
        if id=='5-04':seconds=1.4  # same voice continuity into the real beam cut-in
        if id=='5-06':seconds=max(s['seconds'],cursor-.22)  # one utterance's tail bridges into adulthood
        seconds=math.ceil(seconds*30)/30;s.update(seconds=seconds,start=clock,end=clock+seconds,layers=[])
        shots.append(s);clock+=seconds
    def game(s,round_number,kind='whole',at=0,seconds=None):
        r=rounds[round_number-1]
        if kind=='charge':a=r['commit']-.12;b=r['commit']+.14
        elif kind=='launch':a=r['launch']-.10;b=r['commit']+.23
        elif kind=='clap':a=r['start'];b=a+(seconds or .65)
        else:a=r['reveal']-.025;b=r['commit']+(.55 if round_number==21 else .23)
        if seconds:b=a+seconds
        s['layers'].append({'layer':'G','source':'game','in':a,'out':b,'at':at,'seconds':b-a,'round':round_number,'kind':kind,'initial':r['initial'],'result':r['result']})
    for s in shots:
        id=s['id'];n=s['seconds']
        if id=='3-01':game(s,1,'charge',0);game(s,2,'launch',.29)
        if id=='3-02':game(s,3,'charge',0)
        if id=='3-03':game(s,4,'whole',4.60)
        if id=='4-01':
            for i,r in enumerate([5,6,7]):game(s,r,'charge',i*.2,seconds=.2)
        if id=='4-03':game(s,8,'whole',0)
        if id=='4-05':game(s,12,'whole',0)
        if id=='4-07':game(s,15,'whole',0)
        if id=='5-02':
            for i,r in enumerate([16,17,18,19,20]):game(s,r,'charge',i*.27,seconds=.25)
        if id=='5-03':game(s,21,'whole',0,seconds=.30)
        if id=='5-05':game(s,21,'whole',0)
        if id=='5-06':
            a=rounds[20]['commit']+.55;s['layers'].append({'layer':'G','source':'game','in':a,'out':a+.6,'at':0,'seconds':.6,'round':21,'kind':'victory'})
        if id=='6-04':
            s['layers'].append({'layer':'G','source':'mobile','in':.38,'out':mobile['battle']-.03,'at':.35,'seconds':mobile['battle']-.41,'rect':[1282,82,412,890],'kind':'phone-home'})
        if id=='7-01':
            a=mobile['battle'];s['layers'].append({'layer':'G','source':'mobile','in':a,'out':a+.62,'at':0,'seconds':.62,'kind':'mobile-arena'})
        if id=='7-02':
            a=mobile['battle']+.62;s['layers'].append({'layer':'G','source':'mobile','in':a,'out':a+min(n,3.4),'at':0,'seconds':min(n,3.4),'rect':[1401,627,54,116],'kind':'handset'})
        def an(ref,source_in,seconds,at,**extra):s['layers'].append({'layer':'AN','source':ref,'in':source_in,'out':source_in+seconds,'at':at,'seconds':seconds,**extra})
        if id=='3-03':an('sore',155.4,.55,1.00);an('cylinder',39.0,.55,4.00)
        if id=='3-04C':an('light',1.0,.45,s['scheduled_lines'][1]['start']+.35,alpha=.72,rect=[320,235,470,420],crop=[.4,0,.3,.65])
        if id=='4-02':
            an('street',191.6,.30,.25,alpha=.55,rect=[260,340,720,500]);an('street',193.95,.48,.72)
        if id=='4-05':an('eva',6.6,.45,2.20,alpha=.70,rect=[1160,415,510,510],crop=[.36,.1,.28,.65])
        if id=='4-07':an('naruto',18.1,.50,1.78,flip=True,alpha=.75,rect=[60,130,1040,650])
        if id=='5-03':an('dio',.05,.42,max(.8,n-.58))
        if id=='5-04':
            an('ultra',65.2,.30,.25,alpha=.65,rect=[250,290,800,520]);an('ultra',65.55,.60,.80)
        if id=='5-06':an('jotaro',.15,.25,.61)
        # When a complete attack is playing it stays visible through the hit.
        for layer in s['layers']:
            if layer['at']+layer['seconds']>s['seconds']+.04:
                s['seconds']=math.ceil((layer['at']+layer['seconds'])*30)/30
    clock=0
    for s in shots:s['start']=clock;s['end']=clock+s['seconds'];clock=s['end']
    return {'duration':clock,'shots':shots,'capture':trace,'mobile':mobile}


def pcm(path,offset=0,seconds=None,rate=1,pitch=1):
    import numpy as np
    args=['ffmpeg','-v','error','-ss',str(offset),'-i',str(path)]
    if seconds is not None:args+=['-t',str(seconds)]
    filters=[]
    if pitch!=1:filters+=[f'aresample=24000,asetrate=24000*{pitch},aresample=24000,atempo={1/pitch}']
    if rate!=1:filters+=[f'atempo={rate}']
    if filters:args+=['-af',','.join(filters)]
    args+=['-ar','24000','-ac','2','-f','f32le','-']
    return np.frombuffer(subprocess.check_output(args),dtype='<f4').reshape(-1,2).copy()


def soundtrack(project,spec,voices,out):
    import numpy as np
    sr=24000;seconds=project['duration'];mix=np.zeros((math.ceil(seconds*sr),2),dtype=np.float32);sources=[]
    def add(data,start,gain=1):
        at=round(start*sr);n=min(len(data),len(mix)-at)
        if n>0:mix[at:at+n]+=data[:n]*gain
    def tone(length,hz,gain=.2):
        t=np.arange(round(length*sr))/sr;v=np.sin(2*np.pi*hz*t)*np.exp(-t*10)*gain;return np.stack([v,v],axis=1).astype('float32')
    for s in project['shots']:
        start=s['start'];id=s['id']
        for line in s['scheduled_lines']:
            path=out/'narration'/(line['id']+'.wav');voice=pcm(path)
            if line['id']=='5-06-1':
                # The same single utterance ages across the time cut; no replay.
                adult_tail=pcm(path,pitch=.88);n=min(len(voice),len(adult_tail));ramp=np.clip((np.arange(n)-(n-.40*sr))/(.40*sr),0,1)
                voice[:n]=voice[:n]*(1-ramp[:,None])+adult_tail[:n]*ramp[:,None]
            add(voice,start+line['start'],.83 if line['speaker'].startswith('adult') else .95)
        for l in s['layers']:
            if l['layer']!='G':continue
            path=CAPTURE/('continuous.mp4' if l['source']=='game' else 'mobile.mp4');a=pcm(path,l['in'],l['out']-l['in'])
            gain=1.05
            if id=='3-03':gain*=.20  # one foreground trap-card quote; native sample would duplicate it
            if id in ('4-03','4-07','5-05') and l['source']=='game':
                # Keep the actual launch/impact sound, suppress only the duplicate
                # Japanese voice during the game's separate pre-launch cut-in.
                r=project['capture']['rounds'][l['round']-1];before=max(0,r['launch']-l['in']);a[:round(before*sr)]*=.10
            if s['scheduled_lines']:gain*=.45
            add(a,start+l['at'],gain)
        effect=s.get('sfx')
        if effect in ('clap2','clap-end'):
            r=project['capture']['rounds'][0];a=pcm(CAPTURE/'continuous.mp4',r['start'],1.12 if effect=='clap2' else .20)
            add(a,start+.02,.85)
        if effect=='ding':add(tone(.35,1900,.18)+tone(.35,2837,.10),start+.02)
        if effect=='poweroff':
            for k,hz in enumerate([880,550,220]):add(tone(.16,hz,.15),start+.05+k*.10)
        if effect in ('baby','gibberish'):
            t=np.arange(round(s['seconds']*sr))/sr
            if effect=='baby':
                phase=2*np.pi*(500*t+80*np.sin(2*np.pi*2.6*t)/(2*np.pi*2.6));v=(np.sin(phase)+.35*np.sin(phase*2))*(.5+.5*np.sin(2*np.pi*3*t))*.10
            else:v=(np.sin(2*np.pi*(180*t+4*np.sin(t*50)))+.4*np.sin(2*np.pi*540*t))*(np.sin(2*np.pi*17*t)>0)*.12
            add(np.stack([v,v],axis=1),start)
        if effect=='bell':
            a=tone(.7,2200,.12)+tone(.7,3103,.07);add(a,start+.70)
        if id in ('3-04D','4-02','4-06','5-03'):
            first=project['capture']['rounds'][0];at=start if id!='3-04D' else s['end']-.70
            add(pcm(CAPTURE/'continuous.mp4',first['start'],1.12),at,.65)
        if id=='3-03':
            for ref,a,b,at in [('sore',154.50,157.30,.10),('cylinder',37.95,40.75,2.95)]:
                add(pcm(ROOT/spec['references'][ref]['file'],a,b-a),start+at,.70);sources.append({'id':id,'source':ref,'in':a,'out':b,'at':start+at,'layer':'AN audio'})
        if id=='3-04B' and 'evil_laugh' in spec['references']:
            add(pcm(ROOT/spec['references']['evil_laugh']['file'],0,.7),s['end']-.7,.42)
        if id in ('7-03','7-04'):
            # Synthesized character laughter, explicitly not a real reunion recording.
            pass
    # Two real synthesized voice performances for the warm ending, layered by age.
    laugh_start=next(s['start'] for s in project['shots'] if s['id']=='7-03')-.18
    for label,voice,at,gain in [('adult','zh-CN-YunxiNeural',0,.35),('child','zh-CN-YunxiaNeural',.35,.20)]:
        path=out/'narration'/('ending-laugh-'+label+'.wav');narrate('哈哈，哈哈哈。',path,voice=voice,rate='+2%');add(pcm(path),laugh_start+at,gain)
    score=ROOT/'build/music/playground-battle-original.wav'
    if not score.exists():run(['python','tools/make_playground_score.py'],timeout=120)
    music=pcm(score,0,seconds);env=np.full(len(mix),.12,dtype=np.float32)
    end_start=next(s['start'] for s in project['shots'] if s['id']=='7-01')
    for s in project['shots']:
        a,b=round(s['start']*sr),round(s['end']*sr)
        if s['id'].startswith(('1','2','6')):env[a:b]=.025
        if s['id']=='3-04C':env[a:round((s['start']+s['scheduled_lines'][1]['start'])*sr)]=0
        if s['id']=='3-04B':env[b-round(.08*sr):b]=0
        for line in s['scheduled_lines']:
            x,y=round((s['start']+line['start'])*sr),round((s['start']+line['end']+.08)*sr);env[x:y]*=.45
    tail=round(end_start*sr);env[tail:]=np.linspace(.08,.015,len(env)-tail)
    add(music[:len(mix)]*env[:len(music),None],0)
    t=np.arange(len(mix)-tail)/sr;warm=np.zeros_like(t)
    for hz in [196,246.94,293.66,392]:warm+=np.sin(2*np.pi*hz*t)*.009
    warm*=np.minimum(1,t/.5)*np.minimum(1,np.maximum(0,seconds-end_start-t)/.4)
    add(np.stack([warm,warm],axis=1),end_start)
    f=out/'source-mix.wav';subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','24000','-ac','2','-i','-','-c:a','pcm_f32le',str(f)],input=mix.astype('<f4').tobytes(),check=True)
    write(out/'audio-sources.json',{'anime_audio':sources,'native_game_audio':'Extracted from the same recorded source windows as visible G layers; duplicate pre-launch voices ducked under Chinese shouts. Actual effects retained.','original_sfx':['Boss cartoon gibberish','Cartoon baby cry','glass ding','power-off tones','school bell'],'ending_laugh':'Real Edge TTS character performances, not recordings of real people or a real reunion.','child_to_adult_bridge':'One synthesized utterance only. Final 0.40s crossfades to pitch 0.88 with duration preserved, aging the same tail across 5-06 → 6-01.'});return f


def captions(project,voices,out):
    from video_rush.subtitles import narration_cues
    rows=[];ass=[]
    for s in project['shots']:
        cues=[]
        for l in s['scheduled_lines']:
            v=voices[l['id']];path=out/'narration'/(l['id']+'-source.raw.boundaries.jsonl');bounds=[]
            if path.exists():
                for line in path.read_text().splitlines():
                    b=json.loads(line)
                    if b.get('type')=='SentenceBoundary':
                        b['offset']=max(0,b['offset']-v['trim_start']*1e7);bounds.append(b)
            c,method=narration_cues(l['text'],bounds,s['start']+l['start'],v['duration'],1)
            cues+=c;rows+=c
        if s['id']=='3-03':
            c=[{'start':s['start']+.1,'end':s['start']+2.90,'text':'那可不一定。'},{'start':s['start']+2.95,'end':s['start']+5.75,'text':'陷阱发动——魔法筒！'}];cues+=c;rows+=c
        ass.append({'start':s['start'],'end':s['end'],'cues':cues,'provenance_label':'','emphasis':''})
    ass_file(out/'subtitles.ass',{'display_chapters':False,'shots':ass})
    def stamp(t):
        n=round(t*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
    rows.sort(key=lambda x:x['start']);(out/'subtitles.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i,c in enumerate(rows))+'\n')
    if any(c['start']<0 or c['end']>project['duration']+.03 for c in rows):raise ValueError('Subtitle outside movie')
    return rows


def render(spec,out,voices,structure=False):
    for name,ref in spec['references'].items():
        if sha(ROOT/ref['file'])!=ref['sha256']:raise ValueError('Reference SHA changed: '+name)
    receipt=read(CAPTURE/'receipt.json');mobile=read(CAPTURE/'mobile-receipt.json')
    if receipt['recipe']['commit']!=spec['source_commit'] or receipt['sha256']!=sha(CAPTURE/'continuous.mp4') or receipt['trace_sha256']!=sha(CAPTURE/'trace.json'):
        raise ValueError('Game source or capture changed')
    if mobile['sha256']!=sha(CAPTURE/'mobile.mp4') or mobile['trace_sha256']!=sha(CAPTURE/'mobile-trace.json'):
        raise ValueError('Mobile capture changed')
    project=plan(spec,voices);write(out/'storyboard.json',project)
    for folder in ['r-animation','segments','logs','recording-evidence']:(out/folder).mkdir(exist_ok=True)
    for s in project['shots']:
        visual_shot(s,spec,out,structure);print('Rendered',s['id'],round(s['seconds'],2),flush=True)
    soundtrack_path=soundtrack(project,spec,voices,out);cues=captions(project,voices,out)
    concat=out/'segments.txt';suffix='.structure' if structure else ''
    concat.write_text(''.join(f"file 'segments/{s['id']}{suffix}.mp4'\nduration {s['seconds']}\n" for s in project['shots']))
    joined=out/'joined.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',concat,'-c','copy',joined],log=out/'logs/join.log')
    final=out/('structure.mp4' if structure else 'final.mp4')
    run(['ffmpeg','-v','error','-y','-reinit_filter','0','-i',joined,'-i',soundtrack_path,'-filter_complex',
         f'[0:v]setpts=PTS-STARTPTS,ass={out/"subtitles.ass"},fps=30,format=yuv420p[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=10,aresample=48000[a]',
         '-map','[v]','-map','[a]','-t',project['duration'],'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-color_range','tv',
         '-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',final],log=out/'logs/final.log',timeout=900)
    run(['ffmpeg','-v','error','-i',final,'-f','null','-'],log=out/'logs/decode.log',timeout=180)
    if structure:print('STRUCTURE READY',final,project['duration']);return
    checks=verify_final_shots(final,[{**s,'id':s['id']} for s in project['shots']],out/'segments');write(out/'frame-checks.json',checks)
    if not all(c['passed'] for c in checks):raise ValueError('Final shot verification failed')
    details=[]
    def pixels(path,at,rect):
        x,y,w,h=rect
        return subprocess.check_output(['ffmpeg','-v','error','-ss',str(max(0,at)),'-i',str(path),'-frames:v','1','-vf',f'crop={w}:{h}:{x}:{y},scale=64:48','-pix_fmt','rgb24','-f','rawvideo','-'])
    for s in project['shots']:
        for l in s['layers']:
            if l['layer']!='AN':continue
            rect=l.get('rect',[0,0,1920,900]);t=l['at']+l['seconds']*.5;actual=pixels(final,s['start']+t,rect);errors=[]
            for delta in (0,-1/30,1/30):
                expected=pixels(out/'segments'/(s['id']+'.mp4'),t+delta,rect)
                errors.append(sum(abs(a-b) for a,b in zip(actual,expected))/len(actual) if len(actual)==len(expected)>0 else 255)
            details.append({'shot':s['id'],'reference':l['source'],'timeline_sample':s['start']+t,'mean_absolute_error':min(errors),'passed':min(errors)<18})
    write(out/'anime-layer-checks.json',details)
    if not all(d['passed'] for d in details):raise ValueError('A short anime layer disappeared from the joined film')
    deliver(spec,project,voices,cues,final,out)


def deliver(spec,project,voices,cues,final,out):
    """Keep editable sources and distinguish measured checks from phone review."""
    from PIL import Image,ImageDraw,ImageFont
    from video_rush.common import font
    evidence=out/'recording-evidence';evidence.mkdir(exist_ok=True)
    for name in ['receipt.json','trace.json','mobile-receipt.json','mobile-trace.json']:
        shutil.copyfile(CAPTURE/name,evidence/name)
    audio_manifest=run(['git','-C',ROOT/'build/sources/wave-game','show',spec['source_commit']+':data/audio-manifest.json'])
    (evidence/'game-native-audio-manifest.json').write_text(audio_manifest)
    shutil.copyfile(ROOT/spec['brief'],out/'approved-storyboard.md')
    write(out/'edit-project.json',{'spec':spec,'timeline':project,'rebuild':'python -m tools.make_paipai_film','coordinates':'1920x1080, seconds, source in/out; R baseline and replaceable AN/G overlays','editable_code':['tools/make_paipai_film.py','video_rush/paipai_film_art.py']})
    with (out/'shot-list.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['shot_id','source','in','out','layer','dialogue','sfx','transition','notes']);w.writeheader()
        for s in project['shots']:
            w.writerow(dict(shot_id=s['id'],source='Original stick animation: '+s['scene'],**{'in':0,'out':s['seconds']},layer='R',dialogue=' / '.join(l['text'] for l in s['lines']),sfx=s.get('sfx',''),transition='Hand/pose/sound match or hard cut; see approved storyboard',notes=f"Timeline {s['start']:.3f}–{s['end']:.3f}"))
            for l in s['layers']:
                ref=spec['references'].get(l['source'],{});w.writerow(dict(shot_id=s['id'],source=ref.get('page',str(CAPTURE/('mobile.mp4' if l['source']=='mobile' else 'continuous.mp4'))),**{'in':l['in'],'out':l['out']},layer=l['layer'],dialogue='',sfx='native game audio' if l['layer']=='G' else 'muted except documented quote',transition='overlay' if l.get('rect') or l.get('alpha') else 'hard cut',notes=json.dumps(l,ensure_ascii=False)))
    script=['# 拍拍波 · 新分镜 v1 执行稿','',f"主片 {project['duration']:.2f} 秒。对白来自用户确认稿；游戏镜头为指定版本重新运行录制。",'']
    for s in project['shots']:
        script+= [f"## {s['id']} · {s['start']:.2f}–{s['end']:.2f} 秒",'']+[l['speaker']+'：'+l['text'] for l in s['lines']]+['']
    (out/'script.md').write_text('\n'.join(script))
    sources={'brief':{'file':spec['brief'],'sha256':sha(ROOT/spec['brief'])},'game':{'repository':'https://github.com/zhipijun1996/wave-game','commit':spec['source_commit'],'truth':project['capture']['truth'],'recording':'continuous legal single-player battle; opponent choices scripted before simultaneous selection; no mid-battle state injection'},'mobile':project['mobile']['truth'],'references':{k:{**v,'actual_sha256':sha(ROOT/v['file']),'rights_status':v.get('rights','Copyrighted anime excerpt/repost; original redistribution permission unconfirmed')} for k,v in spec['references'].items()},'originals':{'animation':'Video Rush original procedural stick animation, MIT','music':'Original procedural score, MIT, no samples','font':'Noto Sans CJK, SIL OFL 1.1'},'narration':'47 actual Edge TTS utterances plus generated ending laughter; not original actors or real childhood audio','review':'Private review package; no Bilibili/Toy publication performed. Third-party sources remain replaceable.'}
    sources['originals']['animation']='Video Rush original procedural stick animation, generated for this film; no external drawings'
    sources['game']['native_sound_rights']='Native game contains work recordings as well as original effects; see recording-evidence/game-native-audio-manifest.json; do not assume all native audio is cleared.'
    sources['production']={'repository':'https://github.com/zhipijun1996/video_rush','git_head':run(['git','rev-parse','HEAD']).strip(),'recipe_sha256':{p:sha(ROOT/p) for p in ['tools/make_paipai_film.py','video_rush/paipai_film_art.py','tools/capture_wave_film.py','episodes/ep008-r3-film.json']}}
    write(out/'sources.json',sources)
    (out/'changes.md').write_text('''# 相对确认分镜的执行微调

- 以用户上传的完整 v1.0 为唯一剧情依据，不增加训练、额外对战或说教片尾。
- 时长按实际47句配音和完整命中镜头调整；对白保留，不为卡秒砍对白。
- 三格、五格蓄气使用同一场合法对局的真实跳切；中间相同蓄气轮不逐轮播放。
- 小波反弹只伤血不判整局输；A反弹B的中波；五格光线破B二级反弹，真实血量归零。
- 动漫采用短闪/透明叠影，原音只保留游戏王两句及短笑声；碰撞、伤害和胜负用实机。
- 两人故事是火柴人叙事；实际产品录屏为单机与AI，并未宣称已有联网双人。
- 小学生B的“你就赢这一把”只合成一次，尾音跨到成年镜头。结尾无初心/童心旁白。
- 另附 short-tail.mp4：仅省去7-03重影段；主片完整保留七章。
- 原动画素材存在转载字幕/画质差异，未伪称无水印授权原盘。版权及用户审美审核仍待确认。
''')
    title=spec['title'];(out/'bilibili.md').write_text(f'''# 标题

{title}

# 简介

“你还记不记得，你以前是拍拍波大王？”
小学课间口胡出来的波动拳、魔法筒、宇智波反弹……现在被我做成了小游戏。
这次用火柴人小剧场和真实游戏录屏，重打一场小时候的课间决战。

试玩：https://zhipijun1996.github.io/wave-game/
源码：https://github.com/zhipijun1996/wave-game
游戏版本：{spec['source_commit']}

火柴人动画、剪辑与原创配乐由 Video Rush 生成；角色对白为AI配音。游戏录屏为单机AI对战，剧情不代表已经实现联网双人。
含游戏王、街霸、EVA、火影、JOJO、奥特曼等短引用，逐条来源及授权状态见 sources.json；公开投稿前须确认引用可用性。

#B站AI创造公开赛#

建议分区：游戏 / 单机游戏
建议标签：B站AI创造公开赛，独立游戏，AI开发，拍拍波，童年，火柴人，游戏开发
公开期数需投稿时核对账号，不从内部ep008编号推断。活动资格以平台审核为准。
''')
    cover=Image.new('RGB',(1920,1080),'#faf5e8');d=ImageDraw.Draw(cover)
    sample=next(s for s in project['shots'] if s['id']=='5-06');art=draw_frame(sample,1.45,sample['seconds']).resize((1200,675));cover.paste(art,(700,390))
    for pos,text,size,col in [((90,120),'小时候的口胡',120,'#282529'),((90,290),'被我做成游戏了',120,'#d35c48'),((95,475),'拍拍波大王 · 申请出战',54,'#282529')]:d.text(pos,text,font=ImageFont.truetype(font(True),size),fill=col)
    cover.save(out/'cover.png')
    ghost=next(s for s in project['shots'] if s['id']=='7-03');title_shot=next(s for s in project['shots'] if s['id']=='7-04');short=out/'short-tail.mp4'
    run(['ffmpeg','-v','error','-y','-i',final,'-filter_complex',f"[0:v]trim=0:{ghost['start']},setpts=PTS-STARTPTS[v0];[0:a]atrim=0:{ghost['start']},asetpts=PTS-STARTPTS[a0];[0:v]trim=start={title_shot['start']},setpts=PTS-STARTPTS[v1];[0:a]atrim=start={title_shot['start']},asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',short],log=out/'logs/short-tail.log',timeout=600)
    run(['ffmpeg','-v','error','-i',short,'-f','null','-'],log=out/'logs/short-tail-decode.log',timeout=180)
    info=probe(final);v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio');metrics=audio_metrics(final)
    scan=subprocess.run(['ffmpeg','-hide_banner','-i',str(final),'-vf','blackdetect=d=0.7:pix_th=0.05,freezedetect=n=-50dB:d=3','-an','-f','null','-'],capture_output=True,text=True,check=True)
    (out/'logs/visual-scan.log').write_text(scan.stderr)
    anomalies=[l for l in scan.stderr.splitlines() if 'black_start:' in l or 'freeze_start:' in l]
    r=project['capture']['rounds'];critical={'continuous_21_rounds':len(r)==21 and all(r[i]['result']['next']==r[i+1]['initial'] for i in range(20)),'A_returns_B_medium':r[14]['result']['actions']==['reflect2','wave2'] and r[14]['result']['damage']==[0,2],'legal_final_beam':r[20]['initial']['players'][0]['energy']>=5 and r[20]['initial']['players'][1]['hp']<=3 and r[20]['result']['winner']==0,'single_comeback_line':sum('你就赢这一把' in l['text'] for s in project['shots'] for l in s['lines'])==1}
    checks={'decode':True,'dimensions':(v['width'],v['height'])==(1920,1080),'fps':v['avg_frame_rate']=='30/1','codecs':v['codec_name']=='h264' and a['codec_name']=='aac','duration_in_requested_range':110<=duration(final)<=125,'real_voice_receipts':len(voices)==47 and all(x['metrics']['audible_signal'] for x in voices.values()),'subtitle_bounds':all(0<=c['start']<c['end']<=duration(final)+.03 for c in cues),'no_obvious_clipping':metrics['clipped_fraction']<.0001,'all_parent_shots_survive':all(c['passed'] for c in read(out/'frame-checks.json')),'all_short_anime_layers_survive':all(c['passed'] for c in read(out/'anime-layer-checks.json')),'no_detected_long_black_or_freeze':not anomalies,**critical}
    (out/'phone-review.md').write_text('''# 手机审核（待你判断，不由自动检查代签）

- [ ] 开头老板/哄娃同一动作衔接，手机叮→酒杯叮是否顺。
- [ ] 先认出教室走廊，再进入实机；角色A/B年龄、站位清楚。
- [ ] 魔法筒“翻卡→吸收→返回→掉血”看得懂，原声字幕对齐。
- [ ] 黑化A是被B感染，规则经双方同意，不是突然练成异能。
- [ ] 中波破小反→AT挡中波→B学中波→A升级反弹，笑点是否自然。
- [ ] 五格铺垫与光线命中不被插梗打断；胜利后再JOJO和王冠。
- [ ] “你就赢这一把”童年到成年声桥是否流畅，没重复说。
- [ ] 真手机首页→开局→老登拍手→童年重影，结尾不拖、不说教。
- [ ] 第三方短引用公开使用前确认；当前仅交付私下审核。

自动检查不判断好笑、表演自然或版权已获许可。未自动投稿B站/Toy。
''')
    report={'status':'technical_pass_pending_phone_review' if all(checks.values()) else 'needs_review','duration':duration(final),'checks':checks,'audio':metrics,'visual_detector_events':anomalies,'content_review':'pending user; source and order mechanically checked, humor/timing/aesthetics not certified','rights_review':'Third-party anime permissions unconfirmed','variants':{'main':'final.mp4','short_tail':'short-tail.mp4','short_tail_difference':'Omit only 7-03 double-age overlay, preserve main separately'},'source_commit':spec['source_commit'],'final_sha256':sha(final),'short_tail_sha256':sha(short)};write(out/'report.json',report)
    write(out/'delivery-manifest.json',{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ('.mp4','.png','.json','.md','.ass','.srt','.csv') and p.name not in ('joined.mp4','delivery-manifest.json')})
    if not all(checks.values()):raise ValueError('Technical checks failed: '+str([k for k,v in checks.items() if not v]))
    print('DELIVERED',final,report['duration'],flush=True)


def visual_shot(s,spec,out,structure=False,layer_inputs=None):
    folder=out/'segments';folder.mkdir(exist_ok=True);base=out/'r-animation'/(s['id']+'.mp4');target=folder/(s['id']+('.structure' if structure else '')+'.mp4')
    layers=[l for l in s['layers'] if not structure or l['layer']=='G']
    layer_inputs=layer_inputs or {}
    input_hashes={str(i):sha(layer_inputs[i]['path']) if i in layer_inputs else sha(CAPTURE/('continuous.mp4' if l['source']=='game' else 'mobile.mp4')) if l['layer']=='G' else spec['references'][l['source']]['sha256'] for i,l in enumerate(layers)}
    key=digest({'shot':s,'layers':layers,'inputs':input_hashes,'resolved_layers':{str(i):{k:str(v) if isinstance(v,Path) else v for k,v in r.items()} for i,r in layer_inputs.items()},'art':sha(ROOT/'video_rush/paipai_film_art.py'),'renderer_version':1});receipt=target.with_suffix('.json')
    if target.exists() and receipt.exists() and read(receipt).get('key')==key and read(receipt).get('sha256')==sha(target):return target
    art_key=digest({'shot':s,'art':sha(ROOT/'video_rush/paipai_film_art.py')});art_receipt=base.with_suffix('.json')
    if not base.exists() or not art_receipt.exists() or read(art_receipt).get('key')!=art_key:
        draw_scene(base,s,s['seconds']);write(art_receipt,{'key':art_key,'sha256':sha(base)})
    args=['ffmpeg','-v','error','-y','-i',base];filters=['[0:v]setpts=PTS-STARTPTS,setsar=1[v0]'];current='v0'
    for i,l in enumerate(layers,1):
        path=CAPTURE/('continuous.mp4' if l['source']=='game' else 'mobile.mp4') if l['layer']=='G' else ROOT/spec['references'][l['source']]['file']
        resolved=layer_inputs.get(i-1,{})
        path=Path(resolved.get('path',path));source_in=resolved.get('in',l['in'])
        if source_in<0 or source_in+l['seconds']>duration(path)+.05:raise ValueError('Layer outside recorded source '+str(l))
        args+=['-ss',str(source_in),'-t',str(l['seconds']),'-i',str(path)]
        v=f'[{i}:v]setpts=PTS-STARTPTS+{l["at"]}/TB'
        if l['source']=='game' and not resolved.get('cropped'):v+=',crop=1116:628:402:70'
        if l.get('crop'):
            x,y,w,h=l['crop'];v+=f',crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}'
        if l.get('flip'):v+=',hflip'
        x,y,w,h=l.get('rect',[0,0,1920,1080])
        if l['source']=='mobile' and l.get('kind')=='mobile-arena':v+=',crop=390:220:0:210'
        v+=f',scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0xfaf5e8,setsar=1'
        if l.get('alpha') is not None:
            # A feathered apparition instead of a rectangular pasted screenshot.
            v+=f",format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*{l['alpha']}*clip(4*(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2)),0,1)'"
        v+=f'[l{i}]';filters.append(v)
        nxt=f'v{i}';filters.append(f'[{current}][l{i}]overlay=x={x}:y={y}:eof_action=pass:enable=\'between(t,{l["at"]},{l["at"]+l["seconds"]-0.001})\'[{nxt}]');current=nxt
    if not structure and s['id'] in ('4-03','5-05'):
        color='0x7bdfff' if s['id']=='4-03' else '0xdafaff'
        filters.append(f"[{current}]drawbox=x=0:y=0:w=iw:h=ih:color={color}@0.55:t=fill:enable='lt(t,0.10)'[flash]");current='flash'
    args+=['-filter_complex',';'.join(filters),'-map',f'[{current}]','-an','-t',str(s['seconds']),'-r','30','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',target]
    run(args,log=out/'logs'/(s['id']+('-structure' if structure else '')+'.log'),timeout=240);write(receipt,{'key':key,'sha256':sha(target)});return target


def prepare_voices(spec,out):
    folder=out/'narration';folder.mkdir(parents=True,exist_ok=True)
    jobs=[(s,i,line) for s in spec['shots'] for i,line in enumerate(s['lines'])]
    def one(item):
        s,i,line=item;name=f'{s["id"]}-{i}';target=folder/(name+'.wav');receipt=folder/(name+'.json')
        voice,rate=spec['voices'][line['speaker']];pitch=1.13 if line['speaker']=='kidB' else 1
        key=digest({'text':line['text'],'voice':voice,'rate':rate,'pitch':pitch,'trim_recipe':1})
        if target.exists() and receipt.exists():
            old=read(receipt)
            if old.get('key')==key and old.get('sha256')==sha(target):return name,old
        base=folder/(name+'-source.wav');original=narrate(line['text'],base,voice=voice,rate=rate)
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(base),'-ar','24000','-ac','1','-f','s16le','-'])
        values=array.array('h',raw);threshold=max(60,max(abs(v) for v in values)*.006)
        active=[i for i,v in enumerate(values) if abs(v)>threshold]
        if not active:raise ValueError('Voice is silent')
        start=max(0,active[0]/24000-.035);end=min(original['duration'],active[-1]/24000+.09)
        filt=f'atrim=start={start}:end={end},asetpts=PTS-STARTPTS'
        if pitch!=1:filt+=f',asetrate=48000*{pitch},aresample=48000,atempo={1/pitch}'
        run(['ffmpeg','-v','error','-y','-i',base,'-af',filt,'-ar','48000','-ac','2','-c:a','pcm_s16le',target],timeout=60)
        r={'key':key,'text':line['text'],'speaker':line['speaker'],'voice':voice,'rate':rate,'pitch_ratio':pitch,
           'source_receipt':original,'trim_start':start,'trim_end':end,'duration':duration(target),'sha256':sha(target),'metrics':audio_metrics(target)}
        write(receipt,r);return name,r
    with ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(one,jobs))
    write(out/'voices.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',default='episodes/ep008-r3-film.json');p.add_argument('--output',default='build/episodes/ep008-r3');p.add_argument('--stage',choices=['voices','structure','all'],default='all');a=p.parse_args()
    spec=read(a.spec);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);voices=prepare_voices(spec,out)
    print('Actual speech seconds',sum(v['duration'] for v in voices.values()),'utterances',len(voices),flush=True)
    if a.stage=='voices':return
    render(spec,out,voices,structure=a.stage=='structure')


if __name__=='__main__':main()
