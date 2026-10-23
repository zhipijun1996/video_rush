import pytest
from video_rush.subtitles import narration_cues


def test_real_ep004_opening_edge_overlap_is_removed_without_losing_text():
    boundaries = [
        {'type':'SentenceBoundary','offset':1000000,'duration':15181817,'text':'这只怪死了。'},
        {'type':'SentenceBoundary','offset':15681817,'duration':31704544,'text':'不过这姿势……你就说死没死吧。'},
    ]
    cues, method = narration_cues('这只怪死了。不过这姿势……你就说死没死吧。',
                                  boundaries, 10, 4.8/1.04, 1.04)
    assert ''.join(c['text'] for c in cues) == ''.join(b['text'] for b in boundaries)
    assert all(a['end'] <= b['start'] for a,b in zip(cues,cues[1:]))
    assert cues[0]['start'] == 10.096
    assert cues[0]['end'] == cues[1]['start'] == 11.508
    assert cues[-1]['end'] <= 10 + 4.8/1.04
    assert 'overlap clipped' in method


def test_single_opening_utterance_uses_exact_audio_window_and_no_subdivision():
    cues, method = narration_cues('这只怪死了。', [], 0, 1.65, 1.04, 'utterance')
    assert cues == [{'start':0,'end':1.65,'text':'这只怪死了。'}]
    assert 'decoded narration' in method
    with pytest.raises(ValueError,match='short readable'):
        narration_cues('长'*27, [], 0, 6, 1, 'utterance')
