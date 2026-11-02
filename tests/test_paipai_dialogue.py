import copy
from PIL import ImageChops
from tools.make_paipai_dialogue import apply_lines
from video_rush.paipai_dialogue_art import frame


def test_new_voice_lengths_retime_captions_without_changing_game_window(monkeypatch,tmp_path):
    monkeypatch.setattr('tools.make_paipai_dialogue.duration',lambda p:4 if p.stem=='CREATE-A' else 1.3)
    monkeypatch.setattr('tools.make_paipai_dialogue.base.envelope',lambda p:[.2]*120)
    p={'seconds':12,'segments':[{'id':'a','kind':'MATCH','start':0,'seconds':2},{'id':'g','kind':'G','start':2,'seconds':3,'in':48.5},{'id':'b','kind':'R','start':5,'seconds':2},{'id':'tail','kind':'R','start':7,'seconds':5}], 'voices':[{'id':'IDEA-A','start':.1,'seconds':1.8},{'id':'old-4-04-0','start':5.02,'seconds':1.7},{'id':'BOAST','start':7.02,'seconds':2.8}],'action_start':2,'game_start':2,'peak_at':2.12,'merge_at':2,'speech_end':9.82}
    spec={'dialogue_changes':[{'replace':'IDEA-A','id':'CREATE-A','mode':'create','text':'直到我创造了，三格气的大招！'},{'replace':'old-4-04-0','id':'SURPRISE-B','mode':'surprise','text':'还能这样？！'}]}
    original=copy.deepcopy(p['segments'][1]);apply_lines(p,spec,tmp_path)
    game=p['segments'][1]
    assert game['in']==original['in'] and game['seconds']==original['seconds']
    assert p['game_start']==game['start'] and abs(p['peak_at']-game['start']-.12)<.001
    for v in p['voices']:
        shot=next(s for s in p['segments'] if s['start']<=v['start']<s['start']+s['seconds'])
        assert v['start']+v['seconds']<shot['start']+shot['seconds']
    assert p['segments'][0]['kind']=='DIALOGUE' and p['segments'][2]['kind']=='DIALOGUE'
    assert p['voices'][1]['text']=='还能这样？！'


def test_shock_changes_eyes_jaw_and_arms():
    a=frame('surprise',.01,1.6,[.1]*48);b=frame('surprise',.30,1.6,[.1]*48)
    for region in [(550,240,780,365),(580,365,770,530),(400,390,880,580)]:
        diff=ImageChops.difference(a.crop(region),b.crop(region))
        assert sum(1 for pixel in diff.getdata() if max(pixel)>40)>1000
