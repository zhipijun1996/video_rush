from __future__ import annotations
import re
from pathlib import Path
from fractions import Fraction
from .common import probe, run, sha, read, write
from .narration import audio_metrics


def content_check(spec, timeline, sources):
    ids={a['id'] for a in sources['assets']}
    structural = {
        'explicit_topic': bool(spec['title']),
        'first_15_seconds_hook_authored': bool(spec['shots'][0].get('emphasis')),
        'every_shot_references_media': all(s.get('assets') and set(s['assets']) <= ids for s in timeline['shots']),
        'every_segment_has_pr_evidence': all(s.get('prs') for s in spec['shots']),
        'interpretations_labeled': all(s.get('claim_type') for s in spec['shots']),
        'no_fabricated_human_acceptance': spec['editorial_status'].endswith('human_phone_review_pending')}
    # These are structural checks, never an automatic aesthetic or fact verdict.
    pending = ['前15秒是否值得继续观看；主题是否明确', '逐句口播是否与屏幕展示对应，尤其是概念/预览/正式实机标签',
               '检查AI配音是否错读、语气自然，字幕是否跟得上', '核对引用SHA/PR与具体结论，是否存在过度归因',
               '横向旧新对比是不同阶段，未声称同Seed同布局受控实验', '重复、单调或停留太久的镜头是否应缩短',
               '技术通过是否被误读成品质通过；森林草稿是否清楚', '完整观看后决定标题封面是否准确，手机字是否可读']
    return {'structural_checks': structural, 'structural_pass': all(structural.values()),
            'editorial_review': 'human_review_required', 'aesthetic_acceptance': 'unverified',
            'independent_fact_review': 'unverified', 'phone_checklist': pending}


def detect_intervals(log, prefix):
    if prefix=='black':
        return [{'start':float(a),'end':float(b),'duration':float(c)} for a,b,c in re.findall(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)',log)]
    starts=re.findall(r'freeze_start: ([\d.]+)',log); ends=re.findall(r'freeze_end: ([\d.]+)',log)
    return [{'start':float(a),'end':float(b),'duration':float(b)-float(a)} for a,b in zip(starts,ends)]


def validate(output, spec, timeline, sources):
    output=Path(output);final=output/'final.mp4';logs=output/'logs';logs.mkdir(exist_ok=True)
    meta=probe(final);v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
    dur=float(meta['format']['duration'])
    run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-'],log=logs/'decode.log',timeout=600)
    # run() captures successful stderr but returns stdout; detections are logged to file.
    run(['ffmpeg','-hide_banner','-i',final,'-vf','blackdetect=d=1:pix_th=0.08:pic_th=0.98,freezedetect=n=-50dB:d=5','-an','-f','null','-'],log=logs/'visual-detection.log',timeout=600)
    detections=(logs/'visual-detection.log').read_text()
    black=detect_intervals(detections,'black'); frozen=detect_intervals(detections,'freeze')
    unexpected=[];planned=[]
    media={x['id']:x for x in sources['assets']}
    for f in frozen:
        overlaps=[s for s in timeline['shots'] if min(f['end'],s['end']) > max(f['start'],s['start'])]
        static=overlaps and all(all(media[x]['kind'] not in ('original_game_recording','historical_reconstruction') for x in s['assets']) for s in overlaps)
        (planned if static else unexpected).append(f)
    metrics=audio_metrics(final)
    checks={
      'exists_and_decodes':True,'1920x1080':(v['width'],v['height'])==(1920,1080),'30fps':Fraction(v['avg_frame_rate'])==30,
      'h264_yuv420p':v['codec_name']=='h264' and v['pix_fmt']=='yuv420p','aac_48k':a['codec_name']=='aac' and int(a['sample_rate'])==48000,
      'duration_3_to_5_minutes':180 <= dur <= 300,
      'subtitles_in_bounds':all(0 <= c['start'] < c['end'] <= dur+.02 for s in timeline['shots'] for c in s['cues']),
      'audible_tts_signal':metrics['audible_signal'] and all(read(p)['metrics']['audible_signal'] for p in (output/'narration').glob('s*.json') if not p.name.endswith('.failure.json')),
      'no_obvious_clipping':metrics['clipped_fraction']<.0001,
      'sources_present_and_hash_match':all(Path(s['local_path']).exists() and sha(s['local_path'])==s['sha256'] for s in sources['assets']),
      'no_long_black':not black,'no_unexpected_long_freeze':not unexpected}
    report={'status':'technical_pass_human_review_pending' if all(checks.values()) else 'technical_fail',
      'technical':{'passed':all(checks.values()),'checks':checks,'ffprobe':meta,'audio':metrics,'black_intervals':black,
                   'unexpected_freeze_intervals':unexpected,'planned_still_intervals':planned,'decoded_entire_file':True},
      'content':content_check(spec,timeline,sources),'final':{'path':str(final.resolve()),'sha256':sha(final),'bytes':final.stat().st_size},
      'speech_validation': 'Real Edge/Piper synthesis and decoded non-silent waveform checked; listening/ASR not performed. No silence placeholder.',
      'publication':'not_uploaded_to_bilibili'}
    write(output/'report.json',report)
    (output/'phone-review.md').write_text('# 手机审核清单\n\n技术检测：'+report['status']+'\n\n'+''.join('- [ ] '+x+'\n' for x in report['content']['phone_checklist'])+'\n自动检测不代表人类审美、逐句事实核验或设备体验通过。\n')
    return report
