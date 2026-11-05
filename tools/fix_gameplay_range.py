"""Repair omitted range VUI on this producer's already TV-normalized pixels.

Never relabel pc/full-range sources. Refuse other failed checks. Prove that
decoded YUV frames and PCM audio are unchanged, then rerun the actual gate.
"""
from pathlib import Path
import argparse
import hashlib
import shutil
from video_rush.common import read, write, sha, probe, run
from video_rush.gameplay import validate_gameplay


def decoded_hashes(path):
    frames=run(['ffmpeg','-v','error','-i',path,'-map','0:v:0','-f','framemd5','-'],timeout=600)
    samples=[row.split(',')[-1].strip() for row in frames.splitlines() if row and not row.startswith('#')]
    audio=run(['ffmpeg','-v','error','-i',path,'-map','0:a:0','-c:a','pcm_s16le','-f','hash','-hash','sha256','-'],timeout=300).strip()
    return dict(video_frames=len(samples),ordered_decoded_yuv_sha256=hashlib.sha256('\n'.join(samples).encode()).hexdigest(),decoded_pcm=audio)


def fix(root):
    root=Path(root).resolve();report=read(root/'report.json');movie=root/'final.mp4'
    failed=[k for k,v in report['technical']['checks'].items() if not v]
    if not failed:return {'status':'already_valid_no_change'}
    if failed!=['limited_range'] or report['mode']!='original_game_audio/no_narration':raise ValueError('Only omitted range metadata in the known normalized producer is repairable')
    stream=next(s for s in probe(movie)['streams'] if s['codec_type']=='video')
    if stream.get('color_range') not in (None,'unknown'):raise ValueError('Refusing to relabel explicit/full range')
    manifest=read(root/'delivery-manifest.json')['files'];omitted=[]
    for name,expected in manifest.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('Unsafe manifest path')
        if not path.exists() and name in {'cover-plains1.png','cover-forest1.png'}:omitted.append(name);continue
        if not path.is_file() or sha(path)!=expected:raise ValueError('Original package integrity failed: '+name)
    if sha(movie)!=report['movie_sha256']:raise ValueError('Original movie differs from its report')
    original_sha=sha(movie);before=decoded_hashes(movie);temp=root/'range-fixed.mp4'
    run(['ffmpeg','-nostdin','-y','-v','error','-i',movie,'-map','0','-c','copy','-bsf:v','h264_metadata=video_format=5:video_full_range_flag=0','-movflags','+faststart',temp],log=root/'logs/range-metadata.log',timeout=300)
    after=decoded_hashes(temp)
    if before!=after:raise ValueError('Decoded frames/audio changed; keep original movie')
    if next(s for s in probe(temp)['streams'] if s['codec_type']=='video').get('color_range')!='tv':raise ValueError('Range VUI still not explicit')
    shutil.copyfile(root/'report.json',root/'original-host-report.json')
    shutil.copyfile(root/'delivery-manifest.json',root/'original-host-manifest.json')
    temp.replace(movie)
    result=validate_gameplay(root)
    if not result['technical']['passed']:raise ValueError('Repaired movie failed actual quality checks')
    receipt=dict(status='verified_metadata_only_range_repair',original_movie_sha256=original_sha,final_movie_sha256=sha(movie),decoded_before=before,decoded_after=after,decoded_content_unchanged=True,omitted_render_caches=omitted,original_host_failed_checks=failed)
    write(root/'range-repair.json',receipt)
    write(root/'delivery-manifest.json',{'files':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and p.name!='delivery-manifest.json' and 'cuts' not in p.relative_to(root).parts}})
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');a=p.parse_args();print(fix(a.root))
