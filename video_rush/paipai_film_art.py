"""Original articulated R-layer animation for the user's approved screenplay.

No game UI, collision or outcome is drawn here. Those layers are real recordings.
"""
import math
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw,ImageFont
from .common import font

W,H=1280,720;PAPER='#faf5e8';INK='#242b30';RED='#d84f49';BLUE='#3d7f9a';GOLD='#e5b85f'
FONTS={n:ImageFont.truetype(font(True),n) for n in (24,30,38,48,58,72,96,128)}
def text(d,p,s,n=38,c=INK,anchor=None):d.text(p,s,font=FONTS[n],fill=c,anchor=anchor)
def stroke(d,pts,c=INK,w=5):
 d.line(pts,fill=c,width=w,joint='curve')
 for x,y in (pts[0],pts[-1]):d.ellipse((x-w/2,y-w/2,x+w/2,y+w/2),fill=c)
def smooth(x):return max(0,min(1,x))**2*(3-2*max(0,min(1,x)))


def person(d,x,y,t,who='A',adult=False,pose='idle',mood='normal',talk=False,scale=1,glasses_flash=False,fingers=0,limb_color=None):
 face=RED if who=='A' else BLUE
 def P(a,b):return(x+a*scale,y+b*scale)
 def L(pts,c=None,w=6):stroke(d,[P(a,b) for a,b in pts],c or limb_color or INK,max(2,round(w*scale)))
 phase=t*7;bounce=math.sin(t*3)*2;neck=(0,-176+bounce);hip=(0,-75+bounce);hc=(0,-225+bounce)
 if pose=='nod':hc=(0,-225+math.sin(t*22)*8);neck=(0,-176)
 if pose=='sag':
  q=smooth(t/.3);neck=(18*q,-176+48*q);hc=(43*q,-225+48*q);hip=(0,-80+25*q)
 if pose in ('jojo','jojo_point'):neck=(-20,-160);hip=(20,-75);hc=(-30,-210)
 if pose=='lean':neck=(25,-176);hc=(35,-224)
 L([hip,neck],w=7)
 if pose in ('seated','phone','clap-seat'):
  L([hip,(-62,-61),(-64,0)]);L([hip,(57,-58),(62,0)])
 else:L([hip,(-32,-34),(-60,0)]);L([hip,(33,-34),(58,0)])
 sign=1 if who=='A' else -1
 if pose in ('clap','clap-seat'):
  gap=10+50*(.5-.5*math.cos(t*2*math.pi/.63));L([neck,(-65,-135),(-gap,-150)]);L([neck,(65,-135),(gap,-150)])
 elif pose in ('hadoken','beam'):
  q=smooth((t-.3)/.65);q=0 if pose=='hadoken' and t<.7 else q
  if pose=='beam':L([neck,(48*sign,-153),(48*sign,-240)]);L([neck,(-55*sign,-150),(48*sign,-150)])
  else:L([neck,(-48*sign,-117),((5+75*q)*sign,-126-22*q)]);L([neck,(-65*sign,-143),((8+75*q)*sign,-133-22*q)])
 elif pose=='fan':
  q=math.sin(t*7)*.12;L([neck,(52*sign,-135),(90*sign,-185)]);L([neck,(-52*sign,-120),(-75*sign,-150)])
  px,py=P(102*sign,-200);rr=46*scale;d.ellipse((px-rr,py-rr*1.2,px+rr,py+rr*1.2),fill='#e9dfcd',outline=INK,width=4)
  stroke(d,[(px-rr*.5,py),(px+rr*.5,py)],RED,4)
 elif pose=='point':
  L([neck,(48*sign,-164),((113+4*math.sin(phase))*sign,-195)]);L([neck,(-50*sign,-119),(-56*sign,-89)])
 elif pose=='open':
  amp=5*math.sin(t*8);L([neck,(-70,-160),(-135,-210+amp)]);L([neck,(70,-160),(135,-210-amp)])
 elif pose=='jojo':L([neck,(-72,-221),(-55,-280)]);L([neck,(70,-137),(28,-102)])
 elif pose=='jojo_point':
  L([neck,(-72,-167),(-115,-200)],w=8);L([neck,(70,-137),(28,-102)])
  px,py=P(-115,-200);rr=15*scale;d.ellipse((px-rr,py-rr,px+rr,py+rr),fill=PAPER,outline=INK,width=4)
  stroke(d,[(px-rr/2,py-rr/2),(px-26*scale,py-42*scale)],INK,max(4,round(6*scale)))
 elif pose=='baby':L([neck,(-65,-127),(20,-120)]);L([neck,(67,-128),(20,-116)])
 elif pose=='phone':
  L([neck,(-42,-130),(12,-140)]);L([neck,(55,-126),(25,-140)])
  xx,yy=P(20,-162);d.rounded_rectangle((xx-13*scale,yy-24*scale,xx+13*scale,yy+24*scale),radius=4*scale,fill=BLUE,outline=INK,width=2)
 elif fingers:
  L([neck,(52*sign,-145),(62*sign,-224)]);L([neck,(-46*sign,-120),(-65*sign,-112)])
  px,py=P(62*sign,-234);r=17*scale;d.ellipse((px-r,py-r,px+r,py+r),fill=PAPER,outline=INK,width=3)
  for i in range(fingers):
   a=-math.pi*.85+i*(math.pi*.7/max(1,fingers-1));stroke(d,[(px+12*math.cos(a)*scale,py+12*math.sin(a)*scale),(px+45*math.cos(a)*scale,py+45*math.sin(a)*scale)],INK,round(5*scale))
 else:
  amp=7*math.sin(phase) if talk else 2*math.sin(t*3);L([neck,(-48,-130),(-70,-102-amp)]);L([neck,(48,-128),(70,-103+amp)])
 hx,hy=P(*hc);r=43*scale
 d.ellipse((hx-r,hy-r,hx+r,hy+r),fill=PAPER,outline=INK,width=max(2,round(5*scale)))
 if adult:
  for xx in (-18,-10,2,11):stroke(d,[(hx+xx*scale,hy+25*scale),(hx+(xx+3)*scale,hy+30*scale)],'#6c6c67',2)
  for xx in (-6,3,10):stroke(d,[(hx+xx*scale,hy-r),(hx+(xx-7)*scale,hy-r-13*scale)],INK,2)
 if who=='A':stroke(d,[(hx-r,hy-18*scale),(hx+r,hy-18*scale),(hx+r+35*scale,hy+math.sin(t*10)*8*scale)],RED,max(3,round(7*scale)))
 if mood in ('evil','laugh','yell','smug','angry'):
  d.polygon([(hx-r+5,hy-r*.55),(hx+r-5,hy-r*.55),(hx+r-3,hy+2),(hx-r+3,hy+2)],fill='#bdbbb2')
 eye_y=hy-3*scale
 for i,dx in enumerate((-17,17)):
  ex=hx+dx*scale
  if mood in ('shock','stiff'):
   d.ellipse((ex-13*scale,eye_y-17*scale,ex+13*scale,eye_y+16*scale),fill='white',outline=INK,width=3);d.ellipse((ex-2*scale,eye_y-2*scale,ex+2*scale,eye_y+2*scale),fill=INK)
  elif mood=='tired':
   stroke(d,[(ex-11*scale,eye_y-1),(ex+10*scale,eye_y+1)],INK,4);d.arc((ex-12*scale,eye_y-2,ex+12*scale,eye_y+18*scale),0,180,fill='#9a9c94',width=3)
  elif mood in ('evil','laugh','yell','smug','angry'):
   direction=1 if i==0 else -1;stroke(d,[(ex-12*scale,eye_y-7*scale*direction),(ex+11*scale,eye_y+7*scale*direction)],INK,max(3,round(4*scale)))
   d.ellipse((ex-3*scale,eye_y+2*scale,ex+3*scale,eye_y+8*scale),fill=RED if mood=='evil' else INK)
  else:
   blink=math.sin(t*2.1+1)> .985
   if blink:stroke(d,[(ex-5,eye_y),(ex+5,eye_y)],INK,3)
   else:d.ellipse((ex-3*scale,eye_y-4*scale,ex+3*scale,eye_y+4*scale),fill=INK)
 if who=='B':
  for dx in (-18,18):d.ellipse((hx+(dx-15)*scale,hy-21*scale,hx+(dx+15)*scale,hy+15*scale),outline=BLUE,width=max(3,round(4*scale)))
  stroke(d,[(hx-3*scale,hy-3*scale),(hx+3*scale,hy-3*scale)],BLUE,3)
  if glasses_flash:
   for dx in (-18,18):d.ellipse((hx+(dx-12)*scale,hy-18*scale,hx+(dx+12)*scale,hy+12*scale),fill='white')
 if mood in ('evil','laugh','yell','angry'):
  stretch=(20+14*abs(math.sin(t*13)) if talk else 13)*scale
  box=(hx-25*scale,hy+13*scale,hx+27*scale,hy+13*scale+stretch)
  d.ellipse(box,fill=INK);d.rectangle((hx-19*scale,hy+14*scale,hx+21*scale,hy+19*scale),fill='white')
 elif mood=='shock':d.ellipse((hx-9*scale,hy+18*scale,hx+9*scale,hy+36*scale),fill=INK)
 elif talk:
  opening=(3+9*abs(math.sin(t*15)))*scale;d.ellipse((hx-12*scale,hy+19*scale-opening/2,hx+12*scale,hy+19*scale+opening/2),fill=INK)
 elif mood in ('stiff','tired'):stroke(d,[(hx-14*scale,hy+25*scale),(hx+13*scale,hy+24*scale)],INK,3)
 else:d.arc((hx-18*scale,hy+9*scale,hx+18*scale,hy+33*scale),0,180,fill=INK,width=3)
 return hx,hy,r


