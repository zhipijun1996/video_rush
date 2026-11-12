"""Make a small, complete phone preview from an already verified delivery."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def make(source, output):
    source=Path(source);output=Path(output)
    movie=source/'final.mp4'
    report=json.loads((source/'report.json').read_text())
    manifest=json.loads((source/'delivery-manifest.json').read_text())['files']
    original_sha=sha(movie)
    if not report['technical']['passed'] or original_sha!=report['movie_sha256'] or original_sha!=manifest['final.mp4']:
        raise ValueError('Preview requires the verified complete master')
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(movie),
        '-map','0:v:0','-map','0:a:0','-vf','scale=1280:720:flags=lanczos,setsar=1',
        '-c:v','libx264','-preset','fast','-crf','28','-maxrate','1400k','-bufsize','2800k',
        '-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','80k','-ar','48000',
        '-movflags','+faststart',str(output)],check=True,timeout=600)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(output),'-f','null','-'],check=True,timeout=300)
    before=probe(movie);after=probe(output)
    v=next(s for s in after['streams'] if s['codec_type']=='video')
    a=next(s for s in after['streams'] if s['codec_type']=='audio')
    if [v['width'],v['height']]!=[1280,720] or v['avg_frame_rate']!='30/1' or v['codec_name']!='h264' or a['codec_name']!='aac':
        raise ValueError('Wrong phone preview format')
    if abs(float(after['format']['duration'])-float(before['format']['duration']))>.1:
        raise ValueError('Preview must retain the entire film')
    result=dict(master_sha256=original_sha,preview_sha256=sha(output),bytes=output.stat().st_size,
                duration=after['format']['duration'],full_decode=True,edition='complete 720p phone preview; same edit and original game audio')
    output.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();make(a.source,a.output)
