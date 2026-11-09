import copy
import pytest
from video_rush.world_recording import validate_trace


def trace():
    return {'failures':0,'player_position_health_progress_writes':False,'frames':900,
            'markers':[{'event':'room_enter','room':'P-R03','frame':2},
                       {'event':'room_enter','room':'P-R21','frame':500},
                       {'event':'map_open','frame':510},{'event':'map_close','frame':750},
                       {'event':'room_enter','room':'P-R22','frame':760},
                       {'event':'recoil_start','frame':800},{'event':'recoil_end','frame':860}],
            'rows':[{'frame':i*6} for i in range(100)]}


def test_local_position_fixture_cannot_pass_as_uninterrupted_new_game():
    value=trace();value['player_position_health_progress_writes']=True
    with pytest.raises(ValueError):validate_trace(value)


def test_failed_route_cannot_be_delivered_as_success():
    value=trace();value['failures']=1
    with pytest.raises(ValueError):validate_trace(value)


def test_missing_crossing_or_map_interval_is_rejected():
    good=trace();validate_trace(good)
    for mutate in [lambda t:t['markers'].pop(1),lambda t:t['markers'][3].update(frame=511),lambda t:t['markers'].pop()]:
        value=copy.deepcopy(good);mutate(value)
        with pytest.raises(ValueError):validate_trace(value)
