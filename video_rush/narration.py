from __future__ import annotations
import asyncio
import os
from pathlib import Path
import subprocess
from .common import duration, run, write, digest, sha


async def _edge(text, path, voice, rate):
    import edge_tts
    # aiohttp does not automatically inherit HTTPS_PROXY for WebSockets.
    tts = edge_tts.Communicate(text, voice, rate=rate, proxy=os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'),
                               connect_timeout=20, receive_timeout=45)
    await asyncio.wait_for(tts.save(str(path), str(path.with_suffix(".boundaries.jsonl"))), timeout=90)


def audio_metrics(path):
    import array
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', '16000',
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    samples = array.array('h', raw)
    if not samples:
        raise ValueError('Empty decoded audio')
    peak = max(abs(s) for s in samples) / 32768
    rms = (sum((s / 32768) ** 2 for s in samples) / len(samples)) ** .5
    clipped = sum(abs(s) >= 32760 for s in samples) / len(samples)
    return {'decoded_samples': len(samples), 'peak': peak, 'rms': rms, 'clipped_fraction': clipped,
            'audible_signal': peak > .01 and rms > .001,
            'speech_identity': 'TTS backend receipt; not independently verified by ASR/human'}


def narrate(text, out, backend='edge', voice='zh-CN-XiaoxiaoNeural', rate='-5%', model=None):
    out = Path(out)
    key = digest({'text': text, 'backend': backend, 'voice': voice, 'rate': rate, 'model': model})
    receipt = out.with_suffix('.json')
    if out.exists() and receipt.exists():
        import json
        old = json.loads(receipt.read_text())
        if old.get('input_hash') == key and old.get('sha256') == sha(out):
            return old
    tmp = out.with_suffix('.raw.mp3' if backend == 'edge' else '.raw.wav')
    attempts = []
    try:
        if backend == 'edge':
            asyncio.run(_edge(text, tmp, voice, rate))
        elif backend == 'piper':
            if not model or not Path(model).exists():
                raise ValueError('Piper requires --piper-model with licensed ONNX + .json; see README')
            p = subprocess.run(['piper', '--model', model, '--output_file', str(tmp)], input=text,
                               text=True, capture_output=True, timeout=120)
            if p.returncode:
                raise RuntimeError(p.stderr)
        else:
            raise ValueError(f'Unknown TTS backend {backend}')
        metrics = audio_metrics(tmp)
        if not metrics['audible_signal']:
            raise ValueError('TTS produced silence; refusing delivery')
        run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9',
             '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', out])
        data = {'input_hash': key, 'sha256': sha(out), 'backend': backend, 'voice': voice,
                'text': text, 'duration': duration(out), 'metrics': audio_metrics(out)}
        write(receipt, data)
        return data
    except Exception as e:
        write(out.with_suffix('.failure.json'), {'backend': backend, 'error': str(e), 'text': text})
        raise
    finally:
        tmp.unlink(missing_ok=True)
