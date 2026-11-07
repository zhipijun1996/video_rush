import hashlib,io,json,zipfile
from pathlib import Path
from PIL import Image
import pytest
from video_rush.footage import collect
from video_rush import archive_media


def setup_archive(monkeypatch, *, member='bundle/map.png', extra=None, corrupt=False):
    image=io.BytesIO();Image.new('RGB',(80,45),'#81dce1').save(image,format='PNG');data=image.getvalue()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr(member,data)
        if extra:z.writestr(*extra)
    raw=stream.getvalue();calls=[]
    def fetch(*args,**kwargs):calls.append(args[0]);return io.BytesIO(raw)
    monkeypatch.setattr(archive_media.urllib.request,'urlopen',fetch)
    archive={'url':'https://example.org/source.zip','page_url':'https://example.org/comment','sha256':hashlib.sha256(raw).hexdigest()}
    asset={'id':'map','origin':'archive','archive_id':'source','member':member,'sha256':hashlib.sha256(data).hexdigest(),'kind':'design','preserve_evidence':True}
    if corrupt:asset['sha256']='0'*64
    return archive,asset,data,calls


def test_exact_zip_member_and_preserved_evidence_with_shared_cache(tmp_path,monkeypatch):
    archive,asset,data,calls=setup_archive(monkeypatch)
    spec={'archives':{'source':archive},'assets':[asset,dict(asset,id='second')]}
    rows=collect(tmp_path,spec,tmp_path/'episode/media')
    assert len(calls)==1
    for r in rows:
        assert Path(r['local_path']).read_bytes()==data
        assert (tmp_path/'episode'/r['preserved_evidence']).read_bytes()==data
        assert r['archive_receipt']['archive_sha256']==archive['sha256']
        assert r['dimensions']==[80,45]


@pytest.mark.parametrize('member',['../map.png','/map.png',r'folder\map.png','bundle/run.py'])
def test_refuses_unsafe_or_executable_members(tmp_path,monkeypatch,member):
    archive,asset,_,calls=setup_archive(monkeypatch,member=member)
    with pytest.raises(ValueError,match='Unsafe or unsupported'):archive_media.collect(asset,archive,tmp_path)
    assert not calls


def test_refuses_wrong_member_digest_and_wrong_archive_digest(tmp_path,monkeypatch):
    archive,asset,_,_=setup_archive(monkeypatch,corrupt=True)
    with pytest.raises(ValueError,match='member SHA256'):archive_media.collect(asset,archive,tmp_path)
    archive['sha256']='0'*64
    with pytest.raises(ValueError,match='Archive SHA256'):archive_media.collect(asset,archive,tmp_path/'other')


def test_rejects_zip_size_bomb_before_member_use(tmp_path,monkeypatch):
    archive,asset,_,_=setup_archive(monkeypatch,extra=('large.txt','x'*200))
    monkeypatch.setattr(archive_media,'MAX_UNPACKED',100)
    with pytest.raises(ValueError,match='unpacked size'):archive_media.collect(asset,archive,tmp_path)
