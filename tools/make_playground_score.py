"""Original instrumental battle score: no samples, anime recordings, or lyrics.

Authoring helper requires numpy. Producer only needs the resulting pinned Opus.
"""
from pathlib import Path
import wave,json,hashlib
import numpy as np

def compose(path,seconds=256,sr=24000):
    rng=np.random.default_rng(20261030);beat=60/168
    track=np.zeros(int(seconds*sr),dtype=np.float64)
    def note(start,length,freq,gain,kind='lead'):
        i=int(start*sr);n=min(int(length*sr),len(track)-i)
        if n<=0:return
        t=np.arange(n)/sr;attack=np.minimum(t/.008,1)
        if kind=='kick':
            phase=2*np.pi*(46*t+62*.025*(1-np.exp(-t/.025)));v=np.sin(phase)*np.exp(-t*15)
        elif kind=='snare':v=(rng.normal(0,.55,n)+.3*np.sin(2*np.pi*180*t))*np.exp(-t*19)
        elif kind=='hat':v=rng.normal(0,.33,n)*np.exp(-t*80)
        elif kind=='guitar':
            v=np.tanh(2.2*(np.sin(2*np.pi*freq*t)+.55*np.sin(2*np.pi*freq*1.5*t)+.3*np.sin(2*np.pi*freq*2*t)))*np.exp(-t*5)
        elif kind=='pad':v=(np.sin(2*np.pi*freq*t)+.33*np.sin(2*np.pi*freq*2*t))*.65
        else:v=(np.sin(2*np.pi*freq*t)+.3*np.sin(2*np.pi*freq*2*t)+.15*np.sin(2*np.pi*freq*3*t))*np.exp(-t*2)
        env=attack*np.minimum(np.maximum((length-t)/.035,0),1)
        track[i:i+n]+=gain*v*env
    hz=lambda m:440*2**((m-69)/12)
    roots=[40,40,36,38,40,43,36,38]
    lead=[76,79,83,81,79,76,74,71,72,76,79,78,76,74,71,74]
    for b in range(int(seconds/beat)):
        bar=b//4;root=roots[bar%8];a=b*beat
        # Guitar palm-mute eighths, minor anthem motif, half-time break every16 bars.
        quiet=bar%16 in [7,15]
        for sub in range(2):note(a+sub*beat/2,beat*.43,hz(root),.12,'guitar')
        if b%4 in [0,2]:note(a,.23,0,.22,'kick')
        if b%4 in [1,3] and not quiet:note(a,.16,0,.13,'snare')
        for sub in range(2):note(a+sub*beat/2,.07,0,.055,'hat')
        if bar%8>=2 and not quiet:note(a,beat*.8,hz(lead[(b//2)%16]),.075,'lead')
        if b%4==0:
            for interval in [12,15,19]:note(a,beat*3.9,hz(root+interval),.027,'pad')
    # gentle mastering with headroom; final film ducks this below narration.
    track=np.tanh(track*1.4);track*=.73/max(.001,float(np.max(np.abs(track))))
    pcm=(track*32767).astype('<i2')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())
    path.with_suffix('.json').write_text(json.dumps({'title':'课间最终决战','composer':'Video Rush procedural original composition','bpm':168,'seed':20261030,'samples':'None: synthesized oscillators and seeded noise only','license':'Original Video Rush score, MIT; no third-party music or franchise recordings','sha256':hashlib.sha256(path.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))

if __name__=='__main__':compose('build/music/playground-battle-original.wav')
