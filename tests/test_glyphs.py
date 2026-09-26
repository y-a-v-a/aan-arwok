"""Unit tests for tools/kawara_glyphs.py."""

import contextlib
import io
import json
import re
import unittest
from unittest import mock

from helpers import (FIXTURE, REAL_GLYPHS, TempDir,
                     assert_real_source_untouched, fixture_file, load_generated_js)

import kawara_glyphs as kg


def tearDownModule():
    assert_real_source_untouched()


class Numbers(unittest.TestCase):
    def test_num_keeps_integers_integral(self):
        self.assertEqual(kg._num("12"), 12)
        self.assertIsInstance(kg._num("12.0"), int)
        self.assertEqual(kg._num("-395.794"), -395.794)

    def test_fmt_writes_at_most_three_decimals(self):
        self.assertEqual(kg._fmt(12), "12")
        self.assertEqual(kg._fmt(12.0), "12")
        self.assertEqual(kg._fmt(395.79400), "395.794")
        self.assertEqual(kg._fmt(1234.567), "1234.567")   # {:g} gave 1234.57
        self.assertEqual(kg._fmt(0.1 + 0.2), "0.3")
        self.assertEqual(kg._fmt(-0.0001), "0")            # never "-0"


class ReadGlyphs(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.order, self.glyphs = kg.read_glyphs(fixture_file(self.tmp.path))

    def tearDown(self):
        self.tmp.cleanup()

    def test_order_follows_the_file(self):
        self.assertEqual(self.order, ["I", "O", "i", "I.alt"])

    def test_plain_outline(self):
        self.assertEqual(self.glyphs["I"], {
            "name": "I", "width": 247, "unicode": "0049", "components": [],
            "paths": [{"closed": 1, "nodes": [
                [70, 0, "LINE", False], [177, 0, "LINE", False],
                [177, 700, "LINE", False], [70, 700, "LINE", False]]}],
        })

    def test_curves_smooth_flags_and_fractions(self):
        nodes = self.glyphs["O"]["paths"][0]["nodes"]
        self.assertEqual(nodes[2], [350, 0, "CURVE", True])
        self.assertEqual(nodes[5], [600, 350.5, "CURVE", False])
        self.assertEqual([n[2] for n in nodes].count("OFFCURVE"), 4)

    def test_component_glyph(self):
        g = self.glyphs["i"]
        self.assertEqual(g["paths"], [])
        self.assertEqual(g["components"], [{"name": "I", "transform": [1, 0, 0, 1, 0, 10]}])
        self.assertEqual(g["width"], 247)

    def test_glyph_without_outline_or_unicode(self):
        g = self.glyphs["I.alt"]
        self.assertEqual((g["paths"], g["unicode"], g["width"]), ([], None, 300))

    def test_reads_every_glyph_of_the_real_source(self):
        order, glyphs = kg.read_glyphs(REAL_GLYPHS)
        self.assertIn("A", order)
        for name in order:
            g = glyphs[name]
            self.assertIsInstance(g["width"], int, name)
            self.assertTrue(g["paths"] or g["components"] or name == "space", name)
            for p in g["paths"]:
                kg.validate_paths([p])   # every stored path is well-formed


class ValidatePaths(unittest.TestCase):
    GOOD = [{"nodes": [[0, 0, "LINE", False], [1, 0, "LINE", False], [1, 1, "LINE", False]]}]

    def test_accepts_well_formed_paths(self):
        kg.validate_paths(self.GOOD)

    def test_rejects_malformed_paths(self):
        line = [0, 0, "LINE", False]
        for bad in ([], None, [{}], [{"nodes": [line, line]}],
                    [{"nodes": [line, line, [0, 0, "QCURVE", False]]}],
                    [{"nodes": [line, line, [0, "0", "LINE", False]]}],
                    [{"nodes": [line, line, [0, 0, "LINE", 1]]}],
                    [{"nodes": [line, line, [0, 0, "LINE"]]}]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                kg.validate_paths(bad)


class WriteGlyph(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.path = fixture_file(self.tmp.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rewrites_paths_and_width_of_one_glyph_only(self):
        paths = [{"closed": 1, "nodes": [[0, 0, "LINE", False], [100.25, 0, "LINE", False],
                                         [50, 80, "CURVE", True]]}]
        g = kg.write_glyph("I", width=200, paths=paths, path=self.path)
        self.assertEqual((g["width"], g["paths"]), (200, paths))
        order, glyphs = kg.read_glyphs(self.path)
        self.assertEqual(glyphs["I"]["paths"], paths)
        orig = self.tmp.path / "orig.glyphs"
        orig.write_text(FIXTURE)
        _, before = kg.read_glyphs(orig)
        for name in ("O", "i", "I.alt"):
            self.assertEqual(glyphs[name], before[name])
        self.assertIn('"100.25 0 LINE"', self.path.read_text())
        self.assertIn('"50 80 CURVE SMOOTH"', self.path.read_text())

    def test_writing_a_glyph_unchanged_only_touches_last_change(self):
        _, glyphs = kg.read_glyphs(self.path)
        for name in ("I", "O"):
            kg.write_glyph(name, width=glyphs[name]["width"],
                           paths=glyphs[name]["paths"], path=self.path)
        strip = lambda t: re.sub(r'lastChange = "[^"]*";', "", t)
        self.assertEqual(strip(self.path.read_text()), strip(FIXTURE))
        self.assertNotEqual(self.path.read_text(), FIXTURE)   # stamps were refreshed

    def test_every_real_glyph_round_trips(self):
        copy = self.tmp.path / "copy.glyphs"
        copy.write_bytes(REAL_GLYPHS.read_bytes())
        order, glyphs = kg.read_glyphs(copy)
        for name in order:
            if glyphs[name]["paths"]:
                kg.write_glyph(name, width=glyphs[name]["width"],
                               paths=glyphs[name]["paths"], path=copy)
        strip = lambda t: re.sub(r'lastChange = "[^"]*";', "", t)
        self.assertEqual(strip(copy.read_text()), strip(REAL_GLYPHS.read_text()))

    def test_adds_paths_to_a_glyph_without_outline(self):
        paths = [{"closed": 1, "nodes": [[0, 0, "LINE", False], [9, 0, "LINE", False],
                                         [9, 9, "LINE", False]]}]
        kg.write_glyph("I.alt", paths=paths, path=self.path)
        self.assertEqual(kg.read_glyphs(self.path)[1]["I.alt"]["paths"], paths)

    def test_width_only(self):
        kg.write_glyph("O", width=720, path=self.path)
        g = kg.read_glyphs(self.path)[1]["O"]
        self.assertEqual(g["width"], 720)
        self.assertEqual(len(g["paths"][0]["nodes"]), 7)

    def test_errors_leave_the_file_alone(self):
        for kwargs, msg in (({"name": "Nope", "width": 5}, "not found"),
                            ({"name": "I", "width": -1}, "width must be >= 0"),
                            ({"name": "I", "paths": []}, "non-empty")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, msg):
                    kg.write_glyph(path=self.path, **kwargs)
                self.assertEqual(self.path.read_text(), FIXTURE)


class ExportAndApply(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_writes_a_loadable_script(self):
        out = self.tmp.path / "glyphdata.js"
        with contextlib.redirect_stdout(io.StringIO()):
            kg.export_js(out)
        data = load_generated_js(out, "KAWARA_GLYPHS")
        self.assertEqual(data["upm"], 1000)
        self.assertEqual(set(data["order"]), set(data["glyphs"]))
        self.assertEqual(data["glyphToChar"]["question"], "?")

    def test_apply_writes_a_list_of_edits(self):
        path = fixture_file(self.tmp.path)
        edits = self.tmp.path / "edits.json"
        edits.write_text(json.dumps([{"name": "I", "width": 250}, {"name": "O", "width": 710}]))
        with mock.patch.object(kg, "GLYPHS_FILE", path), \
                contextlib.redirect_stdout(io.StringIO()):
            kg.apply_json(edits)
        _, glyphs = kg.read_glyphs(path)
        self.assertEqual((glyphs["I"]["width"], glyphs["O"]["width"]), (250, 710))


if __name__ == "__main__":
    unittest.main()
