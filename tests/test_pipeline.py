import json
from pathlib import Path
import subprocess
import pytest
from video_rush.pipeline import Stages
from video_rush.footage import collect
from video_rush.render import encode_shot, subtitle_cues
from video_rush.common import write, read


def test_episode_writer_lock_rejects_overlap_and_releases_after_failure(tmp_path):
    from video_rush.pipeline import production_lock
    with pytest.raises(ValueError,match='production failed'):
        with production_lock(tmp_path):
            with pytest.raises(RuntimeError,match='already running'):
                with production_lock(tmp_path):
                    raise AssertionError('Concurrent writer entered')
            raise ValueError('production failed')
    with production_lock(tmp_path):
        assert (tmp_path/'.production.lock').exists()


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
    spec={'repository':'example/game','assets':[{'id':'a','commit':head,'path':'evidence.txt','preserve_evidence':True}]}
    output=tmp_path/'out'
    before=git('status','--porcelain')
    collect(repo,spec,output);(output/'a.txt').write_text('tampered')
    result=collect(repo,spec,output)
    assert (output/'a.txt').read_text()=='original evidence'
    assert result[0]['commit']==head
    assert (output.parent/result[0]['preserved_evidence']).read_text()=='original evidence'
    assert git('status','--porcelain')==before
    with pytest.raises(ValueError):collect(repo,{'repository':'x/y','assets':[{'id':'b','commit':head,'path':'../evidence.txt'}]},output)


def test_subtitles_stay_inside_sentence_and_keep_text():
    text='这是一段真实测试，字幕不会越过实际音频。'
    cues=list(subtitle_cues(text,3.2,4.6))
    assert ''.join(x['text'] for x in cues)==text
    assert cues[0]['start']==3.2
    assert cues[-1]['end']==7.8
    assert all(a['end']==b['start'] for a,b in zip(cues,cues[1:]))


def test_git_movie_frame_keeps_original_provenance_and_checks_bounds(tmp_path):
    from PIL import Image
    from video_rush.common import sha
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    git('init','-q');git('config','user.email','test@example.invalid');git('config','user.name','test')
    movie=repo/'movie.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
                    'testsrc2=s=160x90:r=30:d=1','-c:v','libx264',str(movie)],check=True)
    git('add','.');git('commit','-qm','real video fixture')
    asset={'id':'frame','path':'movie.mp4','commit':git('rev-parse','HEAD'),
           'frame_seconds':.4,'frame_crop':[20,10,80,60]}
    result=collect(repo,{'repository':'example/game','assets':[asset]},tmp_path/'out')[0]
    assert Image.open(result['local_path']).size==(80,60)
    assert result['source_sha256']==sha(movie)
    assert result['blob_sha']==git('rev-parse','HEAD:movie.mp4')
    assert result['sha256']==sha(result['local_path'])
    assert not git('status','--porcelain')
    for seconds in [-1,1,float('nan')]:
        with pytest.raises(ValueError,match='finite time'):
            collect(repo,{'repository':'example/game','assets':[dict(asset,frame_seconds=seconds)]},tmp_path/'out')
    with pytest.raises(ValueError,match='exceeds original'):
        collect(repo,{'repository':'example/game','assets':[dict(asset,frame_crop=[100,0,80,60])]},tmp_path/'out')


def test_clip_is_not_looped_to_hide_missing_footage(tmp_path):
    # A decodable short source cannot silently fill a much longer ShotSpec.
    p=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=blue:s=64x64:r=30:d=0.5','-c:v','libx264',str(p)],check=True)
    with pytest.raises(ValueError,match='insufficient footage'):
        encode_shot({'start':0,'end':4,'assets':['x'],'offsets':[0]}, {'x':{'local_path':str(p)}},tmp_path/'out.mp4',tmp_path/'log')


def test_safe_ui_frame_keeps_top_hud_and_bottom_controls_outside_caption_bars(tmp_path):
    from PIL import Image,ImageDraw
    source=tmp_path/'ui.png';im=Image.new('RGB',(160,90),'#202020');draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,159,89),outline='#ff0000',width=6);im.save(source)
    movie=tmp_path/'out.mp4'
    encode_shot({'start':0,'end':.3,'assets':['ui'],'offsets':[0],'safe_frame':True},
                {'ui':{'local_path':str(source)}},movie,tmp_path/'encode.log')
    frame=tmp_path/'frame.png'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(movie),'-frames:v','1',str(frame)],check=True)
    with Image.open(frame) as image:
        # Sample all four corners of the complete evidence rectangle.
        for xy in [(274,125),(1645,125),(274,875),(1645,875)]:
            red,green,blue=image.getpixel(xy)
            assert red>180 and green<80 and blue<80


