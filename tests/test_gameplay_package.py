import pytest
from tools.check_gameplay_package import check
from video_rush.common import write


def test_missing_original_recording_is_never_treated_as_render_cache(tmp_path):
    write(tmp_path/'delivery-manifest.json',{'files':{'recordings/plains1/gameplay.mp4':'0'*64}})
    with pytest.raises(ValueError,match='Missing delivery asset'):
        check(tmp_path)


def test_tampered_cover_is_rejected_before_delivery(tmp_path):
    (tmp_path/'cover.png').write_bytes(b'wrong cover')
    write(tmp_path/'delivery-manifest.json',{'files':{'cover.png':'0'*64}})
    with pytest.raises(ValueError,match='digest mismatch'):
        check(tmp_path)


def test_delivery_manifest_cannot_escape_package(tmp_path):
    write(tmp_path/'delivery-manifest.json',{'files':{'../outside.mp4':'0'*64}})
    with pytest.raises(ValueError,match='Unsafe delivery path'):
        check(tmp_path)
