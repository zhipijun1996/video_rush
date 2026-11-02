import copy
import pytest
from PIL import ImageChops
from tools.make_paipai_full import validate,opening_audio,signal_envelope
from video_rush.paipai_opening import frame


def valid():
    return {'seconds':20,'chapters':{x:i for i,x in enumerate('1234567')},'voices':[{'id':'OPEN-ADULT','start':.25,'seconds':2,'text':'日复一日的一天。'},{'id':'CREATE-A','start':4,'seconds':3,'text':'到我创造了，三格气的大招！'},{'id':'JP-HADOUKEN','start':8,'seconds':1,'text':'波動拳！'},{'id':'SURPRISE-B','start':10,'seconds':1.3,'text':'还能这样？！'}]}


def test_exact_words_and_complete_story_are_required():
    p=valid();validate(p)
    p['voices'][1]['text']='直到我创造了，三格气的大招！'
    with pytest.raises(ValueError,match='Exact'):validate(p)
    p=valid();p['chapters'].pop('6')
    with pytest.raises(ValueError,match='Missing'):validate(p)


def test_no_old_reaction_and_no_foreground_overlap():
    p=valid();p['voices'][3]['text']='我的反弹呢'
    with pytest.raises(ValueError,match='Removed'):validate(p)
    p=valid();p['voices'][3]['start']=8.5
    with pytest.raises(ValueError,match='Overlapping'):validate(p)


def test_boss_mouth_uses_actual_sfx_onset_and_worker_is_independent():
    fx=opening_audio({'seconds':2,'mode':'boss'},None);env=signal_envelope(fx,2)
    assert env[0]==0 and max(env[5:11])>.05 and env[25]==0
    quiet=frame('boss',.25,2,worker=[0]*60,boss=[0]*60)
    yelling=frame('boss',.25,2,worker=[0]*60,boss=env)
    assert ImageChops.difference(quiet.crop((895,245,1185,420)),yelling.crop((895,245,1185,420))).getbbox()
    assert ImageChops.difference(quiet.crop((320,290,470,445)),yelling.crop((320,290,470,445))).getbbox() is None
