import hashlib
import io
import json
from pathlib import Path
import runpy
import zipfile
import pytest


@pytest.mark.parametrize('tampered',[False,True])
@pytest.mark.parametrize('original_score',[False,True])
def test_actions_music_restores_exact_order_and_rejects_hash_mismatch(tmp_path,monkeypatch,tampered,original_score):
    import requests
    script=Path(__file__).parents[1]/'tools/restore_actions_music.py'
    chunks=[b'first original chunk',b'second original chunk']
    payloads=[]
    for i,b in enumerate(chunks):
        target=io.BytesIO()
        with zipfile.ZipFile(target,'w') as z:z.writestr(f'{i:03}.bin',b)
        payloads.append(target.getvalue())
    class Response:
        def __init__(self,content):self.content=content
        def raise_for_status(self):pass
    class Session:
        headers={}
        def get(self,url,**kwargs):return Response(payloads[0 if '/11/' in url else 1])
    monkeypatch.setattr(requests,'Session',Session)
    monkeypatch.chdir(tmp_path)
    spec={'music_asset':{'sha256':'original_source_hash','path':'original.mp3','source':'user upload'}}
    if original_score:spec['music_asset'].update(origin='procedural_original',source='Original battle score, no samples')
    (tmp_path/'episode.json').write_text(json.dumps(spec))
    for k,v in {'GITHUB_REPOSITORY':'example/repo','GH_TOKEN':'fixture','VR_MUSIC_ARTIFACTS':'[12,11]',
                'VR_MUSIC_SHA256':('0'*64 if tampered else hashlib.sha256(b''.join(chunks)).hexdigest()),
                'VR_SPEC':'episode.json'}.items():monkeypatch.setenv(k,v)
    if tampered:
        with pytest.raises(ValueError,match='SHA256 mismatch'):runpy.run_path(str(script))
        assert not (tmp_path/'build/actions-episode.json').exists()
    else:
        runpy.run_path(str(script))
        assert (tmp_path/'build/music/the_kindred_hearth-actions.ogg').read_bytes()==b''.join(chunks)
        result=json.loads((tmp_path/'build/actions-episode.json').read_text())
        assert result['music_asset']['original_sha256']=='original_source_hash'
        assert result['music_asset']['sha256']==hashlib.sha256(b''.join(chunks)).hexdigest()
        if original_score:
            assert 'Original battle score' in result['music_asset']['source']
            assert 'User-uploaded' not in result['music_asset']['source']
