import asyncio
import math
import wave
import array
import pytest
from video_rush import narration
from video_rush.common import read


def test_shot_style_keeps_voice_and_overrides_delivery():
    spec={'voice':'zh-CN-YunjianNeural','rate':'+8%'}
    assert narration.speech_options(spec,{'rate':'+0%','pitch':'-3Hz'})=={
        'voice':'zh-CN-YunjianNeural','rate':'+0%','pitch':'-3Hz'}
    with pytest.raises(ValueError):narration.speech_options(spec,{'pitch':'very excited'})


def test_pitch_reaches_backend_and_invalidates_audio_cache(tmp_path,monkeypatch):
    calls=[]
    async def fake_edge(text,path,voice,rate,pitch='+0Hz'):
        calls.append((voice,rate,pitch))
        samples=array.array('h',(int(4000*math.sin(i*.08)) for i in range(16000)))
        with wave.open(str(path),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(samples.tobytes())
    monkeypatch.setattr(narration,'_edge',fake_edge)
    p=tmp_path/'test.wav'
    narration.narrate('Unit-test synthetic tone, never delivery voice.',p,voice='test',rate='+8%',pitch='+2Hz')
    first=read(p.with_suffix('.json'))
    narration.narrate('Unit-test synthetic tone, never delivery voice.',p,voice='test',rate='+8%',pitch='+2Hz')
    assert len(calls)==1
    narration.narrate('Unit-test synthetic tone, never delivery voice.',p,voice='test',rate='+8%',pitch='-2Hz')
    last=read(p.with_suffix('.json'))
    assert calls==[('test','+8%','+2Hz'),('test','+8%','-2Hz')]
    assert first['input_hash']!=last['input_hash'] and last['pitch']=='-2Hz'
