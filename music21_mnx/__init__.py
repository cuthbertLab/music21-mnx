# ------------------------------------------------------------------------------
# Name:         music21_mnx/__init__.py
# Purpose:      MNX (W3C music notation format) import/export plugin for music21
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
``music21_mnx`` adds **MNX** support to `music21 <https://www.music21.org>`_.

MNX is the in-development JSON encoding of Common Western Music Notation from the
W3C Music Notation Community Group (https://w3c-cg.github.io/mnx/).  Because MNX
has not yet reached a stable release, this support lives in its own package
rather than in music21 itself.

Importing the package is all it takes — it registers a SubConverter with
music21, so the ``'mnx'`` format immediately works through the normal
:mod:`music21.converter` API::

    import music21_mnx                      # registers the converter as a side effect
    from music21 import converter

    score = converter.parse('song.mnx')     # or converter.parse(jsonText, format='mnx')
    score.write('mnx', fp='out.mnx')

You can also use the converter classes directly:
:class:`~music21_mnx.fromMnx.MNXImporter` and
:class:`~music21_mnx.toMnx.MNXExporter`.

Versioning
==========

This package's version tracks the MNX schema version it targets: ``0.17.x``
follows MNX schema version 17 (see :data:`music21_mnx.base.MNX_SCHEMA_VERSION`).
Documents produced by the exporter declare that schema version in their ``mnx``
header.

This package was written almost entirely by an AI agent (Claude Opus) under the
maintainer's direction; treat it as AI-assisted code pending human review.
'''
from __future__ import annotations

__version__ = '0.17.0'

__all__ = [
    'base',
    'fromMnx',
    'toMnx',
    'converter',
    'MNXImporter',
    'MNXExporter',
    'MNXException',
    'ConverterMNX',
]

from music21_mnx import base
from music21_mnx import fromMnx
from music21_mnx import toMnx
from music21_mnx import converter
from music21_mnx.base import MNXException
from music21_mnx.fromMnx import MNXImporter
from music21_mnx.toMnx import MNXExporter
from music21_mnx.converter import ConverterMNX


def registerWithMusic21() -> None:
    '''
    Register :class:`~music21_mnx.converter.ConverterMNX` with music21's
    converter subsystem.  Called automatically on import; safe to call again
    (music21 checks registered formats by class).
    '''
    from music21 import converter as m21converter
    m21converter.registerSubConverter(ConverterMNX)


registerWithMusic21()
