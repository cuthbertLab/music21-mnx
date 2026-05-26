# ------------------------------------------------------------------------------
# Name:         music21_mnx/toMnx.py
# Purpose:      Export music21 streams to MNX (W3C music notation JSON)
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Export a music21 object to an MNX document (a plain ``dict``, or a JSON string).

The entry point is :class:`MNXExporter`.  This module was written almost entirely
by an AI agent (Claude Opus) under the maintainer's direction; treat it as
AI-assisted code pending human review.

Export also runs in two passes.  A first pass
(:meth:`MNXExporter.assignReferenceIds`) walks the score and assigns MNX ``id``
strings to exactly those notes and events that participate in a tie, slur, or
beam, recording for each the references it must emit.  The serialization pass
then builds the nested ``dict`` structure, attaching those ids and references so
the cross-object relationships survive as MNX id pointers.

* New in v10.4.
'''
from __future__ import annotations

import json
import typing as t

from music21 import clef
from music21 import duration
from music21 import key
from music21 import meter
from music21 import note
from music21 import spanner
from music21 import stream

from music21_mnx import base
from music21_mnx.base import MNXException

if t.TYPE_CHECKING:
    from fractions import Fraction
    from music21 import pitch
    from music21.base import Music21Object

_PLACEMENT_TO_SIDE = {'above': 'up', 'below': 'down'}


class MNXExporter:
    '''
    Convert a music21 object into an MNX document.

    >>> from music21 import converter
    >>> from music21_mnx import MNXExporter
    >>> s = converter.parse('tinyNotation: 4/4 c4 d4 e4 f4')
    >>> exporter = MNXExporter(s)
    >>> doc = exporter.export()
    >>> doc['mnx']
    {'version': 17}
    >>> doc['global']['measures'][0]['time']
    {'count': 4, 'unit': 4}
    >>> firstEvent = doc['parts'][0]['measures'][0]['sequences'][0]['content'][0]
    >>> firstEvent['duration']
    {'base': 'quarter'}
    >>> firstEvent['notes'][0]['pitch']
    {'step': 'C', 'octave': 4}
    '''

    def __init__(self, obj: Music21Object) -> None:
        self.m21Object = obj
        self.score: stream.Score = self._normalizeToScore(obj)

        self._idCounter = 0
        # id(generalNote) -> assigned MNX event id
        self.eventIds: dict[int, str] = {}
        # id(generalNote) -> assigned MNX note id (for the event's first/only note)
        self.noteIds: dict[int, str] = {}
        # id(sourceGeneralNote) -> list of tie dicts ({'target': noteId})
        self.tiesBySource: dict[int, list[dict[str, t.Any]]] = {}
        # id(startGeneralNote) -> list of slur dicts ({'target': eventId, 'side': ...})
        self.slursByStart: dict[int, list[dict[str, t.Any]]] = {}

    # -- normalization --------------------------------------------------------

    def _normalizeToScore(self, obj: Music21Object) -> stream.Score:
        '''
        Coerce the input into a :class:`~music21.stream.Score` whose parts contain
        :class:`~music21.stream.Measure` objects, leaving the original untouched.
        '''
        if isinstance(obj, stream.Score):
            score = obj
        elif isinstance(obj, stream.Part):
            score = stream.Score()
            score.insert(0, obj)
        elif isinstance(obj, stream.Stream):
            score = stream.Score()
            part = stream.Part()
            for el in obj:
                part.insert(obj.elementOffset(el), el)
            score.insert(0, part)
        else:
            score = stream.Score()
            part = stream.Part()
            part.append(obj)
            score.insert(0, part)

        return score

    def _newId(self, prefix: str) -> str:
        self._idCounter += 1
        return f'{prefix}{self._idCounter}'

    def _ensureEventId(self, generalNote: note.GeneralNote) -> str:
        objId = id(generalNote)
        if objId not in self.eventIds:
            self.eventIds[objId] = self._newId('ev')
        return self.eventIds[objId]

    def _ensureNoteId(self, generalNote: note.GeneralNote) -> str:
        objId = id(generalNote)
        if objId not in self.noteIds:
            self.noteIds[objId] = self._newId('note')
        return self.noteIds[objId]

    # -- top level ------------------------------------------------------------

    def export(self) -> base.MNXDocument:
        '''
        Build and return the MNX document as a plain ``dict``.
        '''
        parts = list(self.score.getElementsByClass(stream.Part))
        if not parts:
            raise MNXException('Could not find any parts to export to MNX.')
        preparedParts = [self._partWithMeasures(p) for p in parts]

        self.assignReferenceIds(preparedParts)

        document: dict[str, t.Any] = {
            'mnx': {'version': base.MNX_DOCUMENT_VERSION},
            'global': {'measures': self.buildGlobalMeasures(preparedParts)},
            'parts': [self.parsePart(p) for p in preparedParts],
        }

        title = None
        if self.score.metadata is not None:
            title = self.score.metadata.title
        if title:
            document['scores'] = [{'name': title}]

        return t.cast(base.MNXDocument, document)

    def toJson(self, *, indent: int | None = 2) -> str:
        '''
        Return the MNX document serialized as a JSON string.
        '''
        return json.dumps(self.export(), indent=indent)

    def _partWithMeasures(self, part: stream.Part) -> stream.Part:
        '''
        Return a Part guaranteed to contain Measures, calling ``makeNotation`` only
        if the part is not already measured (so an already-structured score from
        the importer is left untouched).
        '''
        if part.getElementsByClass(stream.Measure):
            return part
        return part.makeNotation()

    # -- first pass: assign ids for ties, slurs, beams ------------------------

    def assignReferenceIds(self, parts: list[stream.Part]) -> None:
        '''
        First pass: assign MNX ids to the notes/events that participate in a tie,
        slur, or beam, and record the references that must be emitted.
        '''
        for part in parts:
            self._assignTieIds(part)
            self._assignBeamIds(part)
        self._assignSlurIds()

    def _sharePitch(self, a: note.NotRest, b: note.NotRest) -> bool:
        aNames = {p.nameWithOctave for p in a.pitches}
        return any(p.nameWithOctave in aNames for p in b.pitches)

    def _assignTieIds(self, part: stream.Part) -> None:
        notes = list(part.recurse().getElementsByClass(note.NotRest))
        for idx, sourceNote in enumerate(notes):
            if sourceNote.tie is None or sourceNote.tie.type not in ('start', 'continue'):
                continue
            for candidate in notes[idx + 1:]:
                if self._sharePitch(sourceNote, candidate):
                    targetNoteId = self._ensureNoteId(candidate)
                    self.tiesBySource.setdefault(id(sourceNote), []).append(
                        {'target': targetNoteId})
                    break

    def _assignBeamIds(self, part: stream.Part) -> None:
        for generalNote in part.recurse().getElementsByClass(note.NotRest):
            beamsObj = getattr(generalNote, 'beams', None)
            if beamsObj is not None and len(beamsObj):
                self._ensureEventId(generalNote)

    def _assignSlurIds(self) -> None:
        for sp in self.score.recurse().getElementsByClass(spanner.Slur):
            spanned = sp.getSpannedElements()
            if len(spanned) < 2:
                continue
            startNote = spanned[0]
            endNote = spanned[-1]
            self._ensureEventId(startNote)
            targetEventId = self._ensureEventId(endNote)
            slurDict: dict[str, t.Any] = {'target': targetEventId}
            placement = getattr(sp, 'placement', None)
            if placement in _PLACEMENT_TO_SIDE:
                slurDict['side'] = _PLACEMENT_TO_SIDE[placement]
            self.slursByStart.setdefault(id(startNote), []).append(slurDict)

    # -- global measures ------------------------------------------------------

    def buildGlobalMeasures(self, parts: list[stream.Part]) -> list[dict[str, t.Any]]:
        '''
        Build the ``global.measures`` list from the measures of the first part,
        emitting a key/time/barline only on the measures where it actually appears
        (so unchanged measures serialize as ``{}``, matching MNX convention).
        '''
        if not parts:
            return []
        measures = list(parts[0].getElementsByClass(stream.Measure))
        globalMeasures: list[dict[str, t.Any]] = []
        for measure in measures:
            measureGlobal: dict[str, t.Any] = {}

            timeSig = measure.getElementsByClass(meter.TimeSignature).first()
            if timeSig is not None:
                measureGlobal['time'] = {
                    'count': timeSig.numerator,
                    'unit': timeSig.denominator,
                }

            keySig = measure.getElementsByClass(key.KeySignature).first()
            if keySig is not None:
                measureGlobal['key'] = {'fifths': keySig.sharps}

            if measure.rightBarline is not None:
                mnxType = base.M21_BARLINE_TO_MNX.get(measure.rightBarline.type)
                if mnxType is not None:
                    measureGlobal['barline'] = {'type': mnxType}

            globalMeasures.append(measureGlobal)
        return globalMeasures

    # -- parts and measures ---------------------------------------------------

    def parsePart(self, part: stream.Part) -> dict[str, t.Any]:
        '''
        Serialize one :class:`~music21.stream.Part` to an MNX part dict.
        '''
        partData: dict[str, t.Any] = {}
        name = part.partName
        if not name:
            inst = part.getInstrument(returnDefault=False)
            if inst is not None and inst.partName:
                name = inst.partName
        if name:
            partData['name'] = name

        measures = list(part.getElementsByClass(stream.Measure))
        partData['measures'] = [self.parsePartMeasure(m) for m in measures]
        return partData

    def parsePartMeasure(self, measure: stream.Measure) -> dict[str, t.Any]:
        '''
        Serialize one :class:`~music21.stream.Measure` to an MNX part-measure dict.
        '''
        partMeasure: dict[str, t.Any] = {}

        clefList = []
        for clefObj in measure.getElementsByClass(clef.Clef):
            offset = measure.elementOffset(clefObj)
            clefList.append(self.clefToMnx(clefObj, offset))
        if clefList:
            partMeasure['clefs'] = clefList

        beamGroups: list[dict[str, t.Any]] = []
        voices = list(measure.getElementsByClass(stream.Voice))
        if voices:
            sequences = []
            for voiceStream in voices:
                sequence = self.sequenceFromStream(voiceStream, beamGroups)
                voiceId = getattr(voiceStream, 'id', None)
                if voiceId is not None and not isinstance(voiceId, int):
                    sequence['voice'] = str(voiceId)
                sequences.append(sequence)
            partMeasure['sequences'] = sequences
        else:
            partMeasure['sequences'] = [self.sequenceFromStream(measure, beamGroups)]

        if beamGroups:
            partMeasure['beams'] = beamGroups

        return partMeasure

    def clefToMnx(self, clefObj: clef.Clef, offset: float | Fraction) -> dict[str, t.Any]:
        '''
        Serialize a music21 clef to an MNX positioned-clef dict.

        >>> from music21 import clef
        >>> from music21_mnx import toMnx
        >>> from music21 import stream
        >>> exporter = toMnx.MNXExporter(stream.Score())
        >>> exporter.clefToMnx(clef.TrebleClef(), 0.0)
        {'clef': {'sign': 'G', 'staffPosition': -2}}
        >>> exporter.clefToMnx(clef.BassClef(), 0.0)
        {'clef': {'sign': 'F', 'staffPosition': 2}}
        '''
        if clefObj.sign is None or clefObj.line is None:
            raise MNXException(f'Cannot export clef without sign and line: {clefObj!r}')
        clefDict: dict[str, t.Any] = {
            'sign': clefObj.sign,
            'staffPosition': base.clefLineToStaffPosition(clefObj.line),
        }
        if clefObj.octaveChange:
            clefDict['octave'] = clefObj.octaveChange
        positioned: dict[str, t.Any] = {'clef': clefDict}
        if offset:
            positioned['position'] = {'fraction': [int(offset), 4]}
        return positioned

    # -- sequence content -----------------------------------------------------

    def sequenceFromStream(
        self,
        sourceStream: stream.Stream,
        beamGroups: list[dict[str, t.Any]],
    ) -> dict[str, t.Any]:
        '''
        Serialize the notes/rests of one stream (a measure or a voice) into an MNX
        sequence dict, appending any beam groups it finds to ``beamGroups``.
        '''
        items = list(sourceStream.getElementsByClass(note.GeneralNote))
        content: list[dict[str, t.Any]] = []

        index = 0
        while index < len(items):
            generalNote = items[index]
            if generalNote.duration.isGrace:
                graceContent = []
                while index < len(items) and items[index].duration.isGrace:
                    graceContent.append(self.eventFromGeneralNote(items[index]))
                    index += 1
                content.append({'type': 'grace', 'content': graceContent})
                continue
            if generalNote.duration.tuplets:
                tupletItem, index = self._tupletFromRun(items, index)
                content.append(tupletItem)
                continue
            content.append(self.eventFromGeneralNote(generalNote))
            index += 1

        self._collectBeamGroups(items, beamGroups)
        return {'content': content}

    def _tupletFromRun(
        self,
        items: list[note.GeneralNote],
        startIndex: int,
    ) -> tuple[dict[str, t.Any], int]:
        '''
        Build an MNX tuplet object from the run of consecutive notes that share a
        tuplet starting at ``startIndex``.  Returns the tuplet dict and the index
        of the first item after the run.
        '''
        firstTuplet = items[startIndex].duration.tuplets[0]
        tupletContent: list[dict[str, t.Any]] = []
        index = startIndex
        while index < len(items):
            generalNote = items[index]
            if not generalNote.duration.tuplets:
                break
            tupletContent.append(self.eventFromGeneralNote(generalNote))
            tupletType = generalNote.duration.tuplets[0].type
            index += 1
            if tupletType == 'stop':
                break

        actualType = firstTuplet.durationActual.type if firstTuplet.durationActual else 'eighth'
        normalType = firstTuplet.durationNormal.type if firstTuplet.durationNormal else 'eighth'
        tupletItem = {
            'type': 'tuplet',
            'inner': {
                'multiple': firstTuplet.numberNotesActual,
                'duration': {'base': base.m21TypeToMnxBase(actualType)},
            },
            'outer': {
                'multiple': firstTuplet.numberNotesNormal,
                'duration': {'base': base.m21TypeToMnxBase(normalType)},
            },
            'content': tupletContent,
        }
        return tupletItem, index

    def eventFromGeneralNote(self, generalNote: note.GeneralNote) -> dict[str, t.Any]:
        '''
        Serialize one note, chord, or rest into an MNX event dict, attaching any
        tie/slur references and ids assigned in the first pass.
        '''
        event: dict[str, t.Any] = {'duration': self.noteValueFromDuration(generalNote.duration)}

        if isinstance(generalNote, note.Rest):
            event['rest'] = {}
        elif isinstance(generalNote, note.NotRest):
            notesList = []
            tieDicts = self.tiesBySource.get(id(generalNote))
            noteId = self.noteIds.get(id(generalNote))
            for i, p in enumerate(generalNote.pitches):
                noteDict: dict[str, t.Any] = {'pitch': self.pitchToMnx(p)}
                if p.accidental is not None and p.accidental.displayStatus:
                    noteDict['accidentalDisplay'] = {'show': True}
                # The note id and ties attach to the first notehead of the event.
                if i == 0 and noteId is not None:
                    noteDict['id'] = noteId
                if i == 0 and tieDicts:
                    noteDict['ties'] = tieDicts
                notesList.append(noteDict)
            event['notes'] = notesList

            stemDirection = generalNote.stemDirection
            if stemDirection in ('up', 'down'):
                event['stemDirection'] = stemDirection
        else:
            raise MNXException(f'Cannot export event of type {type(generalNote).__name__}')

        slurDicts = self.slursByStart.get(id(generalNote))
        if slurDicts:
            event['slurs'] = slurDicts

        eventId = self.eventIds.get(id(generalNote))
        if eventId is not None:
            event['id'] = eventId

        return event

    def noteValueFromDuration(self, dur: duration.Duration) -> dict[str, t.Any]:
        '''
        Serialize a music21 duration to an MNX note-value (``base`` + ``dots``).

        >>> from music21 import duration
        >>> from music21 import stream
        >>> from music21_mnx import toMnx
        >>> exporter = toMnx.MNXExporter(stream.Score())
        >>> exporter.noteValueFromDuration(duration.Duration(type='quarter', dots=1))
        {'base': 'quarter', 'dots': 1}
        >>> exporter.noteValueFromDuration(duration.Duration(type='whole'))
        {'base': 'whole'}
        '''
        noteValue: dict[str, t.Any] = {'base': base.m21TypeToMnxBase(dur.type)}
        if dur.dots:
            noteValue['dots'] = dur.dots
        return noteValue

    def pitchToMnx(self, p: pitch.Pitch) -> dict[str, t.Any]:
        '''
        Serialize a music21 pitch to an MNX pitch dict.

        >>> from music21 import pitch
        >>> from music21 import stream
        >>> from music21_mnx import toMnx
        >>> exporter = toMnx.MNXExporter(stream.Score())
        >>> exporter.pitchToMnx(pitch.Pitch('F#5'))
        {'step': 'F', 'octave': 5, 'alter': 1}
        >>> exporter.pitchToMnx(pitch.Pitch('C4'))
        {'step': 'C', 'octave': 4}
        '''
        pitchDict: dict[str, t.Any] = {'step': p.step, 'octave': p.implicitOctave}
        if p.accidental is not None and p.accidental.alter:
            pitchDict['alter'] = int(p.accidental.alter)
        return pitchDict

    def _collectBeamGroups(
        self,
        items: list[note.GeneralNote],
        beamGroups: list[dict[str, t.Any]],
    ) -> None:
        '''
        Reconstruct MNX beam groups from the per-note music21 ``Beams`` objects.
        Builds the primary group (level 1) and nests secondary/partial beams under
        it, mirroring the structure the importer expects.
        '''
        currentGroup: list[note.NotRest] = []

        def flush(group: list[note.NotRest]) -> None:
            if len(group) < 2:
                return
            beamGroups.append(self._beamGroupDict(group))

        for generalNote in items:
            if not isinstance(generalNote, note.NotRest):
                if currentGroup:
                    flush(currentGroup)
                    currentGroup = []
                continue
            beamsObj = generalNote.beams
            primaryType = None
            if len(beamsObj):
                primaryType = beamsObj.beamsList[0].type
            if primaryType == 'start':
                flush(currentGroup)
                currentGroup = [generalNote]
            elif primaryType in ('continue', 'stop', 'partial') and currentGroup:
                currentGroup.append(generalNote)
                if primaryType == 'stop':
                    flush(currentGroup)
                    currentGroup = []
            else:
                flush(currentGroup)
                currentGroup = []
        flush(currentGroup)

    def _beamGroupDict(self, group: list[note.NotRest]) -> dict[str, t.Any]:
        '''
        Build the level-1 beam group dict (with nested secondary beams) for a run
        of beamed notes.
        '''
        primary: dict[str, t.Any] = {'events': [self._ensureEventId(n) for n in group]}

        # Secondary beams (level 2+): emit nested groups for full secondary beams
        # and partial (hook) beams.
        secondary: list[dict[str, t.Any]] = []
        for n in group:
            beamsList = n.beams.beamsList
            for beamObj in beamsList:
                if beamObj.number == 1:
                    continue
                if beamObj.type == 'partial':
                    secondary.append({
                        'events': [self._ensureEventId(n)],
                        'direction': beamObj.direction or 'left',
                    })
        if secondary:
            primary['beams'] = secondary
        return primary
