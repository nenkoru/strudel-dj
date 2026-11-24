# Loop dialect

One Strudel expression describing a 4-bar loop. One cycle = one 4/4 bar; the tempo is set by
the player, not by the code. `js/dialect.mjs` parses it strictly and never evaluates it as
JavaScript.

```js
stack(
  s("<bd*2 [bd ~@3 bd bd ~@2]>, [~ sd ~ sd], hh*8").bank("RolandTR909"),
  note("<[a1@5 ~ a1 ~ e2@4 a1 ~ c#2 ~] [d2@5 ~ d2 ~ a1@5 ~ a1 ~]>").s("gm_electric_bass_finger"),
  note("<[e4,a4,c#5] [d4,f#4,a4]>").s("gm_epiano2"),
  note("<[c#5 a4 c#5 ~] [d5 a4 d5 ~]>").s("gm_marimba")
)
```

- **Lanes**, in this order when present: drums, bass, chords, lead. `stack(...)` of 1–8 lanes.
- **Drums**: `s("...").bank("RolandTR909")`. Names: `bd sd rim cp hh oh lt mt ht cr rd`.
  Each drum voice is its own sequence, voices joined by `, ` inside the one string.
- **Pitched lanes**: `note("...").s("gm_<instrument>")`, one of the 125 Strudel GM sounds
  (`gm_programs.json`). Notes are `c4`-style names, `c4` = MIDI 60, sharps `c#`/`f#`, flats `eb`/`ab`/`bb`.
  Chords are `[c4,e4,g4]`.
- **Time**: `<b1 b2 b3 b4>` gives one entry per bar (`<b1 b2>` if bars alternate, a bare `b1` if
  all four are the same). Inside a bar, `[...]` divides it evenly; `x@3` lasts three slots, `~`
  is a rest, `x*8` repeats. The finest grid is 16ths.
- Allowed methods: `s bank gain velocity lpf hpf lpq room size delay delaytime delayfeedback
  attack decay sustain release pan legato speed crush shape transpose n octave`.

The dataset (`convert.py`) writes exactly this form from MIDI: quantized to 16ths, one part per
role, pitched lanes made monophonic per onset (simultaneous notes become a chord).
