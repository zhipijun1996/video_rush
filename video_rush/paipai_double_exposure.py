"""Original stick-child lines aligned to the anime face/palm, never gameplay."""
from PIL import Image,ImageDraw
import numpy as np
from .paipai_match_art import face,hand
from .paipai_film_art import PAPER,RED,stroke


def layer(phase,t):
    im=Image.new('RGBA',(1280,720));d=ImageDraw.Draw(im)
    if phase=='face':
        # Face and eye line were inspected at source 193.88-194.28, after hflip.
        # Match eye/mouth landmarks, rather than placing a second head over the ball.
        from .paipai_film_art import INK
        d.ellipse((390,165,895,670),fill=PAPER,outline=INK,width=9)
        stroke(d,[(435,270),(835,310)],RED,18)
        stroke(d,[(435,270),(340,240),(285,270)],RED,14)
        for points in [[(505,350),(615,380)],[(700,350),(785,320)]]:stroke(d,points,INK,10)
        d.ellipse((560,375,575,391),fill=INK);d.ellipse((737,350,752,366),fill=INK)
        d.polygon([(650,480),(760,465),(790,560),(670,595)],fill=INK)
        d.polygon([(657,480),(760,470),(765,490),(662,500)],fill=PAPER)
        stroke(d,[(570,670),(430,720)],PAPER,14)
    elif phase=='palm':
        # Foreground palm close-up, rather than a small standing figure.
        stroke(d,[(150,720),(420,600),(650,440)],PAPER,45)
        hand(d,680,370,3.8,-20)
        stroke(d,[(530,505),(850,580)],RED,10)
    else:raise ValueError(phase)
    return im


def composite(background,phase,t,seconds,*,enter=False):
    foreground=layer(phase,t);a=np.asarray(foreground).copy()
    # Keep the original actor visible beneath the child, with a readable red band.
    opacity=.55*(min(1,t/.12) if enter else 1)
    a[:,:,3]=(a[:,:,3].astype(float)*opacity).astype('uint8')
    return Image.alpha_composite(background.convert('RGBA'),Image.fromarray(a)).convert('RGB')
