from __future__ import annotations
import math
import re
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .common import font, run, sha, digest, read, write, duration, probe

W, H, FPS = 1920, 1080, 30
BG = '#0d1724'


def wrap(text, width=24):
    return '\n'.join(text[i:i+width] for i in range(0, len(text), width))


def panel(path, title, lines, tag='开发记录 · 编辑摘录'):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((105, 140, 1815, 875), 30, fill='#17283b', outline='#35506b', width=2)
    d.text((160, 185), tag, font=ImageFont.truetype(font(), 33), fill='#6fddc7')
    d.text((160, 260), title, font=ImageFont.truetype(font(True), 64), fill='white')
    y = 390
    for line in lines:
        for s in wrap(line, 29).splitlines():
            d.text((175, y), s, font=ImageFont.truetype(font(), 43), fill='#e5edf5')
            y += 67
        y += 25
    im.save(path)


def ass_time(s):
    c = round(s * 100)
    return f'{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}'


def subtitle_cues(text, start, seconds):
    # Conservative sentence/phrase timing; actual TTS boundaries are preferred in compose().
    parts = [x for x in re.split(r'(?<=[，。？！；：])', text) if x.strip()]
    chunks = []
    for p in parts:
        while len(p) > 26:
            chunks.append(p[:24]); p = p[24:]
        if p: chunks.append(p)
    total = sum(len(x) for x in chunks)
    t = start
    for p in chunks:
        end = t + seconds * len(p) / total
        yield {'start': round(t, 3), 'end': round(end, 3), 'text': p}
        t = end


def ass_file(path, timeline):
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,52,&H00FFFFFF,&H000000FF,&H00101824,&H80000000,-1,0,0,0,100,100,1,0,1,3,1,2,100,100,64,1
Style: Title,Noto Sans CJK SC,44,&H00FFFFFF,&H000000FF,&H00101824,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,7,62,60,30,1
Style: Source,Noto Sans CJK SC,27,&H00BCDDCD,&H000000FF,&H00101824,&H80000000,0,0,0,0,100,100,0,0,1,1,0,9,60,60,38,1
Style: Punch,Noto Sans CJK SC,64,&H0087E5FF,&H000000FF,&H0012243A,&H0012243A,-1,0,0,0,100,100,0,0,3,12,1,9,90,100,225,1
Style: Action,Noto Sans CJK SC,46,&H0087E5FF,&H000000FF,&H0012243A,&H0012243A,-1,0,0,0,100,100,0,0,3,8,1,1,80,80,190,1
Style: Emphasis,Noto Sans CJK SC,57,&H008EEBD2,&H000000FF,&H00101824,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,8,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = [header]
    def safe(s):
        return s.replace('\\','／').replace('{','（').replace('}','）').replace('\n',r'\N')
    def put(st, en, style, text):
        lines.append(f'Dialogue: 0,{ass_time(st)},{ass_time(en)},{style},,0,0,0,,{safe(text)}\n')
    for s in timeline['shots']:
        if timeline.get('display_chapters',True):
            put(s['start'], s['end'], 'Title', f'{s["chapter"]}  {s["title"]}')
        if s.get('source_cues'):
            for cue in s['source_cues']:
                put(cue['start'], cue['end'], 'Source', cue['text'])
        else:
            put(s['start'], s['end'], 'Source', s['provenance_label'])
        if s.get('emphasis'):
            put(s['start']+.4, min(s['start']+4, s['end']), 'Emphasis', s['emphasis'])
        if s.get('punchline'):
            put(s['start']+.15,min(s['start']+2.4,s['end']),'Punch',s['punchline'])
        for label in s.get('action_labels',[]):
            put(s['start']+label['start'],s['start']+label['end'],'Action',label['text'])
        for cue in s['cues']:
            put(cue['start'], cue['end'], 'Default', cue['text'])
    Path(path).write_text(''.join(lines))


