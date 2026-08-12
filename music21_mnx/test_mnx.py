# ------------------------------------------------------------------------------
# Name:         music21_mnx/test_mnx.py
# Purpose:      Tests for MNX import and export
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2026 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Unit tests for the :mod:`music21_mnx` package.

The MNX documents embedded below are minimal, self-contained versions of the
example documents published with the spec, so the tests do not depend on any
external files.  This test module was written by an AI agent (Claude Opus); a
human reviewer should remove this note after review.
'''
from __future__ import annotations

import json
import unittest

from music21 import bar
from music21 import chord
from music21 import clef
from music21 import converter
from music21 import dynamics
from music21 import key
from music21 import meter
from music21 import note
from music21 import spanner
from music21 import stream

import music21_mnx
from music21_mnx import MNXImporter, MNXExporter, MNXException
from music21_mnx import base


HELLO_WORLD = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"barline": {"type": "regular"}, "time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "clefs": [{"clef": {"sign": "G", "staffPosition": -2}}],
    "sequences": [{"content": [
      {"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]}
    ]}]
  }]}]
}
'''

CHORD_AND_REST = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "clefs": [{"clef": {"sign": "G", "staffPosition": -2}}],
    "sequences": [{"content": [
      {"duration": {"base": "half"}, "notes": [
        {"pitch": {"step": "C", "octave": 4}},
        {"pitch": {"step": "E", "octave": 4}},
        {"pitch": {"step": "G", "octave": 4}}
      ]},
      {"duration": {"base": "half"}, "rest": {}}
    ]}]
  }]}]
}
'''

DOTTED = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "sequences": [{"content": [
      {"duration": {"base": "quarter", "dots": 1},
       "notes": [{"pitch": {"step": "G", "octave": 4}}]},
      {"duration": {"base": "eighth"}, "notes": [{"pitch": {"step": "E", "octave": 5}}]}
    ]}]
  }]}]
}
'''

KEY_AND_ACCIDENTAL = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"key": {"fifths": -2}, "time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "clefs": [{"clef": {"sign": "G", "staffPosition": -2}}],
    "sequences": [{"content": [
      {"duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "G", "octave": 4, "alter": 1},
                  "accidentalDisplay": {"show": true}}]}
    ]}]
  }]}]
}
'''

TIES = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}, {}]},
  "parts": [{"measures": [
    {"sequences": [{"content": [
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "C", "octave": 5}}]},
      {"duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "E", "octave": 5}, "ties": [{"target": "note3"}]}]},
      {"duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "E", "octave": 5}, "id": "note3"}]},
      {"duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "C", "octave": 5}, "ties": [{"target": "note5"}]}]}
    ]}]},
    {"sequences": [{"content": [
      {"duration": {"base": "half"},
       "notes": [{"pitch": {"step": "C", "octave": 5}, "id": "note5"}]},
      {"duration": {"base": "half"},
       "notes": [{"pitch": {"step": "C", "octave": 5}}]}
    ]}]}
  ]}]
}
'''

SLURS = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "sequences": [{"content": [
      {"id": "ev1", "duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "C", "octave": 5}}],
       "slurs": [{"side": "up", "target": "ev3"}]},
      {"id": "ev2", "duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "D", "octave": 5}}]},
      {"id": "ev3", "duration": {"base": "quarter"},
       "notes": [{"pitch": {"step": "E", "octave": 5}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "F", "octave": 5}}]}
    ]}]
  }]}]
}
'''

MULTI_VOICE = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "sequences": [
      {"content": [
        {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]},
        {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "G", "octave": 3}}]}
      ]},
      {"content": [
        {"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "E", "octave": 5}}]}
      ]}
    ]
  }]}]
}
'''

