import subprocess
import numpy as np
import pytest
from video_rush.pipeline import background_music_filter


def test_supplied_bgm_starts_after_original_game_audio_opening():
    # Execute the real filter with a test tone: no second soundtrack before
    # its entry, audible afterward. The production voice is always real TTS.
    filt=background_music_filter({'music_start_seconds':.5,'music_gain':.5},2.0)
    filt=filt.replace('[2:a]','[0:a]')
    raw=subprocess.check_output(['ffmpeg','-v','error','-f','lavfi','-i',
        'sine=frequency=440:duration=1.5:sample_rate=16000','-filter_complex',filt,
        '-map','[bg]','-t','2','-f','f32le','-ac','1','-'])
    a=np.frombuffer(raw,dtype=np.float32)
    assert np.max(np.abs(a[:int(.49*16000)]))==0
    assert np.max(np.abs(a[int(.75*16000):int(.9*16000)]))>.001
    for bad in [-1,2,float('nan'),True]:
        with pytest.raises(ValueError):background_music_filter({'music_start_seconds':bad},2)