def encode_shot(shot, assets, out, log, *, threads=4):
    """Video: normal speed, exact window. Still: slow camera pan, explicitly tagged."""
    if shot.get('presentation') == 'animated_diagram':
        from .animation import encode_diagram
        return encode_diagram(shot, assets, out, log, threads=threads)
    if shot.get('presentation') == 'montage':
        return encode_montage(shot, assets, out, log, threads=threads)
    if shot.get('presentation') == 'parallax_diagram':
        return encode_parallax_diagram(shot, assets, out, log, threads=threads)
    ids = shot.get('assets', [])
    dur = shot['end'] - shot['start']
    frames = round(dur * FPS)
    args = ['ffmpeg', '-y', '-v', 'warning', '-threads', str(threads), '-filter_complex_threads', '1']
    video_ext = {'.mp4', '.avi', '.webm'}
    paths = [Path(assets[x]['local_path']) for x in ids]
    for i, p in enumerate(paths):
        if p.suffix.lower() in video_ext:
            seek = shot.get('offsets', [0]*len(paths))[i]
            if duration(p) < seek + dur - .1:
                raise ValueError(f'{p.name} has insufficient footage; no silent looping allowed')
            args += ['-ss', str(seek), '-i', str(p)]
        else:
            args += ['-loop', '1', '-framerate', '30', '-i', str(p)]
    if not paths:
        raise ValueError('Shot has no source media')
    if shot.get('presentation') == 'five_style_board':
        # Re-layout five real screenshot crops for phone readability. No gameplay is synthesized.
        original = Image.open(paths[0]).convert('RGB')
        if original.size != (1280, 1975):
            raise ValueError('Unexpected comparison-board dimensions')
        board = Image.new('RGB', (W, H), BG)
        draw = ImageDraw.Draw(board)
        coords = [(40,150),(660,150),(1280,150),(350,550),(970,550)]
        for i, ((xx,yy), label) in enumerate(zip(coords, ['RETRO','BASIC','SCRIBBLE','UNDERWORLD','CAVERN'])):
            crop = original.crop((0,395*i,640,395*i+360)).resize((600,337), Image.Resampling.LANCZOS)
            board.paste(crop,(xx,yy))
            draw.text((xx,yy-45),label,font=ImageFont.truetype(font(True),32),fill='white')
        derived = Path(out).with_suffix('.board.png')
        board.save(derived)
        paths = [derived]
        args = ['ffmpeg','-y','-v','warning','-threads',str(threads),'-filter_complex_threads','1',
                '-loop','1','-framerate','30','-i',str(derived)]
    if len(paths) == 2:
        # Split comparison preserves original aspect ratios; no claim of matching seed.
        crops=shot.get('crop_rects',[None,None])
        filt = (f'[0:v]{crop_filter(crops[0],paths[0])}scale=954:870:force_original_aspect_ratio=decrease,pad=954:870:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1[a];'
                f'[1:v]{crop_filter(crops[1],paths[1])}scale=954:870:force_original_aspect_ratio=decrease,pad=954:870:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1[b];'
                '[a][b]hstack=inputs=2,pad=1920:1080:6:100:color=0x0d1724')
    elif shot.get('safe_frame'):
        # UI evidence needs all four edges: the ordinary caption bars obscure HUDs.
        filt = (f'[0:v]{crop_filter(shot.get("crop_rect"),paths[0])}'
                'scale=1840:780:force_original_aspect_ratio=decrease,'
                'pad=1920:1080:(ow-iw)/2:110+(780-ih)/2:color=0x0d1724,setsar=1')
        if paths[0].suffix.lower() not in video_ext:
            filt += (f",zoompan=z='1+0.01*on/{frames}':x='iw/2-iw/zoom/2':"
                     "y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30,setsar=1")
    elif paths[0].suffix.lower() in video_ext:
        filt = '[0:v]'+crop_filter(shot.get('crop_rect'),paths[0])+'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1'
    else:
        # Zoom <= 3%, smooth at output resolution. Original asset stays unchanged.
        filt = (f'[0:v]{crop_filter(shot.get("crop_rect"),paths[0])}scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,'
                f"zoompan=z='1+0.025*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30,setsar=1")
    filt += ',fps=30,drawbox=x=0:y=0:w=iw:h=100:color=0x0d1724@0.88:t=fill,drawbox=x=0:y=912:w=iw:h=168:color=0x0d1724@0.82:t=fill'
    if shot.get('transition') == 'flash':
        filt += ',fade=t=in:st=0:d=0.10:color=white'
    filt += ',scale=in_range=auto:out_range=tv,format=yuv420p[v]'
    args += ['-filter_complex', filt, '-map', '[v]', '-frames:v', str(frames), '-an',
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-threads', str(threads),
             '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-r', '30', '-movflags', '+faststart', str(out)]
    run(args, log=log, timeout=600)


