import copy
import pytest
from video_rush.boss_film import audit_fight, cue_plan, ass_text


def completed():
    rows=[]
    for i in range(1,241):
        if i<=130:at=[560,612]
        elif i<=140:at=[560+(i-130)*12,612+(i-130)*2.8]
        elif i<=170:at=[680+(i-140)*2/3,640]
        elif i<=200:at=[700+(i-170)*6,640-(i-170)*28/30]
        else:at=[880,612]
        rows.append(dict(frame=i,movie_frame=i,phase=1 if i<=60 else 2 if i<=120 else 3,
            session=2,hp=5,boss_hp=max(0,510-(i-1)*2.5),boss_capacity=510,
            player=at,focus=140<=i<170,time_scale=.15 if 140<=i<170 else 1,
            jump_held=False,grounded=i<=135 or i>=200,battle_finished=i>=220))
    return dict(failure='',victory_frame=220,initial_boss_hp=510,rows=rows,
        invincible=False,position_writes_in_recorded_fight=False,
        shots=[dict(airborne=True,flight_ordinal=1,frame=170,
                    focus=dict(start=140,end=170,frames=30,cross_begin=130))],
        events=[dict(event='phase',phase=p,frame=f,movie_frame=f) for p,f in [(1,1),(2,61),(3,121)]]+
               [dict(event='cross_begin',frame=130,movie_frame=130,origin_rect=[460,630,200,20],goal=[880,612]),
                dict(event='walk_off',frame=140,movie_frame=140,cross_begin=130,position=[680,640]),
                dict(event='cross_landed',frame=200,movie_frame=200,boosted=True,cross_begin=130)])


def test_defeat_alone_does_not_certify_requested_play_style():
    t=completed();audit_fight(t)
    variants=[]
    for field,value in [('failure','checkpoint return'),('victory_frame',-1),('initial_boss_hp',400)]:
        bad=copy.deepcopy(t);bad[field]=value;variants.append(bad)
    for field,value in [('flight_ordinal',2),('focus',dict(start=40,end=45,frames=5))]:
        bad=copy.deepcopy(t);bad['shots'][0][field]=value;variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][150]['focus']=False;variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][-1]['boss_hp']=1;variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][70]['session']=3;variants.append(bad)
    bad=copy.deepcopy(t);bad['events'].pop();variants.append(bad)
    bad=copy.deepcopy(t);bad['rows'][150]['jump_held']=True;variants.append(bad)
    bad=copy.deepcopy(t);bad['events'][-2]['position']=[600,640];variants.append(bad)
    bad=copy.deepcopy(t);bad['invincible']=True;variants.append(bad)
    bad=copy.deepcopy(t)
    for r in bad['rows']:r['phase']=1
    variants.append(bad)
    for bad in variants:
        with pytest.raises(ValueError):audit_fight(bad)


def test_cues_are_finite_ordered_and_do_not_hide_gameplay_with_overlap():
    t=completed();t['shots'][0]['focus']['start']=600;t['victory_frame']=6000
    cues=cue_plan(t,103.5)
    assert all(0<=c['start']<c['end']<=103.5 for c in cues)
    assert all(b['start']>=a['end']-.05 for a,b in zip(cues,cues[1:]))
    text=ass_text(cues,103.5)
    assert '无配音' in text and 'Noto Sans CJK SC' in text
    assert 'Dialogue:' in text


def test_cue_rounding_does_not_exceed_a_real_30fps_end():
    cues=cue_plan(completed(),102.06666666666666)
    assert all(c['end']<=102.06666666666666 for c in cues)
