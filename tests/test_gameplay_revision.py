import pytest
from video_rush.gameplay_revision import verify_base_coverage, equipment_clips


def test_cards_do_not_drop_or_repeat_original_gameplay():
    verify_base_coverage([{'kind':'card'},{'kind':'base','start':0,'end':4},
                          {'kind':'card'},{'kind':'base','start':4,'end':120},
                          {'kind':'equipment-ui'},{'kind':'base','start':120,'end':374.9}],374.9)


@pytest.mark.parametrize('start',[3.5,4.5])
def test_gap_or_repeat_cannot_masquerade_as_full_boss_coverage(start):
    with pytest.raises(ValueError):
        verify_base_coverage([{'kind':'base','start':0,'end':4},{'kind':'base','start':start,'end':100}],100)


def test_failed_equipment_attempt_is_not_an_approved_demo():
    with pytest.raises(ValueError,match='Incomplete'):
        equipment_clips({'trace':{'failures':['native equip failed']}})
