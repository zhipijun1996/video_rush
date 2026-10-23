"""Bounded caption timing from actual synthesis metadata or one short utterance."""
from .render import subtitle_cues


def narration_cues(text, boundaries, start, spoken, speed, mode='sentence'):
    if mode == 'utterance':
        if len(text) > 26:
            raise ValueError('Utterance caption must be one short readable phrase')
        return ([{'start': round(start, 3), 'end': round(start + spoken, 3),
                  'text': text}], 'single utterance; complete decoded narration window')
    if mode != 'sentence':
        raise ValueError('Unknown subtitle mode')
    sentences = sorted((b for b in boundaries if b['type'] == 'SentenceBoundary'),
                       key=lambda b: b['offset'])
    if not sentences:
        return (list(subtitle_cues(text, start, spoken)),
                'duration-proportional estimate; phone timing review required')
    cues = []
    for i, sentence in enumerate(sentences):
        st = sentence['offset'] / 1e7 / speed
        end = min(spoken, st + sentence['duration'] / 1e7 / speed)
        if i + 1 < len(sentences):
            # Edge can report overlapping sentence durations. ASS would show
            # both captions at once and move one away from the expected line.
            end = min(end, sentences[i + 1]['offset'] / 1e7 / speed)
        if end <= st:
            raise ValueError('Invalid overlapping or out-of-bounds sentence metadata')
        cues.extend(subtitle_cues(sentence['text'], start + st, end - st))
    return (cues, 'Edge sentence boundaries; overlap clipped at next sentence; '
            'phrase subdivisions proportional within sentence')
