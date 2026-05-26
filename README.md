# music21-mnx

MNX import and export for [music21](https://www.music21.org).

**MNX** is the [W3C Music Notation Community Group](https://www.w3.org/community/music-notation/)'s
in-development, JSON-based successor to MusicXML for encoding Common Western
Music Notation. Because MNX has **not yet reached a stable release**, this
support lives in its own package instead of in music21 itself; pin a version of
`music21-mnx` to pin the MNX schema revision you target.

> This package was written almost entirely by an AI agent (Claude Opus) under
> the maintainer's direction. Treat the code as AI-assisted pending human
> review.

## Install

```bash
uv add music21-mnx        # or: pip install music21-mnx
```

## Usage

Importing the package registers a music21 SubConverter as a side effect, so the
`'mnx'` format then works through music21's normal API:

```python
import music21_mnx                       # registers the converter
from music21 import converter

score = converter.parse('song.mnx')      # or converter.parse(jsonText, format='mnx')
score.write('mnx', fp='out.mnx')
```

You can also use the converter classes directly:

```python
from music21_mnx import MNXImporter, MNXExporter

score = MNXImporter(json_string_or_dict).run()
mnx_dict = MNXExporter(score).export()    # plain dict
mnx_text = MNXExporter(score).toJson()
```

MNX documents conventionally use the double extension `.mnx.json`. music21 keys
format detection off the last extension, so use a `.mnx` extension or pass
`format='mnx'` explicitly for `.mnx.json` files.

## Versioning

This package's version tracks the MNX schema version it targets: **`0.17.x`**
follows **MNX schema version 17** (`music21_mnx.base.MNX_SCHEMA_VERSION`).
Documents produced by the exporter declare that schema version in their `mnx`
header. The bundled `music21_mnx/mnx-schema.json` is the official schema at that
revision; the test suite validates every exported document against it.

## How it works

Rather than mirror every MNX object with a class, the package works directly on
the plain `dict` objects from `json.loads`; `music21_mnx/base.py` provides
`TypedDict` shapes that document them. Both directions run in **two passes**:

- **Import** (`fromMnx.py`): pass 1 builds the `Score` and records every MNX
  `id` in a registry pointing at the music21 object it produced, queuing
  tie/slur/beam references; pass 2 connects the *actual* objects in the finished
  stream.
- **Export** (`toMnx.py`): pass 1 assigns ids to the notes/events that take part
  in a tie/slur/beam; pass 2 serializes and attaches those id references.

## About the MNX format

An MNX document is a JSON object with three required keys — `mnx`, `global`, and
`parts` — plus optional `scores` and `layouts`:

```
root
├── mnx          {"version": 17, "support": {...}}       (required)
├── global                                               (required)
│   └── measures: [ measure-global, ... ]   # one per measure, shared by all parts
│       └── { time, key, barline, tempos, ending, repeat*, number, ... }
├── parts        [ part, ... ]                            (required)
│   └── part: { name, shortName, staves, measures: [ part-measure, ... ] }
│       └── part-measure: { clefs, beams, sequences, dynamics, ... }
│           └── sequences: [ sequence, ... ]    # each sequence = one voice
│               └── content: [ event | grace | tuplet | space | tremolo, ... ]
│                   └── event: { duration, notes | rest, id, slurs, markings, ... }
│                       ├── duration: { base, dots }          # symbolic note value
│                       └── notes: [ { pitch:{step,octave,alter}, id, ties } ]
├── scores       [ { name, layout, pages, ... } ]         (optional)
└── layouts      [ system-layout, ... ]                   (optional)
```

Key points: `global.measures` runs parallel to each part's `measures` by index,
and attributes persist until changed (so most measures after a change are `{}`).
An event is pitched (`notes`: one note, or several = a chord) or a `rest`.
Durations are symbolic (`base` + `dots`). Cross-references use string `id`s: a
note's `ties` target a note id, an event's `slurs` target an event id, and a
part-measure's `beams` group event ids (with nested `beams` for secondary and
partial/hook beams).

The format is under active development — see https://w3c-cg.github.io/mnx/ and
https://github.com/w3c/mnx. To re-sync to a newer schema, diff the upstream
`docs/mnx-schema.json` against `music21_mnx/mnx-schema.json` and bump this
package's minor version to match.

## Coverage and known limitations

Covered (round-trips through `music21 → MNX → music21` and validates against the
bundled schema): parts, measures, voices, notes/chords/rests, pitches and
accidental display, symbolic durations incl. dotted notes and tuplets, time/key
signatures, clefs, beams (incl. partial/hook), ties, slurs, grace notes, part
names, and barlines.

Not yet round-tripped (recognized but dropped or approximated, marked `TODO` in
the source):

- **Exotic tie targets** — `crossVoice` / `crossJump` ties and ties to specific
  chord members. Export matches a tie to the next same-pitch note.
- multi-note tremolos (parsed as plain events), ottavas, jumps/segno and full
  repeat structure, layouts/pages/systems, percussion kits, most dynamics and
  `markings`, and lyrics.

## Development

```bash
uv sync
uv run pytest music21_mnx     # unit tests + doctests + schema validation
uv run ruff check music21_mnx
uv run mypy music21_mnx
uv run pylint music21_mnx
```

The `examples/` directory holds the 49 example documents shipped with the MNX
spec, handy for experimentation:

```bash
uv run python -c "import music21_mnx; from music21 import converter; \
converter.parse('examples/slurs.json', format='mnx').show('text')"
```

## License

BSD 3-Clause, the same as music21. See `LICENSE`.
