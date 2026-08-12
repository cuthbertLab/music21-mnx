# ------------------------------------------------------------------------------
# Name:         music21_mnx/fromMnx.py
# Purpose:      Import MNX (W3C music notation JSON) into music21 streams
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Import an MNX document (a JSON string or an already-parsed ``dict``) into a
music21 :class:`~music21.stream.Score`.

The entry point is :class:`MNXImporter`.  This module was written almost entirely
by an AI agent (Claude Opus) under the maintainer's direction; treat it as
AI-assisted code pending human review.

Importing happens in two passes, as the maintainer requested.  The first pass
(:meth:`MNXImporter.parseDocument`) builds the score and, as it creates each
music21 object, records that object in :attr:`MNXImporter.m21EventById` /
:attr:`MNXImporter.m21NoteById` under the MNX ``id`` it came from, while queuing
unresolved tie/slur/beam references.  The second pass
(:meth:`MNXImporter.resolveReferences`) walks those queues and connects the
*actual* music21 objects in the finished stream — ties via
:class:`~music21.tie.Tie`, slurs via :class:`~music21.spanner.Slur`, and beams via
:class:`~music21.beam.Beams`.

* New in v10.4.
'''
from __future__ import annotations

import json
import typing as t

from music21 import bar
from music21 import beam
from music21 import chord
from music21 import clef
from music21 import common
from music21 import duration
from music21 import dynamics
from music21 import instrument
from music21 import key
from music21 import metadata
from music21 import meter
from music21 import note
from music21 import pitch
from music21 import spanner
from music21 import stream
from music21 import tie

from music21_mnx import base
from music21_mnx.base import MNXException

if t.TYPE_CHECKING:
    from music21.common.types import OffsetQL, StepName


# Map MNX side values to music21 placement values for slurs/ties.
_SIDE_TO_PLACEMENT = {'up': 'above', 'down': 'below'}

# MNX multi-staff-orientation values music21 can express as a placement.  'auto'
# and 'between' have no music21 equivalent and leave the default in place.
_ORIENT_TO_PLACEMENT = {'above': 'above', 'below': 'below'}


def _fractionToQuarterLength(frac: list[int]) -> OffsetQL:
    '''
    Convert an MNX ``fraction`` (``[numerator, denominator]`` measured in whole
    notes) to a music21 quarter length.

    >>> from music21_mnx import fromMnx
    >>> fromMnx._fractionToQuarterLength([1, 4])
    1.0
    >>> fromMnx._fractionToQuarterLength([3, 8])
    1.5
    >>> fromMnx._fractionToQuarterLength([1, 1])
    4.0
    '''
    numerator, denominator = frac
    return common.opFrac(numerator * 4 / denominator)


class MNXImporter:
    '''
    Convert an MNX document into a music21 :class:`~music21.stream.Score`.

    Pass either a JSON string or an already-parsed ``dict`` to the constructor,
    then call :meth:`run`:

    >>> from music21_mnx import MNXImporter
    >>> src = (
    ...     '{"mnx": {"version": 1}, '
    ...     '"global": {"measures": [{"time": {"count": 4, "unit": 4}}]}, '
    ...     '"parts": [{"measures": [{"sequences": [{"content": ['
    ...     '{"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]}'
    ...     ']}]}]}]}'
    ... )
    >>> score = MNXImporter(src).run()
    >>> score
    <music21.stream.Score ...>
    >>> n = score.recurse().notes.first()
    >>> n.nameWithOctave
    'C4'
    >>> n.duration.type
    'whole'
    '''

    def __init__(self, dataString: str | base.MNXObject = '') -> None:
        self.src: str | base.MNXObject = dataString
        self.mnxData: base.MNXObject = {}
        self.stream: stream.Score = stream.Score()

        # Pass-1 registries: MNX id -> music21 object it produced.
        self.m21EventById: dict[str, note.GeneralNote] = {}
        self.m21NoteById: dict[str, note.GeneralNote] = {}

        # Pass-1 queues of references to resolve in pass 2.
        # (sourceGeneralNote, targetNoteId-or-None)
        self.pendingTies: list[tuple[note.GeneralNote, str | None]] = []
        # (sourceGeneralNote, targetEventId, slurDict)
        self.pendingSlurs: list[tuple[note.GeneralNote, str, base.MNXSlur]] = []
        # raw top-level beam group dicts (their event ids resolve via the registry)
        self.beamGroups: list[base.MNXObject] = []
        # (part, measureIndex, startOffset, gradual dynamic group) — a hairpin,
        # whose 'end' names a global measure by id, so it resolves in pass 2.
        self.pendingWedges: list[
            tuple[stream.Part, int, OffsetQL, base.MNXDynamicGroup]] = []
        # global measure id -> its index in global.measures
        self.globalMeasureIndexById: dict[str, int] = {}

    # -- top level ------------------------------------------------------------

    def run(self) -> stream.Score:
        '''
        Parse the document and return the resulting :class:`~music21.stream.Score`.
        '''
        if isinstance(self.src, str):
            stripped = self.src.strip()
            if stripped.startswith('mnx:'):
                stripped = stripped[4:]
            self.mnxData = json.loads(stripped)
        else:
            self.mnxData = self.src

        self.parseDocument()
        self.resolveReferences()
        return self.stream

    def parseDocument(self) -> None:
        '''
        First pass: build the score's parts/measures/notes and fill the id
        registries and reference queues.
        '''
        doc = self.mnxData
        if 'parts' not in doc or 'global' not in doc:
            raise MNXException(
                "Not a valid MNX document: missing required 'parts' or 'global' key.")

        globalMeasures: list[base.MNXMeasureGlobal] = doc.get('global', {}).get('measures', [])
        for i, globalMeasure in enumerate(globalMeasures):
            measureId = globalMeasure.get('id')
            if measureId:
                self.globalMeasureIndexById[measureId] = i

        self._parseMetadata()

        for partData in doc.get('parts', []):
            part = self.parsePart(partData, globalMeasures)
            self.stream.insert(0, part)

    def _parseMetadata(self) -> None:
        md = metadata.Metadata()
        wroteAny = False
        scores = self.mnxData.get('scores')
        if scores and scores[0].get('name'):
            md.title = scores[0]['name']
            wroteAny = True
        if wroteAny:
            self.stream.insert(0, md)

    # -- parts and measures ---------------------------------------------------

    def parsePart(
        self,
        partData: base.MNXPart,
        globalMeasures: list[base.MNXMeasureGlobal],
    ) -> stream.Part:
        '''
        Build one :class:`~music21.stream.Part` from an MNX part dict.
        '''
        part = stream.Part()
        name = partData.get('name')
        if name:
            part.partName = name
            inst = instrument.Instrument()
            inst.partName = name
            shortName = partData.get('shortName')
            if shortName:
                inst.partAbbreviation = shortName
            part.insert(0, inst)

        for i, partMeasure in enumerate(partData.get('measures', [])):
            globalMeasure: base.MNXMeasureGlobal = (
                globalMeasures[i] if i < len(globalMeasures) else {})
            measure = self.parseMeasure(partMeasure, globalMeasure, measureNumber=i + 1)
            part.append(measure)
            self.parseDynamics(partMeasure.get('dynamics', []), measure, part, i)

        return part

    def parseMeasure(
        self,
        partMeasure: base.MNXPartMeasure,
        globalMeasure: base.MNXMeasureGlobal,
        *,
        measureNumber: int,
    ) -> stream.Measure:
        '''
        Build one :class:`~music21.stream.Measure`, merging the part-specific
        content (clefs, sequences, beams) with the measure-wide ``global``
        content (time signature, key, barline).
        '''
        measure = stream.Measure(number=measureNumber)

        timeData = globalMeasure.get('time')
        if timeData:
            measure.insert(0, meter.TimeSignature(
                f"{timeData['count']}/{timeData['unit']}"))

        keyData = globalMeasure.get('key')
        if keyData is not None and 'fifths' in keyData:
            measure.insert(0, key.KeySignature(keyData['fifths']))

        for positionedClef in partMeasure.get('clefs', []):
            clefObj, clefOffset = self.parseClef(positionedClef)
            measure.insert(clefOffset, clefObj)

        barlineData = globalMeasure.get('barline')
        if barlineData and barlineData.get('type'):
            m21Type = base.MNX_BARLINE_TO_M21.get(barlineData['type'], 'regular')
            measure.rightBarline = bar.Barline(m21Type)

        sequences = partMeasure.get('sequences', [])
        if len(sequences) <= 1:
            if sequences:
                self.fillStreamWithSequence(measure, sequences[0])
        else:
            for i, sequenceData in enumerate(sequences):
                voiceStream = stream.Voice()
                voiceStream.id = sequenceData.get('voice', str(i + 1))
                self.fillStreamWithSequence(voiceStream, sequenceData)
                measure.insert(0, voiceStream)

        for beamGroup in partMeasure.get('beams', []):
            self.beamGroups.append(beamGroup)

        measureRepeat = partMeasure.get('measureRepeat')
        if measureRepeat is not None:
            # A simile marking ("repeat the previous N measures").  music21 has no
            # object for this, so carry the MNX dict on the measure's editorial,
            # which the exporter writes back out unchanged.
            measure.editorial.mnxMeasureRepeat = measureRepeat

        return measure

    def parseClef(self, positionedClef: base.MNXPositionedClef) -> tuple[clef.Clef, float]:
        '''
        Convert an MNX positioned-clef to a (music21 clef, offset) pair.

        >>> from music21_mnx import fromMnx
        >>> imp = fromMnx.MNXImporter()
        >>> c, offset = imp.parseClef({'clef': {'sign': 'G', 'staffPosition': -2}})
        >>> c
        <music21.clef.TrebleClef>
        >>> offset
        0.0
        '''
        clefData = positionedClef['clef']
        sign = clefData['sign']
        staffPosition = clefData.get('staffPosition', 0)
        line = base.staffPositionToClefLine(sign, staffPosition)
        octaveShift = clefData.get('octave', 0)
        clefObj = clef.clefFromString(f'{sign}{line}', octaveShift=octaveShift)

        offset = 0.0
        position = positionedClef.get('position')
        if position and 'fraction' in position:
            offset = float(_fractionToQuarterLength(position['fraction']))
        return clefObj, offset

    # -- dynamics -------------------------------------------------------------

    def parseDynamics(
        self,
        dynamicGroups: list[base.MNXDynamicGroup],
        measure: stream.Measure,
        part: stream.Part,
        measureIndex: int,
    ) -> None:
        '''
        Insert the measure's MNX dynamic groups into ``measure``.  Immediate and
        accent groups become :class:`~music21.dynamics.Dynamic` objects right
        away; gradual ones (hairpins) are queued for :meth:`resolveWedges`,
        because their ``end`` points at another measure by id.

        * New in v0.27.
        '''
        for group in dynamicGroups:
            position = group.get('position')
            if not position or 'fraction' not in position:
                continue
            offset = _fractionToQuarterLength(position['fraction'])

            if group.get('type') == 'gradual':
                self.pendingWedges.append((part, measureIndex, offset, group))
                continue

            text = self.dynamicGroupToText(group)
            if text is None:
                continue
            dynamicObj = dynamics.Dynamic(text)
            placement = _ORIENT_TO_PLACEMENT.get(group.get('orient', ''))
            if placement is not None:
                dynamicObj.placement = placement
            measure.insert(offset, dynamicObj)

    def dynamicGroupToText(self, group: base.MNXDynamicGroup) -> str | None:
        '''
        Spell an MNX dynamic group the way music21 writes dynamics, or return
        ``None`` for one music21 cannot hold.

        >>> from music21_mnx import fromMnx
        >>> imp = fromMnx.MNXImporter()
        >>> imp.dynamicGroupToText({'type': 'immediate', 'value': 'ff'})
        'ff'
        >>> imp.dynamicGroupToText({'type': 'accent', 'value': 'f'})
        'sfz'
        >>> imp.dynamicGroupToText(
        ...     {'type': 'accent', 'value': 'f', 'accentPrefix': '',
        ...      'accentSuffix': '', 'residualValue': 'p'})
        'fp'

        A ``'relative'`` group ("più p") has no music21 equivalent:

        >>> imp.dynamicGroupToText({'type': 'relative', 'relativeValue': 'softer'}) is None
        True

        * New in v0.27.
        '''
        groupType = group.get('type')
        if groupType == 'immediate':
            return group.get('value')
        if groupType == 'accent':
            value = group.get('value')
            if not value:
                return None
            return base.joinAccentDynamic(
                value,
                prefix=group.get('accentPrefix'),
                suffix=group.get('accentSuffix'),
                residual=group.get('residualValue', ''),
            )
        # TODO: 'relative' groups (più f / più p) have no music21 object; the
        # free-text 'prefix'/'suffix' and 'glyphs' of any group are also dropped.
        return None

    # -- sequence content -----------------------------------------------------

    def fillStreamWithSequence(
        self,
        targetStream: stream.Stream,
        sequenceData: base.MNXSequence,
    ) -> None:
        '''
        Append every content item of an MNX sequence to ``targetStream`` at the
        correct rhythmic offset.
        '''
        offset: OffsetQL = 0.0
        for item in sequenceData.get('content', []):
            offset = self.parseContentItem(targetStream, item, offset)

    def parseContentItem(
        self,
        targetStream: stream.Stream,
        item: base.MNXObject,
        offset: OffsetQL,
    ) -> OffsetQL:
        '''
        Parse one item from a sequence's ``content`` list, insert the resulting
        object(s) into ``targetStream`` at ``offset``, and return the offset for
        the next item.
        '''
        itemType = item.get('type', 'event')
        if itemType == 'event':
            generalNote = self.parseEvent(item)
            targetStream.insert(offset, generalNote)
            return common.opFrac(offset + generalNote.duration.quarterLength)
        if itemType == 'grace':
            self.parseGrace(targetStream, item, offset)
            # Grace notes "steal" time visually but do not advance the beat here.
            return offset
        if itemType == 'tuplet':
            return self.parseTuplet(targetStream, item, offset)
        if itemType == 'space':
            return self.parseSpace(targetStream, item, offset)
        # TODO: 'tremolo' (multi-note-tremolo). Parse its content as plain events
        # so nothing is silently dropped.
        if itemType == 'tremolo':
            for sub in item.get('content', []):
                offset = self.parseContentItem(targetStream, sub, offset)
            return offset
        raise MNXException(f'Unknown sequence content type: {itemType!r}')

    def parseEvent(self, eventData: base.MNXObject) -> note.GeneralNote:
        '''
        Convert an MNX event into a :class:`~music21.note.Note`,
        :class:`~music21.chord.Chord`, or :class:`~music21.note.Rest`.
        '''
        dur = self.parseNoteValue(eventData['duration']) if 'duration' in eventData else None

        if 'rest' in eventData and 'notes' not in eventData:
            rest = note.Rest()
            if dur is not None:
                rest.duration = dur
            self._registerEvent(eventData, rest)
            return rest

        notesData = eventData.get('notes', [])
        generalNote: note.NotRest
        if len(notesData) == 1:
            singleNote = note.Note()
            singleNote.pitch = self.parsePitch(notesData[0])
            generalNote = singleNote
        else:
            chordObj = chord.Chord([self.parsePitch(nd) for nd in notesData])
            generalNote = chordObj

        if dur is not None:
            generalNote.duration = dur

        stemDirection = eventData.get('stemDirection')
        if stemDirection in ('up', 'down'):
            generalNote.stemDirection = stemDirection

        self._registerEvent(eventData, generalNote)

        # Per-note id registration and tie queuing.
        for noteData in notesData:
            noteId = noteData.get('id')
            if noteId:
                self.m21NoteById[noteId] = generalNote
            for tieData in noteData.get('ties', []):
                self.pendingTies.append((generalNote, tieData.get('target')))

        # Event-level slurs.
        for slurData in eventData.get('slurs', []):
            if slurData.get('target'):
                self.pendingSlurs.append((generalNote, slurData['target'], slurData))

        return generalNote

    def parseNoteValue(self, noteValue: base.MNXNoteValue) -> duration.Duration:
        '''
        Convert an MNX note-value (``base`` + ``dots``) to a
        :class:`~music21.duration.Duration`.

        >>> from music21_mnx import fromMnx
        >>> imp = fromMnx.MNXImporter()
        >>> d = imp.parseNoteValue({'base': 'quarter', 'dots': 1})
        >>> d.type, d.dots, d.quarterLength
        ('quarter', 1, 1.5)
        '''
        dur = duration.Duration(type=base.mnxBaseToM21Type(noteValue['base']))
        dots = noteValue.get('dots', 0)
        if dots:
            dur.dots = dots
        return dur

    def parsePitch(self, noteData: base.MNXNote) -> pitch.Pitch:
        '''
        Convert an MNX note's ``pitch`` to a :class:`~music21.pitch.Pitch`,
        honoring ``accidentalDisplay`` for whether the accidental prints.

        >>> from music21_mnx import fromMnx
        >>> imp = fromMnx.MNXImporter()
        >>> p = imp.parsePitch({'pitch': {'step': 'F', 'octave': 5, 'alter': 1}})
        >>> p.nameWithOctave
        'F#5'
        '''
        pitchData = noteData['pitch']
        stepValue = pitchData['step']
        if stepValue not in pitch.STEPNAMES:
            raise MNXException(f'Invalid MNX pitch step: {stepValue!r}')
        resultPitch = pitch.Pitch()
        resultPitch.step = t.cast('StepName', stepValue)
        resultPitch.octave = pitchData['octave']
        alter = pitchData.get('alter')
        if alter:
            resultPitch.accidental = pitch.Accidental(alter)
        accidentalDisplay = noteData.get('accidentalDisplay')
        if resultPitch.accidental is not None:
            if accidentalDisplay is not None:
                resultPitch.accidental.displayStatus = bool(accidentalDisplay.get('show'))
            else:
                resultPitch.accidental.displayStatus = False
        return resultPitch

    def parseGrace(
        self,
        targetStream: stream.Stream,
        item: base.MNXObject,
        offset: OffsetQL,
    ) -> None:
        '''
        Parse an MNX ``grace`` object — a small sequence of events with no
        rhythmic value — inserting music21 grace notes at ``offset``.
        '''
        slash = item.get('slash', False)
        for sub in item.get('content', []):
            generalNote = self.parseEvent(sub)
            graceNote = generalNote.getGrace()
            if slash:
                graceNote.duration.slash = True
            # Re-register the ids onto the grace version, replacing the plain note.
            self._registerEvent(sub, graceNote)
            for noteData in sub.get('notes', []):
                if noteData.get('id'):
                    self.m21NoteById[noteData['id']] = graceNote
            targetStream.insert(offset, graceNote)

    def parseTuplet(
        self,
        targetStream: stream.Stream,
        item: base.MNXObject,
        offset: OffsetQL,
    ) -> OffsetQL:
        '''
        Parse an MNX ``tuplet`` object, applying a :class:`~music21.duration.Tuplet`
        to each event in its ``content`` and inserting them at the running offset.
        '''
        inner = item['inner']
        outer = item['outer']
        actualType = base.mnxBaseToM21Type(inner['duration']['base'])
        normalType = base.mnxBaseToM21Type(outer['duration']['base'])

        content = item.get('content', [])
        for i, sub in enumerate(content):
            generalNote = self.parseEvent(sub)
            tuplet = duration.Tuplet(
                numberNotesActual=inner['multiple'],
                numberNotesNormal=outer['multiple'],
                durationActual=actualType,
                durationNormal=normalType,
            )
            if i == 0:
                tuplet.type = 'start'
            elif i == len(content) - 1:
                tuplet.type = 'stop'
            generalNote.duration.appendTuplet(tuplet)
            targetStream.insert(offset, generalNote)
            offset = common.opFrac(offset + generalNote.duration.quarterLength)
        return offset

    def parseSpace(
        self,
        targetStream: stream.Stream,
        item: base.MNXObject,
        offset: OffsetQL,
    ) -> OffsetQL:
        '''
        Parse an MNX ``space`` (an invisible gap).  We insert a hidden
        :class:`~music21.note.Rest` so the stream stays rhythmically complete.
        '''
        quarterLength = _fractionToQuarterLength(item['duration'])
        spacer = note.Rest(quarterLength=quarterLength)
        spacer.style.hideObjectOnPrint = True
        targetStream.insert(offset, spacer)
        return common.opFrac(offset + quarterLength)

    def _registerEvent(self, eventData: base.MNXObject, obj: note.GeneralNote) -> None:
        eventId = eventData.get('id')
        if eventId:
            self.m21EventById[eventId] = obj

    # -- second pass: resolve cross-references --------------------------------

    def resolveReferences(self) -> None:
        '''
        Second pass: connect ties, slurs, and beams using the id registries
        built during :meth:`parseDocument`.
        '''
        self.resolveTies()
        self.resolveSlurs()
        self.resolveBeams()
        self.resolveWedges()

    def resolveTies(self) -> None:
        '''
        Turn queued tie references into :class:`~music21.tie.Tie` objects on the
        actual music21 notes.  A note that both starts and stops a tie becomes a
        ``'continue'`` tie.
        '''
        startObjs: set[int] = set()
        stopObjs: set[int] = set()
        byId: dict[int, note.GeneralNote] = {}

        for sourceNote, targetNoteId in self.pendingTies:
            startObjs.add(id(sourceNote))
            byId[id(sourceNote)] = sourceNote
            if targetNoteId and targetNoteId in self.m21NoteById:
                targetNote = self.m21NoteById[targetNoteId]
                stopObjs.add(id(targetNote))
                byId[id(targetNote)] = targetNote

        for objId, generalNote in byId.items():
            isStart = objId in startObjs
            isStop = objId in stopObjs
            if isStart and isStop:
                generalNote.tie = tie.Tie('continue')
            elif isStart:
                generalNote.tie = tie.Tie('start')
            else:
                generalNote.tie = tie.Tie('stop')

    def resolveSlurs(self) -> None:
        '''
        Turn queued slur references into :class:`~music21.spanner.Slur` objects,
        inserting them into the score.
        '''
        for sourceNote, targetEventId, slurData in self.pendingSlurs:
            targetNote = self.m21EventById.get(targetEventId)
            if targetNote is None:
                # Unresolvable target id; skip rather than fail the whole import.
                continue
            slur = spanner.Slur()
            slur.addSpannedElements([sourceNote, targetNote])
            side = slurData.get('side')
            if side in _SIDE_TO_PLACEMENT:
                slur.placement = _SIDE_TO_PLACEMENT[side]
            self.stream.insert(0, slur)

    def resolveBeams(self) -> None:
        '''
        Apply MNX beam groups to the music21 notes they reference.  Beam
        instructions are accumulated per note across all levels of nesting and
        then built into a :class:`~music21.beam.Beams` object, so primary and
        secondary (and partial/hook) beams all land on the right note.
        '''
        # id(note) -> ordered list of (level, type, direction)
        instructions: dict[int, list[tuple[int, str, str | None]]] = {}
        byId: dict[int, note.GeneralNote] = {}

        def applyLevel(beamGroup: base.MNXObject, level: int) -> None:
            eventIds = beamGroup.get('events', [])
            count = len(eventIds)
            for i, eventId in enumerate(eventIds):
                generalNote = self.m21EventById.get(eventId)
                if generalNote is None:
                    continue
                byId[id(generalNote)] = generalNote
                if count == 1:
                    direction = beamGroup.get('direction', 'left')
                    if direction == 'auto':
                        direction = 'left'
                    instructions.setdefault(id(generalNote), []).append(
                        (level, 'partial', direction))
                elif i == 0:
                    instructions.setdefault(id(generalNote), []).append((level, 'start', None))
                elif i == count - 1:
                    instructions.setdefault(id(generalNote), []).append((level, 'stop', None))
                else:
                    instructions.setdefault(id(generalNote), []).append(
                        (level, 'continue', None))
            for subGroup in beamGroup.get('beams', []):
                applyLevel(subGroup, level + 1)

        for topGroup in self.beamGroups:
            applyLevel(topGroup, 1)

        for objId, beamInstrs in instructions.items():
            generalNote = byId[objId]
            if not isinstance(generalNote, note.NotRest):
                continue
            beamsObj = beam.Beams()
            for _level, beamType, direction in sorted(beamInstrs, key=lambda x: x[0]):
                beamsObj.append(beamType, direction)
            generalNote.beams = beamsObj

    def resolveWedges(self) -> None:
        '''
        Turn queued ``'gradual'`` dynamic groups into
        :class:`~music21.dynamics.Crescendo` / :class:`~music21.dynamics.Diminuendo`
        spanners, resolving each one's ``end`` (a global measure id plus a
        rhythmic position) to the note it lands on.

        * New in v0.27.
        '''
        for part, measureIndex, startOffset, group in self.pendingWedges:
            wedgeClassName = base.MNX_WEDGE_TO_M21_CLASS.get(group.get('wedgeType', ''))
            end = group.get('end')
            if wedgeClassName is None or not end:
                # 'wedgeType' and 'end' are both required for a gradual group;
                # a document missing either is not something we can span.
                continue
            endIndex = self.globalMeasureIndexById.get(end.get('measure', ''))
            if endIndex is None:
                continue
            endPosition = end.get('position', {})
            if 'fraction' not in endPosition:
                continue
            endOffset = _fractionToQuarterLength(endPosition['fraction'])

            startNote = self._noteAtOrAfter(part, measureIndex, startOffset)
            endNote = self._noteAtOrBefore(part, endIndex, endOffset)
            if startNote is None or endNote is None or startNote is endNote:
                continue

            wedge = getattr(dynamics, wedgeClassName)()
            wedge.addSpannedElements([startNote, endNote])
            placement = _ORIENT_TO_PLACEMENT.get(group.get('orient', ''))
            if placement is not None:
                wedge.placement = placement
            self.stream.insert(0, wedge)

    def _notesWithOffsets(
        self,
        part: stream.Part,
        measureIndex: int,
    ) -> list[tuple[OffsetQL, note.GeneralNote]]:
        '''
        Every note/rest of one measure of ``part``, paired with its offset from
        the start of the measure and sorted by that offset.  Voices are flattened
        in, so a wedge can span notes in any voice.
        '''
        measures = list(part.getElementsByClass(stream.Measure))
        if not 0 <= measureIndex < len(measures):
            return []
        measure = measures[measureIndex]
        found: list[tuple[OffsetQL, note.GeneralNote]] = [
            (measure.elementOffset(n), n)
            for n in measure.getElementsByClass(note.GeneralNote)
        ]
        for voiceStream in measure.getElementsByClass(stream.Voice):
            voiceOffset = measure.elementOffset(voiceStream)
            found.extend(
                (common.opFrac(voiceOffset + voiceStream.elementOffset(n)), n)
                for n in voiceStream.getElementsByClass(note.GeneralNote)
            )
        found.sort(key=lambda pair: pair[0])
        return found

    def _noteAtOrAfter(
        self,
        part: stream.Part,
        measureIndex: int,
        offset: OffsetQL,
    ) -> note.GeneralNote | None:
        found = self._notesWithOffsets(part, measureIndex)
        for noteOffset, generalNote in found:
            if noteOffset >= offset:
                return generalNote
        return found[-1][1] if found else None

    def _noteAtOrBefore(
        self,
        part: stream.Part,
        measureIndex: int,
        offset: OffsetQL,
    ) -> note.GeneralNote | None:
        found = self._notesWithOffsets(part, measureIndex)
        for noteOffset, generalNote in reversed(found):
            if noteOffset <= offset:
                return generalNote
        return found[0][1] if found else None
