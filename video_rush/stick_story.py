"""Original animated stick-figure scenes for a fictional first-person story."""
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

from .common import font

W,H=1280,720
PAPER='#f7f4eb';INK='#282b2a';RED='#bf5146';BLUE='#527b87';LIGHT='#dedfd4'
FONTS={n:ImageFont.truetype(font(True),n) for n in (20,24,30,38,48,64,80)}


def words(d,xy,s,size=30,fill=INK,anchor=None):
    d.text(xy,s,font=FONTS[size],fill=fill,anchor=anchor)


def line(d,pts,fill=INK,width=5):
    d.line([(round(x),round(y)) for x,y in pts],fill=fill,width=width,joint='curve')
    for x,y in (pts[0],pts[-1]):d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=fill)


def actor(d,x,y,t,*,adult=True,friend=False,boss=False,pose='stand',scale=1,expression='normal',color=INK,crown=False):
    """y is ground; poses articulate hands, elbows, knees and torso."""
    def pt(a,b):return (x+a*scale,y+b*scale)
    def limb(points,stroke=color,width=5):line(d,[pt(a,b) for a,b in points],stroke,max(2,round(width*scale)))
    bob=2*math.sin(t*3);hip=(0,-84+bob);neck=(-8,-172+bob);head=(-8,-207+bob)
    if pose=='slump':hip=(0,-85);neck=(36,-149);head=(58,-174)
    if pose=='run':hip=(0,-86+6*math.sin(t*12));neck=(24,hip[1]-85);head=(34,neck[1]-33)
    if pose=='seated':hip=(0,-100);neck=(-8,-186+bob);head=(-8,-221+bob)
    limb([hip,neck],width=6)
    if pose=='run':
        a=math.sin(t*12)*52;limb([hip,(-a,-40),(-a*1.25,-3)]);limb([hip,(a,-38),(a*1.3,-4)])
        limb([neck,(35+a*.5,-120),(50+a*.65,-170)]);limb([neck,(-20-a*.6,-135),(-50-a*.5,-90)])
    elif pose=='seated':
        limb([hip,(62,-80),(60,0)]);limb([hip,(-55,-68),(-65,0)])
        reach=8*math.sin(t*2)
        limb([neck,(-49,-135),(-75,-155-reach)]);limb([neck,(48,-141),(88,-171+reach)])
    else:
        limb([hip,(-30,-39),(-48,0)]);limb([hip,(29,-38),(49,0)])
        if pose=='point':
            direction=-1 if friend or boss else 1;reach=7*math.sin(t*8)
            limb([neck,(direction*45,-168),(direction*(107+reach),-188)]);limb([neck,(-direction*35,-120),(-direction*15,-95)])
        elif pose=='baby':
            limb([neck,(-47,-123),(0,-107)]);limb([neck,(53,-113),(8,-102)])
        elif pose in ('charge','fight'):
            a=5*math.sin(t*8);limb([neck,(-54,-136),(-10,-133-a)]);limb([neck,(53,-136),(15,-133+a)])
        elif pose=='beam':
            limb([neck,(50,-155),(50,-227)]);limb([neck,(-60,-146),(49,-146)])
        elif pose=='phone':
            limb([neck,(-32,-132),(24,-145)]);limb([neck,(45,-126),(24,-145)])
        elif pose=='cheer':
            limb([neck,(-54,-219),(-80,-265)]);limb([neck,(54,-219),(80,-265)])
        elif pose=='slump':
            limb([neck,(62,-114),(73,-73)]);limb([neck,(16,-109),(8,-64)])
        else:
            limb([neck,(-42,-130),(-65,-107)]);limb([neck,(43,-131),(65,-108)])
    hx,hy=pt(*head);r=32*scale
    d.ellipse((hx-r,hy-r,hx+r,hy+r),fill=PAPER,outline=color,width=max(2,round(4*scale)))
    if adult:
        d.arc((hx-r+5*scale,hy-r-5*scale,hx+r-5*scale,hy+10*scale),185,257,fill=color,width=max(2,round(4*scale)))
        for a in (-9,-3,4):limb([(head[0]+a,head[1]-31),(head[0]+a-4,head[1]-39)],width=2)
        for dx in (-15,-7,4,13):line(d,[(hx+dx*scale,hy+20*scale),(hx+(dx+2)*scale,hy+24*scale)],color,max(1,round(scale)))
    if friend:
        for dx in (-13,13):d.ellipse((hx+(dx-10)*scale,hy-10*scale,hx+(dx+10)*scale,hy+10*scale),outline=BLUE,width=max(2,round(3*scale)))
        line(d,[(hx-3*scale,hy),(hx+3*scale,hy)],BLUE,max(2,round(2*scale)))
    elif not boss:
        line(d,[(hx-r,hy-12*scale),(hx+r,hy-12*scale),(hx+r+27*scale,hy-4*scale)],RED,max(3,round(6*scale)))
    if boss:
        nx,ny=pt(*neck);d.polygon([(nx,ny+9*scale),(nx-8*scale,ny+42*scale),(nx,ny+52*scale),(nx+8*scale,ny+42*scale)],fill=BLUE)
    for dx in (-12,12):
        ex=hx+dx*scale
        if expression=='shock':d.ellipse((ex-4*scale,hy-5*scale,ex+4*scale,hy+4*scale),fill=color)
        elif expression=='tired':line(d,[(ex-5*scale,hy),(ex+5*scale,hy+1*scale)],color,max(2,round(2*scale)))
        else:d.ellipse((ex-2*scale,hy-2*scale,ex+2*scale,hy+2*scale),fill=color)
    if expression=='shock':d.ellipse((hx-6*scale,hy+10*scale,hx+6*scale,hy+24*scale),outline=color,width=max(2,round(2*scale)))
    elif expression=='talk':
        a=(3+4*abs(math.sin(t*15)))*scale;d.ellipse((hx-8*scale,hy+13*scale-a,hx+8*scale,hy+13*scale+a),fill=color)
    elif expression=='tired':line(d,[(hx-9*scale,hy+18*scale),(hx+7*scale,hy+16*scale)],color,max(2,round(2*scale)))
    else:d.arc((hx-12*scale,hy+4*scale,hx+12*scale,hy+24*scale),5,175,fill=color,width=max(2,round(2*scale)))
    if crown:
        pts=[(hx-r,hy-r-6*scale),(hx-r-8*scale,hy-r-40*scale),(hx-10*scale,hy-r-28*scale),
             (hx,hy-r-52*scale),(hx+13*scale,hy-r-28*scale),(hx+r+8*scale,hy-r-40*scale),(hx+r,hy-r-6*scale)]
        d.polygon(pts,fill='#e5ba51',outline=color);line(d,pts+[pts[0]],color,max(2,round(3*scale)))
    if pose=='phone':
        xx,yy=pt(24,-163);d.rounded_rectangle((xx-14*scale,yy-22*scale,xx+14*scale,yy+22*scale),radius=4*scale,fill=BLUE,outline=color,width=2)


