"""Phone-sized movie package; full raw recordings stay in the full Artifact."""
import argparse
from pathlib import Path
import shutil
from video_rush.common import read, write, sha


def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--full-url',required=True);a=p.parse_args()
    source=Path(a.source);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    for file in source.rglob('*'):
        if not file.is_file():continue
        relative=file.relative_to(source)
        if file.suffix=='.mp4' and relative.as_posix()!='final.mp4':continue
        if relative.as_posix()=='delivery-manifest.json':relative=Path('full-delivery-manifest.json')
        target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    external=[dict(stage=r['stage'],path=r['delivered_recording'],sha256=r['movie_sha256']) for r in read(source/'sources.json')['captures']]
    write(out/'watch-package.json',dict(kind='phone movie with external full recordings',full_package_url=a.full_url,external_recordings=external,movie_unchanged=sha(out/'final.mp4')==read(out/'report.json')['movie_sha256']))
    (out/'recordings.md').write_text('手机观看包包含成片、封面、投稿资料及录像证据。五份完整录像单独保存在[完整交付包]('+a.full_url+')；完整包清单为 full-delivery-manifest.json，当前手机包清单为 delivery-manifest.json。成片完全相同。\n')
    write(out/'delivery-manifest.json',{'files':{str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='delivery-manifest.json'}})


if __name__=='__main__':main()
