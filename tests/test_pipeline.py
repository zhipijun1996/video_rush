import json
from pathlib import Path
import subprocess
import pytest
from video_rush.pipeline import Stages
from video_rush.footage import collect
from video_rush.render import encode_shot, subtitle_cues
from video_rush.common import write, read


def test_failed_stage_resumes_and_output_tamper_invalidates_cache(tmp_path):
    runner=Stages(tmp_path);out=tmp_path/'data.json';count=[]
    def fail():
        raise RuntimeError('real failure')
    with pytest.raises(RuntimeError):runner.execute('Research',{'version':1},fail)
    assert read(tmp_path/'state.json')['stages']['Research']['status']=='failed'
    def good():
        count.append(1);write(out,{'ok':1});return [out]
    runner.execute('Research',{'version':1},good)
    runner.execute('Research',{'version':1},good)
    assert len(count)==1
    out.write_text('corrupt')
    runner.execute('Research',{'version':1},good)
    assert len(count)==2
    runner.execute('Research',{'version':2},good)
    assert len(count)==3


def test_collect_is_readonly_and_repairs_corrupted_cached_blob(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    git('init','-q');git('config','user.email','test@example.invalid');git('config','user.name','test')
    (repo/'evidence.txt').write_text('original evidence')
    git('add','.');git('commit','-qm','source');head=git('rev-parse','HEAD')
    spec={'repository':'example/game','assets':[{'id':'a','commit':head,'path':'evidence.txt'}]}
    output=tmp_path/'out'
    before=git('status','--porcelain')
    collect(repo,spec,output);(output/'a.txt').write_text('tampered')
    result=collect(repo,spec,output)
    assert (output/'a.txt').read_text()=='original evidence'
    assert result[0]['commit']==head
    assert git('status','--porcelain')==before
    with pytest.raises(ValueError):collect(repo,{'repository':'x/y','assets':[{'id':'b','commit':head,'path':'../evidence.txt'}]},output)


def test_subtitles_stay_inside_sentence_and_keep_text():
    text='这是一段真实测试，字幕不会越过实际音频。'
    cues=list(subtitle_cues(text,3.2,4.6))
    assert ''.join(x['text'] for x in cues)==text
    assert cues[0]['start']==3.2
    assert cues[-1]['end']==7.8
    assert all(a['end']==b['start'] for a,b in zip(cues,cues[1:]))


def test_clip_is_not_looped_to_hide_missing_footage(tmp_path):
    # A decodable short source cannot silently fill a much longer ShotSpec.
    p=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=blue:s=64x64:r=30:d=0.5','-c:v','libx264',str(p)],check=True)
    with pytest.raises(ValueError,match='insufficient footage'):
        encode_shot({'start':0,'end':4,'assets':['x'],'offsets':[0]}, {'x':{'local_path':str(p)}},tmp_path/'out.mp4',tmp_path/'log')