TUPLET = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "sequences": [{"content": [
      {"type": "tuplet",
       "inner": {"multiple": 3, "duration": {"base": "eighth"}},
       "outer": {"multiple": 2, "duration": {"base": "eighth"}},
       "content": [
         {"duration": {"base": "eighth"}, "notes": [{"pitch": {"step": "C", "octave": 5}}]},
         {"duration": {"base": "eighth"}, "notes": [{"pitch": {"step": "D", "octave": 5}}]},
         {"duration": {"base": "eighth"}, "notes": [{"pitch": {"step": "E", "octave": 5}}]}
       ]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "F", "octave": 5}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "G", "octave": 5}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "A", "octave": 5}}]}
    ]}]
  }]}]
}
'''

BEAMS = '''
{
  "mnx": {"version": 1, "support": {"useBeams": true}},
  "global": {"measures": [{"time": {"count": 2, "unit": 4}}]},
  "parts": [{"measures": [{
    "beams": [{"events": ["ev1", "ev2", "ev3", "ev4"]}],
    "sequences": [{"content": [
      {"id": "ev1", "duration": {"base": "eighth"},
       "notes": [{"pitch": {"step": "C", "octave": 5}}]},
      {"id": "ev2", "duration": {"base": "eighth"},
       "notes": [{"pitch": {"step": "D", "octave": 5}}]},
      {"id": "ev3", "duration": {"base": "eighth"},
       "notes": [{"pitch": {"step": "E", "octave": 5}}]},
      {"id": "ev4", "duration": {"base": "eighth"},
       "notes": [{"pitch": {"step": "F", "octave": 5}}]}
    ]}]
  }]}]
}
'''

TWO_PARTS = '''
{
  "mnx": {"version": 1},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [
    {"name": "Melody", "measures": [{
      "clefs": [{"clef": {"sign": "G", "staffPosition": -2}}],
      "sequences": [{"content": [
        {"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "C", "octave": 5}}]}
      ]}]
    }]},
    {"name": "Bass", "measures": [{
      "clefs": [{"clef": {"sign": "F", "staffPosition": 2}}],
      "sequences": [{"content": [
        {"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "C", "octave": 3}}]}
      ]}]
    }]}
  ]
}
'''

DYNAMICS = '''
{
  "mnx": {"version": 27},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}]},
  "parts": [{"measures": [{
    "dynamics": [
      {"position": {"fraction": [0, 1]}, "type": "immediate", "value": "ff"},
      {"position": {"fraction": [3, 4]}, "type": "immediate", "value": "ppp", "orient": "above"}
    ],
    "sequences": [{"content": [
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "E", "octave": 4}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "G", "octave": 4}}]},
      {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "C", "octave": 5}}]}
    ]}]
  }]}]
}
'''

# The four accent spellings from the spec's dynamics-accents example, plus the
# two residualValue forms (fp and sfzp).
DYNAMIC_ACCENTS = '''
{
  "mnx": {"version": 27},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}, {}]},
  "parts": [{"measures": [
    {"dynamics": [
       {"position": {"fraction": [0, 1]}, "type": "accent", "value": "f"},
       {"position": {"fraction": [1, 4]}, "type": "accent", "accentPrefix": "r", "value": "f"},
       {"position": {"fraction": [1, 2]}, "type": "accent", "accentPrefix": "", "value": "f"},
       {"position": {"fraction": [3, 4]}, "type": "accent", "value": "f", "accentSuffix": ""}
     ],
     "sequences": [{"content": [
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "D", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "E", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "F", "octave": 4}}]}
     ]}]},
    {"dynamics": [
       {"position": {"fraction": [0, 1]}, "type": "accent", "accentPrefix": "",
        "value": "f", "accentSuffix": "", "residualValue": "p"},
       {"position": {"fraction": [1, 2]}, "type": "accent", "value": "f", "residualValue": "p"}
     ],
     "sequences": [{"content": [
       {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "G", "octave": 4}}]},
       {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "E", "octave": 4}}]}
     ]}]}
  ]}]
}
'''

HAIRPIN = '''
{
  "mnx": {"version": 27},
  "global": {"measures": [
    {"id": "m1", "time": {"count": 4, "unit": 4}},
    {"id": "m2"}
  ]},
  "parts": [{"measures": [
    {"dynamics": [
       {"position": {"fraction": [0, 1]}, "type": "immediate", "value": "p"},
       {"position": {"fraction": [1, 4]}, "type": "gradual", "wedgeType": "increasing",
        "end": {"measure": "m2", "position": {"fraction": [1, 2]}}}
     ],
     "sequences": [{"content": [
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "C", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "D", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "E", "octave": 4}}]},
       {"duration": {"base": "quarter"}, "notes": [{"pitch": {"step": "F", "octave": 4}}]}
     ]}]},
    {"sequences": [{"content": [
       {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "G", "octave": 4}}]},
       {"duration": {"base": "half"}, "notes": [{"pitch": {"step": "A", "octave": 4}}]}
     ]}]}
  ]}]
}
'''

MEASURE_REPEAT = '''
{
  "mnx": {"version": 27},
  "global": {"measures": [{"time": {"count": 4, "unit": 4}}, {}]},
  "parts": [{"measures": [
    {"sequences": [{"content": [
      {"duration": {"base": "whole"}, "notes": [{"pitch": {"step": "C", "octave": 5}}]}
    ]}]},
    {"measureRepeat": {"number": 1, "counter": {"count": 2, "orient": "above"}},
     "sequences": [{"content": []}]}
  ]}]
}
'''

ALL_EXAMPLES = {
    'hello': HELLO_WORLD,
    'dynamics': DYNAMICS,
    'dynamicAccents': DYNAMIC_ACCENTS,
    'hairpin': HAIRPIN,
    'measureRepeat': MEASURE_REPEAT,
    'chordRest': CHORD_AND_REST,
    'dotted': DOTTED,
    'keyAccidental': KEY_AND_ACCIDENTAL,
    'ties': TIES,
    'slurs': SLURS,
    'multiVoice': MULTI_VOICE,
    'tuplet': TUPLET,
    'beams': BEAMS,
    'twoParts': TWO_PARTS,
}


def _roundTripSignature(score: stream.Score):
    '''
    A comparable fingerprint of a score's pitches, durations, ties, slurs,
    dynamics, and hairpins — enough to detect content drift across a round trip.
    '''
    pitches = []
    durs = []
    for n in score.recurse().notesAndRests:
        durs.append(round(float(n.duration.quarterLength), 6))
        if n.isRest:
            pitches.append('rest')
        else:
            pitches.append(','.join(p.nameWithOctave for p in n.pitches))
    ties = sum(1 for n in score.recurse().notes if n.tie is not None)
    slurs = len(list(score.recurse().getElementsByClass(spanner.Slur)))
    dynamicValues = [d.value for d in score.recurse().getElementsByClass(dynamics.Dynamic)]
    wedges = [
        (type(w).__name__, [n.nameWithOctave for n in w.getSpannedElements()])
        for w in score.recurse().getElementsByClass(dynamics.DynamicWedge)
    ]
    repeats = [
        m.editorial.get('mnxMeasureRepeat')
        for m in score.recurse().getElementsByClass(stream.Measure)
        if m.editorial.get('mnxMeasureRepeat') is not None
    ]
    return (pitches, durs, ties, slurs, dynamicValues, wedges, repeats)


class Test(unittest.TestCase):

    def setUp(self):
        # The converter is not registered on import (by design), so activate it
        # for the tests that go through music21's converter.parse/.write API.
        music21_mnx.register()

    def tearDown(self):
        music21_mnx.unregister()

    def testHelloWorld(self):
        score = MNXImporter(HELLO_WORLD).run()
        self.assertEqual(len(score.parts), 1)
        notes = list(score.recurse().notes)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].nameWithOctave, 'C4')
        self.assertEqual(notes[0].duration.type, 'whole')
        treble = score.recurse().getElementsByClass(clef.TrebleClef).first()
        self.assertIsNotNone(treble)
        ts = score.recurse().getElementsByClass(meter.TimeSignature).first()
        self.assertEqual(ts.ratioString, '4/4')

    def testParseFromDict(self):
        # The importer should accept an already-parsed dict, not only a string.
        score = MNXImporter(json.loads(HELLO_WORLD)).run()
        self.assertEqual(len(score.recurse().notes), 1)

    def testChordAndRest(self):
        score = MNXImporter(CHORD_AND_REST).run()
        chords = list(score.recurse().getElementsByClass(chord.Chord))
        self.assertEqual(len(chords), 1)
        self.assertEqual([p.nameWithOctave for p in chords[0].pitches], ['C4', 'E4', 'G4'])
        rests = list(score.recurse().getElementsByClass(note.Rest))
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].duration.quarterLength, 2.0)

    def testDottedDurations(self):
        score = MNXImporter(DOTTED).run()
        notes = list(score.recurse().notes)
        self.assertEqual(notes[0].duration.type, 'quarter')
        self.assertEqual(notes[0].duration.dots, 1)
        self.assertEqual(notes[0].duration.quarterLength, 1.5)

    def testKeyAndAccidental(self):
        score = MNXImporter(KEY_AND_ACCIDENTAL).run()
        ks = score.recurse().getElementsByClass(key.KeySignature).first()
        self.assertEqual(ks.sharps, -2)
        n = score.recurse().notes.first()
        self.assertEqual(n.pitch.nameWithOctave, 'G#4')
        self.assertTrue(n.pitch.accidental.displayStatus)

    def testTies(self):
        score = MNXImporter(TIES).run()
        tiedNotes = [n for n in score.recurse().notes if n.tie is not None]
        # Two tie pairs: one within m1->m1 and one across m1->m2.
        self.assertEqual(len(tiedNotes), 4)
        types = [n.tie.type for n in tiedNotes]
        self.assertIn('start', types)
        self.assertIn('stop', types)

    def testSlurs(self):
        score = MNXImporter(SLURS).run()
        slurs = list(score.recurse().getElementsByClass(spanner.Slur))
        self.assertEqual(len(slurs), 1)
        spanned = slurs[0].getSpannedElements()
        self.assertEqual(spanned[0].nameWithOctave, 'C5')
        self.assertEqual(spanned[-1].nameWithOctave, 'E5')
        self.assertEqual(slurs[0].placement, 'above')

    def testMultiVoice(self):
        score = MNXImporter(MULTI_VOICE).run()
        voices = list(score.recurse().getElementsByClass(stream.Voice))
        self.assertEqual(len(voices), 2)

    def testTuplet(self):
        score = MNXImporter(TUPLET).run()
        tupletNotes = [n for n in score.recurse().notes if n.duration.tuplets]
        self.assertEqual(len(tupletNotes), 3)
        firstTuplet = tupletNotes[0].duration.tuplets[0]
        self.assertEqual(firstTuplet.numberNotesActual, 3)
        self.assertEqual(firstTuplet.numberNotesNormal, 2)
        # Three eighths in the time of two => each is 1/3 quarter.
        self.assertAlmostEqual(float(tupletNotes[0].duration.quarterLength), 1 / 3)

    def testBeams(self):
        score = MNXImporter(BEAMS).run()
        beamed = [n for n in score.recurse().notes if len(n.beams)]
        self.assertEqual(len(beamed), 4)
        self.assertEqual(beamed[0].beams.beamsList[0].type, 'start')
        self.assertEqual(beamed[-1].beams.beamsList[0].type, 'stop')

    def testTwoParts(self):
        score = MNXImporter(TWO_PARTS).run()
        self.assertEqual(len(score.parts), 2)
        self.assertEqual(score.parts[0].partName, 'Melody')
        self.assertEqual(score.parts[1].partName, 'Bass')
        bassClef = score.parts[1].recurse().getElementsByClass(clef.BassClef).first()
        self.assertIsNotNone(bassClef)

    def testDynamicsImmediate(self):
        score = MNXImporter(DYNAMICS).run()
        found = list(score.recurse().getElementsByClass(dynamics.Dynamic))
        self.assertEqual([d.value for d in found], ['ff', 'ppp'])
        measure = score.recurse().getElementsByClass(stream.Measure).first()
        self.assertEqual(measure.elementOffset(found[0]), 0.0)
        self.assertEqual(measure.elementOffset(found[1]), 3.0)
        # 'orient' maps onto music21 placement; the default stays untouched.
        self.assertEqual(found[1].placement, 'above')

    def testDynamicAccentSpellings(self):
        score = MNXImporter(DYNAMIC_ACCENTS).run()
        found = list(score.recurse().getElementsByClass(dynamics.Dynamic))
        self.assertEqual(
            [d.value for d in found], ['sfz', 'rfz', 'fz', 'sf', 'fp', 'sfzp'])

    def testDynamicAccentsSurviveExport(self):
        score = MNXImporter(DYNAMIC_ACCENTS).run()
        doc = MNXExporter(score).export()
        groups = doc['parts'][0]['measures'][0]['dynamics']
        self.assertEqual([g['type'] for g in groups], ['accent'] * 4)
        # We always write accentPrefix/accentSuffix rather than relying on MNX's
        # 's'/'z' defaults, so the spelling is unambiguous.
        self.assertEqual(
            [(g['accentPrefix'], g['value'], g['accentSuffix']) for g in groups],
            [('s', 'f', 'z'), ('r', 'f', 'z'), ('', 'f', 'z'), ('s', 'f', '')])
        secondMeasure = doc['parts'][0]['measures'][1]['dynamics']
        self.assertEqual([g.get('residualValue') for g in secondMeasure], ['p', 'p'])

    def testHairpinImport(self):
        score = MNXImporter(HAIRPIN).run()
        wedges = list(score.recurse().getElementsByClass(dynamics.DynamicWedge))
        self.assertEqual(len(wedges), 1)
        self.assertIsInstance(wedges[0], dynamics.Crescendo)
        spanned = wedges[0].getSpannedElements()
        # Starts on the note at 1/4 of measure 1, ends on the note at 1/2 of m2.
        self.assertEqual(spanned[0].nameWithOctave, 'D4')
        self.assertEqual(spanned[-1].nameWithOctave, 'A4')

    def testHairpinExportNamesEndMeasureById(self):
        score = MNXImporter(HAIRPIN).run()
        doc = MNXExporter(score).export()
        gradual = [g for g in doc['parts'][0]['measures'][0]['dynamics']
                   if g['type'] == 'gradual']
        self.assertEqual(len(gradual), 1)
        self.assertEqual(gradual[0]['wedgeType'], 'increasing')
        endMeasureId = gradual[0]['end']['measure']
        self.assertEqual(gradual[0]['end']['position'], {'fraction': [1, 2]})
        # The id must actually resolve to a measure in global.measures.
        globalIds = [m.get('id') for m in doc['global']['measures']]
        self.assertIn(endMeasureId, globalIds)
        self.assertEqual(globalIds.index(endMeasureId), 1)

    def testDiminuendoFromMusic21(self):
        score = converter.parse('tinyNotation: 4/4 c4 d4 e4 f4')
        notes = list(score.recurse().notes)
        wedge = dynamics.Diminuendo()
        wedge.addSpannedElements([notes[0], notes[-1]])
        score.insert(0, wedge)
        doc = MNXExporter(score).export()
        gradual = [g for g in doc['parts'][0]['measures'][0]['dynamics']
                   if g['type'] == 'gradual']
        self.assertEqual(gradual[0]['wedgeType'], 'decreasing')
        self.assertEqual(gradual[0]['position'], {'fraction': [0, 1]})
        self.assertEqual(gradual[0]['end']['position'], {'fraction': [3, 4]})

    def testUnrepresentableDynamicIsDropped(self):
        score = converter.parse('tinyNotation: 4/4 c4 d4 e4 f4')
        score.recurse().getElementsByClass(stream.Measure).first().insert(
            0.0, dynamics.Dynamic('cresc.'))
        doc = MNXExporter(score).export()
        self.assertNotIn('dynamics', doc['parts'][0]['measures'][0])

    def testRelativeDynamicIsSkipped(self):
        # 'relative' groups (più p) have no music21 equivalent; the import must
        # drop them rather than inventing a Dynamic.
        src = DYNAMICS.replace(
            '{"position": {"fraction": [0, 1]}, "type": "immediate", "value": "ff"}',
            '{"position": {"fraction": [0, 1]}, "type": "relative", "relativeValue": "softer"}')
        score = MNXImporter(src).run()
        self.assertEqual(
            [d.value for d in score.recurse().getElementsByClass(dynamics.Dynamic)], ['ppp'])

    def testMeasureRepeatRoundTrip(self):
        score = MNXImporter(MEASURE_REPEAT).run()
        measures = list(score.recurse().getElementsByClass(stream.Measure))
        self.assertIsNone(measures[0].editorial.get('mnxMeasureRepeat'))
        self.assertEqual(
            measures[1].editorial.get('mnxMeasureRepeat'),
            {'number': 1, 'counter': {'count': 2, 'orient': 'above'}})
        doc = MNXExporter(score).export()
        self.assertEqual(
            doc['parts'][0]['measures'][1]['measureRepeat'],
            {'number': 1, 'counter': {'count': 2, 'orient': 'above'}})

    def testAccentSplitAndJoinAreInverses(self):
        for text in ('sfz', 'rfz', 'fz', 'sf', 'fp', 'sfzp', 'sffz'):
            with self.subTest(dynamic=text):
                parts = base.splitAccentDynamic(text)
                self.assertIsNotNone(parts, f'{text} should parse as an accent')
                prefix, value, suffix, residual = parts
                self.assertEqual(
                    base.joinAccentDynamic(
                        value, prefix=prefix, suffix=suffix, residual=residual),
                    text)

    def testMissingRequiredKeysRaises(self):
        with self.assertRaises(MNXException):
            MNXImporter('{"mnx": {"version": 1}}').run()

    def testExportTinyNotation(self):
        score = converter.parse('tinyNotation: 4/4 c4 d4 e4 f4')
        doc = MNXExporter(score).export()
        self.assertEqual(doc['mnx'], {'version': base.MNX_SCHEMA_VERSION})
        self.assertEqual(doc['global']['measures'][0]['time'], {'count': 4, 'unit': 4})
        firstEvent = doc['parts'][0]['measures'][0]['sequences'][0]['content'][0]
        self.assertEqual(firstEvent['duration'], {'base': 'quarter'})
        self.assertEqual(firstEvent['notes'][0]['pitch'], {'step': 'C', 'octave': 4})

    def testExportChord(self):
        c = chord.Chord(['C4', 'E4', 'G4'], type='half')
        m = stream.Measure()
        m.append(c)
        p = stream.Part()
        p.append(m)
        doc = MNXExporter(p).export()
        ev = doc['parts'][0]['measures'][0]['sequences'][0]['content'][0]
        self.assertEqual(len(ev['notes']), 3)
        self.assertEqual(ev['duration'], {'base': 'half'})

    def testExportRest(self):
        r = note.Rest(type='quarter')
        m = stream.Measure()
        m.append(r)
        p = stream.Part()
        p.append(m)
        doc = MNXExporter(p).export()
        ev = doc['parts'][0]['measures'][0]['sequences'][0]['content'][0]
        self.assertEqual(ev['rest'], {})

    def testExportClefSigns(self):
        exporter = MNXExporter(stream.Score())
        self.assertEqual(
            exporter.clefToMnx(clef.TrebleClef(), 0.0),
            {'clef': {'sign': 'G', 'staffPosition': -2}})
        self.assertEqual(
            exporter.clefToMnx(clef.BassClef(), 0.0),
            {'clef': {'sign': 'F', 'staffPosition': 2}})
        self.assertEqual(
            exporter.clefToMnx(clef.AltoClef(), 0.0),
            {'clef': {'sign': 'C', 'staffPosition': 0}})

    def testExportBarline(self):
        m = stream.Measure()
        m.append(note.Note('C4', type='whole'))
        m.rightBarline = bar.Barline('final')
        p = stream.Part()
        p.append(m)
        doc = MNXExporter(p).export()
        self.assertEqual(doc['global']['measures'][0]['barline'], {'type': 'final'})

    def testToJsonIsValidJson(self):
        score = converter.parse('tinyNotation: 4/4 c4 d4 e4 f4')
        text = MNXExporter(score).toJson()
        parsed = json.loads(text)
        self.assertIn('mnx', parsed)

    def testRoundTripAllExamples(self):
        for name, src in ALL_EXAMPLES.items():
            with self.subTest(example=name):
                score1 = MNXImporter(src).run()
                doc = MNXExporter(score1).export()
                score2 = MNXImporter(doc).run()
                self.assertEqual(
                    _roundTripSignature(score1),
                    _roundTripSignature(score2),
                    f'round trip changed content for {name}')

    def testRegisterUnregisterIsIdempotent(self):
        from music21_mnx.converter import ConverterMNX
        # setUp already registered; register() again must not duplicate.
        music21_mnx.register()
        self.assertTrue(music21_mnx.isRegistered())
        formats = converter.Converter().getSubConverterFormats()
        self.assertIn('mnx', formats)
        self.assertIs(formats['mnx'], ConverterMNX)

        # unregister removes it; doing so twice must not raise.
        music21_mnx.unregister()
        self.assertFalse(music21_mnx.isRegistered())
        music21_mnx.unregister()
        self.assertNotIn('mnx', converter.Converter().getSubConverterFormats())

    def testImportHasNoSideEffect(self):
        # Importing the package must not, on its own, register the converter.
        # We cannot re-trigger import here, but we can assert that after a clean
        # unregister the format is absent until register() is called again.
        music21_mnx.unregister()
        self.assertNotIn('mnx', converter.Converter().getSubConverterFormats())
        music21_mnx.register()
        self.assertIn('mnx', converter.Converter().getSubConverterFormats())

    def testConverterParseAndWrite(self):
        import os
        score = converter.parse(HELLO_WORLD, format='mnx')
        self.assertEqual(len(score.recurse().notes), 1)
        outPath = score.write('mnx')
        try:
            reparsed = converter.parse(str(outPath))
            self.assertEqual(len(reparsed.recurse().notes), 1)
        finally:
            os.remove(outPath)

    def testJsonExtensionsRouteToMnx(self):
        # While registered, both .json and the conventional .mnx.json extension
        # are parsed as MNX (music21 keys off the final extension).
        import os
        import tempfile
        for suffix in ('.json', '.mnx.json', '.mnx'):
            with self.subTest(suffix=suffix):
                fd, path = tempfile.mkstemp(suffix=suffix)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(HELLO_WORLD)
                    score = converter.parse(path)
                    self.assertEqual(len(score.recurse().notes), 1)
                finally:
                    os.remove(path)

    def testTinyNotationRoundTrip(self):
        score1 = converter.parse('tinyNotation: 3/4 c4 d8 e8 f4')
        doc = MNXExporter(score1).export()
        score2 = MNXImporter(doc).run()
        notes1 = [n.nameWithOctave for n in score1.recurse().notes]
        notes2 = [n.nameWithOctave for n in score2.recurse().notes]
        self.assertEqual(notes1, notes2)

    def testExportsValidateAgainstSchema(self):
        # Validate exported documents against the official MNX JSON schema, if the
        # optional jsonschema package and the schema file are both available.
        try:
            import jsonschema  # type: ignore[import-untyped]
        except ImportError:  # pragma: no cover
            self.skipTest('jsonschema not installed')

        import os
        schemaPath = os.path.join(os.path.dirname(__file__), 'mnx-schema.json')
        if not os.path.exists(schemaPath):  # pragma: no cover
            self.skipTest('MNX schema file not available')

        with open(schemaPath, encoding='utf-8') as f:
            schema = json.load(f)
        validator = jsonschema.Draft202012Validator(schema)

        for name, src in ALL_EXAMPLES.items():
            with self.subTest(example=name):
                score = MNXImporter(src).run()
                doc = MNXExporter(score).export()
                errors = list(validator.iter_errors(doc))
                self.assertEqual(errors, [], f'{name} export is schema-invalid: '
                                 f'{errors[0].message if errors else ""}')

    def testNoteValueRoundTrip(self):
        for m21type in ('whole', 'half', 'quarter', 'eighth', '16th', '32nd'):
            mnxBase = base.m21TypeToMnxBase(m21type)
            self.assertEqual(base.mnxBaseToM21Type(mnxBase), m21type)

    def testDuplexMaximaName(self):
        self.assertEqual(base.m21TypeToMnxBase('duplex-maxima'), 'duplexMaxima')
        self.assertEqual(base.mnxBaseToM21Type('duplexMaxima'), 'duplex-maxima')

    def testUnknownBaseRaises(self):
        with self.assertRaises(MNXException):
            base.mnxBaseToM21Type('4096th')

    def testClefLineConversion(self):
        self.assertEqual(base.staffPositionToClefLine('G', -2), 2)
        self.assertEqual(base.staffPositionToClefLine('F', 2), 4)
        self.assertEqual(base.staffPositionToClefLine('C', 0), 3)
        self.assertEqual(base.clefLineToStaffPosition(2), -2)
        self.assertEqual(base.clefLineToStaffPosition(4), 2)


if __name__ == '__main__':
    import music21
    music21.mainTest(Test)
