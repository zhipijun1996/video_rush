from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from PIL import Image
from video_rush.graphics import graphic
from video_rush.footage import collect
from video_rush.common import sha


def test_explanatory_diagram_is_readable_editable_and_traceable(tmp_path):
    g={'layout':'diagram','elements':[
        {'type':'rect','bounds':[100,200,700,300]},
        {'type':'text','x':130,'y':240,'text':'入口 < 出口 & 有向路线','width':640},
        {'type':'line','points':[[850,300],[1100,300]],'arrow':True,'both':True}]}
    rows=collect(tmp_path,{'repository':'test/repo','assets':[{'id':'route','origin':'editorial','kind':'explanatory_diagram','graphic':g}]},tmp_path/'media')
    svg=tmp_path/rows[0]['editable_svg']
    assert sha(svg)==rows[0]['svg_sha256']
    root=ET.parse(svg).getroot()
    ns={'s':'http://www.w3.org/2000/svg'}
    assert root.find('s:text',ns).text=='入口 < 出口 & 有向路线'
    assert len(root.findall('s:polygon',ns))==2
    im=Image.open(rows[0]['local_path'])
    assert im.size==(1920,1080) and im.getpixel((850,300))!=(16,27,43)
    with pytest.raises(ValueError,match='too long'):
        graphic(tmp_path/'bad.png',{'layout':'diagram','elements':[{'type':'text','x':10,'y':10,'text':'字'*100,'width':50}]})
    with pytest.raises(ValueError,match='outside canvas'):
        graphic(tmp_path/'bad.png',{'layout':'diagram','elements':[{'type':'rect','bounds':[1900,100,100,100]}]})


def test_animation_has_real_layer_motion_and_static_video_is_rejected(tmp_path):
    from video_rush.animation import encode_diagram, audit_motion, tracks
    from video_rush.common import run
    import subprocess
    shot={'id':'moving','assets':['a'],'start':0,'end':3}
    g={'layout':'diagram','elements':[
        {'type':'rect','bounds':[200,250,240,180],'fill':'#ff3030','stroke':'#ff3030','group':'candidate'}],
        'motion_groups':[{'id':'candidate','start':.12,'end':.85,'from':[0,0],'to':[600,0],'travel':.4,'fade':.02}]}
    # Regression: a late seven-layer tree used to cause unbounded buffering
    # when overlays were disabled before their start time (actual r20 OOM).
    for i in range(6):
        name='branch'+str(i)
        g['elements'].append({'type':'rect','bounds':[100+i*220,600,140,100],'group':name})
        g['motion_groups'].append({'id':name,'start':.1+i*.12,'travel':.1,'fade':.02})
    cut=tmp_path/'cuts/moving.mp4';cut.parent.mkdir()
    encode_diagram(shot,{'a':{'origin':'editorial','graphic':g}},cut,tmp_path/'encode.log')
    proof=audit_motion(tmp_path,shot,g)
    assert proof['actual_motion_detected']
    assert (tmp_path/'animation-evidence/moving-contact.jpg').exists()
    def pixel(t,x,y):
        p=subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(cut),'-vf',f'crop=2:2:{x}:{y}',
                          '-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True)
        return p.stdout[:3]
    assert pixel(.05,220,280)[0]<50  # not yet visible
    assert pixel(1.9,820,280)[0]>200  # moved into its final position
    assert pixel(2.9,820,280)[0]<50  # exited, not a permanent full-canvas overlay
    run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=0x101b2b:s=1920x1080:r=30',
         '-frames:v','90','-an','-c:v','libx264','-preset','ultrafast',cut])
    assert not audit_motion(tmp_path,shot,g)['actual_motion_detected']
    bad=dict(g,motion_groups=[dict(g['motion_groups'][0],start=.9,end=.5)])
    with pytest.raises(ValueError,match='interval'):tracks(bad)


def test_animation_timing_edit_invalidates_cache_even_with_identical_flat_png(tmp_path):
    import copy,subprocess
    from video_rush.animation import encode_diagram
    from video_rush.pipeline import Stages,cut_source_fingerprints
    source=tmp_path/'preview.png';movie=tmp_path/'cut.mp4'
    shot={'id':'cue','presentation':'animated_diagram','assets':['a'],'start':0,'end':2}
    g={'layout':'diagram','elements':[{'type':'rect','bounds':[200,250,300,150],
        'fill':'#ff3030','stroke':'#ff3030','group':'cue'}],
        'motion_groups':[{'id':'cue','start':.1,'from':[0,0]}]}
    asset={'origin':'editorial','graphic':g}
    runner=Stages(tmp_path/'state')
    def render():
        encode_diagram(shot,{'a':asset},movie,tmp_path/'encode.log');return [movie]
    def red_channel():
        r=subprocess.run(['ffmpeg','-v','error','-ss','0.8','-i',str(movie),'-vf','crop=2:2:220:280',
            '-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True)
        return r.stdout[0]
    graphic(source,g);asset['sha256']=sha(source)
    runner.execute('Rendering',cut_source_fingerprints(shot,{'a':asset}),render)
    assert red_channel()>200
    before=sha(source);later=copy.deepcopy(g);later['motion_groups'][0]['start']=.7
    graphic(source,later);assert sha(source)==before
    asset['graphic']=later
    runner.execute('Rendering',cut_source_fingerprints(shot,{'a':asset}),render)
    assert red_channel()<50
