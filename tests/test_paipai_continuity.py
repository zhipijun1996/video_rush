import copy
from PIL import ImageChops
from video_rush.paipai_film_art import image
from tools.make_paipai_continuity import validate
import pytest


def test_memory_transition_blends_people_and_location_instead_of_age_pop():
    s={'id':'6-01','scene':'back-now','memory_dissolve':True,'scheduled_lines':[]}
    start=image(s,0,1.1);middle=image(s,.525,1.1);end=image(s,1.1,1.1)
    assert ImageChops.difference(start,middle).getbbox()
    assert ImageChops.difference(middle,end).getbbox()
    # At the midpoint both locations contribute, without a white/black flash.
    import numpy as np
    expected=(np.asarray(start,dtype=float)+np.asarray(end,dtype=float))/2
    assert abs(np.asarray(middle,dtype=float)-expected).mean()<14


def test_continuous_villain_and_uninterrupted_victory_are_required():
    face={'kind':'R','id':'face','mode':'dio_face','start':0,'seconds':.6}
    an={'kind':'AN','start':.6,'seconds':2.3}
    g={'kind':'G','round':21,'start':5,'seconds':5,'blue_in':False}
    king={'kind':'FILM','shot':{'id':'5-06','layers':[{'alpha':.4,'rect':[750,30,570,850]}]},'start':10}
    p={'segments':[face,an,g,king],'voices':[{'id':'DIO-CONT-A','start':.03,'seconds':2.48},{'id':'KING-FAST','start':10.08,'seconds':.88}]}
    validate(p)
    bad=copy.deepcopy(p);bad['voices'][1]['start']=8
    with pytest.raises(ValueError,match='interrupts'):validate(bad)
    bad=copy.deepcopy(p);bad['voices'][0]['start']=.7
    with pytest.raises(ValueError,match='cross'):validate(bad)
