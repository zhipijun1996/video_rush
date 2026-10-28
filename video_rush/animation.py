"""Deterministic editorial layer animation, never counterfeit gameplay.

Fractions refer to the actual synthesized shot duration. A diagram element may
belong to one motion group; base elements stay fixed, groups slide/fade in/out.
"""
from pathlib import Path
import math
import re
from PIL import Image, ImageChops, ImageDraw
from .common import run, sha, digest, read, write
from .graphics import diagram


def tracks(graphic):
    groups=graphic.get('motion_groups',[])
    if not 1 <= len(groups) <= 12:
        raise ValueError('Animated diagrams require 1–12 explicit motion groups')
    ids=set()
    for g in groups:
        name=g['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name) or name in ids:
            raise ValueError('Invalid or duplicate motion group')
        ids.add(name)
        start,end=g.get('start',0),g.get('end',1)
        if not 0 <= start < end <= 1:
            raise ValueError('Motion interval outside synthesized shot')
        for key in ('from','to'):
            xy=g.get(key,[0,0])
            if len(xy)!=2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1920 for v in xy):
                raise ValueError('Invalid motion offset')
        travel=g.get('travel',.12);fade=g.get('fade',.025)
        if not (0<travel<=end-start and 0<fade<=end-start):
            raise ValueError('Motion travel/fade must fit its interval')
        if not any(e.get('group')==name for e in graphic['elements']):
            raise ValueError('Motion group has no diagram elements')
    if any(e.get('group') and e['group'] not in ids for e in graphic['elements']):
        raise ValueError('Diagram references undeclared motion group')
    return groups


def encode_diagram(shot, assets, out, log, *, threads=4):
    if len(shot['assets'])!=1:
        raise ValueError('Animated diagram needs one authored diagram source')
    asset=assets[shot['assets'][0]];g=asset.get('graphic',{})
    if asset.get('origin')!='editorial' or g.get('layout')!='diagram':
        raise ValueError('Only authored explanatory diagrams can be animated')
    groups=tracks(g);out=Path(out);folder=out.parent/'diagram-layers'/shot['id'];folder.mkdir(parents=True,exist_ok=True)
    base=folder/'base.png'
    diagram(base,dict(g,elements=[e for e in g['elements'] if not e.get('group')]))
    seconds=shot['end']-shot['start'];frames=round(seconds*30)
    args=['ffmpeg','-y','-v','warning','-filter_complex_threads','1',
          '-threads','1','-thread_queue_size','2','-loop','1','-framerate','30','-t',str(seconds),'-i',base]
    offsets=[]
    for group in groups:
        path=folder/(group['id']+'.png')
        diagram(path,{'elements':[e for e in g['elements'] if e.get('group')==group['id']]},transparent=True)
        # Decode/composite only nontransparent bounds, not a full 1080p canvas
        # per group per frame. Source SVG keeps its original coordinates.
        with Image.open(path) as im:
            bounds=im.getbbox()
            if not bounds:raise ValueError('Empty animation layer')
            im.crop(bounds).save(path)
        offsets.append(bounds[:2])
        args+=['-threads','1','-thread_queue_size','2','-loop','1','-framerate','30','-t',str(seconds),'-i',path]
    filters=['[0:v]format=rgba[b0]']
    for i,group in enumerate(groups,1):
        start=group.get('start',0)*seconds;end=group.get('end',1)*seconds
        fade=group.get('fade',.025)*seconds;travel=group.get('travel',.12)*seconds
        f=f'[{i}:v]format=rgba,fade=t=in:st={start:.6f}:d={fade:.6f}:alpha=1'
        if group.get('end',1)<1:f+=f',fade=t=out:st={end-fade:.6f}:d={fade:.6f}:alpha=1'
        filters.append(f+f'[g{i}]')
        q=f'clip((t-{start:.6f})/{travel:.6f},0,1)';ease=f'({q})*({q})*(3-2*({q}))'
        xy=[]
        for origin,a,b in zip(offsets[i-1],group.get('from',[0,0]),group.get('to',[0,0])):
            xy.append(f'{origin+a}+({b-a})*({ease})')
        # Alpha already gates each group's lifetime. Keep every overlay active
        # so FFmpeg consumes all inputs synchronously; disabling a late overlay
        # can otherwise queue unbounded frames from its upstream branches.
        filters.append(f"[b{i-1}][g{i}]overlay=x='{xy[0]}':y='{xy[1]}':eval=frame:shortest=1[b{i}]")
    filters.append(f'[b{len(groups)}]drawbox=x=0:y=0:w=iw:h=100:color=0x0d1724:t=fill,drawbox=x=0:y=912:w=iw:h=168:color=0x0d1724:t=fill,scale=in_range=auto:out_range=tv,format=yuv420p[v]')
    args+=['-filter_complex',';'.join(filters),'-map','[v]','-frames:v',str(frames),'-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-color_range','tv','-r','30','-threads',str(threads),'-movflags','+faststart',out]
    run(args,log=log,timeout=600)


