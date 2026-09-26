"""Shared fixtures for the tools tests.

The tests never write to the real kawara2.glyphs: every write goes to a
copy in a temporary directory.
"""

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

MASTER = "4646E42D-B7EF-4922-8014-FEFC5A6E791A"

# a cut-down .glyphs source in the same plist dialect as kawara2.glyphs:
# a plain outline (I), a curved one (O), a component glyph (i), a dotted
# name (I.alt) and a kerning block
FIXTURE = f"""{{
familyName = "On Kawara";
glyphs = (
{{
glyphname = I;
lastChange = "2019-06-26 19:22:04 +0000";
layers = (
{{
layerId = "{MASTER}";
name = Regular;
paths = (
{{
closed = 1;
nodes = (
"70 0 LINE",
"177 0 LINE",
"177 700 LINE",
"70 700 LINE"
);
}}
);
width = 247;
}}
);
unicode = 0049;
}},
{{
glyphname = O;
lastChange = "2019-06-26 19:22:04 +0000";
layers = (
{{
layerId = "{MASTER}";
name = Regular;
paths = (
{{
closed = 1;
nodes = (
"100 350 OFFCURVE",
"200 0 OFFCURVE",
"350 0 CURVE SMOOTH",
"500 0 OFFCURVE",
"600 350 OFFCURVE",
"600 350.5 CURVE",
"300 700 LINE"
);
}}
);
width = 700;
}}
);
unicode = 004F;
}},
{{
glyphname = i;
lastChange = "2019-06-26 19:21:58 +0000";
layers = (
{{
components = (
{{
name = I;
transform = "{{1, 0, 0, 1, 0, 10}}";
}}
);
layerId = "{MASTER}";
name = Regular;
width = 247;
}}
);
unicode = 0069;
}},
{{
glyphname = I.alt;
lastChange = "2019-06-26 19:22:04 +0000";
layers = (
{{
layerId = "{MASTER}";
name = Regular;
width = 300;
}}
);
}}
);
kerning = {{
"{MASTER}" = {{
I = {{
I.alt = 5;
O = "-20";
}};
I.alt = {{
O = "-7";
}};
O = {{
I = 0;
}};
}};
}};
unitsPerEm = 1000;
}}
"""


class TempDir:
    """A temporary directory that is removed on cleanup."""

    def __init__(self):
        self.path = Path(tempfile.mkdtemp(prefix="kawara-test-"))

    def cleanup(self):
        shutil.rmtree(self.path, ignore_errors=True)


def fixture_file(tmp):
    """Write FIXTURE into tmp and return its path."""
    path = Path(tmp) / "fixture.glyphs"
    path.write_text(FIXTURE)
    return path


REAL_GLYPHS = REPO / "kawara2.glyphs"
_REAL_BYTES = REAL_GLYPHS.read_bytes()


def assert_real_source_untouched():
    """Fail loudly if kawara2.glyphs changed during the run (a test wrote
    to it, or it was saved from the workbench meanwhile)."""
    if REAL_GLYPHS.read_bytes() != _REAL_BYTES:
        raise AssertionError("kawara2.glyphs changed while the tests ran")


def load_generated_js(path, var):
    """The JSON payload of a generated `window.VAR = {...};` script."""
    import json
    text = Path(path).read_text()
    prefix = f"window.{var} = "
    return json.loads(text[text.index(prefix) + len(prefix):].rstrip().rstrip(";"))
