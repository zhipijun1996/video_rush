import json,subprocess
from pathlib import Path
import pytest
from video_rush.common import sha,probe


def test_recording_frame_keeps_movie_provenance_and_rejects_outside_time(tmp_path,monkeypatch):
    from video_rush import browser_movie
    from video_rush.footage import collect
    movie=tmp_path/'movie.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=30:d=1',
                    '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(movie)],check=True)
    receipt={'movie_sha256':sha(movie),'recipe':{'commit':'a'*40},'ffprobe':probe(movie)}
    for name,data in [('trace.json',{'test_fixture':True}),('receipt.json',receipt)]:
        (tmp_path/name).write_text(json.dumps(data))
    monkeypatch.setattr(browser_movie,'capture',lambda *args:(movie,receipt))
    asset={'id':'example','origin':'browser_movie','case':'example','commit':'a'*40,'kind':'historical_reconstruction'}
    out=tmp_path/'episode/media'
    r=collect(tmp_path,{'repository':'example/game','assets':[dict(asset,frame_seconds=.4)]},out)[0]
    assert r['source_sha256']==sha(movie)
    assert r['local_path'].endswith('.png')
    assert r['extraction']['seconds']==.4
    assert (out.parent/'browser-evidence/example-trace.json').is_file()
    assert 'a'*40 in r['source_url']
    for t in [-1,1,float('nan')]:
        with pytest.raises(ValueError,match='Frame outside'):
            collect(tmp_path,{'repository':'example/game','assets':[dict(asset,frame_seconds=t)]},out)


def test_school_story_is_real_motion_and_bounded(tmp_path):
    from video_rush.school_animation import render
    movie=tmp_path/'story.mp4';render(movie,{'seconds':1.2,'scene':'recess'})
    meta=probe(movie);v=meta['streams'][0]
    assert v['codec_name']=='h264' and (v['width'],v['height'])==(1920,1080)
    frames=[]
    for t in ['0','0.8']:
        frames.append(subprocess.check_output(['ffmpeg','-v','error','-ss',t,'-i',str(movie),
            '-frames:v','1','-vf','crop=400:400:1200:210,scale=100:100','-f','rawvideo','-pix_fmt','rgb24','-']))
    assert sum(a!=b for a,b in zip(*frames))>400
    with pytest.raises(ValueError,match='length'):render(movie,{'seconds':31})
