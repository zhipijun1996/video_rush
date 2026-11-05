"""Verify an actual downloaded gameplay package and remove only omitted caches.

No audiovisual file is changed. Missing source/recording/cover/posting assets
are fatal. Only two known cover-extraction intermediates may be omitted.
"""
import argparse
from pathlib import Path
from video_rush.common import read, write, sha, run, probe

ALLOWED_CACHES={'cover-plains1.png','cover-forest1.png'}


def check(root):
    root=Path(root).resolve();manifest=read(root/'delivery-manifest.json')['files']
    old_hash=sha(root/'delivery-manifest.json');removed=[]
    for name,expected in manifest.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('Unsafe delivery path')
        if not path.exists():
            if name in ALLOWED_CACHES:removed.append(name);continue
            raise ValueError('Missing delivery asset: '+name)
        if sha(path)!=expected:raise ValueError('Delivery digest mismatch: '+name)
    for name in ['final.mp4','cover.png','bilibili.md','script.md','storyboard.json','subtitles.ass','sources.json','report.json']:
        if not (root/name).is_file():raise ValueError('Missing required delivery '+name)
    report=read(root/'report.json');movie_hash=sha(root/'final.mp4')
    if not report['technical']['passed'] or movie_hash!=report['movie_sha256']:raise ValueError('Invalid technical report/movie')
    sources=read(root/'sources.json')['captures']
    for source in sources:
        recording=root/source['delivered_recording']
        if sha(recording)!=source['movie_sha256']:raise ValueError('Original recording mismatch')
        if sha(recording.parent/'recording_driver.gd')!=source['driver_sha256']:raise ValueError('Executed driver mismatch')
    total=float(probe(root/'final.mp4')['format']['duration']);cues=[]
    def seconds(value):
        h,m,s=value.split(':');return int(h)*3600+int(m)*60+float(s)
    for line in (root/'subtitles.ass').read_text().splitlines():
        if line.startswith('Dialogue:'):
            fields=line.split(',',9);cues.append((seconds(fields[1]),seconds(fields[2])))
    if not cues or not all(0<=a<b<=total+.02 for a,b in cues):raise ValueError('Actual ASS bounds invalid')
    if not all(a[1]<=b[0]+.01 for a,b in zip(cues,cues[1:])):raise ValueError('Actual ASS cues overlap')
    run(['ffmpeg','-v','error','-xerror','-i',root/'final.mp4','-f','null','-'],log=root/'logs/downloaded-decode.log',timeout=600)
    result=dict(original_manifest_sha256=old_hash,verified_existing_files=len(manifest)-len(removed),removed_omitted_render_caches=removed,
                final_sha256=movie_hash,audiovisual_changes=False,original_recordings_verified=len(sources),actual_ass_cues_verified=len(cues),full_downloaded_movie_decode=True,
                reason='Omitted temporary cover extraction frames are not final cover or gameplay sources. All required delivery assets and original recordings remain digest-verified.')
    write(root/'download-verification.json',result)
    write(root/'delivery-manifest.json',{'files':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and p.name!='delivery-manifest.json' and 'cuts' not in p.relative_to(root).parts}})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args();print(check(a.root))


if __name__=='__main__':main()