def audit_motion(output, shot, graphic):
    """Measure decoded pre-caption cut frames; subtitles cannot fake this check."""
    groups=tracks(graphic);output=Path(output);movie=output/'cuts'/(shot['id']+'.mp4')
    if not movie.exists():raise ValueError('Missing encoded animation cut: '+shot['id'])
    evidence=output/'animation-evidence';evidence.mkdir(exist_ok=True)
    receipt=evidence/(shot['id']+'.json');sheet=evidence/(shot['id']+'-contact.jpg')
    movie_hash=sha(movie);plan_hash=digest(graphic)
    if receipt.exists() and sheet.exists():
        old=read(receipt)
        if old.get('cut_sha256')==movie_hash and old.get('graphic_hash')==plan_hash and old.get('contact_sha256')==sha(sheet):return old
    seconds=shot['end']-shot['start'];n=round(seconds*30)
    indices=sorted({min(n-1,round((n-1)*f)) for f in [.04,.22,.44,.67,.91]})
    select='+'.join(f'eq(n,{i})' for i in indices)
    raw=__import__('subprocess').run(['ffmpeg','-v','error','-i',str(movie),'-vf',f"select='{select}',scale=960:540",'-vsync','0','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
    size=960*540*3
    if len(raw)!=len(indices)*size:raise ValueError('Animation sampling frame count mismatch')
    frames=[Image.frombytes('RGB',(960,540),raw[i*size:(i+1)*size]) for i in range(len(indices))]
    changes=[]
    for a,b in zip(frames,frames[1:]):
        # Restrict to diagram content; no top label, subtitle or soundtrack.
        diff=ImageChops.difference(a,b).crop((0,52,960,454)).convert('L')
        hist=diff.histogram();changes.append({'pixels_over_12':sum(hist[13:]),'mean_absolute_difference':sum(i*v for i,v in enumerate(hist))/(960*402)})
    contact=Image.new('RGB',(1920,1080),'#101b2b');d=ImageDraw.Draw(contact)
    for i,frame in enumerate(frames):
        frame=frame.resize((640,360));x=i%3*640;y=i//3*400;contact.paste(frame,(x,y));d.text((x+12,y+365),f'{indices[i]/30:.2f}s',fill='white')
    contact.save(sheet,quality=85)
    result={'shot':shot['id'],'kind':'original_editorial_animation_not_gameplay','cut_sha256':movie_hash,'graphic_hash':plan_hash,'groups':groups,'sample_frame_indices':indices,'sample_frame_sha256':[__import__('hashlib').sha256(f.tobytes()).hexdigest() for f in frames],'decoded_pre_caption_changes':changes,'actual_motion_detected':any(c['pixels_over_12']>800 and c['mean_absolute_difference']>.15 for c in changes),'method':'Decoded pre-caption cut, five sample frames; content-region pixel changes. No subtitle changes or whole-frame camera zoom used as evidence. Does not certify narrative quality.','contact_file':sheet.name,'contact_sha256':sha(sheet)}
    write(receipt,result);return result
