#!/usr/bin/env python3
"""Compile kawara2.glyphs to OnKawara-Regular.otf (repo root + www/)
and refresh www/kerning.js for the kerning workbench.

Usage: python3 tools/build.py
"""

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GLYPHS_FILE = REPO / "kawara2.glyphs"
OTF_ROOT = REPO / "OnKawara-Regular.otf"
OTF_WWW = REPO / "www" / "OnKawara-Regular.otf"


def build():
    import glyphsLib
    import ufo2ft

    font = glyphsLib.GSFont(str(GLYPHS_FILE))
    master = font.masters[0]
    # old Glyphs Mini files sometimes store numbers as strings
    for attr in ("ascender", "capHeight", "descender", "xHeight"):
        setattr(master, attr, int(getattr(master, attr)))

    ufos = glyphsLib.to_ufos(font)
    otf = ufo2ft.compileOTF(ufos[0], removeOverlaps=True)
    otf.save(OTF_ROOT)
    shutil.copyfile(OTF_ROOT, OTF_WWW)

    gpos_pairs = 0
    if "GPOS" in otf:
        for lookup in otf["GPOS"].table.LookupList.Lookup:
            for st in lookup.SubTable:
                if hasattr(st, "PairSet") and st.PairSet:
                    gpos_pairs += sum(len(ps.PairValueRecord) for ps in st.PairSet)
                elif hasattr(st, "Class1Record"):
                    gpos_pairs += sum(len(c1.Class2Record) for c1 in st.Class1Record)
    print(f"built {OTF_ROOT.name}: {otf['maxp'].numGlyphs} glyphs, "
          f"{gpos_pairs} GPOS kern records -> ./ and www/")

    sys.path.insert(0, str(REPO / "tools"))
    from kawara_kerning import export_js
    export_js(REPO / "www" / "kerning.js")


if __name__ == "__main__":
    build()
