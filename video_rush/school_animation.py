"""Original stick-figure story animation, explicitly not game footage."""
import math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .common import font

def render(path,asset):
    seconds=asset.get('seconds',18);ending=asset.get('scene')=='back-to-class'
    if not 1<=seconds<=30:raise ValueError('Editorial animation length must be 1–30 seconds')
    path=Path(path);ink='#29282a';paper='#f7f1e5';red='#ce6854';blue='#4a9cbd'
    fonts={n:ImageFont.truetype(font(True),n) for n in [32,48,64,94]}
    def text(d,xy,value,size=48,color=ink):d.text(xy,value,font=fonts[size],fill=color)
    def stick(d,x,y,phase=0,run=False,raise_hand=False,color=ink):
        bounce=8*math.sin(phase*2) if run else 2*math.sin(phase)
        y+=bounce;d.ellipse((x-38,y-205,x+38,y-129),fill=paper,outline=color,width=7)
        d.line((x,y-129,x,y-35),fill=color,width=8)
        if run:
            a=math.sin(phase)*64
            d.line((x,y-98,x+a,y-70,x+a+30,y-104),fill=color,width=8)
            d.line((x,y-98,x-a,y-140,x-a-28,y-110),fill=color,width=8)
            d.line((x,y-35,x-a*.7,y+20,x-a,y+60),fill=color,width=9)
            d.line((x,y-35,x+a*.7,y+10,x+a,y+60),fill=color,width=9)
        else:
            d.line((x,y-35,x-45,y+50),fill=color,width=9);d.line((x,y-35,x+45,y+50),fill=color,width=9)
            if raise_hand:d.line((x,y-105,x-65,y-180,x-90,y-250),fill=color,width=8);d.line((x,y-105,x+65,y-180,x+90,y-250),fill=color,width=8)
            else:d.line((x,y-105,x-65,y-60),fill=color,width=8);d.line((x,y-105,x+65,y-60),fill=color,width=8)
        d.arc((x-20,y-180,x+20,y-147),5,170,fill=color,width=4)
        # Protagonist's red headband matches the story framing, not a fake game skin.
        d.line((x-38,y-185,x+38,y-185,x+70,y-170),fill=red,width=8)
    args=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-',
          '-an','-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(path)]
    p=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in range(round(seconds*30)):
            t=frame/30;im=Image.new('RGB',(1920,1080),paper);d=ImageDraw.Draw(im)
            for yy in range(120,960,65):d.line((70,yy,1850,yy),fill='#e8dfcc',width=1)
            text(d,(110,125),'课间最终决战' if not ending else '决战暂时中止',64)
            text(d,(1130,145),'原创剧情动画 · 非实机',32,'#8a8171')
            if not ending and t<6:
                d.rounded_rectangle((160,290,1000,590),radius=12,fill='#385d52',outline=ink,width=6)
                text(d,(235,340),'数学 · 最后一道题',48,'#f5efe0')
                text(d,(235,435),'x + y = 下课？',64,'#f5efe0')
                d.ellipse((1270,260,1550,540),fill='#fffaf0',outline=ink,width=8)
                a=-math.pi/2+t*.9
                d.line((1410,400,1410+95*math.cos(a),400+95*math.sin(a)),fill=ink,width=6)
                d.line((1410,400,1380,350),fill=red,width=9)
                stick(d,680,800,t*4,raise_hand=t>2.7)
                if t<2.7:
                    d.rectangle((450,730,910,765),fill='#c69a70',outline=ink,width=6)
                    for xx in [490,875]:d.line((xx,765,xx,910),fill=ink,width=7)
                else:
                    text(d,(1110,660),'下——课——！',64,red)
                    for k in range(8):
                        ang=k*math.pi/4;d.line((1410+160*math.cos(ang),400+160*math.sin(ang),1410+200*math.cos(ang),400+200*math.sin(ang)),fill=red,width=6)
            elif not ending and t<12:
                text(d,(130,300),'目标：操场最强',64,red)
                x=340+(t-6)*170;stick(d,x,710,t*13,run=True)
                d.rectangle((1520,290,1770,850),outline=ink,width=9);text(d,(1545,330),'操场',48)
                for k in range(12):
                    yy=460+(k%6)*55;xx=150+((k*147+t*900)%1000)
                    d.line((xx,yy,xx-100,yy),fill='#c9bb9e',width=4)
            else:
                d.line((180,800,1740,800),fill='#a6ab8d',width=4)
                if ending:
                    text(d,(180,310),'上课了！世界先别救了！',64,red)
                    for i in range(2):stick(d,1120-i*360+130*math.sin(t*.8),695,t*12+i,run=True)
                    d.rectangle((170,470,380,810),outline=ink,width=7);text(d,(190,505),'教室',48)
                    x=1550+8*math.sin(t*25);d.arc((x-65,465,x+65,605),180,360,fill=red,width=8);d.line((x-65,535,x+65,535),fill=red,width=8)
                else:
                    text(d,(350,285),'放学别走！课间也别走！',64,red)
                    stick(d,610,705,t*3,raise_hand=True);stick(d,1300,705,t*3+1,raise_hand=True)
                    radius=40+13*math.sin(t*8);d.ellipse((960-radius,530-radius,960+radius,530+radius),fill='#a4d1dc',outline=blue,width=6)
                    text(d,(850,720),'拍！拍！',48,blue)
            p.stdin.write(im.tobytes())
        p.stdin.close();err=p.stderr.read();code=p.wait(timeout=60)
        if code:raise RuntimeError('Editorial animation encoder failed: '+err.decode()[-800:])
    finally:
        if p.poll() is None:p.kill();p.wait()
