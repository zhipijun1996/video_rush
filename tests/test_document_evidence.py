import hashlib
from pathlib import Path
import pytest
from video_rush.document_evidence import collect_documents


def test_cached_document_must_match_git_blob_and_displayed_quote(tmp_path):
    data='当前规则，不等于旧设计。'.encode();commit='a'*40
    d={'id':'doc','repository':'owner/repo','commit':commit,'path':'docs/rules.md','url':f'https://raw.githubusercontent.com/owner/repo/{commit}/docs/rules.md','sha256':hashlib.sha256(data).hexdigest(),'blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'verified_quotes':['当前规则']}
    p=tmp_path/'doc/rules.md';p.parent.mkdir();p.write_bytes(data)
    assert collect_documents([d],tmp_path)[0]['quoted_document_not_browser_screenshot']
    with pytest.raises(ValueError,match='quote absent'):collect_documents([{**d,'verified_quotes':['虚构结论']}],tmp_path)
    with pytest.raises(ValueError,match='blob differs'):collect_documents([{**d,'blob_sha':'0'*40}],tmp_path)
    with pytest.raises(ValueError,match='URL'):collect_documents([{**d,'url':'https://example.com/other'}],tmp_path)
