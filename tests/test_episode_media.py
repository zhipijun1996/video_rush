"""Prior-delivery reuse validates the exact source, not an arbitrary new edit."""
import hashlib,json,zipfile
from pathlib import Path
import pytest
from PIL import Image
from video_rush.episode_media import collect
from video_rush.common import sha


def fixture(tmp_path,monkeypatch,*,corrupt=False,unsafe=False):
    image=tmp_path/'source.png';Image.new('RGB',(20,12),'red').save(image);raw=image.read_bytes();h=sha(image)
    prior={'id':'source','local_path':'/original-run/media/source.png','sha256':h,'kind':'original_game_screenshot','commit':'a'*40,'source_url':'https://example.invalid/pinned-original'}
    cache=tmp_path/'cache';cache.mkdir();zpath=cache/'source.zip'
    with zipfile.ZipFile(zpath,'w') as z:
        z.writestr('sources.json',json.dumps({'assets':[prior]}));z.writestr('media/source.png',b'bad bytes' if corrupt else raw)
        if unsafe:z.writestr('../escape.txt','must not extract')
    zh=sha(zpath);zpath.rename(cache/(zh+'.zip'));monkeypatch.setenv('VIDEO_RUSH_EPISODE_ARCHIVES',str(cache))
    delivery={'repository':'owner/production','artifact_id':1,'sha256':zh,'episode':'previous'}
    asset=dict(prior,id='reuse',origin='episode_artifact',source_asset='source')
    output=tmp_path/'output'/'media';output.mkdir(parents=True)
    return asset,delivery,output,h


def test_reuses_original_bytes_and_preserves_provenance(tmp_path,monkeypatch):
    a,d,out,h=fixture(tmp_path,monkeypatch)
    r=collect(a,d,out)
    assert sha(r['local_path'])==h and r['prior_delivery']['source_asset']=='source'
    assert r['source_url']=='https://example.invalid/pinned-original'
    assert (out.parent/'source-evidence/delivery-previous-sources.json').exists()


def test_rejects_other_commit(tmp_path,monkeypatch):
    a,d,out,h=fixture(tmp_path,monkeypatch);a['commit']='b'*40
    with pytest.raises(ValueError,match='provenance mismatch'):collect(a,d,out)


def test_rejects_corrupt_member_even_in_correctly_hashed_archive(tmp_path,monkeypatch):
    a,d,out,h=fixture(tmp_path,monkeypatch,corrupt=True)
    with pytest.raises(ValueError,match='member hash mismatch'):collect(a,d,out)


def test_rejects_path_escape_even_if_not_selected(tmp_path,monkeypatch):
    a,d,out,h=fixture(tmp_path,monkeypatch,unsafe=True)
    with pytest.raises(ValueError,match='Unsafe delivery member'):collect(a,d,out)
