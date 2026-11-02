import copy
import pytest
from video_rush.common import ROOT,read,sha
from tools.make_paipai_film import validate_game_trace


def battle():
    # Independent small regression fixture: failure examples change only the
    # visible story's invariants, not the combat implementation.
    rows=[]
    for i in range(21):
        state={'players':[{'hp':4,'energy':5},{'hp':1,'energy':2}]}
        rows.append({'initial':copy.deepcopy(state),'result':{'next':copy.deepcopy(state),'actions':['charge','charge'],'damage':[0,0],'winner':None}})
    rows[14]['result'].update(actions=['reflect2','wave2'],damage=[0,2])
    rows[20]['result'].update(actions=['wave3','reflect2'],winner=0)
    return {'rounds':rows}


def test_legal_battle_and_story_failures():
    validate_game_trace(battle())
    t=battle();t['rounds'][14]['result']['actions']=['wave2','reflect2']
    with pytest.raises(ValueError,match='A must return'):validate_game_trace(t)
    t=battle();t['rounds'][20]['initial']['players'][0]['energy']=4
    with pytest.raises(ValueError):validate_game_trace(t)
    t=battle();t['rounds'][6]['initial']['players'][0]['hp']=99
    with pytest.raises(ValueError,match='Discontinuous'):validate_game_trace(t)


def test_uploaded_approved_screenplay_remains_exact():
    spec=read(ROOT/'episodes/ep008-r3-film.json')
    assert sha(ROOT/spec['brief'])==spec['brief_sha256']
    assert len(spec['shots'])==36
    lines=[l['text'] for s in spec['shots'] for l in s['lines']]
    assert len(lines)==47
    assert sum('你就赢这一把' in l for l in lines)==1
    assert not any('不忘初心' in l or '永葆童心' in l for l in lines)


def test_expression_animation_has_motion_and_dramatic_limbs():
    from video_rush.paipai_film_art import image
    from PIL import ImageChops
    shot={'id':'3-04B','scene':'evil-B','scheduled_lines':[{'speaker':'evilB','start':0,'end':3}]}
    a=image(shot,.2,3);b=image(shot,.5,3)
    assert ImageChops.difference(a,b).getbbox() is not None
    # Original failure: dark limbs vanished against the dramatic background.
    assert sum(1 for r,g,b in a.crop((250,430,1200,700)).getdata() if r>180 and g>180 and b>180)>1000
