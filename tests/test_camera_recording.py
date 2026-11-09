import pytest
from video_rush.camera_recording import validate_trace,SEGMENTS

def good_trace():
    return {'failures':0,'position_writes_within_marked_clips':False,'frames':1200,
            'segments':[{'id':name,'start_frame':i*100,'end_frame':i*100+80} for i,name in enumerate(sorted(SEGMENTS))],
            'rows':[{'clip':name,'relative_frame':i} for name in SEGMENTS for i in range(80)]}

def test_camera_comparison_rejects_failed_or_position_driven_clip():
    t=good_trace();validate_trace(t)
    t['position_writes_within_marked_clips']=True
    with pytest.raises(ValueError):validate_trace(t)
    t=good_trace();t['failures']=1
    with pytest.raises(ValueError):validate_trace(t)

def test_missing_camera_segment_or_motion_cannot_be_certified():
    t=good_trace();t['segments'].pop()
    with pytest.raises(ValueError):validate_trace(t)
    t=good_trace();t['rows']=[]
    with pytest.raises(ValueError):validate_trace(t)
