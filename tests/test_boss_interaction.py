import copy
import pytest
from video_rush.boss_interaction import audit_interactions


def interactive():
    trace=dict(arena_bounds=[320,160,1120,600],rows=[],events=[],shots=[])
    for phase in [1,2]:
        offset=(phase-1)*300
        for i in range(1,301):
            boss_x=700+i*.8;relative=-200 if i<10 else 200 if i<100 else -200 if i<200 else 200
            air=False
            for start,end,sign in [(10,40,1),(100,140,-1),(200,240,1)]:
                if start<=i<=end:
                    relative=(-200+400*(i-start)/(end-start))*sign
                    air=sign==1 and i<end
            trace['rows'].append(dict(frame=offset+i,movie_frame=offset+i,phase=phase,
                player=[boss_x+relative,500 if air else 742],boss=[boss_x,535 if 100<=i<=140 else 695],
                boss_airborne=100<=i<=140,grounded=not air,jump_held=False))
        for start,end,kind,direction in [(10,40,'over',1),(100,140,'under',-1),(200,240,'over',1)]:
            ident=offset+start
            trace['events'] += [dict(event='maneuver_begin',id=ident,kind=kind,phase=phase,frame=ident,direction=direction),dict(event='maneuver_complete',id=ident,kind=kind,phase=phase,frame=offset+end)]
            if kind=='over':trace['shots'].append(dict(airborne=True,frame=ident+15,focus=dict(maneuver_id=ident,reason='over_walking_boss')))
    return trace


def test_real_position_and_posture_must_support_tactic_labels():
    t=interactive();assert audit_interactions(t)['phases']['2']['underpasses']==1
    variants=[]
    bad=copy.deepcopy(t)
    for r in bad['rows']:r['player'][0]=1400
    variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][119]['boss_airborne']=False;variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][119]['jump_held']=True;variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][24]['player'][1]=742;variants.append(bad)
    bad=copy.deepcopy(t);bad['shots'].pop();variants.append(bad)
    bad=copy.deepcopy(t);bad['events']=[e for e in bad['events'] if e.get('kind')!='under'];variants.append(bad)
    for bad in variants:
        with pytest.raises(ValueError):audit_interactions(bad)


def test_a_few_passages_do_not_excuse_corner_farming_between_them():
    t=interactive();active=set()
    begins={e['id']:e['frame'] for e in t['events'] if e['event']=='maneuver_begin'}
    for e in t['events']:
        if e['event']=='maneuver_complete':active.update(range(begins[e['id']],e['frame']+1))
    for row in t['rows']:
        if row['frame'] not in active:row['player'][0]=1400
    with pytest.raises(ValueError,match='camps the boundary'):audit_interactions(t)
