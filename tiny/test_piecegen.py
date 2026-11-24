import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from piecegen import parts_of, header, bpm_of

T = '''setcps(124/60/4)
stack(
  s("<[bd ~ bd ~]!3 [bd bd bd ~]>, <~ sd>").bank("RolandTR909"),  // drums
  note("<[f2 ~ f2 ab2] [~ f2 ~ eb2]>").s("gm_synth_bass_1"),  // bass
  note("<[f3,ab3,c4]@4 [eb3,g3,bb3]@4>").s("gm_pad_warm"),  // chords
  note("<[c5 eb5").s("gm_lead_2_sawtooth"),  // lead
  note("~ ~").s("gm_piano"),  // part
  note("<c5 eb5 f5 ab5>").gain(0.5).s("gm_lead_2_sawtooth")  // lead
)
\x1e
  note("c4 d4").s("gm_piano")  // bass
'''

def test_parts():
    p = parts_of(T)
    assert [x['role'] for x in p] == ['drums', 'bass', 'chords', 'lead'], p
    assert p[0] == {'role': 'drums', 'kind': 's', 'mini': '<[bd ~ bd ~]!3 [bd bd bd ~]>, <~ sd>', 'sound': 'RolandTR909'}
    assert p[1]['mini'] == '<[f2 ~ f2 ab2] [~ f2 ~ eb2]>' and p[1]['sound'] == 'gm_synth_bass_1' and p[1]['kind'] == 'note'
    assert p[3]['mini'] == '<c5 eb5 f5 ab5>' and p[3]['sound'] == 'gm_lead_2_sawtooth'

def test_header_bpm():
    assert header('f#', 'minor', 'prog') == '// key: f# minor | style: prog | bars: 4 | parts: 4\n'
    assert header('c', 'major', 'house', 8, 3) == '// key: c major | style: house | bars: 8 | parts: 3\n'
    assert bpm_of(T) == 124.0 and bpm_of('stack(\n)') is None

if __name__ == '__main__':
    test_parts(); test_header_bpm(); print('ok')
