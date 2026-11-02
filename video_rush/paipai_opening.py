"""Adult establishing shot and audio-envelope-driven boss/worker mouths."""
import math
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from .paipai_film_art import PAPER,INK,BLUE,RED,stroke,person,text


def frame(mode,t,seconds,worker=None,boss=None):
    im=Image.new('RGB',(1280,720),PAPER);d=ImageDraw.Draw(im)
    def amplitude(values):return values[min(len(values)-1,int(t*30))] if values else 0
    if mode=='intro':
        d.rectangle((0,0,1280,460),fill='#e1e5df')
        d.rounded_rectangle((75,100,390,380),20,fill='#c7d9da',outline=INK,width=5)
        for x in [180,285]:stroke(d,[(x,100),(x,380)],'#9eb2b5',3)
        # A morning routine before the abrupt comic intrusion of the boss.
        person(d,620,685,t,'A',True,'seated','tired',False,1.5)
        d.rectangle((300,570,1040,600),fill='#caa578',outline=INK,width=5)
        d.rounded_rectangle((825,340,1130,545),12,fill='#687a82',outline=INK,width=6)
        text(d,(977,420),'周 一',48,PAPER,'mm');stroke(d,[(980,545),(980,570)],INK,12)
        d.ellipse((1000,50,1160,210),fill=PAPER,outline=INK,width=5)
        stroke(d,[(1080,130),(1080,77)],INK,5);stroke(d,[(1080,130),(1120,151)],INK,5)
        # A tiny clock-hand drift keeps the quiet introduction alive.
        a=t*.3;stroke(d,[(1080,130),(1080+60*math.sin(a),130-60*math.cos(a))],RED,2)
        return im
    if mode!='boss':raise ValueError(mode)
    a=min(1,amplitude(worker)*6);b=min(1,amplitude(boss)*6)
    # Worker is left, boss is right; separate envelopes prevent false lip motion.
    person(d,395,690,t,'A',True,'nod','tired',False,1.55)
    d.ellipse((810,80,1230,480),fill='#ddcbb8',outline=INK,width=8)
    text(d,(1010,125),'？',72,RED,'mm')
    if b>.03:d.ellipse((900,270-15*b,1180,300+100*b),fill=INK)
    else:stroke(d,[(900,290),(1180,290)],INK,7)
    # Draw worker mouth only when his own captured voice has energy.
    cy=690+(-225+math.sin(t*22)*8)*1.55
    d.rectangle((370,cy+24,420,cy+55),fill=PAPER)
    if a>.05:d.ellipse((375,cy+30-4*a,413,cy+34+23*a),fill=INK)
    else:stroke(d,[(375,cy+40),(413,cy+40)],INK,3)
    if b>.05:
        for k in range(4):
            x=1030-((t*800+k*160)%500);y=280+math.sin(t*14+k)*60
            text(d,(x,y),['@#￥%','！！'][k%2],48,RED)
    return im


def render(path,mode,seconds,**kwargs):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-','-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-color_range','tv',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for n in range(round(seconds*30)):p.stdin.write(frame(mode,n/30,seconds,**kwargs).tobytes())
        p.stdin.close();err=p.stderr.read();code=p.wait(timeout=120)
        if code:raise RuntimeError(err.decode()[-1000:])
    finally:
        if p.poll() is None:p.kill();p.wait()
