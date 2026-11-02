"""One original five-note theme, orchestrated with the MIT FluidR3 sample bank.

Offline sample-based rendering through libfluidsynth; not a claim of a neural
music generator or a licensed commercial library recording.
"""
import ctypes as C
import ctypes.util
import math
from pathlib import Path
import struct
import wave
import numpy as np
from .common import sha,write

STYLES={'deadpan':80,'warm':112,'battle':164,'villain':96,'rock':176,'heroic':144,'reprise':112}
PROGRAMS={0:80,1:29,2:33,3:48,4:60,5:10,6:70,7:24,8:56,9:0,10:81,11:47}


class Synth:
    def __init__(self,soundfont,sr=24000):
        self.sr=sr;self.lib=C.CDLL(ctypes.util.find_library('fluidsynth') or 'libfluidsynth.so.3')
        def bind(n,restype,*args):
            f=getattr(self.lib,n);f.restype=restype;f.argtypes=list(args);return f
        self.settings=bind('new_fluid_settings',C.c_void_p)()
        bind('fluid_settings_setnum',C.c_int,C.c_void_p,C.c_char_p,C.c_double)(self.settings,b'synth.sample-rate',sr)
        self.synth=bind('new_fluid_synth',C.c_void_p,C.c_void_p)(self.settings)
        sf=bind('fluid_synth_sfload',C.c_int,C.c_void_p,C.c_char_p,C.c_int)(self.synth,str(soundfont).encode(),1)
        if sf<0:raise RuntimeError('SoundFont failed to load')
        select=bind('fluid_synth_program_select',C.c_int,C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int)
        for ch,program in PROGRAMS.items():
            if select(self.synth,ch,sf,128 if ch==9 else 0,program)!=0:raise RuntimeError('Missing MIDI program')
        self.noteon=bind('fluid_synth_noteon',C.c_int,C.c_void_p,C.c_int,C.c_int,C.c_int)
        self.noteoff=bind('fluid_synth_noteoff',C.c_int,C.c_void_p,C.c_int,C.c_int)
        self.render=bind('fluid_synth_write_float',C.c_int,C.c_void_p,C.c_int,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_int,C.c_int)
        self.delete=bind('delete_fluid_synth',None,C.c_void_p);self.delete_settings=bind('delete_fluid_settings',None,C.c_void_p)

    def perform(self,events,seconds):
        total=round(seconds*self.sr);result=np.zeros((total,2),np.float32);at=0
        for t,kind,ch,key,velocity in sorted(events,key=lambda e:(e[0],e[1]))+[(seconds,0,0,0,0)]:
            end=min(total,max(at,round(t*self.sr)));n=end-at
            if n:
                ptr=result.ctypes.data+at*8;self.render(self.synth,n,ptr,0,2,ptr,1,2);at=end
            if kind==1:self.noteon(self.synth,ch,key,velocity)
            elif kind==-1:self.noteoff(self.synth,ch,key)
        self.delete(self.synth);self.delete_settings(self.settings)
        return result


