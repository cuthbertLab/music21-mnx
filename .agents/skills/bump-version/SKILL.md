---
name: bump-version
description: >-
  When and how to bump music21-mnx's version. Unlike ordinary semver, this
  package's version tracks the MNX schema revision it targets
  (0.<schema>.<patch>). Use this whenever a change warrants a new version —
  especially after syncing a new MNX schema revision, but also for feature work
  and bug fixes. Covers the THREE places the number appears and the
  Changed in / New in docstring markers.
---

# Bumping music21-mnx's version

The version is `0.<MNX schema version>.<patch>`. `0.17.3` means "targets MNX
schema version 17, third release against it". This is deliberate: pinning a
`music21-mnx` version pins the MNX schema revision you target, which matters while
MNX is unstable.

## Where the number lives

1. **`music21_mnx/__init__.py`** — `__version__ = '0.17.0'` (hatchling reads the
   package version from here, per `[tool.hatch.version]`).
2. **`music21_mnx/base.py`** — `MNX_SCHEMA_VERSION = 17`, the middle digit's
   source of truth. `MNX_DOCUMENT_VERSION` derives from it and is what the
   exporter writes into each document's `"mnx": {"version": N}` header.
3. **Prose** — the "Versioning" sections of `README.md` and the
   `music21_mnx/__init__.py` module docstring both name the current `0.NN.x`
   series, and `base.py`'s module docstring names the schema revision and the date
   it was synced. Update all of them together.

Nothing enforces the match automatically, so grep before you finish:

```bash
grep -rn '0\.17\|SCHEMA_VERSION\|version/17' music21_mnx README.md
```

## Which digit to change

- **Middle digit** — a new MNX schema revision was synced. Set it to the integer
  from the schema's `$id`
  (`https://w3c-cg.github.io/mnx/docs/mnx-schema.json/version/NN`) and reset the
  patch to `0`. See the `sync-mnx-spec` skill for the sync itself.
- **Patch digit** — anything else: new music21↔MNX coverage, bug fixes, refactors,
  packaging. Bump it against the same schema revision.
- **Major digit** — stays `0` while MNX is pre-release and this package is alpha.
  It moves to `1` only when MNX itself reaches a stable release.

Note the middle digit is *not* a minor-version-in-semver, so a schema sync that
happens to break the API is still just a middle-digit bump. Say so loudly in the
changelog/commit message instead.

Unlike music21, there is no pickled-stream cache keyed to this version and no
even/odd alpha convention — do not carry those rules over from `../music21base`.

## `Changed in` / `New in` docstring markers

When a bump accompanies a public-interface change, annotate the affected
method/class docstring, music21-style:

- `* Changed in v0.27: one-line explanation.`
- `* New in v0.27: one-line explanation.`

Use `0.<schema>` (no patch digit) as the version in these markers.

## Checklist

1. `__version__` in `music21_mnx/__init__.py`.
2. `MNX_SCHEMA_VERSION` in `music21_mnx/base.py` (only when the schema moved).
3. The Versioning prose in `README.md` and `music21_mnx/__init__.py`, and the
   schema/date note in `base.py`'s module docstring.
4. `Changed in` / `New in` markers on any changed public API.
5. `uv run pytest music21_mnx` — `testExportTinyNotation` asserts the exported
   header equals `MNX_SCHEMA_VERSION`, so a half-done bump shows up there.
