"""Original editorial graphics/audio; never rendered as counterfeit game footage."""
from pathlib import Path
import math
import wave
import array
from PIL import Image, ImageDraw, ImageFont
from .common import font


def graphic(path, spec):
    if spec.get('layout') == 'diagram':
        return diagram(path, spec)
    if spec.get('layout') == 'parallax_template':
        im=Image.new('RGB',(3840,720),'#13263a');d=ImageDraw.Draw(im)
        colors=[('#406281','#8298ac'),('#255b61','#73ac9d'),('#574b3e','#c5a969')]
        for row,(background,shape) in enumerate(colors):
            y=row*240
            d.rectangle((0,y,3840,y+240),fill=background)
            for x in range(-180,4000,360):
                d.polygon([(x,y+220),(x+150,y+45+row*15),(x+300,y+220)],fill=shape)
                d.rectangle((x+160,y+85,x+180,y+225),fill='#d6bd78')
                d.ellipse((x+125,y+45,x+215,y+125),fill=shape)
            d.line((0,y+238,3840,y+238),fill='#102131',width=4)
        im.save(path)
        return
    if spec.get('layout') in {'weapon_tree','weapon_skills'}:
        return weapon_diagram(path,spec)
    im=Image.new('RGB',(1920,1080),spec.get('background','#122137'));d=ImageDraw.Draw(im)
    for x in range(40,1920,70):
        for y in range(40,1080,70):d.ellipse((x,y,x+3,y+3),fill='#29415c')
    yellow='#ffe085';cyan='#8cebd2';white='#f4f7ff'
    d.rounded_rectangle((90,120,1830,900),40,fill='#1a304b',outline=cyan,width=4)
    d.text((135,155),spec.get('kicker','原创小剧场'),font=ImageFont.truetype(font(True),34),fill=cyan)
    face=spec.get('face','happy');cx,cy=1510,520
    d.ellipse((cx-170,cy-170,cx+170,cy+170),fill=yellow,outline='#101c2e',width=8)
    if face=='panic':
        for xx in [cx-65,cx+65]:d.line((xx-24,cy-55,xx+24,cy-7),fill='#162436',width=12);d.line((xx+24,cy-55,xx-24,cy-7),fill='#162436',width=12)
        d.ellipse((cx-36,cy+25,cx+36,cy+100),fill='#162436')
        d.polygon([(cx+130,cy-155),(cx+95,cy-95),(cx+160,cy-100)],fill='#78dcff')
    elif face=='thinking':
        d.line((cx-100,cy-50,cx-40,cy-50),fill='#162436',width=12);d.line((cx+35,cy-50,cx+95,cy-50),fill='#162436',width=12)
        d.line((cx-50,cy+70,cx+50,cy+70),fill='#162436',width=12)
    else:
        for xx in [cx-65,cx+65]:d.ellipse((xx-14,cy-48,xx+14,cy-6),fill='#162436')
        d.arc((cx-70,cy-5,cx+70,cy+100),0,180,fill='#162436',width=14)
    lines=spec.get('lines',[]);y=310
    for i,line in enumerate(lines):
        size=spec.get('font_size',80 if len(line)<14 else 64)
        d.text((145,y),line,font=ImageFont.truetype(font(True),size),fill=yellow if i==spec.get('highlight',len(lines)-1) else white)
        y+=132
    if spec.get('footer'):d.text((145,825),spec['footer'],font=ImageFont.truetype(font(),32),fill='#b9c9dc')
    im.save(path)