def test_aac_cuts_keep_late_voice_pulses_on_timeline_across_channel_changes(tmp_path):
    import array, math, wave
    from video_rush.render import concatenate_cuts
    from video_rush.common import probe
    # Short AAC edits reproduce delay accumulation much sooner than long shots.
    sources=[]
    for channels in [1,2]:
        p=tmp_path/f'cut-{channels}.mp4'
        pulse=r'aevalsrc=if(between(t\,0.06\,0.10)\,0.7*sin(2*PI*1000*t)\,0):s=48000:d=0.2333333333'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
            'color=blue:s=64x64:r=30:d=0.2333333333','-f','lavfi','-i',pulse,
            '-c:v','libx264','-c:a','aac','-ac',str(channels),'-t','0.2333333333',str(p)],check=True)
        sources.append(p)
    shots=[{'start':i*7/30,'end':(i+1)*7/30} for i in range(20)]
    video,audio=concatenate_cuts([sources[i%2] for i in range(20)],shots,tmp_path/'out',tmp_path/'logs')
    with wave.open(str(audio)) as stream:
        assert stream.getnframes()==20*11200
        assert (stream.getnchannels(),stream.getframerate())==(2,48000)
        samples=array.array('h',stream.readframes(stream.getnframes()))
    def rms(start,end):
        window=samples[round(start*96000):round(end*96000)]
        return math.sqrt(sum(x*x for x in window)/len(window))
    for shot in shots:
        assert rms(shot['start']+.07,shot['start']+.09)>5000
        assert rms(shot['start']+.15,shot['start']+.18)<100
    assert abs(float(probe(video)['format']['duration'])-20*7/30)<.002


def test_failed_or_tampered_movie_cannot_be_prereleased(tmp_path):
    from video_rush.publish import verified_files
    from video_rush.common import sha
    movie=tmp_path/'final.mp4';movie.write_bytes(b'validated fixture')
    write(tmp_path/'report.json',{'technical':{'passed':False},'content':{'structural_pass':True},'final':{'sha256':sha(movie)}})
    write(tmp_path/'delivery.json',{'files':{'final.mp4':sha(movie)}})
    with pytest.raises(ValueError,match='requires technical'):verified_files(tmp_path)
    r=read(tmp_path/'report.json');r['technical']['passed']=True;write(tmp_path/'report.json',r)
    with pytest.raises(ValueError,match='Missing required delivery files'):verified_files(tmp_path)
    from video_rush.publish import REQUIRED_FILES
    for name in REQUIRED_FILES-{'final.mp4','report.json'}:
        (tmp_path/name).write_text('fixture')
    manifest={name:sha(tmp_path/name) for name in REQUIRED_FILES}
    write(tmp_path/'delivery.json',{'files':manifest})
    assert verified_files(tmp_path)==manifest
    (tmp_path/'cover.png').write_text('changed cover')
    with pytest.raises(ValueError,match='manifest mismatch'):verified_files(tmp_path)
    movie.write_bytes(b'changed after review')
    with pytest.raises(ValueError,match='changed after validation'):verified_files(tmp_path)


def test_external_media_requires_pinned_hash_and_checks_bytes(tmp_path, monkeypatch):
    import io,hashlib
    from video_rush import footage
    raw=b'original fixture';expected=hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(footage.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(raw))
    asset={'id':'reference','origin':'external','url':'https://example.invalid/image.png','page_url':'https://example.invalid','sha256':expected,'kind':'official_reference_screenshot'}
    assert collect(tmp_path,{'assets':[asset]},tmp_path/'out')[0]['sha256']==expected
    asset['sha256']='0'*64
    with pytest.raises(ValueError,match='SHA256 mismatch'):collect(tmp_path,{'assets':[asset]},tmp_path/'other')


def test_external_archived_movie_keeps_mp4_type_and_probes_real_stream(tmp_path, monkeypatch):
    import io, hashlib
    from video_rush import footage
    movie=tmp_path/'archive.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
                    'testsrc2=s=160x90:r=30:d=0.5','-c:v','libx264',str(movie)],check=True)
    raw=movie.read_bytes()
    monkeypatch.setattr(footage.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(raw))
    asset={'id':'archive','origin':'external','url':'https://example.invalid/commit/movie.mp4',
           'page_url':'https://example.invalid/commit','sha256':hashlib.sha256(raw).hexdigest()}
    result=collect(tmp_path,{'assets':[asset]},tmp_path/'out')[0]
    assert Path(result['local_path']).suffix=='.mp4'
    stream=next(s for s in result['ffprobe']['streams'] if s['codec_type']=='video')
    assert (stream['width'],stream['height'])==(160,90)
    assert Path(result['local_path']).read_bytes()==raw