def glass(d,x,y,t=0):
    d.rounded_rectangle((x-15,y-37,x+15,y+4),radius=4,fill='#e3bb65',outline=INK,width=3)
    d.rectangle((x-12,y-36,x+12,y-25),fill='#fffef8')
    d.arc((x+8,y-30,x+29,y),270,90,fill=INK,width=3)


def frame(scene,t,seconds):
    im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
    # Restrained set dressing; the foreground is always the same two characters.
    if scene=='office':
        for x in range(100,1200,200):d.rectangle((x,100,x+150,330),outline=LIGHT,width=2)
        d.rectangle((240,493,830,520),fill='#b6aa90');line(d,[(300,520),(300,635)]);line(d,[(780,520),(780,635)])
        d.rounded_rectangle((365,333,563,469),radius=7,fill='#d9dfda',outline=INK,width=4);line(d,[(464,469),(464,494)])
        actor(d,650,590,t,pose='seated',expression='tired');actor(d,1000,610,t,boss=True,pose='point',expression='talk')
        d.rectangle((950,355,1006,415),fill='#fffdf4',outline=RED,width=3);words(d,(978,384),'改',30,RED,'mm')
    elif scene=='baby':
        d.rectangle((180,260,410,520),outline=LIGHT,width=3);d.arc((930,300,1120,490),180,360,fill=LIGHT,width=4)
        x=640+10*math.sin(t*6);actor(d,x,605,t,pose='baby',expression='talk',scale=1.55)
        by=430+7*math.sin(t*6);d.ellipse((x-100,by-20,x+61,by+57),fill='#d3e1e0',outline=INK,width=4)
        d.ellipse((x-109,by-31,x-48,by+30),fill=PAPER,outline=INK,width=4)
        words(d,(x-170,by-67),'哇' if int(t*4)%2 else '哇——',38,RED)
        for a in (-1,1):line(d,[(x-115+a*15,by-20),(x-128+a*30,by-40)],BLUE,3)
    elif scene in ('collapse','message'):
        d.rounded_rectangle((280,420,990,610),radius=30,fill='#d9ded4',outline=INK,width=4)
        actor(d,618,609,t,pose='slump',expression='tired',scale=1.6)
        if scene=='message':
            d.rounded_rectangle((820,120,1110,340),radius=25,fill='#fffdf7',outline=INK,width=4)
            words(d,(965,165),'老朋友',30,BLUE,'mm');words(d,(965,248),'出来坐坐？',38,INK,'mm')
        else:
            for i in range(3):words(d,(760+i*65,215+math.sin(t*3+i)*9),'…',48,'#8e938c')
    elif scene in ('bar','bar-me','bar-friend','phone','ending'):
        for x in (220,1060):
            line(d,[(x,0),(x,120)],LIGHT,3);d.polygon([(x-50,150),(x-25,119),(x+25,119),(x+50,150)],fill='#ddc590')
        if scene=='ending':
            actor(d,480,500,t,adult=False,pose='fight',scale=1.25,color='#c2c8bb')
            actor(d,800,500,t,adult=False,friend=True,pose='fight',scale=1.25,color='#c2c8bb')
        pose='phone' if scene=='phone' else 'seated'
        actor(d,400,642,t,pose=pose,expression='talk' if scene=='bar-me' else 'normal',scale=1.35)
        actor(d,880,642,t+.7,friend=True,pose=pose,expression='talk' if scene=='bar-friend' else 'normal',scale=1.35)
        d.rounded_rectangle((190,450,1090,487),radius=10,fill='#bca884',outline=INK,width=4)
        for x in (270,1010):line(d,[(x,487),(x,670)],INK,7)
        glass(d,555,441);glass(d,735,441)
        d.ellipse((620,432,684,450),fill='#e9e1c9',outline=INK,width=2)
    elif scene=='clink':
        u=min(1,t/.7);lx=420+210*u;rx=860-210*u
        line(d,[(40,650),(lx-80,420),(lx,375)],INK,12);line(d,[(1240,650),(rx+80,420),(rx,375)],INK,12)
        glass(d,lx,365);glass(d,rx,365)
        if u>.9:
            for a in range(5):
                v=-math.pi+a*math.pi/4;line(d,[(640+50*math.cos(v),315+50*math.sin(v)),(640+75*math.cos(v),315+75*math.sin(v))],RED,5)
    elif scene=='recess':
        d.rectangle((70,100,430,560),outline=INK,width=5);words(d,(250,160),'教室',38,INK,'mm')
        x=360+min(t*210,650);actor(d,x,585,t,adult=False,pose='run',scale=1.35)
        for i in range(8):
            xx=70+((i*94-t*500)%800);line(d,[(xx,360+i*24),(xx+75,360+i*24)],LIGHT,3)
    elif scene in ('challenge','training','transform','reaction','crown'):
        line(d,[(100,600),(1180,600)],'#aab69e',3)
        if scene=='reaction':
            actor(d,640,830,t,adult=False,expression='shock',scale=2.8)
            words(d,(925,225),'？',80,RED)
        elif scene=='transform':
            for i in range(18):
                a=i*math.pi/9+t*.5;r=80+min(t,1.5)*170
                line(d,[(640+r*.45*math.cos(a),370+r*.45*math.sin(a)),(640+r*math.cos(a),370+r*math.sin(a))],'#d9b668',4)
            actor(d,640,630,t,adult=False,pose='cheer' if t<1.2 else 'beam',scale=1.8)
        elif scene=='training':
            n=int(t*2)%3;x=640+(n-1)*100
            actor(d,x,600,t*1.5,adult=False,pose=['fight','charge','beam'][n],scale=1.65)
            for i in range(10):
                a=i*math.pi/5+t*.2;line(d,[(x+210*math.cos(a),365+170*math.sin(a)),(x+270*math.cos(a),365+220*math.sin(a))],LIGHT,3)
        elif scene=='crown':
            actor(d,640,630,t,adult=False,pose='cheer',scale=1.8,crown=True)
            for i in range(23):
                x=(i*137+17*t)%1280;y=(i*47+t*60)%610;d.rectangle((x,y,x+6,y+12),fill=(RED,BLUE,'#d6b357')[i%3])
        else:
            actor(d,410,610,t,adult=False,pose='fight',scale=1.6)
            actor(d,870,610,t+.4,adult=False,friend=True,pose='fight',scale=1.6)
    elif scene=='title':
        actor(d,290,610,t,adult=False,pose='beam',scale=1.5)
        actor(d,990,610,t,adult=False,friend=True,pose='fight',scale=1.5)
        words(d,(640,210),'拍拍波',80,INK,'mm');words(d,(640,315),'小时候没打完的，接着打。',38,RED,'mm')
        words(d,(640,430),'手机试玩：zhipijun1996.github.io/wave-game',24,BLUE,'mm')
    else:raise ValueError('Unknown story scene '+scene)
    return im


def render(path,scene,seconds):
    if not .2<=seconds<=30:raise ValueError('Story animation duration must be .2–30 seconds')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-',
                        '-an','-vf','scale=1920:1080:flags=lanczos,format=yuv420p','-c:v','libx264','-threads','2',
                        '-preset','veryfast','-crf','22','-movflags','+faststart',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(round(seconds*30)):p.stdin.write(frame(scene,i/30,seconds).tobytes())
        p.stdin.close();err=p.stderr.read();rc=p.wait(timeout=60)
        if rc:raise RuntimeError(err.decode()[-1500:])
    finally:
        if p.poll() is None:p.kill();p.wait()
