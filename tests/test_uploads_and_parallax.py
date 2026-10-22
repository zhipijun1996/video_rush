import hashlib
import io
import subprocess
import zipfile

import pytest
from PIL import Image

from video_rush.footage import collect
from video_rush.transfers import restore_upload_pack
from video_rush.render import encode_shot


def test_exact_uploaded_image_is_restored_preserved_and_tampering_refused(tmp_path, monkeypatch):
    import video_rush.footage as footage
    monkeypatch.setattr(footage, 'ROOT', tmp_path)
    stream=io.BytesIO();Image.new('RGB',(20,12),'orange').save(stream,format='JPEG')
    raw=stream.getvalue();asset={'id':'photo','origin':'user_upload','path':'build/inputs/ep/photo.jpg',
        'original_filename':'phone-original.jpg','sha256':hashlib.sha256(raw).hexdigest(),
        'user_attachment':True,'kind':'concept_art'}
    pack=io.BytesIO()
    with zipfile.ZipFile(pack,'w') as z:z.writestr('photo.jpg',raw)
    restore_upload_pack(pack.getvalue(),[asset],tmp_path)
    results=collect(tmp_path,{'repository':'owner/game','assets':[asset]},tmp_path/'episode/media')
    assert (tmp_path/'episode/original_uploads/phone-original.jpg').read_bytes()==raw
    assert results[0]['source_url']=='user-upload:phone-original.jpg'
    assert results[0]['sha256']==asset['sha256']
    (tmp_path/asset['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='SHA256 mismatch'):
        collect(tmp_path,{'repository':'owner/game','assets':[asset]},tmp_path/'episode/media')


def test_upload_pack_refuses_unrequested_path_before_writing(tmp_path):
    pack=io.BytesIO()
    with zipfile.ZipFile(pack,'w') as z:z.writestr('../outside.jpg',b'not an image')
    asset={'path':'build/inputs/ep/photo.jpg','sha256':'0'*64}
    with pytest.raises(ValueError,match='exactly the declared'):
        restore_upload_pack(pack.getvalue(),[asset],tmp_path)
    assert not (tmp_path/'outside.jpg').exists()


def test_actual_parallax_film_moves_near_marker_faster_than_far(tmp_path):
    source=tmp_path/'bands.png';im=Image.new('RGB',(3840,720),'#18212d')
    from PIL import ImageDraw
    ImageDraw.Draw(im).rectangle((1000,0,1011,719),fill='white');im.save(source)
    movie=tmp_path/'parallax.mp4'
    encode_shot({'start':0,'end':2.1,'assets':['template'],'presentation':'parallax_diagram',
                 'parallax_rates':[20,40,80]}, {'template':{'local_path':str(source)}},
                movie,tmp_path/'render.log')
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(movie),'-vf',
        "select='eq(n,0)+eq(n,60)'",'-vsync','0','-pix_fmt','rgb24','-f','rawvideo','-'])
    frame_bytes=1920*1080*3;assert len(raw)==frame_bytes*2
    images=[Image.frombytes('RGB',(1920,1080),raw[i*frame_bytes:(i+1)*frame_bytes]) for i in range(2)]
    displacements=[]
    for y in [260,500,740]:
        xs=[]
        for image in images:
            bright=[x for x in range(500,1400) if min(image.getpixel((x,y)))>220]
            assert bright
            xs.append(sum(bright)/len(bright))
        displacements.append(xs[0]-xs[1])
    assert displacements==pytest.approx([40,80,160],abs=3)
