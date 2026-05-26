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

Importing the package has **no side effects**.  Call :func:`register` once to
plug the MNX SubConverter into music21; afterwards the ``'mnx'`` format works
through the normal :mod:`music21.converter` API.  :func:`unregister` cleanly
removes it again::

    import music21_mnx
    music21_mnx.register()                  # activate; import alone does nothing

    from music21 import converter
    score = converter.parse('song.mnx')     # or converter.parse(jsonText, format='mnx')
    score.write('mnx', fp='out.mnx')

    music21_mnx.unregister()                # deactivate when you are done

We avoid registering on import on purpose: importing a module should not mutate
another library's global state behind the user's back (it would also fire when a
linter or documentation tool merely imports the package).  Both functions are
idempotent, so calling them more than once is harmless.

You can always use the converter classes directly without registering at all:
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
    'register',
    'unregister',
    'isRegistered',
]

from music21_mnx import base
from music21_mnx import fromMnx
from music21_mnx import toMnx
from music21_mnx import converter
from music21_mnx.base import MNXException
from music21_mnx.fromMnx import MNXImporter
from music21_mnx.toMnx import MNXExporter
from music21_mnx.converter import ConverterMNX


def isRegistered() -> bool:
    '''
    Return whether :class:`~music21_mnx.converter.ConverterMNX` is currently
    registered with music21's converter subsystem.

    >>> import music21_mnx
    >>> music21_mnx.unregister()
    >>> music21_mnx.isRegistered()
    False
    >>> music21_mnx.register()
    >>> music21_mnx.isRegistered()
    True
    >>> music21_mnx.unregister()
    '''
    from music21 import converter as m21converter
    return ConverterMNX in m21converter.Converter().subConvertersList()


def register() -> None:
    '''
    Plug the MNX SubConverter into music21 so that the ``'mnx'`` format works
    through :mod:`music21.converter`.  Idempotent: calling it when already
    registered does nothing.

    >>> import music21_mnx
    >>> music21_mnx.register()
    >>> from music21 import converter
    >>> 'mnx' in converter.Converter().getSubConverterFormats()
    True
    >>> music21_mnx.unregister()
    '''
    from music21 import converter as m21converter
    if not isRegistered():
        m21converter.registerSubConverter(ConverterMNX)


def unregister() -> None:
    '''
    Remove the MNX SubConverter from music21.  Idempotent: calling it when not
    registered does nothing (and never raises).

    >>> import music21_mnx
    >>> from music21 import converter
    >>> music21_mnx.register()
    >>> music21_mnx.unregister()
    >>> 'mnx' in converter.Converter().getSubConverterFormats()
    False
    '''
    from music21 import converter as m21converter
    if isRegistered():
        m21converter.unregisterSubConverter(ConverterMNX)
