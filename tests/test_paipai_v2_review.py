import copy
import hashlib
import io
import zipfile
import pytest
from PIL import Image,ImageDraw,ImageChops
from tools.make_paipai_v2_review import validate_trials
from tools.paipai_v2_assets import restore_portable
from video_rush.paipai_v2_art import actor
from video_rush.paipai_v2_score import arrange,midi_file


def test_no_accidental_overlapping_foreground_dialogue():
    trials=[{'id':id,'seconds':3,'segments':[{'seconds':3}],'voices':[{'start':0,'seconds':1},{'start':1.1,'seconds':1}]} for id in ['01_light','02_hadouken','03_dio_ultra']]
    validate_trials(trials)
    trials[1]['voices'][1]['start']=.5
    with pytest.raises(ValueError,match='Overlapping foreground'):validate_trials(trials)


def test_madness_moves_actor_limbs_without_background_tricks():
    frames=[]
    for t in [.15,.95]:
        canvas=Image.new('RGB',(1280,720),'white');actor(ImageDraw.Draw(canvas),canvas,355,655,t,'mad',.5,.5);frames.append(canvas)
    # Compare arms/torso, below the head, against a completely static background.
    diff=ImageChops.difference(*frames).crop((150,400,600,650))
    assert sum(1 for r,g,b in diff.getdata() if max(r,g,b)>40)>2500


def test_original_score_has_real_peak_and_editable_midi(tmp_path):
    events,bpm=arrange('heroic',8,4)
    assert any(abs(t-4)<.001 and ch==9 and velocity>=110 for t,kind,ch,key,velocity in events if kind==1)
    assert any(ch in [4,8] and 2<=t<4 for t,kind,ch,key,velocity in events if kind==1)
    p=tmp_path/'hero.mid';midi_file(p,events,bpm);assert p.read_bytes().startswith(b'MThd')


def test_transport_rejects_reordering_and_path_traversal(tmp_path,monkeypatch):
    import requests
    def zipped(name,data):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr(name,data)
        return b.getvalue()
    raw=zipped('../outside.txt',b'never extract')
    pieces=[raw[:len(raw)//2],raw[len(raw)//2:]]
    class Response:
        def __init__(self,content):self.content=content
        def raise_for_status(self):pass
    class Session:
        def __init__(self):self.headers={}
        def get(self,url,**kwargs):return Response(zipped('000.bin',pieces[0 if '/11/' in url else 1]))
    monkeypatch.setattr(requests,'Session',Session)
    h=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError,match='SHA256 mismatch'):restore_portable([12,11],h,tmp_path,'owner/repo','fixture')
    with pytest.raises(ValueError,match='Unsafe review bundle'):restore_portable([11,12],h,tmp_path,'owner/repo','fixture')
    assert not (tmp_path.parent/'outside.txt').exists()
