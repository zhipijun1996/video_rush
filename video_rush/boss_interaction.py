"""Measure requested side-switch tactics from observed game state, not labels."""
from collections import Counter


def audit_interactions(trace):
    rows=trace['rows'];events=trace['events'];shots=trace['shots']
    bounds=trace['arena_bounds'];left=bounds[0]+110;right=bounds[0]+bounds[2]-110
    by_frame={r['frame']:r for r in rows}
    begins={e['id']:e for e in events if e['event']=='maneuver_begin'}
    passages=[]
    for end in (e for e in events if e['event']=='maneuver_complete'):
        begin=begins.get(end['id'])
        if not begin or begin['kind']!=end['kind'] or begin['phase']!=end['phase']:
            raise ValueError('Unlinked or inconsistent interaction event')
        segment=[by_frame[f] for f in range(begin['frame'],end['frame']+1)]
        if any(r['phase']!=begin['phase'] for r in segment):
            continue  # A passage spanning a phase change is not counted twice.
        direction=begin['direction'];first=segment[0];last=segment[-1]
        relative=lambda r:(r['player'][0]-r['boss'][0])*direction
        if relative(first)>=0 or relative(last)<180:
            raise ValueError('Declared passage did not actually change sides')
        crossed=next(r for r in segment if relative(r)>=0)
        if begin['kind']=='under':
            if any(not r['grounded'] or r['jump_held'] for r in segment[1:]) or not crossed['boss_airborne'] or crossed['player'][1]-crossed['boss'][1]<100:
                raise ValueError('Claimed pounce underpass was not a real grounded run below the Boss')
            if any(s['airborne'] and begin['frame']<=s['frame']<=end['frame'] for s in shots):
                raise ValueError('An underpass used an airborne attack')
        elif begin['kind']=='over':
            if crossed['grounded'] or crossed['boss_airborne'] or crossed['boss'][1]-crossed['player'][1]<130:
                raise ValueError('Claimed walking-Boss overpass did not cross above the grounded body')
            matching=[s for s in shots if s['airborne'] and s.get('focus',{}).get('maneuver_id')==end['id'] and s['focus'].get('reason')=='over_walking_boss' and begin['frame']<=s['frame']<=end['frame']]
            if len(matching)!=1:raise ValueError('Overpass needs exactly one actual focused recoil shot')
        else:raise ValueError('Unknown interaction tactic')
        passages.append(dict(kind=begin['kind'],phase=begin['phase'],start_frame=begin['frame'],
            end_frame=end['frame'],cross_frame=crossed['frame'],cross_seconds=crossed['movie_frame']/60))
    phases={}
    for phase in [1,2]:
        observed=[r for r in rows if r['phase']==phase]
        if not observed:raise ValueError('Missing early phase')
        corners=[r['player'][0]<left or r['player'][0]>right for r in observed]
        run=longest=0
        for at_corner in corners:
            run=run+1 if at_corner else 0;longest=max(longest,run)
        share=sum(corners)/len(corners)
        span=max(r['player'][0] for r in observed)-min(r['player'][0] for r in observed)
        boss_span=max(r['boss'][0] for r in observed)-min(r['boss'][0] for r in observed)
        counts=Counter(p['kind'] for p in passages if p['phase']==phase)
        if share>.2 or longest/60>2 or span<500 or boss_span<200:
            raise ValueError('Early phase still camps the boundary or lacks active pursuit')
        if counts['over']<2 or counts['under']<1:
            raise ValueError('Each early phase needs repeated overpasses and a real pounce underpass')
        phases[str(phase)]=dict(overpasses=counts['over'],underpasses=counts['under'],
            player_horizontal_span=span,boss_horizontal_span=boss_span,
            near_wall_fraction=share,longest_near_wall_seconds=longest/60)
    return dict(phases=phases,passages=passages,corner_band_width=110,
        measured_behavior=True,human_enjoyment='pending phone review; not certified by automatic play')
