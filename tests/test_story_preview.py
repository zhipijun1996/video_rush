import json
from pathlib import Path
import subprocess

import pytest

from tools.capture_wave_story import verify_runtime
from tools.make_wave_story import source_window
from video_rush.stick_story import frame


def test_pinned_runtime_detects_changed_game_source(tmp_path):
    source=tmp_path/'source';runtime=tmp_path/'runtime';source.mkdir();runtime.mkdir()
    subprocess.run(['git','init',str(source)],check=True,capture_output=True)
    for root in (source,runtime):
        (root/'src').mkdir()
        for i in range(21):(root/'src'/f'{i}.txt').write_text(f'source {i}')
    subprocess.run(['git','-C',str(source),'add','.'],check=True)
    subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@example.com','commit','-m','fixture'],check=True,capture_output=True)
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert len(verify_runtime(source,runtime,commit)['files'])==21
    (runtime/'src/6.txt').write_text('wrong game revision')
    with pytest.raises(ValueError,match='differs from pinned source'):verify_runtime(source,runtime,commit)


def test_story_windows_cannot_loop_or_overrun_real_footage(tmp_path):
    p=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=160x90:r=30:d=1','-c:v','libx264','-threads','1',str(p)],check=True)
    source_window(p,.2,.7)
    for offset,seconds in [(-.1,.2),(.8,.5),(0,float('nan')),(0,0)]:
        with pytest.raises(ValueError,match='outside actual footage'):source_window(p,offset,seconds)


def test_story_characters_articulate_inside_body_regions():
    # Body-only regions: changes must come from poses, not source labels/camera.
    import PIL.ImageChops
    for scene,box in [('baby',(470,230,800,590)),('training',(440,280,850,610)),('clink',(350,290,930,460))]:
        a=frame(scene,.1,3).crop(box);b=frame(scene,1.4,3).crop(box)
        assert PIL.ImageChops.difference(a,b).getbbox() is not None


def test_final_frame_check_rejects_a_wrong_but_decodable_shot(tmp_path):
    from tools.make_wave_story import verify_final_shots
    segments=tmp_path/'segments';segments.mkdir()
    for filename,color in [(segments/'one.mp4','white'),(tmp_path/'wrong.mp4','black')]:
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color={color}:s=1920x1080:r=30:d=0.5',
                        '-c:v','libx264','-preset','ultrafast','-threads','1',str(filename)],check=True)
    timeline=[{'id':'one','start':0,'seconds':.5}]
    assert verify_final_shots(segments/'one.mp4',timeline,segments)[0]['passed']
    assert not verify_final_shots(tmp_path/'wrong.mp4',timeline,segments)[0]['passed']