def test_posting_materials_have_copyable_title_and_description():
    from video_rush.publish import posting_copy
    copy=posting_copy({'title':'主标题','title_candidates':['主标题','备选标题']},'真实的开发简介')
    assert '## 推荐标题\n\n主标题' in copy
    assert '- 备选标题' in copy
    assert '## 简介（可复制）\n\n真实的开发简介' in copy
    with pytest.raises(ValueError,match='title and description'):
        posting_copy({'title':'主标题'},'  ')


@pytest.mark.parametrize('upload_fails',[False,True])
def test_prerelease_includes_submission_asset_and_only_finalizes_complete_upload(tmp_path, monkeypatch, upload_fails):
    from video_rush import publish as publisher
    from video_rush.common import sha
    names=['final.mp4','cover.png','bilibili.md']
    for name in names:(tmp_path/name).write_text('fixture '+name)
    write(tmp_path/'script.json',{'episode':'ep-test','title':'标题'})
    write(tmp_path/'delivery.json',{'files':{}})
    monkeypatch.setattr(publisher,'verified_files',lambda out:{n:sha(tmp_path/n) for n in names})
    assets=[];commands=[]
    current={'id':42,'tag_name':'ep-test','target_commitish':'abc','draft':True,'prerelease':True,'html_url':'https://example.invalid/release','assets':assets}
    def fake_run(args,**kwargs):
        args=[str(a) for a in args];commands.append(args)
        if args[0]=='git':
            return '' if 'status' in args else ('abc refs/heads/main' if 'ls-remote' in args else 'abc')
        if args[1]=='api':return json.dumps(current)
        if args[1:3]==['release','upload']:
            if upload_fails:raise RuntimeError('HTTP401 upload fixture')
            p=Path(args[4]);assets.append({'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+sha(p),'browser_download_url':'https://example.invalid/'+p.name})
        return ''
    monkeypatch.setattr(publisher,'run',fake_run)
    if upload_fails:
        with pytest.raises(RuntimeError,match='HTTP401'):publisher.publish(tmp_path)
        assert (tmp_path/'prerelease.failure.json').exists()
    else:
        publisher.publish(tmp_path)
        assert {a['name'] for a in assets}=={'final.mp4','cover.png','bilibili.md','ep-test-delivery.zip'}
    assert any('--notes-file' in c for c in commands)
    assert any('--draft=false' in c for c in commands)==(not upload_fails)
    assert (tmp_path/'bilibili.md').read_text()=='fixture bilibili.md'
    assert 'bilibili.md' in (tmp_path/'release-notes.md').read_text()


def test_committed_browser_capture_uses_real_controls_and_keeps_source_unchanged(tmp_path):
    import shutil
    pytest.importorskip('playwright.sync_api')
    if not any(shutil.which(x) for x in ['chromium','google-chrome','google-chrome-stable','chromium-browser']):
        pytest.skip('No local Chromium/Chrome executable')
    repo=tmp_path/'source';repo.mkdir()
    html=repo/'index.html';html.write_text('<button id="open" onclick="document.getElementById(\'result\').textContent=\'Opened\'">Open</button><p id="result">Closed</p>')
    subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(repo),'add','.'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','Fixture'],check=True,capture_output=True)
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();original=html.read_bytes()
    asset={'id':'editor','origin':'browser_capture','kind':'editor_screenshot_reconstruction','commit':commit,
           'entry':'index.html','snapshot_paths':['index.html'],'viewport':{'width':640,'height':360},
           'steps':[{'operation':'click','selector':'#open'}]}
    result=collect(repo,{'repository':'test/editor','assets':[asset]},tmp_path/'out'/'media')[0]
    assert result['browser_receipt']['source_commit']==commit
    assert 'Opened' in result['browser_receipt']['observed_page_text']
    assert result['browser_receipt']['all_snapshot_git_blobs_verified']
    assert result['browser_receipt']['page_errors']==[]
    assert (tmp_path/'out'/result['capture_receipt']).exists()
    assert html.read_bytes()==original
    assert subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True)==''
