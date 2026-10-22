from __future__ import annotations
import re
from pathlib import Path
from fractions import Fraction
from .common import probe, run, sha, read, write
from .narration import audio_metrics
from .render import montage_spans


def content_check(spec, timeline, sources):
    ids={a['id'] for a in sources['assets']}
    evidence_ids={e['id'] for e in spec.get('evidence',[])}
    structural = {
        'explicit_topic': bool(spec['title']),
        'first_15_seconds_hook_authored': any(s['start']<15 and (s.get('emphasis') or s.get('punchline')) for s in timeline['shots']),
        'every_shot_references_media': all(s.get('assets') and set(s['assets']) <= ids for s in timeline['shots']),
        'every_segment_has_evidence': all(s.get('prs') or s.get('evidence') for s in spec['shots']),
        'evidence_references_resolve':all(set(s.get('evidence',[])) <= evidence_ids for s in spec['shots']),
        'interpretations_labeled': all(s.get('claim_type') for s in spec['shots']),
        'no_fabricated_human_acceptance': spec['editorial_status'].endswith('human_phone_review_pending')}
    # These are structural checks, never an automatic aesthetic or fact verdict.
    pending = ['前15秒是否值得继续观看；主题是否明确', '逐句口播是否与屏幕展示对应，尤其是概念/预览/正式实机标签',
               '检查AI配音是否错读、语气自然，字幕是否跟得上', '核对引用SHA/PR与具体结论，是否存在过度归因',
               spec.get('comparison_review','横向旧新对比是不同阶段，未声称同Seed同布局受控实验'), '重复、单调或停留太久的镜头是否应缩短',
               '技术通过是否被误读成品质通过；当前开发演示与未完成范围是否清楚', '完整观看后决定标题封面是否准确，手机字是否可读']
    return {'structural_checks': structural, 'structural_pass': all(structural.values()),
            'editorial_review': 'human_review_required', 'aesthetic_acceptance': 'unverified',
            'independent_fact_review': 'unverified', 'phone_checklist': pending}


