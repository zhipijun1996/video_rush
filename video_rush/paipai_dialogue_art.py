"""Original school-story dialogue acting; no game frames are modified."""
import math
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from .paipai_film_art import PAPER,INK,BLUE,stroke,corridor,person,smooth
from .paipai_match_art import frame as match_frame
from .paipai_v2_art import frame as previous_frame


def frame(mode,t,seconds,envelope=None,previous=None):
    if mode=='create':
        # Keep the camera and fade out of Light's last pose; raise three fingers
        # while the second clause names the new move.
        im=match_frame('idea',t,seconds,previous=previous)
        if t>seconds*.42:return im
        im2=Image.new('RGB',(1280,720),PAPER);d=ImageDraw.Draw(im2);corridor(d)
        person(d,355,655,t,'A',False,'idle','smug',t>.08,1.45)
        im2=im2.crop((0,70,880,565)).resize((1280,720))
        if previous and t<.23:
            old=previous_frame('light_mad',previous['seconds']-1/30,previous['seconds'],previous.get('envelope'))
            return Image.blend(old,im2,smooth(t/.23))
        return im2
    if mode!='surprise':raise ValueError(mode)
    im=Image.new('RGB',(1280,720),PAPER);d=ImageDraw.Draw(im);corridor(d)
    pop=smooth((t-.03)/.13);voice=.45
    if envelope:voice=min(1,envelope[min(len(envelope)-1,int(t*30))]*6)
    lean=24*pop;bounce=8*math.sin(t*23)*math.exp(-t*2.2)
    cx=650+lean;cy=315+bounce-16*pop;r=130
    neck=(cx,cy+r-5);hip=(cx+25,690)
    stroke(d,[neck,hip],INK,12)
    for sign in [-1,1]:
        # Both elbows and hands recoil, rather than keeping the old pointing pose.
        stroke(d,[neck,(cx+sign*(155+25*pop),cy+195),(cx+sign*(165+20*pop),cy+80+9*math.sin(t*13))],INK,10)
    d.ellipse((cx-r,cy-r,cx+r,cy+r+22*pop),fill=PAPER,outline=INK,width=8)
    for dx in [-53,53]:
        ex=cx+dx;ey=cy-10
        d.ellipse((ex-37,ey-43-14*pop,ex+37,ey+34+10*pop),fill='white',outline=INK,width=5)
        pupil=max(3,9-6*pop);d.ellipse((ex-pupil,ey-pupil,ex+pupil,ey+pupil),fill=INK)
        # B's established blue round glasses stay recognisable while slipping.
        d.ellipse((ex-45,ey-49+8*pop,ex+45,ey+47+8*pop),outline=BLUE,width=7)
        stroke(d,[(ex-28,ey-65),(ex+25,ey-70-7*pop)],INK,6)
    stroke(d,[(cx-8,cy-7+8*pop),(cx+8,cy-7+8*pop)],BLUE,6)
    opening=20+70*pop+36*voice
    d.ellipse((cx-44,cy+54,cx+44,cy+54+opening),fill=INK)
    d.rectangle((cx-29,cy+56,cx+29,cy+68),fill=PAPER)
    sx=cx+r+18;sy=cy-35+(t*105)%90
    d.ellipse((sx-8,sy,sx+8,sy+29),fill=BLUE)
    d.polygon([(sx,sy-12),(sx-8,sy+10),(sx+8,sy+10)],fill=BLUE)
    return im


def render(path,mode,seconds,**kwargs):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-','-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-color_range','tv',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(round(seconds*30)):p.stdin.write(frame(mode,n/30,seconds,**kwargs).tobytes())
        p.stdin.close();error=p.stderr.read();code=p.wait(timeout=90)
        if code:raise RuntimeError(error.decode()[-1000:])
    finally:
        if p.poll() is None:p.kill();p.wait()
