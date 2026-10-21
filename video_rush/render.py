from __future__ import annotations
import math
import re
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .common import font, run, sha, digest, read, write, duration

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
Style: Punch,Noto Sans CJK SC,64,&H0087E5FF,&H000000FF,&H0012243A,&H0012243A,-1,0,0,0,100,100,0,0,3,12,1,9,90,100,130,1
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
        put(s['start'], s['end'], 'Source', s['provenance_label'])
        if s.get('emphasis'):
            put(s['start']+.4, min(s['start']+4, s['end']), 'Emphasis', s['emphasis'])
        if s.get('punchline'):
            put(s['start']+.15,min(s['start']+2.4,s['end']),'Punch',s['punchline'])
        for cue in s['cues']:
            put(cue['start'], cue['end'], 'Default', cue['text'])
    Path(path).write_text(''.join(lines))


def encode_shot(shot, assets, out, log, *, threads=4):
    """Video: normal speed, exact window. Still: slow camera pan, explicitly tagged."""
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
        filt = ('[0:v]scale=954:870:force_original_aspect_ratio=decrease,pad=954:870:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1[a];'
                '[1:v]scale=954:870:force_original_aspect_ratio=decrease,pad=954:870:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1[b];'
                '[a][b]hstack=inputs=2,pad=1920:1080:6:100:color=0x0d1724')
    elif paths[0].suffix.lower() in video_ext:
        filt = '[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,setsar=1'
    else:
        # Zoom <= 3%, smooth at output resolution. Original asset stays unchanged.
        filt = (f'[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0d1724,'
                f"zoompan=z='1+0.025*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30,setsar=1")
    filt += ',fps=30,drawbox=x=0:y=0:w=iw:h=100:color=0x0d1724@0.88:t=fill,drawbox=x=0:y=912:w=iw:h=168:color=0x0d1724@0.82:t=fill,format=yuv420p[v]'
    args += ['-filter_complex', filt, '-map', '[v]', '-frames:v', str(frames), '-an',
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-threads', str(threads),
             '-pix_fmt', 'yuv420p', '-r', '30', '-movflags', '+faststart', str(out)]
    run(args, log=log, timeout=600)


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
