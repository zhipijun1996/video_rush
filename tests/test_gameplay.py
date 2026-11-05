import pytest
from video_rush.gameplay import assert_boss_clear, load_capture, plan
from video_rush.common import write


def test_partial_live_fight_does_not_become_complete_level():
    with pytest.raises(ValueError,match='Boss defeat missing'):
        assert_boss_clear('plains1',{'failures':[], 'boss_defeat_process_frame':-1})
    with pytest.raises(ValueError):
        assert_boss_clear('plains2',{'failures':['player_died'], 'boss_defeat_process_frame':600})
    with pytest.raises(ValueError):
        assert_boss_clear('forest1',{'failures':[], 'combat':{'defeats':1,'final':{'boss_hp':1}}})


def test_headless_result_is_never_video(tmp_path):
    p=tmp_path/'plains1';p.mkdir()
    write(p/'receipt.json',{'source_commit':'a'*40,'kind':'headless_input_diagnostic'})
    write(p/'trace.json',{})
    with pytest.raises(ValueError,match='not footage'):
        load_capture(tmp_path,'plains1','a'*40)


def test_gameplay_plan_preserves_whole_boss_and_excludes_postcombat_fixture():
    spec={'main_commit':'a'*40,'random_commit':'b'*40,'stages':{n:{'label':n,'boss':'Boss'} for n in ['plains1','plains2','forest1','forest2','random']}}
    captures={n:{'duration':140,'trace':{'boss_start_process_frame':3600,'boss_defeat_process_frame':7200}} for n in ['plains1','plains2']}
    for n in ['forest1','forest2']:
        captures[n]={'duration':65,'trace':{'combat':{'frames':[
            {'physics_frame':2100,'boss_hp':24,'segment':'before_reload'},
            {'physics_frame':2400,'boss_hp':16,'segment':'before_reload'},
            {'physics_frame':2412,'boss_hp':16,'segment':'after_reload'},
            {'physics_frame':2900,'boss_hp':0,'segment':'after_reload'}]},'gold_effect_probe':{'before':{'physics_frame':3000}}}}
    captures['random']={'duration':66,'trace':{'ready_process_frame':600,'overview_process_frames':[600,1800],'route_complete':False}}
    clips=plan(spec,captures)
    for n in ['plains1','plains2']:
        boss=[c for c in clips if c['stage']==n and '完整 Boss' in c['note']]
        assert len(boss)==1 and boss[0]['start']==60 and boss[0]['end']>=120
    forest=[c for c in clips if c['stage']=='forest2']
    assert len(forest)==2 and forest[0]['end']<=2401/60+.02 and forest[1]['start']>=2412/60-.02
    assert forest[-1]['end']<50
    assert all(c['speed']==1 and c['end']<=captures[c['stage']]['duration'] for c in clips)
    assert '未跑通' in clips[-1]['note'] and '非游玩' in clips[-2]['note']
