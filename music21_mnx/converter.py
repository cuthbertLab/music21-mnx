# ------------------------------------------------------------------------------
# Name:         music21_mnx/converter.py
# Purpose:      music21 SubConverter that plugs MNX import/export into converter
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
The :class:`ConverterMNX` SubConverter wires this package into music21's
:mod:`music21.converter` subsystem.  It is registered automatically when
``music21_mnx`` is imported (see :mod:`music21_mnx`), so simply importing the
package gives music21 the ability to ``parse`` and ``write`` the ``'mnx'``
format.
'''
from __future__ import annotations

from io import IOBase
import pathlib
import typing as t

from music21 import stream
from music21.converter.subConverters import SubConverter

if t.TYPE_CHECKING:
    from collections.abc import Iterable
    import music21


class ConverterMNX(SubConverter):
    '''
    Converter for MNX, the W3C Music Notation Community Group's JSON encoding of
    Common Western Music Notation.  Both import and export are supported.

    While this converter is registered (see :func:`music21_mnx.register`), both
    the ``.mnx`` and the ``.json`` input extensions are treated as MNX.  That
    covers plain ``.json`` files as well as the spec's conventional double
    extension ``.mnx.json`` (music21 keys off the final extension, ``json``).
    Since nothing else in music21 currently claims ``.json``, this is a
    convenience for now; it can be narrowed later as the format stabilizes.

    Files are written with the ``.mnx`` extension by default.
    '''
    registerFormats = ('mnx',)
    registerInputExtensions = ('mnx', 'json')
    registerShowFormats = ('mnx',)
    registerOutputExtensions = ('mnx',)

    def parseData(self, dataString: str, number: int | None = None) -> stream.Stream:
        '''
        Convert a string containing an MNX (JSON) document into music21 objects.
        '''
        from music21_mnx import MNXImporter
        self.stream = MNXImporter(dataString).run()
        return self.stream

    def parseFile(
        self,
        filePath: str | pathlib.Path,
        number: int | None = None,
        **keywords,
    ) -> stream.Stream:
        '''
        Convert a file containing an MNX (JSON) document into music21 objects.
        '''
        with open(filePath, encoding='utf-8') as f:
            dataStream = f.read()
        self.parseData(dataStream, number)
        return self.stream

    def write(
        self,
        obj: music21.base.Music21Object,
        fmt: str | None,
        fp: str | pathlib.Path | IOBase | None = None,
        subformats: Iterable[str] = (),
        **keywords,
    ) -> pathlib.Path:
        '''
        Write ``obj`` out as an MNX (JSON) document and return the file path.
        '''
        from music21_mnx import MNXExporter
        dataStr = MNXExporter(obj).toJson()
        return self.writeDataStream(fp, dataStr)