def montage_spans(shot):
    """Partition one voice segment into exact, non-overlapping 30fps cuts."""
    ids = shot['assets']
    weights = shot.get('montage_weights', [1] * len(ids))
    if len(ids) < 2 or len(weights) != len(ids) or any(
            not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError('Montage needs at least two assets and positive finite weights')
    total = round((shot['end'] - shot['start']) * FPS)
    spans = []
    cumulative = 0
    previous = 0
    for index, (asset, weight) in enumerate(zip(ids, weights)):
        cumulative += weight
        boundary = total if index == len(ids) - 1 else round(total * cumulative / sum(weights))
        count = boundary - previous
        if count < 1:
            raise ValueError('Montage cut is shorter than one frame')
        spans.append({'asset': asset, 'index': index, 'start': previous / FPS,
                      'end': boundary / FPS, 'frames': count})
        previous = boundary
    return spans


def encode_montage(shot, assets, out, log, *, threads=4):
    spans = montage_spans(shot)
    args = ['ffmpeg', '-y', '-v', 'warning', '-threads', str(threads), '-filter_complex_threads', '1']
    filters = []
    for span in spans:
        i = span['index']
        path = Path(assets[span['asset']]['local_path'])
        if path.suffix.lower() in {'.mp4', '.webm', '.avi'}:
            offset = shot.get('offsets', [0] * len(spans))[i]
            if duration(path) < offset + span['frames'] / FPS - .02:
                raise ValueError(f'{path.name} has insufficient footage; no silent looping allowed')
            args += ['-ss', str(offset), '-i', str(path)]
        else:
            args += ['-loop', '1', '-framerate', '30', '-i', str(path)]
        crops=shot.get('crop_rects',[None]*len(spans))
        if len(crops)!=len(spans):
            raise ValueError('Montage crop rectangles must match the cuts')
        filters.append(f'[{i}:v]{crop_filter(crops[i],path)}scale=1920:1080:force_original_aspect_ratio=decrease,'
                       f'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1,'
                       f'fps=30,trim=end_frame={span["frames"]},setpts=PTS-STARTPTS[seg{i}]')
    joined = ''.join(f'[seg{i}]' for i in range(len(spans)))
    final = (joined + f'concat=n={len(spans)}:v=1:a=0,'
             'drawbox=x=0:y=0:w=iw:h=100:color=0x0d1724@0.88:t=fill,'
             'drawbox=x=0:y=912:w=iw:h=168:color=0x0d1724@0.82:t=fill')
    if shot.get('transition') == 'flash':
        final += ',fade=t=in:st=0:d=0.10:color=white'
    filters.append(final + ',scale=in_range=auto:out_range=tv,format=yuv420p[v]')
    args += ['-filter_complex', ';'.join(filters), '-map', '[v]', '-frames:v',
             str(sum(s['frames'] for s in spans)), '-an', '-c:v', 'libx264',
             '-preset', 'veryfast', '-crf', '20', '-threads', str(threads),
             '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-r', '30', '-movflags', '+faststart', str(out)]
    run(args, log=log, timeout=600)


def encode_parallax_diagram(shot, assets, out, log, *, threads=4):
    """Move three original explanatory bands; never pretend this is game footage."""
    source=Path(assets[shot['assets'][0]]['local_path'])
    if Image.open(source).size != (3840,720):
        raise ValueError('Parallax diagram template must be3840x720')
    rates=shot.get('parallax_rates',[18,48,96])
    seconds=shot['end']-shot['start']
    if len(rates)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 or v*seconds>1920 for v in rates):
        raise ValueError('Parallax diagram motion exceeds its declared source')
    filters=['[0:v]split=3[a][b][c]']
    for i,(name,rate) in enumerate(zip('abc',rates)):
        filters.append(f'[{name}]crop=1920:240:x=\'t*{rate}\':y={i*240},setsar=1[s{i}]')
    final='[s0][s1][s2]vstack=inputs=3,pad=1920:1080:0:140:color=0x0d1724'
    for y,label in [(180,'远景 · 慢'),(420,'中景 · 稍快'),(660,'近景 · 快')]:
        final+=f",drawtext=fontfile='{font(True)}':text='{label}':fontsize=46:fontcolor=white:box=1:boxcolor=0x0d1724@0.85:boxborderw=14:x=60:y={y}"
    filters.append(final+',fps=30,scale=in_range=auto:out_range=tv,format=yuv420p[v]')
    run(['ffmpeg','-y','-v','warning','-loop','1','-framerate','30','-i',source,
         '-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[v]',
         '-frames:v',str(round(seconds*FPS)),'-an','-c:v','libx264','-preset','veryfast',
         '-crf','20','-threads',str(threads),'-pix_fmt','yuv420p','-color_range','tv',
         '-r','30','-movflags','+faststart',out],log=log,timeout=600)

def crop_filter(rect,path):
    if rect is None:return ''
    if len(rect)!=4 or any(type(v) is not int for v in rect):raise ValueError('Crop rectangle needs four integers')
    x,y,w,h=rect
    if Path(path).suffix.lower() in {'.mp4','.avi','.webm'}:
        video=next(s for s in probe(path)['streams'] if s['codec_type']=='video');width,height=video['width'],video['height']
    else:
        with Image.open(path) as im:width,height=im.size
    if min(x,y)<0 or min(w,h)<=0 or x+w>width or y+h>height:raise ValueError('Crop rectangle exceeds original footage')
    return f'crop={w}:{h}:{x}:{y},'


