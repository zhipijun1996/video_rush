import copy
import pytest
from tools.make_paipai_matchcut import CUTS, validate


def trial():
    return {'seconds':8,'voices':[{'id':'JP-HADOUKEN','start':1,'seconds':1,'text':'波動拳！'}], 'matches':[{'performer':kind,'phase':phase,'source_in':at,'seconds':seconds} for kind,phase,seconds,at in CUTS]}


def test_one_forward_action_with_paired_cameras():
    p=trial();validate(p)
    for a,b in zip(p['matches'][::2],p['matches'][1::2]):
        assert a['performer']=='MATCH' and b['performer']=='AN'
        assert a['phase']==b['phase']


@pytest.mark.parametrize('failure',['duplicate','overlap','rewind','rule_repetition'])
def test_reject_regressions(failure):
    p=copy.deepcopy(trial())
    if failure=='duplicate':p['voices'].append({'id':'K03-B','start':3,'seconds':1,'text':'波动拳'})
    if failure=='overlap':p['voices'].append({'id':'OTHER','start':1.5,'seconds':1,'text':'其他'})
    if failure=='rewind':p['matches'][-1]['source_in']=189
    if failure=='rule_repetition':p['voices'].append({'id':'N02','start':3,'seconds':1,'text':'反弹以后也算'})
    with pytest.raises(ValueError):validate(p)
