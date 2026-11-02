import numpy as np
from PIL import Image
from tools.make_paipai_accel import music_events
from video_rush.paipai_double_exposure import composite


def test_music_stops_under_reaction_and_resolves_after_speech():
    p={'seconds':20.84,'idea_at':8,'game_start':14,'peak_at':14.12,'speech_end':20,'segments':[{'start':14,'seconds':1.2}]}
    events,cues=music_events(p)
    assert not any(cues['rock_stop']<=t<cues['cadence_start'] and kind==1 for t,kind,*_ in events)
    assert cues['cadence_start']>p['speech_end']
    assert cues['cadence_end']+.15<p['seconds']
    # The last sounded note resolves to E; the rhythm track cannot restart here.
    last=max((e for e in events if e[1]==1),key=lambda e:e[0])
    assert last[2]==7 and last[3]%12==4


def test_double_exposure_keeps_background_and_adds_real_child_layer():
    source=Image.new('RGB',(1280,720),(90,120,150))
    first=np.asarray(composite(source,'face',0,.4,enter=True))
    merged=np.asarray(composite(source,'face',.25,.4,enter=True))
    assert np.array_equal(first,np.asarray(source))
    changed=np.max(np.abs(merged.astype(int)-np.asarray(source).astype(int)),axis=2)>5
    assert 10000<changed.sum()<1280*720*.4
    # Alpha is partial: source stays visible even within the drawn head.
    assert np.max(np.abs(merged[365,730].astype(int)-np.array([90,120,150])))<130
