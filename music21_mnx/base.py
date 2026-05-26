# ------------------------------------------------------------------------------
# Name:         music21_mnx/base.py
# Purpose:      Shared definitions for MNX (the W3C music notation format) support
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Shared type definitions, mapping tables, and small pure helpers used by both the
MNX importer (:mod:`music21_mnx.fromMnx`) and the MNX exporter
(:mod:`music21_mnx.toMnx`).

MNX is the in-development JSON encoding of Common Western Music Notation being
designed by the W3C Music Notation Community Group.  See :mod:`music21_mnx` for
an overview of the format and of how music21 maps onto it.

This module deliberately works with plain Python ``dict`` objects (as produced by
:func:`json.loads`) rather than building a parallel class for every MNX object.
The :class:`~typing.TypedDict` definitions below document the shapes of those
dicts and give static type-checkers something to work with; they impose no
runtime cost.

This implementation was written against the schema published in the
``w3c/mnx`` repository as of 2026-05-26, whose ``$id`` declares schema version
17.  The format is under active development, so the integer below records what we
targeted.  Many of the spec's own example documents still carry an old
``"version": 1`` in their ``mnx`` header, but documents we *produce* are written
against schema version 17, so that is what we emit on export.
'''
from __future__ import annotations

import typing as t

from music21 import exceptions21

# The schema revision this code was written against (the integer in the
# schema's $id: https://w3c-cg.github.io/mnx/docs/mnx-schema.json/version/17).
# This package's release version (0.MNX_SCHEMA_VERSION.x) tracks it.
MNX_SCHEMA_VERSION = 17

# The value emitted in the "mnx": {"version": N} header on export.  We write
# documents against the schema version we target rather than the stale "1" that
# the spec's example documents still use.
MNX_DOCUMENT_VERSION = MNX_SCHEMA_VERSION


class MNXException(exceptions21.Music21Exception):
    '''
    An exception raised when importing from or exporting to MNX fails in a way
    specific to the format (a malformed document, an unsupported construct, an
    unresolvable id reference, etc.).
    '''


# ------------------------------------------------------------------------------
# Mapping tables between MNX vocabularies and music21 vocabularies.

# MNX "note-value" base strings <-> music21 duration.type strings.  The two
# vocabularies agree on everything except the longest note (camelCase in MNX,
# hyphenated in music21) and MNX's 4096th, which music21 does not model.
MNX_BASE_TO_M21_TYPE: dict[str, str] = {
    'duplexMaxima': 'duplex-maxima',
    'maxima': 'maxima',
    'longa': 'longa',
    'breve': 'breve',
    'whole': 'whole',
    'half': 'half',
    'quarter': 'quarter',
    'eighth': 'eighth',
    '16th': '16th',
    '32nd': '32nd',
    '64th': '64th',
    '128th': '128th',
    '256th': '256th',
    '512th': '512th',
    '1024th': '1024th',
    '2048th': '2048th',
}
M21_TYPE_TO_MNX_BASE: dict[str, str] = {v: k for k, v in MNX_BASE_TO_M21_TYPE.items()}

# MNX clef "sign" (C, F, or G) <-> music21 clef letter.  These happen to be
# identical, but the mapping documents the intent and isolates the dependency.
MNX_CLEF_SIGNS = frozenset({'C', 'F', 'G'})

# MNX barline "type" -> music21 bar.Barline type.  music21 uses slightly
# different spellings for a few values.
MNX_BARLINE_TO_M21: dict[str, str] = {
    'regular': 'regular',
    'dotted': 'dotted',
    'dashed': 'dashed',
    'heavy': 'heavy',
    'double': 'double',
    'final': 'final',
    'heavyLight': 'heavy-light',
    'heavyHeavy': 'heavy-heavy',
    'tick': 'tick',
    'short': 'short',
    'noBarline': 'none',
}
M21_BARLINE_TO_MNX: dict[str, str] = {v: k for k, v in MNX_BARLINE_TO_M21.items()}


# ------------------------------------------------------------------------------
# TypedDict shapes for the MNX dicts.  total=False throughout because almost
# every key is optional in some context; the docstrings note what MNX requires.

class MNXPitch(t.TypedDict, total=False):
    '''A pitch: ``step`` (A-G) and ``octave`` are required by MNX; ``alter`` is
    a signed integer count of semitones (e.g. ``1`` for sharp, ``-1`` for flat).'''
    step: str
    octave: int
    alter: int


class MNXNoteValue(t.TypedDict, total=False):
    '''A symbolic duration: ``base`` (required) is a note-value-base string and
    ``dots`` is a count of augmentation dots.'''
    base: str
    dots: int


class MNXAccidentalDisplay(t.TypedDict, total=False):
    show: bool
    force: bool


class MNXTie(t.TypedDict, total=False):
    '''A tie originating on the containing note, optionally targeting the id of
    the note it ties to.'''
    target: str
    targetType: str
    lv: bool
    side: str


class MNXNote(t.TypedDict, total=False):
    '''A single notehead within an event; ``pitch`` is required by MNX.'''
    pitch: MNXPitch
    id: str
    ties: list[MNXTie]
    accidentalDisplay: MNXAccidentalDisplay
    staff: int


class MNXSlur(t.TypedDict, total=False):
    '''An event-level slur; ``target`` (an event id) is required by MNX.'''
    target: str
    side: str
    sideEnd: str
    startNote: str
    endNote: str
    lineType: str


class MNXRest(t.TypedDict, total=False):
    staffPosition: int


class MNXEvent(t.TypedDict, total=False):
    '''A rhythmic event: either pitched (``notes``) or a ``rest``.  ``duration``
    is required by MNX except inside a full-measure context.'''
    type: str
    duration: MNXNoteValue
    notes: list[MNXNote]
    rest: MNXRest
    id: str
    slurs: list[MNXSlur]
    stemDirection: str
    staff: int
    markings: dict[str, t.Any]


class MNXClef(t.TypedDict, total=False):
    sign: str
    staffPosition: int
    octave: int


class MNXPositionedClef(t.TypedDict, total=False):
    clef: MNXClef
    position: dict[str, t.Any]
    staff: int


class MNXTime(t.TypedDict, total=False):
    count: int
    unit: int
    display: str


class MNXKey(t.TypedDict, total=False):
    fifths: int
    color: str


class MNXBarline(t.TypedDict, total=False):
    type: str


class MNXMeasureGlobal(t.TypedDict, total=False):
    '''One entry in ``global.measures`` — measure-wide content shared by all
    parts (time signature, key, barline, etc.).'''
    time: MNXTime
    key: MNXKey
    barline: MNXBarline
    number: int
    index: int


class MNXSequence(t.TypedDict, total=False):
    '''A voice within a part-measure; ``content`` (a list of events) is required.'''
    content: list[dict[str, t.Any]]
    voice: str
    staff: int


class MNXPartMeasure(t.TypedDict, total=False):
    '''One measure of one part; ``sequences`` is required by MNX.'''
    sequences: list[MNXSequence]
    clefs: list[MNXPositionedClef]
    beams: list[dict[str, t.Any]]


class MNXPart(t.TypedDict, total=False):
    '''A part; ``measures`` is required by MNX.'''
    measures: list[MNXPartMeasure]
    name: str
    shortName: str
    staves: int


class MNXGlobal(t.TypedDict, total=False):
    measures: list[MNXMeasureGlobal]


class MNXHeader(t.TypedDict, total=False):
    version: int
    support: dict[str, t.Any]


class MNXDocument(t.TypedDict, total=False):
    '''The root MNX object: ``mnx``, ``global``, and ``parts`` are required.'''
    mnx: MNXHeader
    # 'global' is a Python keyword, so it cannot be a TypedDict field name; it is
    # accessed as document['global'] at runtime.
    parts: list[MNXPart]
    scores: list[dict[str, t.Any]]
    layouts: list[dict[str, t.Any]]


# ------------------------------------------------------------------------------
# Pure conversion helpers shared by importer and exporter.

def mnxBaseToM21Type(base: str) -> str:
    '''
    Convert an MNX note-value ``base`` string to a music21 ``duration.type``.

    >>> from music21_mnx import base
    >>> base.mnxBaseToM21Type('quarter')
    'quarter'
    >>> base.mnxBaseToM21Type('16th')
    '16th'
    >>> base.mnxBaseToM21Type('duplexMaxima')
    'duplex-maxima'

    Unknown values raise an :class:`MNXException`:

    >>> base.mnxBaseToM21Type('4096th')
    Traceback (most recent call last):
    music21_mnx.base.MNXException: Unsupported MNX note-value base: '4096th'
    '''
    try:
        return MNX_BASE_TO_M21_TYPE[base]
    except KeyError:
        raise MNXException(f'Unsupported MNX note-value base: {base!r}')


def m21TypeToMnxBase(durType: str) -> str:
    '''
    Convert a music21 ``duration.type`` to an MNX note-value ``base`` string.

    >>> from music21_mnx import base
    >>> base.m21TypeToMnxBase('eighth')
    'eighth'
    >>> base.m21TypeToMnxBase('duplex-maxima')
    'duplexMaxima'
    '''
    try:
        return M21_TYPE_TO_MNX_BASE[durType]
    except KeyError:
        raise MNXException(f'Cannot represent music21 duration type {durType!r} in MNX')


def staffPositionToClefLine(sign: str, staffPosition: int) -> int:
    '''
    Convert an MNX clef ``staffPosition`` (steps from the center staff line,
    where the center line is 0 and adjacent lines are ±2) to a music21 clef
    ``line`` number (counted from the bottom line of the staff, 1-5).

    A treble (G) clef sits on the second line from the bottom, MNX position -2:

    >>> from music21_mnx import base
    >>> base.staffPositionToClefLine('G', -2)
    2

    A bass (F) clef sits on the fourth line, MNX position 2:

    >>> base.staffPositionToClefLine('F', 2)
    4

    An alto (C) clef sits on the center line, MNX position 0:

    >>> base.staffPositionToClefLine('C', 0)
    3
    '''
    # The center line is line 3 of a 5-line staff; each line is two staff
    # positions apart.
    return 3 + staffPosition // 2


def clefLineToStaffPosition(line: int) -> int:
    '''
    Inverse of :func:`staffPositionToClefLine`.

    >>> from music21_mnx import base
    >>> base.clefLineToStaffPosition(2)
    -2
    >>> base.clefLineToStaffPosition(4)
    2
    '''
    return (line - 3) * 2
