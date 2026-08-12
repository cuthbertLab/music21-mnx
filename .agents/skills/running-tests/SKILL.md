---
name: running-tests
description: >-
  How to correctly run music21-mnx's tests and doctests with pytest, and which
  gates to run before a PR. Use this whenever you need to run, verify, or judge
  the pass/fail of tests or doctests in this repo. Especially consult this before
  concluding that a doctest "fails": the repo borrows music21's pytest plugin,
  which normalizes object addresses and injects the doctest namespace, so running
  doctests any other way (e.g. raw doctest.testmod) produces FALSE failures.
---

# Running music21-mnx tests and doctests

Everything at once:

```bash
uv run pytest music21_mnx
```

That is 45-ish items: the `Test` class in `music21_mnx/test_mnx.py`, plus the
doctests in every module. A single module:

```bash
uv run pytest music21_mnx/base.py
```

`pyproject.toml` `[tool.pytest.ini_options]` already wires up what makes this work:

```
addopts = ['--doctest-modules', '-p', 'music21.test.pytest_plugin']
doctest_optionflags = ['NORMALIZE_WHITESPACE', 'ELLIPSIS']
```

So do not pass `--doctest-modules` yourself, and note that we deliberately depend
on **music21's** pytest plugin (`music21.test.pytest_plugin`) rather than
reimplementing it.

## Why the plugin matters (and why not to use raw doctest)

The plugin does two things that make doctests pass the way the project intends:

- It runs `stripAddresses(...)` on every doctest, so docstrings that hardcode a
  repr like `<music21.note.Note C at 0x10b0cf5f8>` are normalized and DO pass. The
  literal hex address in the docstring is expected and fine.
- It injects the `music21.__all__` names plus `music21` itself into the doctest
  namespace, so examples can reference `note`, `stream`, `converter`, etc. without
  importing them. (Our own doctests still import `music21_mnx` explicitly — that
  is not injected.)

Judge doctest pass/fail **through pytest**. Do NOT use `doctest.testmod(...)` or
`doctest.DocTestSuite(...)` directly to decide whether doctests pass: neither the
address normalizer nor the namespace injection applies there, so it manufactures
false failures. If you ever see only an object-address example "failing," that is
the tell that you ran doctests the wrong way.

## Register/unregister hygiene in tests

The converter is **not** registered on import, by design. `Test.setUp` calls
`music21_mnx.register()` and `tearDown` calls `unregister()`. Any doctest or test
that registers must unregister again, or it leaks the `'mnx'` format into other
tests' `converter.Converter()` state. The existing doctests in `__init__.py` end
with `unregister()` for exactly this reason.

## The schema-validation test

`testExportsValidateAgainstSchema` validates every document in `ALL_EXAMPLES`,
round-tripped through the exporter, against the bundled
`music21_mnx/mnx-schema.json` using `jsonschema` (a `dev` dependency). It
`skipTest`s if `jsonschema` is missing — so a "passed" run with a stale env can
hide schema breakage. If you changed the schema or the exporter, confirm the test
actually ran:

```bash
uv run pytest music21_mnx/test_mnx.py -k Schema -v
```

New format support should be added to `ALL_EXAMPLES`, which gets it into both the
round-trip test and this one.

## The other gates

Before a PR or a push to an open PR, run all four the way CI does:

```bash
uv run pytest music21_mnx
uv run ruff check music21_mnx
uv run mypy music21_mnx
uv run pylint -j0 music21_mnx
```