def arrange(style,seconds,peak_at=None):
    if style not in STYLES:raise ValueError(style)
    bpm=STYLES[style];beat=60/bpm;rng=np.random.default_rng(20261102);events=[]
    def note(t,length,ch,key,velocity=85):
        if t<0 or t>=seconds:return
        velocity=int(np.clip(velocity+rng.integers(-4,5),1,123))
        events.extend([(t,1,ch,key,velocity),(min(seconds,t+length),-1,ch,key,0)])
    major=style in ('warm','heroic','reprise');motif=[76,80 if major else 79,81,83,88]
    if style=='villain':motif=[76,79,81,82,88]
    roots=[40,36 if not major else 37,45,47]
    for bar in range(math.ceil(seconds/(4*beat))):
        t=bar*4*beat;root=roots[bar%4];hot=peak_at is None or t>=peak_at
        if style=='deadpan':
            note(t,.35,2,40,55)
            if bar%2:note(t+2*beat,.18,5,64,52)
            continue
        if style=='villain':
            note(t,3.4*beat,6,40,65);note(t+.12,3.3*beat,3,46,40)
            for j,key in enumerate(motif):note(t+j*.6*beat,.44*beat,6,key-12,55+j*4)
            continue
        if style in ('warm','reprise'):
            chord=[root+12,root+16,root+19]
            for j,key in enumerate(chord*2):note(t+j*.5*beat,.48*beat,7,key,62)
            for j,key in enumerate(motif):note(t+[0,.5,1,2,2.5][j]*beat,.55*beat,5,key-12,64)
            note(t,2.8*beat,2,root,55)
            if style=='reprise':note(t+beat,.10,9,37,35);note(t+3*beat,.10,9,37,35)
            continue
        # One groove continues through reversals; the two major attacks change
        # orchestration and density instead of introducing unrelated songs.
        for b in range(8):
            a=t+b*.5*beat
            note(a,.33*beat,2,root+(12 if b%4==3 else 0),80 if hot else 57)
            if style in ('battle','rock'):
                for interval in [12,19]:note(a,.20*beat,1,root+interval,78 if hot else 44)
            if hot:note(a,.06,9,42,51 if b%2 else 66)
        if hot:
            for b in [0,2,2.75]:note(t+b*beat,.12,9,36,106)
            for b in [1,3]:note(t+b*beat,.13,9,38,102)
            if bar%4==0:note(t,.6,9,49,103)
        else:
            for j in range(8):note(t+j*.5*beat,.08,9,38,38+j*4)
        melody_channel=4 if style=='heroic' else 0 if style=='battle' else 10
        if hot:
            for j,key in enumerate(motif):
                a=t+[0,.5,1,2,2.5][j]*beat
                note(a,.50*beat,melody_channel,key,92)
                if style=='heroic':note(a,.60*beat,8,key-12,82)
            for key in [root+12,root+(16 if major else 15),root+19]:note(t,3.7*beat,3,key,69 if style=='heroic' else 38)
    if peak_at is not None:
        if style=='heroic':
            entry=max(0,peak_at-2.0)
            for key in [52,56,59,64]:note(entry,2.4,3,key,78)
            note(entry,.65,4,64,92);note(entry+.55,.7,4,71,96)
            for j in range(6):note(max(entry,peak_at-.75)+j*.12,.18,11,40+(j%2)*7,66+j*7)
        # Exact impact point, independent of where it falls on the old grid.
        for ch,key,vel in [(9,49,120),(9,36,120),(11,40,110)]:note(peak_at,.8,ch,key,vel)
        for key in [52,59,64]:note(peak_at,1.8,4 if style=='heroic' else 1,key,112)
        for j,key in enumerate(motif):note(peak_at+j*.5*beat,.58*beat,4 if style=='heroic' else 10,key,108)
    return events,bpm


def midi_file(path,events,bpm):
    def vlq(n):
        out=[n&127];n>>=7
        while n:out.insert(0,(n&127)|128);n>>=7
        return bytes(out)
    tempo=round(60_000_000/bpm);data=b'\x00\xff\x51\x03'+tempo.to_bytes(3,'big')
    for ch,program in PROGRAMS.items():data+=b'\x00'+bytes([0xc0+ch,program])
    previous=0
    for t,kind,ch,key,velocity in sorted(events,key=lambda e:(e[0],e[1])):
        tick=round(t*480*bpm/60);data+=vlq(tick-previous)+bytes([(0x90 if kind==1 else 0x80)+ch,key,velocity]);previous=tick
    data+=b'\x00\xff\x2f\x00';Path(path).write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(data))+data)


def compose(path,soundfont,style,seconds,peak_at=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);events,bpm=arrange(style,seconds,peak_at)
    audio=Synth(soundfont).perform(events,seconds)
    peak=np.max(np.abs(audio));audio*=.75/max(.001,peak)
    n=min(round(.08*24000),len(audio));audio[:n]*=np.linspace(0,1,n)[:,None]
    n=min(round(.22*24000),len(audio));audio[-n:]*=np.linspace(1,0,n)[:,None]
    with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000);w.writeframes((audio*32767).astype('<i2').tobytes())
    midi_file(path.with_suffix('.mid'),events,bpm)
    write(path.with_suffix('.json'),{'style':style,'bpm':bpm,'seconds':seconds,'peak_at':peak_at,'motif':'E G A B E (major reprise raises G)','source':'Original Video Rush arrangement, rendered with FluidR3 GM MIT sample bank','soundfont_sha256':sha(soundfont),'sha256':sha(path),'events':len(events)})
    return path
