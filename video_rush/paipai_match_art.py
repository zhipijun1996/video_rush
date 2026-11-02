"""Pose-matched R replacements for the Street Fighter inserts.

Hands, elbow/eye line and framing are paired with inspected anime timecodes.
These drawings are fictional stick animation, never altered gameplay.
"""
import math
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw
from .paipai_film_art import PAPER,INK,RED,BLUE,stroke,person,corridor,smooth
from .paipai_v2_art import frame as previous_frame

W,H=1280,720


def hand(d,x,y,scale=1,angle=0,open_hand=True):
    def P(a,b):
        q=math.radians(angle);return (x+scale*(a*math.cos(q)-b*math.sin(q)),y+scale*(a*math.sin(q)+b*math.cos(q)))
    for a,b in [(-23,-58),(-9,-74),(7,-78),(23,-65),(48,-25)]:
        stroke(d,[P(0,15),P(a*.75,b*.6),P(a,b)],PAPER,round(9*scale))
    pts=[P(-25,-5),P(-25,28),P(0,45),P(27,25),P(27,-10)]
    d.polygon(pts,fill=PAPER);stroke(d,pts+[pts[0]],INK,max(2,round(3*scale)))


def face(im,x,y,r,t,mouth=.5,angle=-12):
    layer=Image.new('RGBA',(360,360));d=ImageDraw.Draw(layer);cx=cy=180
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=PAPER,outline=INK,width=7)
    for dx in [-r*.30,r*.29]:
        ex=cx+dx;stroke(d,[(ex-r*.18,cy-r*.07),(ex+r*.17,cy+r*.04)],INK,6)
        d.ellipse((ex+6,cy+5,ex+15,cy+14),fill=INK)
    d.ellipse((cx-r*.15,cy+r*.30,cx+r*.55,cy+r*(.42+mouth*.44)),fill=INK)
    d.rectangle((cx-r*.06,cy+r*.31,cx+r*.40,cy+r*.37),fill=PAPER)
    stroke(d,[(cx-r,cy-r*.31),(cx+r,cy-r*.31)],RED,13)
    stroke(d,[(cx-r,cy-r*.30),(cx-r-65,cy-r*.24+10*math.sin(t*12)),(cx-r-110,cy-r*.42)],RED,11)
    layer=layer.rotate(angle,resample=Image.Resampling.BICUBIC);im.paste(layer,(round(x-180),round(y-180)),layer)


def frame(phase,t,seconds,action_at=0,envelope=None,previous=None):
    q=smooth(t/max(.1,seconds));clock=action_at+t
    if phase=='idea':
        im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im);corridor(d)
        person(d,355,655,t,'A',False,'idle','smug',t>.08,1.45,fingers=3)
        im=im.crop((0,70,880,565)).resize((W,H))
        if previous and t<.23:
            old=previous_frame('light_mad',previous['seconds']-1/30,previous['seconds'],previous.get('envelope'))
            im=Image.blend(old,im,smooth(t/.23))
        return im
    im=Image.new('RGB',(W,H),'#080d17');d=ImageDraw.Draw(im)
    # Same dark subjective space as the anime; avoid alternating white flashes.
    d.rectangle((0,0,158,H),fill='black');d.rectangle((1122,0,W,H),fill='black')
    voice=.5 if not envelope else min(1,envelope[min(len(envelope)-1,int(t*30))]*6)
    if phase=='hands':
        bx,by=820,448
        stroke(d,[(-20,250),(370,330),(685,380)],PAPER,27)
        stroke(d,[(1050,850),(895,660),(810,565)],PAPER,26)
        hand(d,685,380,1.65,35);hand(d,810,565,1.55,175)
        for k in range(5):
            r=38+k*13+3*math.sin(clock*14);d.ellipse((bx-r,by-r,bx+r,by+r),outline=['#e1fbff','#a4e8ff','#67bce9','#33759e','#204457'][k],width=4)
    elif phase in ('torso','push'):
        push=smooth(q) if phase=='push' else .10+.08*math.sin(clock*5)
        head=(575+push*25,220+push*22);neck=(470+push*55,365);hip=(300,760)
        stroke(d,[hip,neck],PAPER,15)
        upper=(1050+push*200,285+push*40);lower=(1060+push*210,460-push*12)
        stroke(d,[neck,(790+push*120,515-push*65),lower],PAPER,15)
        stroke(d,[(450,390),(770+push*120,430-push*90),upper],PAPER,15)
        hand(d,*upper,.8,90);hand(d,*lower,.8,-90)
        face(im,*head,100,clock,voice)
        d=ImageDraw.Draw(im);bx=1080+push*170;by=370
        for k in range(5):
            r=44+k*11+5*math.sin(clock*17);d.ellipse((bx-r,by-r,bx+r,by+r),outline=['#efffff','#bcefff','#78c6f5','#4d91c0','#1d4b70'][k],width=4)
    elif phase=='face':
        im=frame('torso',t,seconds,action_at=action_at,envelope=envelope)
        return im.crop((300,60,1100,510)).resize((W,H))
    elif phase=='mouth':
        d.polygon([(180,0),(1100,0),(1070,700),(190,700)],fill=PAPER)
        opening=390+voice*100+20*math.sin(clock*18)
        d.ellipse((410,145,940,145+opening),fill=INK);d.rectangle((460,145,890,200),fill=PAPER)
        stroke(d,[(180,140),(260,560),(400,660)],INK,8)
    elif phase=='palm':
        for k in range(8):
            r=100+k*34;d.ellipse((720-r,430-r,720+r,430+r),outline=['#ecffff','#bcefff','#9adaff','#74b5e3','#4287b9','#2d6790','#204c70','#16334c'][k],width=10)
        stroke(d,[(220,720),(470,630),(700,525)],PAPER,65);hand(d,720,425,4.3,-14)
    else:raise ValueError(phase)
    return im


def render(path,phase,seconds,**kwargs):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-','-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-color_range','tv',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(round(seconds*30)):p.stdin.write(frame(phase,n/30,seconds,**kwargs).tobytes())
        p.stdin.close();err=p.stderr.read();rc=p.wait(timeout=90)
        if rc:raise RuntimeError(err.decode()[-1000:])
    finally:
        if p.poll() is None:p.kill();p.wait()
