import subprocess

import pytest
from PIL import Image

from video_rush.render import ass_file, encode_shot


def test_montage_encodes_actual_cuts_at_frame_boundaries_and_changes_source_labels(tmp_path):
    assets = {}
    for name, color in [('concept', (255, 0, 0)), ('reaction', (0, 255, 0)), ('game', (0, 0, 255))]:
        path = tmp_path / (name + '.png')
        Image.new('RGB', (64, 36), color).save(path)
        assets[name] = {'local_path': str(path)}
    shot = {'start': 0, 'end': 1, 'assets': list(assets), 'presentation': 'montage',
            'montage_weights': [.2, .3, .5], 'cues': [], 'provenance_label': 'unused',
            'source_cues': [{'start': 0, 'end': .2, 'text': 'AI concept, not gameplay'},
                            {'start': .2, 'end': .5, 'text': 'Original editorial reaction'},
                            {'start': .5, 'end': 1, 'text': 'Game source'}]}
    movie = tmp_path / 'montage.mp4'
    encode_shot(shot, assets, movie, tmp_path/'encode.log')
    pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(movie), '-vf',
                                     'crop=2:2:960:540,scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    assert len(pixels) == 30 * 3
    for index in range(30):
        rgb = pixels[index*3:index*3+3]
        expected = 0 if index < 6 else 1 if index < 15 else 2
        assert rgb[expected] > 220
        assert all(value < 30 for channel, value in enumerate(rgb) if channel != expected)
    captions = tmp_path/'captions.ass'
    ass_file(captions, {'shots': [shot], 'display_chapters': False})
    text = captions.read_text()
    assert '0:00:00.20,0:00:00.50,Source' in text
    assert 'Original editorial reaction' in text
    assert 'unused' not in text


def test_montage_refuses_to_loop_short_game_source(tmp_path):
    image = tmp_path/'concept.png'
    Image.new('RGB', (64, 36), 'red').save(image)
    video = tmp_path/'game.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=blue:s=64x36:r=30:d=0.1',
                    '-c:v', 'libx264', str(video)], check=True)
    with pytest.raises(ValueError, match='insufficient footage'):
        encode_shot({'start': 0, 'end': 2, 'assets': ['concept', 'game'], 'presentation': 'montage'},
                    {'concept': {'local_path': str(image)}, 'game': {'local_path': str(video)}},
                    tmp_path/'out.mp4', tmp_path/'encode.log')


def test_planned_montage_still_is_not_confused_with_later_movie():
    from video_rush.quality import classify_freezes
    timeline={'shots':[{'start':0,'end':10,'presentation':'montage',
                        'assets':['still','game'],'montage_weights':[7,3]}]}
    media={'still':{'kind':'concept_art'},'game':{'kind':'original_game_recording'}}
    freeze={'start':0,'end':7+1/30,'duration':7+1/30}
    unexpected,planned=classify_freezes([freeze],timeline,media)
    assert not unexpected and planned==[freeze]


def test_montage_does_not_excuse_frozen_gameplay_after_still():
    from video_rush.quality import classify_freezes
    timeline={'shots':[{'start':0,'end':14,'presentation':'montage',
                        'assets':['still','game'],'montage_weights':[1,1]}]}
    media={'still':{'kind':'concept_art'},'game':{'kind':'original_game_recording'}}
    freeze={'start':0,'end':13,'duration':13}
    unexpected,planned=classify_freezes([freeze],timeline,media)
    assert unexpected==[freeze] and not planned
