# music21-mnx

Alpha-level MNX import and export for [music21](https://www.music21.org).

**MNX** is the [W3C Music Notation Community Group](https://www.w3.org/community/music-notation/)'s
in-development, JSON-based successor to MusicXML for encoding Common Western
Music Notation. MNX has **not yet reached a stable release**, so this
support lives in its own package instead of in music21 itself; pin a version of
`music21-mnx` to pin the MNX schema revision you target. (If MNX becomes a common format, as we hope,
this package may become bundled with `music21` as MusicXML, MIDI, etc. are).

> This package was written largely by an AI agent (Claude).
> Treat the code as AI-assisted pending more human review (See AI note below)

## Install

```bash
uv add music21-mnx        # or: pip install music21-mnx
```

## Usage

Importing the package has no side effects until you call `music21_mnx.register()`. The `'mnx'` format then works through
music21's normal API.

```python
import music21_mnx
music21_mnx.register()                    # activate (import alone does nothing)

from music21 import converter
score = converter.parse('song.mnx')       # or converter.parse(jsonText, format='mnx')
score.write('mnx', fp='out.mnx')

music21_mnx.unregister()                   # not needed, but can deactivate when done
```

Advanced users can also use the converter classes directly without calling register

```python
from music21_mnx import MNXImporter, MNXExporter

score = MNXImporter(json_string_or_dict).run()
mnx_dict = MNXExporter(score).export()    # plain dict
mnx_text = MNXExporter(score).toJson()
```

While registered, the converter claims both the `.mnx` and `.json` input
extensions, so plain `.json` files and the spec's future `.mnx.json`
double extensions are both parsed as MNX (music21 keys off the final extension).
Nothing else in music21 currently claims `.json`, so this is a convenience for
now; it can be narrowed as the format stabilizes. For a raw string (no file)
pass `format='mnx'` to converter.

## Versioning

This package's version tracks the MNX schema version it targets: **`0.27.x`**
follows **MNX schema version 27** (`music21_mnx.base.MNX_SCHEMA_VERSION`).
Documents produced by the exporter declare that schema version in their `mnx`
header. The bundled `music21_mnx/mnx-schema.json` is the official schema at that
revision; the test suite validates every exported document against it.

## How it works

Rather than mirror every MNX object with a class, the package works directly on
the plain `dict` objects from `json.loads`; `music21_mnx/base.py` provides
`TypedDict` shapes that document them. Both directions run in two passes:

- **Import** (`fromMnx.py`): pass 1 builds the `Score` and records every MNX
  `id` in a registry pointing at the music21 object it produced, queuing
  tie/slur/beam references; pass 2 connects the *actual* objects in the finished
  stream.
- **Export** (`toMnx.py`): pass 1 assigns ids to the notes/events that take part
  in a tie/slur/beam; pass 2 serializes and attaches those id references.

## Coverage and known limitations

Covered (round-trips through `music21 → MNX → music21` and validates against the
bundled schema): parts, measures, voices, notes/chords/rests, pitches and
accidental display, symbolic durations incl. dotted notes and tuplets, time/key
signatures, clefs, beams (incl. partial/hook), ties, slurs, grace notes, part
names, barlines, and dynamics.

Dynamics map onto MNX's dynamic groups as follows:

| MNX dynamic group | music21 |
| --- | --- |
| `immediate` (`p`, `ff`) | `dynamics.Dynamic` |
| `accent` (`sfz`, `fp`, `rfz`, `sfzp`) | `dynamics.Dynamic`, spelling rebuilt from `accentPrefix`/`value`/`accentSuffix`/`residualValue` |
| `gradual` (hairpins) | `dynamics.Crescendo` / `Diminuendo`, spanning the notes at the group's `position` and `end` |
| `relative` (`più p`) | *dropped* — no music21 equivalent |

Measure repeats (`measureRepeat`, new in schema 27) have no music21 object
either; the MNX dict rides along on `measure.editorial.mnxMeasureRepeat`, so it
survives a round trip without being rendered as anything.

Not yet round-tripped (recognized but dropped or approximated, marked `TODO` in
the source):

- **Exotic tie targets** — `crossVoice` / `crossJump` ties and ties to specific
  chord members. Export matches a tie to the next same-pitch note.
- **Dynamic-group extras** — `relative` groups, the free-text `prefix`/`suffix`,
  explicit SMuFL `glyphs`, `staff`/`staffEnd`/`voice` scoping, and
  `visuallyContinues`. `orient` survives only as `above`/`below`.
- multi-note tremolos (parsed as plain events), ottavas, jumps/segno and full
  repeat structure, layouts/pages/systems, percussion kits, `markings`
  (incl. arpeggios), and lyrics.

## Development

```bash
uv sync
uv run pytest music21_mnx     # unit tests + doctests + schema validation
uv run ruff check music21_mnx
uv run mypy music21_mnx
uv run pylint music21_mnx
```

The `examples/` directory holds the 52 example documents shipped with the MNX
spec, handy for experimentation:

```bash
uv run python -c "import music21_mnx; music21_mnx.register(); from music21 import converter; \
converter.parse('examples/slurs.json', format='mnx').show('text')"
```

## License

BSD 3-Clause, the same as music21. See `LICENSE`.

## Author and Copyright

Copyright © 2026, Michael Scott Asato Cuthbert

## AI Usage

Note from MSAC: at this point this code is heavily AI-Agent generated 
(almost to the level of vibe coding). As the spec gets further developed more human time will
be spent inside the code.  For now, use at your own risk. (I suppose, that's true for music21 and almost all free software too!)
