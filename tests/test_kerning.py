"""Unit tests for tools/kawara_kerning.py."""

import contextlib
import io
import json
import unittest
from unittest import mock

from helpers import (FIXTURE, MASTER, REAL_GLYPHS, TempDir,
                     assert_real_source_untouched, fixture_file)

import kawara_kerning as kk


def tearDownModule():
    assert_real_source_untouched()


class ReadKerning(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.path = fixture_file(self.tmp.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_master_and_pairs(self):
        master, kern = kk.read_kerning(self.path)
        self.assertEqual(master, MASTER)
        self.assertEqual(kern, {
            "I": {"I.alt": 5, "O": -20},
            "I.alt": {"O": -7},
            "O": {"I": 0},
        })

    def test_dotted_names_do_not_leak_into_the_previous_glyph(self):
        # regression: [A-Za-z]+ names filed I.alt's pairs under I
        _, kern = kk.read_kerning(self.path)
        self.assertEqual(kern["I"], {"I.alt": 5, "O": -20})
        self.assertEqual(kern["I.alt"], {"O": -7})

    def test_missing_block_is_an_error(self):
        self.path.write_text("{\nfamilyName = x;\n}\n")
        with self.assertRaisesRegex(ValueError, "no `kerning = {` block"):
            kk.read_kerning(self.path)

    def test_unbalanced_block_is_an_error(self):
        text = FIXTURE[:FIXTURE.index("unitsPerEm")].rstrip().rstrip("};")
        self.path.write_text(text)
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            kk.read_kerning(self.path)


class SerializeKerning(unittest.TestCase):
    def test_round_trips_the_fixture_byte_for_byte(self):
        start, end = kk.find_kerning_block(FIXTURE)
        master, kern = kk.read_kerning(fixture_file(self._tmp()))
        self.assertEqual(kk.serialize_kerning(master, kern), FIXTURE[start:end])

    def test_round_trips_the_real_source_byte_for_byte(self):
        text = REAL_GLYPHS.read_text()
        start, end = kk.find_kerning_block(text)
        master, kern = kk.read_kerning(REAL_GLYPHS)
        self.assertEqual(kk.serialize_kerning(master, kern), text[start:end])

    def test_quotes_negatives_sorts_keys_and_drops_empty_lefts(self):
        out = kk.serialize_kerning("M", {"V": {"period": 3, "A": -5}, "A": {}, "B": {"C": 0}})
        self.assertEqual(out.splitlines(), [
            "kerning = {", '"M" = {',
            "B = {", "C = 0;", "};",
            "V = {", "A = \"-5\";", "period = 3;", "};",
            "};", "};",
        ])

    def _tmp(self):
        tmp = TempDir()
        self.addCleanup(tmp.cleanup)
        return tmp.path


class WriteKerning(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.path = fixture_file(self.tmp.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_replaces_only_the_kerning_block(self):
        n = kk.write_kerning({"O": {"O": -3}, "I": {}}, self.path)
        self.assertEqual(n, 1)
        text = self.path.read_text()
        start, end = kk.find_kerning_block(FIXTURE)
        new_start, new_end = kk.find_kerning_block(text)
        self.assertEqual(text[:new_start], FIXTURE[:start])
        self.assertEqual(text[new_end:], FIXTURE[end:])
        self.assertEqual(kk.read_kerning(self.path), (MASTER, {"O": {"O": -3}}))

    def test_coerces_values_to_int(self):
        kk.write_kerning({"I": {"O": "-12"}}, self.path)
        self.assertEqual(kk.read_kerning(self.path)[1], {"I": {"O": -12}})


class UnknownGlyphs(unittest.TestCase):
    # reads the real source (read-only) through glyphsLib

    def test_known_table_has_no_unknowns(self):
        self.assertEqual(kk.unknown_glyphs({"A": {"V": -80}, "V": {"period": -100}}), [])

    def test_reports_unknown_left_and_right_names(self):
        # regression: apply used to report the left glyph for a bad right one
        self.assertEqual(kk.unknown_glyphs({"A": {"Bogus": 1}}), ["Bogus"])
        self.assertEqual(kk.unknown_glyphs({"Nope": {"A": 1}, "A": {"Zilch": 2}}),
                         ["Nope", "Zilch"])


class ApplyJson(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        # apply_json writes to GLYPHS_FILE: point it at a copy of the real source
        self.copy = self.tmp.path / "copy.glyphs"
        self.copy.write_bytes(REAL_GLYPHS.read_bytes())
        patcher = mock.patch.object(kk, "GLYPHS_FILE", self.copy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def _json(self, payload):
        path = self.tmp.path / "kerning.json"
        path.write_text(json.dumps(payload))
        return path

    def test_rejects_unknown_glyphs_naming_the_bad_one(self):
        with self.assertRaises(SystemExit) as cm:
            kk.apply_json(self._json({"kerning": {"A": {"Bogus": -5}}}))
        self.assertIn("['Bogus']", str(cm.exception))
        self.assertEqual(self.copy.read_bytes(), REAL_GLYPHS.read_bytes())

    def test_applies_a_wrapped_table_and_reports_the_diff(self):
        _, before = kk.read_kerning(self.copy)
        after = {l: dict(rs) for l, rs in before.items()}
        after["A"]["V"] = before["A"].get("V", 0) - 1        # changed
        del after["A"]["B"]                                  # removed
        after.setdefault("Z", {})["period"] = -33            # added (or changed)
        added = "period" not in before.get("Z", {})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            kk.apply_json(self._json({"kerning": after}))
        self.assertEqual(kk.read_kerning(self.copy)[1], after)
        self.assertIn("-1 removed", out.getvalue())
        self.assertIn("+1 new" if added else "~2 changed", out.getvalue())


class Gaps(unittest.TestCase):
    def test_canon_covers_the_workbench_glyphs(self):
        self.assertEqual(set(kk.CANON),
                         {g for g in kk.GLYPH_TO_CHAR if not g.islower() or len(g) > 1} - {"space"})

    def test_lists_never_kerned_glyphs_from_the_data(self):
        tmp = TempDir()
        self.addCleanup(tmp.cleanup)
        out = tmp.path / "gaps.md"
        with mock.patch.object(kk, "read_kerning", return_value=(MASTER, {"A": {"V": -80}})), \
                contextlib.redirect_stdout(io.StringIO()):
            kk.gaps(out)
        text = out.read_text()
        self.assertIn(f"- universe: {len(kk.CANON)} glyphs", text)
        self.assertIn("- kerned (non-zero): **1**", text)
        self.assertNotIn("`A` appears in no kerning pair", text)
        self.assertNotIn("`V` appears in no kerning pair", text)
        self.assertIn("`hyphen` appears in no kerning pair", text)
        self.assertIn("`question` appears in no kerning pair", text)


if __name__ == "__main__":
    unittest.main()