def detect_intervals(log, prefix):
    if prefix=='black':
        return [{'start':float(a),'end':float(b),'duration':float(c)} for a,b,c in re.findall(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)',log)]
    starts=re.findall(r'freeze_start: ([\d.]+)',log); ends=re.findall(r'freeze_end: ([\d.]+)',log)
    return [{'start':float(a),'end':float(b),'duration':float(b)-float(a)} for a,b in zip(starts,ends)]


def classify_freezes(frozen, timeline, media):
    """Review the actual visual cuts, including brief stings within one voice shot."""
    segments=[]
    for shot in timeline['shots']:
        if shot.get('presentation')=='montage':
            segments.extend({'start':shot['start']+cut['start'],
                             'end':shot['start']+cut['end'],'assets':[cut['asset']]}
                            for cut in montage_spans(shot))
        else:
            segments.append(shot)
    unexpected=[];planned=[]
    for freeze in frozen:
        # FFmpeg reports the first changed frame as freeze_end. A single boundary
        # frame is not evidence that a neighbouring movie stayed frozen.
        overlaps=[s for s in segments if min(freeze['end'],s['end'])-
                  max(freeze['start'],s['start']) > 1/30+.002]
        static=overlaps and all(all(
            media[x]['kind'] not in ('original_game_recording','historical_reconstruction')
            and Path(media[x].get('local_path','')).suffix.lower() not in ('.mp4','.webm','.avi')
            for x in s['assets']) for s in overlaps)
        (planned if static else unexpected).append(freeze)
    return unexpected,planned



def narration_receipts_valid(output,spec):
    shots=spec.get('shots',[])
    if not shots:return False
    for shot in shots:
        audio=Path(output)/'narration'/(shot['id']+'.wav')
        receipt=audio.with_suffix('.json')
        if not audio.exists() or not receipt.exists():return False
        r=read(receipt)
        if r.get('backend') not in {'edge','piper'} or r.get('text')!=shot['narration'] or r.get('sha256')!=sha(audio) or not r.get('metrics',{}).get('audible_signal'):return False
    return True


def validate(output, spec, timeline, sources):
    output=Path(output);final=output/'final.mp4';logs=output/'logs';logs.mkdir(exist_ok=True)
    meta=probe(final);v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
    dur=float(meta['format']['duration'])
    run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-'],log=logs/'decode.log',timeout=600)
    # run() captures successful stderr but returns stdout; detections are logged to file.
    run(['ffmpeg','-hide_banner','-i',final,'-vf','blackdetect=d=1:pix_th=0.08:pic_th=0.98,freezedetect=n=-50dB:d=5','-an','-f','null','-'],log=logs/'visual-detection.log',timeout=600)
    detections=(logs/'visual-detection.log').read_text()
    black=detect_intervals(detections,'black'); frozen=detect_intervals(detections,'freeze')
    media={x['id']:x for x in sources['assets']}
    unexpected,planned=classify_freezes(frozen,timeline,media)
    metrics=audio_metrics(final)
    bgm=None
    music=sources.get('audio',{}).get('music')
    if music:
        bgm={'path':music,'sha256':sha(music),'metrics':audio_metrics(music),'mix_evidence':str(logs/'final-render.log'),'gain':spec.get('music_gain',.16),'ducking':'voice-triggered; threshold .025, ratio 8, attack20ms/release250ms','fade_in':1,'fade_out':3,'provenance':spec.get('music_asset'),'listening':'not human-reviewed'}
    minimum,maximum=spec.get('target_duration',[180,300])
    if bgm:
        bgm['metrics'].pop('speech_identity',None)
        bgm['metrics']['signal_type']='user-provided background music; waveform presence check, not speech identity'
    checks={
      'exists_and_decodes':True,'1920x1080':(v['width'],v['height'])==(1920,1080),'30fps':Fraction(v['avg_frame_rate'])==30,
      'h264_yuv420p':v['codec_name']=='h264' and v['pix_fmt']=='yuv420p','aac_48k':a['codec_name']=='aac' and int(a['sample_rate'])==48000,
      'duration_matches_brief':minimum <= dur <= maximum,
      'subtitles_in_bounds':all(0 <= c['start'] < c['end'] <= dur+.02 for s in timeline['shots'] for c in s['cues']),
      'action_labels_in_bounds':all(0<=x['start']<x['end']<=s['end']-s['start']+.02 for s in timeline['shots'] for x in s.get('action_labels',[])),
      'source_labels_in_bounds':all(s['start']<=c['start']<c['end']<=s['end']+.02 for s in timeline['shots'] for c in s.get('source_cues',[])),
      'audible_tts_signal':metrics['audible_signal'] and narration_receipts_valid(output,spec),
      'no_obvious_clipping':metrics['clipped_fraction']<.0001,
      'requested_music_source_valid':not music or (bgm['metrics']['audible_signal'] and (not spec.get('music_asset') or bgm['sha256']==spec['music_asset']['sha256'])),
      'sources_present_and_hash_match':all(Path(s['local_path']).exists() and sha(s['local_path'])==s['sha256'] for s in sources['assets']),
      'no_long_black':not black,'no_unexpected_long_freeze':not unexpected}
    report={'status':'technical_pass_human_review_pending' if all(checks.values()) else 'technical_fail',
      'background_music':bgm,
      'technical':{'passed':all(checks.values()),'checks':checks,'ffprobe':meta,'audio':metrics,'black_intervals':black,
                   'unexpected_freeze_intervals':unexpected,'planned_still_intervals':planned,'decoded_entire_file':True,'requested_duration_range':[minimum,maximum]},
      'content':content_check(spec,timeline,sources),'final':{'path':str(final.resolve()),'sha256':sha(final),'bytes':final.stat().st_size},
      'speech_validation': 'Real Edge/Piper synthesis and decoded non-silent waveform checked; listening/ASR not performed. No silence placeholder.',
      'publication':'not_uploaded_to_bilibili'}
    write(output/'report.json',report)
    (output/'phone-review.md').write_text('# 手机审核清单\n\n技术检测：'+report['status']+'\n\n'+''.join('- [ ] '+x+'\n' for x in report['content']['phone_checklist'])+'\n自动检测不代表人类审美、逐句事实核验或设备体验通过。\n')
    return report
