from PIL import ImageChops
import pytest
from video_rush.paipai_film_art import image
from tools.make_paipai_counterplay import validate_counterplay


def test_angry_counter_has_different_face_and_points_at_a():
    shot={'id':'4-07','scene':'return-A','scheduled_lines':[{'speaker':'kidB','id':'ANGER-B','start':3.25,'end':4.7}]}
    shocked=image(shot,3.7,7.7);angry=image({**shot,'angry_counter':True},3.7,7.7)
    for box in [(830,230,1010,400),(760,380,1050,565)]:
        assert ImageChops.difference(shocked.crop(box),angry.crop(box)).getbbox()


def test_victory_points_instead_of_touching_head():
    shot={'id':'5-06','scene':'king','scheduled_lines':[]}
    old=image(shot,1,3.3);new=image({**shot,'victory_pose':'jojo_point'},1,3.3)
    assert ImageChops.difference(old.crop((100,200,500,550)),new.crop((100,200,500,550))).getbbox()


def test_counterplay_order_and_no_duplicate_shout():
    ids=['RETRY-A','AT-B','TURN-B','4-07-0','4-07-1','ANGER-B','JOJO-A','K04-B']
    p={'voices':[{'id':id,'text':'test','start':n*2,'seconds':1} for n,id in enumerate(ids)]}
    validate_counterplay(p)
    p['voices'][2]['start']=12
    with pytest.raises(ValueError,match='order'):validate_counterplay(p)
    p['voices'][2]['start']=4;p['voices'][-1]['start']=12.3
    with pytest.raises(ValueError,match='overlaps'):validate_counterplay(p)
