import copy
import pytest
from video_rush.trial_recording import validate_trace, DRIVER


def trace():
    phases=['entry','entry_to_w1','w1_to_h1','h1_to_w3','w3_to_relay','relay',
            'relay_to_w4','w4_to_h2','h2_to_w5','w5_to_w6','w6_to_finish',
            'finish_platform','return_bridge','return_chute','returned']
    return {'frames':180,'failures':0,'position_writes_after_entry':False,
            'capabilities':{'H':True,'W':True,'D':True,'Q':True},
            'inputs':[{'frame':i,'action':a} for i,a in enumerate(['jump_edge','shoot_release','grapple'])],
            'finish_latch':True,'returned_to_entry':True,
            'events':[{'phase':p,'frame':i*10} for i,p in enumerate(phases)],
            'rows':[{'frame':i,'session':2,'hp':5,'floor':True,'p':[120,1838],
                     'latch':True} for i in range(1,181)]}


def test_partial_or_reset_run_is_not_a_complete_recording():
    good=trace();validate_trace(good)
    variants=[]
    for key,value in [('finish_latch',False),('returned_to_entry',False),
                      ('position_writes_after_entry',True),('failures',1)]:
        t=copy.deepcopy(good);t[key]=value;variants.append(t)
    t=copy.deepcopy(good);t['rows'][50]['session']=3;variants.append(t)
    t=copy.deepcopy(good);del t['rows'][50];variants.append(t)
    t=copy.deepcopy(good);t['rows'][50]['hp']=4;variants.append(t)
    t=copy.deepcopy(good);t['rows'][50]['p']=[720,1198];variants.append(t)
    t=copy.deepcopy(good);t['events'].pop(5);variants.append(t)
    for t in variants:
        with pytest.raises(ValueError):validate_trace(t)


def test_trial_driver_never_positions_or_grants_resources_midplay():
    text=DRIVER.read_text()
    for forbidden in ['reset_at(','.position=', '.global_position=', '.grant(',
                      'health.current=', 'shot_charges=', 'cooldown=']:
        assert forbidden not in text
    assert '"stage":"hwdq"' in text