def diagram(path, spec, *, transparent=False):
    """Render authored diagram primitives to matching PNG and editable SVG.

    Coordinates describe an editorial explanation, never simulated gameplay.
    Reject overflowing labels instead of silently cutting off Chinese text.
    """
    from html import escape
    path = Path(path)
    bg = spec.get('background', '#101b2b')
    im = Image.new('RGBA' if transparent else 'RGB', (1920, 1080), (0,0,0,0) if transparent else bg); d = ImageDraw.Draw(im)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">',
           '<rect width="1920" height="1080" fill="'+('none' if transparent else escape(bg, quote=True))+'"/>']
    def text_at(x, y, value, size=42, color='#eef3fa', bold=False, width=1700):
        size = int(size)
        while size >= 28:
            f = ImageFont.truetype(font(bold), size)
            if d.textlength(value, font=f) <= width: break
            size -= 1
        if size < 28: raise ValueError('Diagram label too long: '+value)
        if not (0 <= x and 0 <= y and x+d.textlength(value,font=f) <= 1920 and y+size*1.5 <= 1080):
            raise ValueError('Diagram text outside canvas: '+value)
        # Top-left em anchoring is shared with SVG's text-before-edge baseline.
        d.text((x,y), value, font=f, fill=color, anchor='lt')
        svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" font-family="Noto Sans CJK SC" font-size="{size}" font-weight="{700 if bold else 400}" fill="{escape(color,quote=True)}">{escape(value)}</text>')
    for e in spec.get('elements', []):
        kind = e['type']; color = e.get('color','#89e6cc')
        if kind == 'text':
            text_at(e['x'],e['y'],e['text'],e.get('size',42),color,e.get('bold',False),e.get('width',1700))
        elif kind in {'rect','circle'}:
            x,y,w,h=e['bounds']; fill=e.get('fill','#1c3048'); stroke=e.get('stroke',color); sw=e.get('stroke_width',3)
            if not (0<=x<x+w<=1920 and 0<=y<y+h<=1080): raise ValueError('Diagram shape outside canvas')
            if kind=='rect':
                r=e.get('radius',16); d.rounded_rectangle((x,y,x+w,y+h),r,fill=fill,outline=stroke,width=sw)
                svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{escape(fill,quote=True)}" stroke="{escape(stroke,quote=True)}" stroke-width="{sw}"/>')
            else:
                d.ellipse((x,y,x+w,y+h),fill=fill,outline=stroke,width=sw)
                svg.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="{escape(fill,quote=True)}" stroke="{escape(stroke,quote=True)}" stroke-width="{sw}"/>')
        elif kind=='line':
            pts=[tuple(p) for p in e['points']]; sw=e.get('width',5)
            if len(pts)<2 or any(not (0<=x<=1920 and 0<=y<=1080) for x,y in pts): raise ValueError('Invalid diagram line')
            d.line(pts,fill=color,width=sw)
            svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{escape(color,quote=True)}" stroke-width="{sw}"/>')
            for a,b in ([(pts[-2],pts[-1])] if e.get('arrow') else []) + ([(pts[1],pts[0])] if e.get('both') else []):
                theta=math.atan2(b[1]-a[1],b[0]-a[0]); length=18
                head=[b,(b[0]-length*math.cos(theta-.45),b[1]-length*math.sin(theta-.45)),(b[0]-length*math.cos(theta+.45),b[1]-length*math.sin(theta+.45))]
                d.polygon(head,fill=color)
                svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in head)+f'" fill="{escape(color,quote=True)}"/>')
        else: raise ValueError('Unknown diagram primitive: '+kind)
    svg.append('</svg>')
    path.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
    im.save(path)


def score(path, seconds=210, sample_rate=24000):
    # Original simple pentatonic note sequence, not sampled from games/music.
    notes=[60,67,69,64,62,67,64,69,60,64,67,72,69,67,62,64]
    data=array.array('h');beat=.4
    for i in range(int(seconds*sample_rate)):
        t=i/sample_rate;step=int(t/beat);phase=t%beat
        midi=notes[step%len(notes)];hz=440*2**((midi-69)/12)
        env=(1-math.exp(-phase*80))*math.exp(-phase*9)
        melody=(math.sin(2*math.pi*hz*t)+.18*math.sin(4*math.pi*hz*t))*env
        bass_hz=440*2**(([48,53,45,55][int(t/(beat*4))%4]-69)/12)
        bass=math.sin(2*math.pi*bass_hz*t)*math.exp(-(t%(beat*2))*6)
        v=(melody*.40+bass*.22)*min(1,t/1.5,max(0,(seconds-t)/2))
        data.append(int(v*15000))
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sample_rate);w.writeframes(data.tobytes())


