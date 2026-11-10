from video_rush.pipeline import Stages,delivery_fingerprints,delivery_members
from video_rush.common import write,read,sha


def test_metadata_only_revision_refreshes_delivery_when_quality_report_is_identical(tmp_path):
    # Actual regression: report stayed identical after a sources-only correction,
    # so the old Delivery stage ran from cache and left an unusable manifest.
    for name in delivery_members(tmp_path):
        if name!='bilibili.md':(tmp_path/name).write_text('fixture, not a production movie')
    stage=Stages(tmp_path);calls=[]
    def deliver():
        calls.append(1);write(tmp_path/'delivery.json',{'files':delivery_fingerprints(tmp_path)})
        return [tmp_path/'delivery.json']
    def resume():stage.execute('Delivery',{'payload':delivery_fingerprints(tmp_path),'report':sha(tmp_path/'report.json')},deliver)
    resume();resume();assert len(calls)==1
    report_hash=sha(tmp_path/'report.json')
    (tmp_path/'sources.json').write_text('corrected source attribution')
    resume();assert len(calls)==2 and sha(tmp_path/'report.json')==report_hash
    assert read(tmp_path/'delivery.json')['files']['sources.json']==sha(tmp_path/'sources.json')
    folder=tmp_path/'source-evidence';folder.mkdir();(folder/'exact-note.txt').write_text('new retained evidence')
    resume();assert len(calls)==3 and 'source-evidence/exact-note.txt' in read(tmp_path/'delivery.json')['files']
