"""Acting upgrades for three review clips; never draws gameplay or outcomes."""
import math
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw
from .paipai_film_art import W,H,PAPER,INK,RED,BLUE,GOLD,stroke,corridor,person,smooth


def actor(d,canvas,x,y,t,pose='disgust',progress=0,voice=.5):
    scale=1.45;neck=(x,y-245);hip=(x,y-105);head=(x,y-318);lean=0;angle=0
    elbows=[(-72,-172),(72,-172)];hands=[(-95,-135),(95,-135)]
    if pose=='grin':angle=-12*progress;lean=15*progress
    if pose=='mad':
        lean=35*math.sin(t*5);bounce=10*math.sin(t*16)
        hip=(x+lean*.4,y-105+bounce);neck=(x+lean,y-245+bounce)
        head=(x+lean*1.25,y-322+bounce-20*math.sin(t*7));angle=-18+18*math.sin(t*5)
        elbows=[(-110,-180+30*math.sin(t*7)),(110,-180-30*math.sin(t*7))]
        hands=[(-20-95*progress,-130-115*progress),(20+95*progress,-130-115*progress)]
    if pose=='charge':
        lean=25*progress;hip=(x+5,y-88);neck=(x+lean,y-225);head=(x+lean,y-299)
        elbows=[(-68,-142),(-75,-190)];hands=[(-12+145*progress,-163),(0+145*progress,-170)]
    if pose=='boast':elbows=[(-60,-190),(70,-220)];hands=[(-90,-170),(102,-330)];angle=8
    if pose=='dio':
        head=(x+10,y-315-10*math.sin(t*6));angle=10*math.sin(t*5)
        elbows=[(-105,-215),(105,-215)];hands=[(-105,-330),(105,-330)]
    if pose=='cross':elbows=[(-75,-205),(72,-200)];hands=[(56,-205),(54,-318)];lean=20;head=(x+lean,y-318)
    if pose=='disgust':angle=-6;elbows=[(-60,-165),(65,-185)];hands=[(-92,-140),(102,-188)]
    if pose=='recover':angle=5;elbows=[(-60,-175),(70,-218)];hands=[(-95,-155),(160,-240)]
    stroke(d,[hip,neck],INK,9)
    for sign in (-1,1):stroke(d,[hip,(x+sign*65,y-75),(x+sign*76,y)],INK,8)
    for e,h in zip(elbows,hands):stroke(d,[neck,(x+e[0]+lean,y+e[1]),(x+h[0]+lean,y+h[1])],INK,8)
    if pose=='charge':
        hx=x+hands[0][0]+lean;hy=y+hands[0][1]
        for i in range(5):
            r=13+i*7;d.arc((hx-r,hy-r,hx+r,hy+r),-110+50*t,80+50*t,fill=BLUE,width=2)
    if pose=='dio':
        for sign in (-1,1):
            for j in range(3):stroke(d,[(x+sign*105,y-330),(x+sign*(110+j*12),y-348-j*8)],INK,4)
    # Head is independently rotated, with an animated jaw/eyes. Its motion is
    # separate from the torso, arms and knees rather than a camera shake preset.
    face=Image.new('RGBA',(230,230),(0,0,0,0));fd=ImageDraw.Draw(face);cx=cy=115;r=62
    fd.ellipse((cx-r,cy-r,cx+r,cy+r),fill=PAPER,outline=INK,width=6)
    evil=pose in ('grin','mad','dio','boast');mad=pose in ('mad','dio')
    if evil:fd.polygon([(55,78),(175,78),(176,112),(54,112)],fill='#c7c0b2')
    for j,dx in enumerate([-24,24]):
        ex=cx+dx;ey=107;sign=1 if j==0 else -1
        if pose=='disgust':stroke(fd,[(ex-14,ey),(ex+13,ey+1)],INK,5)
        elif evil:
            stroke(fd,[(ex-15,ey-sign*9),(ex+13,ey+sign*9)],INK,5)
            rr=4+int((3+3*math.sin(t*8))*progress) if mad else 4
            fd.ellipse((ex-rr,ey+5-rr,ex+rr,ey+5+rr),fill=RED if mad else INK)
        else:fd.ellipse((ex-4,ey-5,ex+4,ey+5),fill=INK)
    if pose=='disgust':stroke(fd,[(92,150),(138,148)],INK,4)
    elif pose=='grin':
        fd.arc((82,128,152,158+18*progress),0,180,fill=INK,width=5)
    else:
        opening=(10+40*voice+20*abs(math.sin(t*9))) if mad else (5+22*voice)
        fd.ellipse((84,139,150,139+opening),fill=INK)
        if evil:fd.rectangle((90,140,144,147),fill='white')
    stroke(fd,[(54,90),(178,89),(215,99+9*math.sin(t*11))],RED,9)
    face=face.rotate(angle,resample=Image.Resampling.BICUBIC)
    canvas.paste(face,(round(head[0]-115),round(head[1]-115)),face)
    return head