def effects(path, timeline, sample_rate=24000):
    data=array.array('h',[0])*int((timeline['duration']+1)*sample_rate)
    for shot in timeline['shots']:
        kind=shot.get('sfx')
        if not kind:continue
        start=int((shot['start']+.08)*sample_rate);length=.25 if kind=='pop' else .45
        for j in range(int(length*sample_rate)):
            t=j/sample_rate;env=(1-t/length)**2
            freq=(650+2000*t) if kind=='pop' else (600-900*t)
            v=int(math.sin(2*math.pi*freq*t)*env*3600)
            data[start+j]=max(-30000,min(30000,data[start+j]+v))
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sample_rate);w.writeframes(data.tobytes())


def weapon_diagram(path,spec):
    """Authored explanatory chart; never disguised as an in-game upgrade UI."""
    im=Image.new('RGB',(1920,1080),'#0d1724');d=ImageDraw.Draw(im)
    cyan='#8cebd2';gold='#ffe085';white='#f4f7ff'
    d.text((95,120),spec.get('kicker','九种武器，三条起点'),font=ImageFont.truetype(font(True),66),fill=gold)
    if spec['layout']=='weapon_tree':
        rows=[('普通枪','三连机关枪','恒流激光'),('影步手里剑','散华手里剑','遥控回旋刃'),('反冲炸弹','磁吸遥爆雷','坍缩奇点')]
        for i,(base,a,b) in enumerate(rows):
            y=245+i*215
            color=gold if spec.get('highlight_family')==i else cyan
            d.rounded_rectangle((95,y,600,y+150),25,fill='#1a304b',outline=color,width=3)
            d.text((135,y+45),base,font=ImageFont.truetype(font(True),52),fill=white)
            d.text((645,y+43),'→',font=ImageFont.truetype(font(True),60),fill=color)
            for x,label in [(780,a),(1320,b)]:
                d.rounded_rectangle((x,y,x+500,y+150),25,fill='#1a304b',outline=color,width=3)
                d.text((x+28,y+48),label,font=ImageFont.truetype(font(True),46),fill=white)
            d.text((1284,y+54),'或',font=ImageFont.truetype(font(True),32),fill=color)
        d.text((100,900),'基础武器：3把      二级分支：6条      三级：保留普攻＋主动技能',font=ImageFont.truetype(font(),36),fill=cyan)
    else:
        rows=[('三连机关枪','弹幕风暴'),('恒流激光','日晷贯穿炮'),('散华手里剑','千刃绽放'),('遥控回旋刃','噬月回刃'),('磁吸遥爆雷','磁暴猎杀雷'),('坍缩奇点','吞星坍缩')]
        for i,(a,b) in enumerate(rows):
            x=95+(i%2)*900;y=260+(i//2)*210
            d.rounded_rectangle((x,y,x+840,y+165),22,fill='#1a304b',outline=cyan,width=3)
            d.text((x+25,y+22),a,font=ImageFont.truetype(font(True),43),fill=white)
            d.text((x+25,y+88),'＋ '+b,font=ImageFont.truetype(font(True),44),fill=gold)
        d.text((100,930),'主动技需要真实命中积攒共鸣；本表不是正式成长授予完成证明',font=ImageFont.truetype(font(),34),fill=cyan)
    d.text((100,1010),'编辑性机制示意 · 据现有武器定义整理 · 非游戏升级界面',font=ImageFont.truetype(font(),28),fill='#b9c9dc')
    im.save(path)
