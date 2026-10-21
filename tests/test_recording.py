from copy import deepcopy
import pytest
from video_rush.recording import validate_trace
from video_rush.render import crop_filter
from PIL import Image


def test_real_recording_trace_rejects_respawn_missing_attack_and_motion():
    trace={'case':'gun_up','failures':[],'no_midflight_position_health_resource_injection':True,'accepted_shots':1,
           'frames':[{'hp':5,'epoch':3,'actor_epoch':3,'position':[0,i]} for i in range(120)]}
    validate_trace(trace,'gun_up',120)
    changed=deepcopy(trace);changed['frames'][50]['actor_epoch']=4
    with pytest.raises(ValueError,match='respawn'):validate_trace(changed,'gun_up',120)
    changed=deepcopy(trace);changed['accepted_shots']=0
    with pytest.raises(ValueError,match='attack'):validate_trace(changed,'gun_up',120)
    changed=deepcopy(trace)
    for row in changed['frames']:row['position']=[0,0]
    with pytest.raises(ValueError,match='movement'):validate_trace(changed,'gun_up',120)
    changed=deepcopy(trace);changed['no_midflight_position_health_resource_injection']=False
    with pytest.raises(ValueError,match='real motion'):validate_trace(changed,'gun_up',120)


def test_cropping_preserves_original_and_rejects_outside_pixels(tmp_path):
    path=tmp_path/'original.png';Image.new('RGB',(80,60),'blue').save(path)
    before=path.read_bytes()
    assert crop_filter([10,10,40,30],path)=='crop=40:30:10:10,'
    with pytest.raises(ValueError,match='exceeds'):crop_filter([40,0,60,30],path)
    assert path.read_bytes()==before


def test_advanced_clip_needs_actual_catch_not_only_attack():
    trace={'case':'boomerang_return','failures':[],'no_midflight_position_health_resource_injection':True,'accepted_shots':1,
           'events':[{'kind':'returning'}], 'frames':[{'hp':5,'epoch':3,'actor_epoch':3,'position':[0,i]} for i in range(120)]}
    with pytest.raises(ValueError,match='actual catch'):validate_trace(trace,'boomerang_return',120)
    trace['events'].append({'kind':'caught'})
    validate_trace(trace,'boomerang_return',120)


def test_narration_guard_covers_non_s_ids_and_rejects_missing_or_tampered_voice(tmp_path):
    from video_rush.quality import narration_receipts_valid
    from video_rush.common import write,sha
    spec={'shots':[{'id':'r01','narration':'真实配音'}]}
    assert not narration_receipts_valid(tmp_path,spec)
    p=tmp_path/'narration/r01.wav';p.parent.mkdir();p.write_bytes(b'fixture waveform')
    write(p.with_suffix('.json'),{'backend':'edge','text':'真实配音','sha256':sha(p),'metrics':{'audible_signal':True}})
    assert narration_receipts_valid(tmp_path,spec)
    p.write_bytes(b'changed waveform')
    assert not narration_receipts_valid(tmp_path,spec)


def test_mine_clip_cannot_claim_combo_from_one_blast():
    t={'case':'route_mine_combo','failures':[],'no_midflight_position_health_resource_injection':True,'accepted_shots':1,
       'frames':[{'hp':5,'epoch':3,'actor_epoch':3,'position':[0,i]} for i in range(120)],
       'events':[{'kind':'accepted_packet','grounded':True},{'kind':'attached'},{'kind':'blast'}]}
    with pytest.raises(ValueError,match='two real airborne bombs'):validate_trace(t,'route_mine_combo',120)