def corridor(d):
 d.polygon([(0,0),(1280,0),(1120,430),(160,430)],fill='#eee9da')
 for x in (160,480,800,1120):stroke(d,[(x,60),(x,475)],'#c8c9bd',3)
 for x in (185,505,825):
  d.rounded_rectangle((x,100,x+260,310),12,fill='#dce6df',outline='#aeb7ad',width=3)
  stroke(d,[(x+130,100),(x+130,310)],'#aeb7ad',3)
 d.rectangle((1020,55,1240,115),fill=PAPER,outline=INK,width=2);text(d,(1130,85),'二年三班',30,INK,'mm')
 stroke(d,[(0,650),(1280,650)],'#c9c1a9',3)


def table(d):
 for x in (170,1110):
  stroke(d,[(x,0),(x,100)],'#a5a291',3);d.polygon([(x-60,135),(x-25,100),(x+25,100),(x+60,135)],fill=GOLD)
 d.rounded_rectangle((140,460,1140,500),14,fill='#bc9367',outline=INK,width=4)
 for x in (230,1050):stroke(d,[(x,500),(x,710)],INK,7)
 for x in (550,730):
  d.rounded_rectangle((x-16,418,x+16,458),5,fill='#e0b457',outline=INK,width=3);d.rectangle((x-13,420,x+13,431),fill='white')
 d.ellipse((606,445,682,463),fill='#e9d7ae',outline=INK,width=2)


