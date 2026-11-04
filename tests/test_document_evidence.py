import hashlib
from pathlib import Path
import pytest
from video_rush.document_evidence import collect_documents
from video_rush.quality import validate_evidence_registry


def test_cached_document_must_match_git_blob_and_displayed_quote(tmp_path):
    data='当前规则，不等于旧设计。'.encode();commit='a'*40
    d={'id':'doc','repository':'owner/repo','commit':commit,'path':'docs/rules.md','url':f'https://raw.githubusercontent.com/owner/repo/{commit}/docs/rules.md','sha256':hashlib.sha256(data).hexdigest(),'blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'verified_quotes':['当前规则']}
    p=tmp_path/'doc/rules.md';p.parent.mkdir();p.write_bytes(data)
    assert collect_documents([d],tmp_path)[0]['quoted_document_not_browser_screenshot']
    with pytest.raises(ValueError,match='quote absent'):collect_documents([{**d,'verified_quotes':['虚构结论']}],tmp_path)
    with pytest.raises(ValueError,match='blob differs'):collect_documents([{**d,'blob_sha':'0'*40}],tmp_path)
    with pytest.raises(ValueError,match='URL'):collect_documents([{**d,'url':'https://example.com/other'}],tmp_path)


def test_run_metadata_cannot_overwrite_source_registry_id():
    evidence={'id':'ci-failure-api',**{'id':41659241932}}
    spec={'evidence':[evidence],'shots':[{'id':'case','evidence':['ci-failure-api']}]}
    with pytest.raises(ValueError,match='non-empty strings'):validate_evidence_registry(spec)
    spec['evidence']=[{'id':'ci-failure-api','run_id':41659241932}]
    validate_evidence_registry(spec)
    spec['shots'][0]['evidence']=['missing-proof']
    with pytest.raises(ValueError,match='Unresolved'):validate_evidence_registry(spec)


def test_evidence_repair_cannot_hide_a_changed_narration_or_music():
    from copy import deepcopy
    from tools.repair_episode_metadata import comparable
    old={'evidence':[{'id':4165}],'shots':[{'narration':'真实原稿'}],'music_asset':{'path':'runner/music.ogg','source':'transport','sha256':'a'*64},'research_scope':{'episode_evidence':[{'id':4165}],'head':'abc'}}
    new={'evidence':[{'id':'proof','run_id':4165}],'shots':[{'narration':'真实原稿'}],'music_asset':{'path':'local/music.ogg','source':'user','sha256':'a'*64},'research_scope':{'head':'abc'}}
    assert comparable(old)==comparable(new)
    changed=deepcopy(new);changed['shots'][0]['narration']='修改后的口播'
    assert comparable(old)!=comparable(changed)
    changed=deepcopy(new);changed['music_asset']['sha256']='b'*64
    assert comparable(old)!=comparable(changed)