def concatenate_cuts(paths, shots, output, logs):
    """Decode each AAC edit separately to avoid accumulating encoder delay."""
    output, logs = Path(output), Path(logs)
    output.mkdir(parents=True, exist_ok=True); logs.mkdir(parents=True, exist_ok=True)
    if not paths or len(paths) != len(shots):
        raise ValueError('Each cut needs one timeline sample budget')
    listing = output / 'cuts-concat.txt'
    listing.write_text(''.join("file '" + str(Path(p).resolve()).replace("'", "'\\''") + "'\n"
        + f'duration {s["end"]-s["start"]:.12f}\n' for p,s in zip(paths,shots)))
    video, audio = output/'joined.mp4', output/'continuous-audio.wav'
    run(['ffmpeg','-y','-v','warning','-f','concat','-safe','0','-i',listing,
         '-map','0:v:0','-an','-c:v','copy',video],log=logs/'concat.log',timeout=180)
    args=['ffmpeg','-y','-v','warning','-threads','4','-filter_complex_threads','1']
    filters=[]
    for i,(p,s) in enumerate(zip(paths,shots)):
        args += ['-i',p]
        samples=round(s['end']*48000)-round(s['start']*48000)
        if samples <= 0: raise ValueError('Cut audio sample budget must be positive')
        filters.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,'
                       f'apad,atrim=end_sample={samples},asetpts=PTS-STARTPTS[a{i}]')
    filters.append(''.join(f'[a{i}]' for i in range(len(paths)))
                   +f'concat=n={len(paths)}:v=0:a=1[continuous]')
    run([*args,'-filter_complex',';'.join(filters),'-map','[continuous]',
         '-c:a','pcm_s16le','-ar','48000',audio],log=logs/'continuous-audio.log',timeout=300)
    return video,audio


def cover(path, left, right, design=None):
    if design and design.get('layout')=='intro':
        im=ImageOps.fit(Image.open(right).convert('RGB'),(1920,1080))
        shade=Image.new('RGBA',im.size,(0,0,0,0));d=ImageDraw.Draw(shade)
        d.rectangle((0,0,1920,1080),fill=(8,18,32,75))
        d.rounded_rectangle((45,45,1175,1035),40,fill=(12,27,45,245),outline=(135,235,212,255),width=3)
        d.text((100,85),design['series'],font=ImageFont.truetype(font(True),40),fill='#9ce7d4')
        # Original controller doodle, rather than cropping text from a narrative card.
        d.rounded_rectangle((130,215,710,510),90,fill='#ffe085',outline='#13263a',width=10)
        d.rectangle((230,285,265,410),fill='#16304b');d.rectangle((185,330,310,365),fill='#16304b')
        for x,y,color in [(535,325,'#e7798c'),(595,385,'#65b9d2')]:d.ellipse((x-28,y-28,x+28,y+28),fill=color)
        d.text((130,550),'童年梦想 × AI 新队友',font=ImageFont.truetype(font(True),52),fill='white')
        d.text((100,665),design['line1'],font=ImageFont.truetype(font(True),107),fill='white')
        d.text((100,825),design['line2'],font=ImageFont.truetype(font(True),76),fill='#99ecd7')
        d.rounded_rectangle((1290,90,1810,180),18,fill=(8,18,32,230))
        d.text((1330,108),'右侧：本作开发实机',font=ImageFont.truetype(font(True),36),fill='white')
        Image.alpha_composite(im.convert('RGBA'),shade).convert('RGB').save(path)
        return
    im = Image.new('RGB', (1920, 1080), BG)
    for p, x in [(left, 0),(right, 960)]:
        a = Image.open(p).convert('RGB')
        a = ImageOps.fit(a, (960, 1080))
        im.paste(a,(x,0))
    mask = Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(mask)
    d.rectangle((0,0,1920,1080),fill=(4,12,22,75))
    d.rectangle((0,690,1920,1080),fill=(5,14,26,235))
    d.rectangle((950,0,970,690),fill=(125,238,210,255))
    d.text((70,55),(design or {}).get('series','AI 独立游戏开发记录  /  01'),font=ImageFont.truetype(font(True),43),fill='white')
    for x,t in [(70,(design or {}).get('left_label','概念图')),(1040,(design or {}).get('right_label','真实运行画面'))]:
        d.rounded_rectangle((x,565,x+470,657),14,fill=(7,18,28,230))
        d.text((x+25,579),t,font=ImageFont.truetype(font(True),48),fill='white')
    d.text((65,732),(design or {}).get('line1','概念图很好看'),font=ImageFont.truetype(font(True),102),fill='white')
    d.text((65,870),(design or {}).get('line2','为什么实机总差一截？'),font=ImageFont.truetype(font(True),98),fill='#8ee8cf')
    Image.alpha_composite(im.convert('RGBA'),mask).convert('RGB').save(path)