def image(shot,t,seconds):
 scene=shot['scene'];id=shot['id'];im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
 lines=shot.get('scheduled_lines',[]);active=next((x for x in lines if x['start']<=t<x['end']),{})
 speaker=active.get('speaker','');talkA=speaker.endswith('A');talkB=speaker.endswith('B')
 evil_phase=scene=='turn-evil' and len(lines)>1 and t>=lines[1]['start']
 adult=id[0] in ('1','2','6','7');a_mood='normal';b_mood='normal';pa='idle';pb='idle';fa=fb=0;flash=False
 if scene=='boss':
  person(d,395,690,t,'A',True,'nod','tired',talkA,1.55)
  d.ellipse((810,80,1230,480),fill='#ddcbb8',outline=INK,width=8);text(d,(1010,125),'？',72,RED,'mm')
  d.ellipse((900,260,1180,350+45*abs(math.sin(t*23))),fill=INK)
  for k in range(7):
   xx=1080-((t*900+k*155)%760);yy=280+math.sin(t*19+k)*65;text(d,(xx,yy),['@#￥%','★※#！','！！'][k%3],48,RED)
  return im
 if scene=='baby':
  person(d,395,690,t,'A',True,'nod','tired' if t>.55 else 'normal',talkA,1.55)
  xx=510+8*math.sin(t*22);yy=510
  d.ellipse((xx-95,yy-30,xx+92,yy+60),fill='#c6dce1',outline=INK,width=5);d.ellipse((xx-103,yy-50,xx-28,yy+25),fill=PAPER,outline=INK,width=5)
  text(d,(700,330),'哇——！',96,RED);stroke(d,[(xx-100,yy-10),(xx-130,yy+28)],BLUE,5);return im
 if scene in ('collapse','message'):
  d.rounded_rectangle((250,365,1050,660),35,fill='#d1d9ce',outline=INK,width=5)
  person(d,585,640+40*smooth(t/.25),t,'A',True,'sag','tired',talkA,1.5)
  if scene=='collapse':
   pct=1 if t<.3 else 0;d.rounded_rectangle((840,180,990,235),8,outline=INK,width=4);d.rectangle((846,186,846+128*pct,228),fill=RED);text(d,(915,145),f'{pct}%',48,RED,'mm')
  else:
   d.rounded_rectangle((780,100,1190,295),24,fill='white',outline=INK,width=4);text(d,(985,150),'老朋友',30,BLUE,'mm');text(d,(985,225),'出来喝两杯？',48,INK,'mm')
  return im
 if scene in ('bar','body-memory','slide-phone','home-phone','old-clap','phone-banter','double-age','back-now'):
  if scene=='home-phone':
   person(d,390,720,t,'B',True,'phone','shock' if t<seconds-.6 else 'laugh',talkB,1.9)
   if t>.30:d.rounded_rectangle((840,35,1145,685),30,fill=INK);d.rounded_rectangle((855,55,1130,650),10,fill=PAPER)
   return im
  age=True
  if scene=='back-now':age=t>.27
  poseA=poseB='seated';ma='smug' if id.startswith('6') else 'normal';mb='normal'
  if scene=='body-memory':poseB='clap-seat';poseA='clap-seat' if t>.33 else 'seated'
  if scene in ('old-clap','double-age'):poseA=poseB='clap-seat'
  if scene=='double-age':ma=mb='laugh';talkA=talkB=True
  if scene in ('phone-banter','home-phone'):poseB='phone';mb='shock' if scene=='home-phone' and t<seconds-.5 else 'normal'
  if scene=='back-now':poseB='point'
  person(d,355,680,t,'A',age,poseA,ma,talkA,1.4)
  person(d,925,680,t,'B',age,poseB,mb,talkB,1.4)
  table(d)
  if scene=='slide-phone':
   x=500+min(1,t/.75)*310;d.rounded_rectangle((x,440,x+100,466),6,fill=BLUE,outline=INK,width=3)
  if scene=='double-age':
   layer=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(layer)
   person(ld,355,680,t,'A',False,'clap-seat','laugh',True,1.4)
   person(ld,925,680,t,'B',False,'clap-seat','laugh',True,1.4)
   alpha=.40*math.sin(math.pi*smooth(t/max(.1,seconds)))
   layer.putalpha(layer.getchannel('A').point(lambda v:round(v*alpha)));im=Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')
  if scene=='back-now' and t<.30:return im.crop((620,300,1020,525)).resize((W,H))
  return im
 if scene=='flashback':
  adult=t<.7
  if not adult:corridor(d)
  person(d,355,650,t,'A',adult,'clap','smug',talkA,1.45)
  person(d,925,650,t,'B',adult,'clap','normal',talkB,1.45)
  if .35<t<.8:
   # Match the same two moving palms across the age cut.
   return im.crop((650,220,1240,552)).resize((W,H))
  return im
 if scene=='title':
  text(d,(640,220),'拍拍波',128,INK,'mm');text(d,(640,358),'小时候没打完的，现在接着打。',48,RED,'mm')
  text(d,(640,485),shot.get('end_url','zhipijun1996.github.io/wave-game'),38,BLUE,'mm');return im
 corridor(d)
 if scene in ('evil-A','turn-evil'):a_mood='evil';pa='open' if scene=='turn-evil' else 'idle'
 if scene=='evil-B':b_mood='laugh';pb='open';flash=t<.25
 if scene=='turn-evil' and not evil_phase:a_mood='stiff';pa='idle'
 if scene=='shock-A':a_mood='shock';b_mood='smug';flash=t<.2
 if scene=='spell-B':
  a_mood='shock' if t>5.69 else 'smug';b_mood='evil';pb='point';flash=t<.3;talkB=.1<t<5.75
 if scene=='argument':pa='point' if talkA else 'idle';b_mood='evil' if talkB else 'smug';flash=talkB and t%1<.2
 if scene=='agree':a_mood='smug';b_mood='stiff';pa='point'
 if scene in ('three','three-taunt'):fa=3;a_mood='smug';b_mood='shock' if scene=='three-taunt' else 'normal'
 if scene=='five':fa=5;a_mood='smug';b_mood='shock'
 if scene=='hadoken-A':pa='hadoken';a_mood='yell'
 if scene=='hadoken-B':pb='hadoken';b_mood='smug';a_mood='evil' if talkA else 'shock'
 if scene=='stiff-A':a_mood='stiff';b_mood='smug';flash=t<.25
 if scene=='return-A':
  pa='fan';a_mood='evil';b_mood='shock'
  if shot.get('angry_counter') and active.get('speaker','').endswith('B') and t>=3.20:b_mood='angry';pb='point'
 if scene=='dio':a_mood='yell';pb='fan';b_mood='smug';pa='open'
 if scene=='ultra-A':pa='beam';a_mood='yell'
 if scene=='king':pa=shot.get('victory_pose','jojo');a_mood='yell';pb='point';b_mood='stiff'
 dramatic=scene=='evil-B' or evil_phase
 if dramatic:
  im=Image.new('RGB',(W,H),'#251b2c' if scene=='evil-B' else '#343726');d=ImageDraw.Draw(im)
  for i in range(35):
   a=i*math.tau/35+t*.08;cx=925 if scene=='evil-B' else 355
   stroke(d,[(cx+180*math.cos(a),300+150*math.sin(a)),(cx+1000*math.cos(a),300+700*math.sin(a))],RED if scene=='evil-B' else GOLD,3)
 person(d,355,650,t,'A',False,pa,a_mood,talkA,1.45,fingers=fa,limb_color=PAPER if dramatic else None)
 person(d,925,650,t,'B',False,pb,b_mood,talkB,1.45,glasses_flash=flash,fingers=fb,limb_color=PAPER if dramatic else None)
 if scene=='king':
  yy=min(278, -140+t*650);pts=[(255,yy),(245,yy-60),(285,yy-35),(311,yy-85),(340,yy-35),(375,yy-60),(365,yy)]
  d.polygon(pts,fill=GOLD,outline=INK);stroke(d,pts+[pts[0]],INK,4)
 if scene in ('evil-B','evil-A','shock-A'):
  box=(480,100,1280,550) if scene=='evil-B' else (0,130,800,580)
  im=im.crop(box).resize((W,H))
 if scene=='spell-B':im=im.crop((480,100,1280,550) if t<5.69 else (0,130,800,580)).resize((W,H))
 if scene in ('three','three-taunt','five'):im=im.crop((0,120,850,598)).resize((W,H))
 if evil_phase:
  q=smooth((t-active.get('start',t))/.45);left=round(0+30*q);width=round(1280-500*q)
  im=im.crop((left,round(100*q),left+width,round(100*q)+round(width*9/16))).resize((W,H))
 return im


def render(path,shot,seconds):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30','-i','-',
  '-an','-vf','scale=1920:1080,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','22','-threads','2',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for n in range(round(seconds*30)):p.stdin.write(image(shot,n/30,seconds).tobytes())
  p.stdin.close();err=p.stderr.read();rc=p.wait(timeout=90)
  if rc:raise RuntimeError(err.decode()[-1000:])
 finally:
  if p.poll() is None:p.kill();p.wait()