def frame(mode,t,seconds,envelope=None):
    im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im);corridor(d)
    q=smooth(t/max(.1,seconds));voice=.5
    if envelope:
        voice=min(1,envelope[min(len(envelope)-1,int(t*30))]*5)
    if mode=='hadoken_three':
        person(d,355,655,t,'A',False,'idle','smug',t<1.85,1.45,fingers=3);person(d,925,655,t,'B',False,'idle','shock',t>1.95,1.45)
        return im.crop((0,120,850,598)).resize((W,H))
    if mode=='dio_setup':
        person(d,355,655,t,'A',False,'open','evil',False,1.45);person(d,925,655,t,'B',False,'fan','smug',True,1.45);return im
    poses={'light_disgust':'disgust','light_grin':'grin','light_mad':'mad','light_break':'disgust','light_recover':'recover','hadoken_charge':'charge','hadoken_reply':'boast','hadoken_boast':'boast','dio_face':'dio','ultra_cross':'cross'}
    pose=poses[mode]
    if mode in ('light_break','hadoken_reply'):voice=0
    if mode in ('light_mad','dio_face'):
        # Background augments an actually moving actor; it does not stand in for acting.
        tint='#24202e' if mode=='dio_face' else '#383325';im=Image.new('RGB',(W,H),tint);d=ImageDraw.Draw(im)
        for j in range(22):
            a=j*math.tau/22+t*.08;stroke(d,[(355+150*math.cos(a),320+125*math.sin(a)),(355+1100*math.cos(a),320+800*math.sin(a))],GOLD if mode=='light_mad' else RED,3)
        # Bright bones on the dramatic background.
        layer=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(layer)
        head=actor(ld,layer,355,655,t,pose,q,voice)
        # Preserve paper face/body silhouette without introducing an inset window.
        import numpy as np
        a=np.asarray(layer).copy();mask=a[:,:,3]>0;yy,xx=np.indices((H,W));outside_head=(xx-head[0])**2+(yy-head[1])**2>84**2
        # Skeleton ink becomes warm white; red headband and skin retain their colors.
        dark=(a[:,:,0]<80)&(a[:,:,1]<90)&(a[:,:,2]<95)&mask&outside_head
        a[dark,:3]=[243,231,207];im=Image.alpha_composite(im.convert('RGBA'),Image.fromarray(a)).convert('RGB');d=ImageDraw.Draw(im)
    else:actor(d,im,355,655,t,pose,q,voice)
    if mode in ('light_disgust','light_grin','light_break','light_recover','hadoken_reply','hadoken_boast'):
        b_talk=mode in ('light_break','hadoken_reply')
        person(d,925,655,t,'B',False,'point' if b_talk else 'idle','stiff' if b_talk else 'normal',b_talk,1.45)
    if mode=='dio_face':return im.crop((160,160,660,441)).resize((W,H))
    if mode=='light_grin':
        width=round(1040-340*q);return im.crop((20,100,20+width,100+round(width*9/16))).resize((W,H))
    if mode=='light_mad':
        width=round(1000-120*q);return im.crop((0,70,width,70+round(width*9/16))).resize((W,H))
    return im


def render(path,mode,seconds,envelope=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-','-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(round(seconds*30)):p.stdin.write(frame(mode,n/30,seconds,envelope).tobytes())
        p.stdin.close();err=p.stderr.read();rc=p.wait(timeout=90)
        if rc:raise RuntimeError(err.decode()[-1000:])
    finally:
        if p.poll() is None:p.kill();p.wait()
