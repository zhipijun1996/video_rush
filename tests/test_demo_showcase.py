"""Reject partial or reset gameplay even when the driver says complete."""
from copy import deepcopy
import shutil
import subprocess

import pytest

from video_rush.demo_showcase import audit_take, verify_audio_alignment


def p10_trace():
    # Synthetic policy fixture, not footage or a claim of a real capture.
    frames=[]
    for f,ground in [(0,1),(1,0),(4,1),(5,0),(8,1),(9,0),(14,1),
                    (15,0),(17,1),(18,0),(20,1)]:
        frames.append(dict(frame=f,hp=5,session=7,room='P-R10',
                           grounded=bool(ground),position=[768,142]))
    events=[dict(event='take_start',invincible=False,stage='base')]
    events += [dict(event='native_shot',movie_frame=f) for f in [1,2,5,6,9,10,11,12,15,18]]
    events += [dict(event='check',ok=True,label='native hit refills air shot: '+str(i)) for i in range(5)]
    return dict(case='p10',complete=True,failures=[],frames=frames,
                events=events,initial_pose=[896,2030])


def test_native_four_shot_chain_policy():
    result=audit_take(p10_trace(),'p10')
    assert result['max_shots_single_flight']==4
    assert result['actual_hit_refills']==5


@pytest.mark.parametrize('alter', ['reset','no_refill','no_summit','no_chain','extra_ability','invincible'])
def test_refuses_false_completion(alter):
    trace=deepcopy(p10_trace())
    if alter=='reset':trace['frames'][4]['session']=8
    elif alter=='no_refill':trace['events'].pop()
    elif alter=='no_summit':trace['frames'][-1]['position'][1]=718
    elif alter=='no_chain':trace['frames'][6]['frame']=12
    elif alter=='extra_ability':trace['events'][0]['stage']='h'
    elif alter=='invincible':trace['events'][0]['invincible']=True
    with pytest.raises(ValueError):audit_take(trace,'p10')


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
def test_rejects_accumulated_audio_delay(tmp_path):
    original=tmp_path/'original.wav';delayed=tmp_path/'delayed.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                    'anoisesrc=duration=3:color=pink:seed=41','-ar','48000',str(original)],check=True)
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(original),
                    '-af','adelay=80','-t','3',str(delayed)],check=True)
    clips=[dict(stage='fixture',start=0,timeline_start=0,duration=3)]
    captures={'fixture':{'movie':original}}
    assert verify_audio_alignment(original,clips,captures)[0]['passed']
    assert not verify_audio_alignment(delayed,clips,captures)[0]['passed']
