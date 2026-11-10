"""Synthetic unit traces only; production requires native recorded evidence."""
import copy
import pytest
from video_rush.camera_recording import validate_trace,STORY_SEGMENTS


def trace():
    segments=[];rows=[]
    for n,label in enumerate(sorted(STORY_SEGMENTS)):
        segments.append({'id':label,'start_frame':n*40,'end_frame':(n+1)*40})
        for i in range(40):
            inside=label=='secret_enter'
            rows.append({'clip':label,'zone':'secret' if inside else 'main','concealed':not inside,'chest_open':label in {'secret_enter','secret_return'},'session_id':1,'lead':80 if i<20 else -80,'actor_screen_fraction_x':.4 if i<20 else .6})
    return {'failures':0,'frames':400,'position_writes_within_marked_clips':False,'segments':segments,'rows':rows}


def test_story_profile_requires_hidden_entry_return_and_actual_framing():
    validate_trace(trace(),STORY_SEGMENTS)
    t=trace();next(r for r in t['rows'] if r['clip']=='secret_preview')['concealed']=False
    with pytest.raises(ValueError,match='exposed before'):validate_trace(t,STORY_SEGMENTS)
    t=trace()
    for r in t['rows']:
        if r['clip']=='lead':r['actor_screen_fraction_x']=.5
    with pytest.raises(ValueError,match='visibly shifts'):validate_trace(t,STORY_SEGMENTS)


def test_story_rejects_respawn_and_reward_without_restored_outside_view():
    t=trace();next(r for r in t['rows'] if r['clip']=='corner')['session_id']=2
    with pytest.raises(ValueError,match='respawned'):validate_trace(t,STORY_SEGMENTS)
    t=trace();[r for r in t['rows'] if r['clip']=='secret_return'][-1]['concealed']=False
    with pytest.raises(ValueError,match='restore view'):validate_trace(t,STORY_SEGMENTS)
