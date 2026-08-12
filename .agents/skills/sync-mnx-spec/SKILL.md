---
name: sync-mnx-spec
description: >-
  How to bring this package up to date with a newer revision of the MNX spec —
  where the upstream schema, example documents, and prose docs live in the
  w3c-cg/mnx repo, what to diff, and everything that has to move together
  (bundled schema, base.py TypedDicts, examples/, version, README coverage list).
  Use whenever the task is "update to the latest MNX", "what changed in MNX
  since X", or any edit to music21_mnx/mnx-schema.json or examples/.
---

# Syncing with the MNX spec

## Where upstream lives

The spec repo is `https://github.com/w3c-cg/mnx`, cloned locally as a sibling of
this repo at `../mnx`. It is a read-only reference clone — fetch it, but do not
commit to it. If it is not there, clone it.

| What | Path in `../mnx` | Path here |
| --- | --- | --- |
| JSON schema | `docs/mnx-schema.json` | `music21_mnx/mnx-schema.json` |
| Example documents | `doctools/media/examples/json/*.json` | `examples/*.json` |
| Prose docs (element semantics) | `docs/*.md` | — |
| Implementation-status table | `doctools/data.json`, `notationref.json` | — |

The schema's `$id` ends in `/version/NN` — that integer is the schema revision and
this package's middle version digit.

## The sync

```bash
cd ../mnx
git fetch origin
git log --oneline --date=short --format='%h %ad %s' HEAD..origin/HEAD
```

Read the commit subjects first: the spec repo has genuinely descriptive ones
("Added support for dynamic groups", "Added measure repeats"), so they tell you
which features moved before you read a line of JSON. Then diff the schema:

```bash
git show origin/HEAD:docs/mnx-schema.json > /tmp/mnx-schema-new.json
diff -u music21_mnx/mnx-schema.json /tmp/mnx-schema-new.json
```

The schema is generated and its `$defs` are alphabetized, so the diff is readable:
renamed definitions show as a paired delete/add, and a changed feature usually
shows up as new `$defs` plus a changed `$ref` in the object that uses it.

Also diff the examples — upstream renames and adds them, and new example files are
the clearest statement of how a new feature is meant to be encoded:

```bash
diff -rq examples/ ../mnx/doctools/media/examples/json/
```

Prose docs in `../mnx/docs/` are the authority on semantics the schema cannot
express (which fields are mutually exclusive, what a value *means*). Read the doc
page for any feature you are implementing; do not infer semantics from the schema
alone.

## What has to move together

1. **`music21_mnx/mnx-schema.json`** — copy the new file in verbatim. Do not
   hand-edit it; it is generated upstream and the test suite validates against it.
2. **`examples/*.json`** — copy the new set in verbatim, including deletions and
   renames. These are reference material only; no test reads them.
3. **`music21_mnx/base.py`** — update the `TypedDict` shapes for anything that
   changed, and the module docstring's "written against the schema published …
   as of DATE, whose `$id` declares schema version NN" line.
4. **Version** — see the `bump-version` skill; a schema sync moves the middle
   digit and resets the patch.
5. **`README.md`** — the "Coverage and known limitations" list. A newly added MNX
   feature that we do not implement belongs in the "not yet round-tripped" list on
   the same commit that syncs the schema, so the README never silently overstates
   coverage.
6. **`music21_mnx/test_mnx.py`** — if the sync changed an encoding we *do* emit,
   the affected `ALL_EXAMPLES` entry needs updating, and
   `testExportsValidateAgainstSchema` will fail loudly if the exporter now emits
   something the new schema rejects. That failure is the point; fix the exporter,
   not the schema.

## Smoke-test the whole example set after a sync

No test reads `examples/`, so run this by hand — it catches an importer that
chokes on a newly-shaped example, and an exporter that now emits something the
new schema rejects:

```python
# uv run python - (or a scratch file)
import glob, json, jsonschema, os
from music21_mnx import MNXImporter, MNXExporter
validator = jsonschema.Draft202012Validator(json.load(open('music21_mnx/mnx-schema.json')))
for path in sorted(glob.glob('examples/*.json')):
    try:
        doc = MNXExporter(MNXImporter(open(path).read()).run()).export()
    except Exception as exc:
        print('FAIL', os.path.basename(path), exc); continue
    for err in list(validator.iter_errors(doc))[:1]:
        print('INVALID', os.path.basename(path), err.message[:160])
```

As of schema 27 all 52 examples import, export, and validate cleanly. Anything
that regresses that is a real bug, not an expected cost of the sync.

## Watch out for

- **Renamed `$defs` with the same shape.** e.g. schema 17→27 renamed `dynamic` to
  `dynamic-group` *and* changed its required keys from `position`+`value` to
  `position`+`type`. A rename that looks cosmetic in the diff can be a semantic
  redesign — check the prose docs.
- **Examples still carrying `"version": 1`.** Many upstream examples have a stale
  `mnx.version` header. That is expected; we emit `MNX_SCHEMA_VERSION` on export
  regardless.
- **A schema bump alone proves nothing.** `uv run pytest music21_mnx` passing
  after a sync only means the constructs we *already* emit still validate. It says
  nothing about newly added features, which is why step 5 exists.
