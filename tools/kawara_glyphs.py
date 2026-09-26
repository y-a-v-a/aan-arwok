#!/usr/bin/env python3
"""Read and write glyph outlines inside kawara2.glyphs.

Same approach as kawara_kerning.py: the .glyphs file is a NeXTSTEP-style
plist, and this module edits one glyph's `paths`/`width` block as text so
the rest of the file stays byte-for-byte identical (nice for git diffs).

CLI:
    python3 tools/kawara_glyphs.py export [-o www/glyphdata.js]
    python3 tools/kawara_glyphs.py apply glyph.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from kawara_kerning import GLYPH_TO_CHAR, GLYPHS_FILE

NODE_RE = re.compile(r'"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (LINE|CURVE|OFFCURVE)( SMOOTH)?"')
NODE_TYPES = {"LINE", "CURVE", "OFFCURVE"}


def _glyph_blocks(text):
    """Yield (name, start, end) for each glyph block, brace-matched."""
    for m in re.finditer(r"^glyphname = ([A-Za-z0-9._]+);$", text, re.M):
        start = text.rindex("{", 0, m.start())
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield m.group(1), start, i + 1
                    break


def _paren_span(block, open_idx):
    """Span of a (...) group: (open_idx, index just past the closing ');')."""
    depth = 0
    for i in range(open_idx, len(block)):
        if block[i] == "(":
            depth += 1
        elif block[i] == ")":
            depth -= 1
            if depth == 0:
                j = i + 1
                if j < len(block) and block[j] == ";":
                    j += 1
                return open_idx, j
    raise ValueError("unbalanced parentheses")


def _parse_block(name, block):
    glyph = {"name": name, "width": None, "unicode": None,
             "paths": [], "components": []}
    wm = re.search(r"^width = (\d+);$", block, re.M)
    if wm:
        glyph["width"] = int(wm.group(1))
    um = re.search(r"^unicode = ([0-9A-F]{4});$", block, re.M)
    if um:
        glyph["unicode"] = um.group(1)

    cm = re.search(r"^components = \(", block, re.M)
    if cm:
        s, e = _paren_span(block, cm.end() - 1)
        for comp in re.finditer(
                r'name = ([A-Za-z0-9._]+);\n(?:transform = "\{([^}]*)\}";\n)?',
                block[s:e]):
            t = [float(v) for v in comp.group(2).split(",")] if comp.group(2) \
                else [1, 0, 0, 1, 0, 0]
            glyph["components"].append({"name": comp.group(1), "transform": t})

    pm = re.search(r"^paths = \(", block, re.M)
    if pm:
        s, e = _paren_span(block, pm.end() - 1)
        for pb in re.finditer(r"\{\n(?:closed = (\d);\n)?nodes = \(([^)]*)\);",
                              block[s:e]):
            nodes = [[_num(x), _num(y), t, bool(sm)]
                     for x, y, t, sm in NODE_RE.findall(pb.group(2))]
            closed = int(pb.group(1)) if pb.group(1) is not None else 0
            glyph["paths"].append({"closed": closed, "nodes": nodes})
    return glyph


def read_glyphs(path=GLYPHS_FILE):
    """Parse every glyph. Returns (order, {name: glyph dict})."""
    text = path.read_text()
    order, glyphs = [], {}
    for name, s, e in _glyph_blocks(text):
        order.append(name)
        glyphs[name] = _parse_block(name, text[s:e])
    return order, glyphs


def _num(v):
    """Coordinates as int when integral, float otherwise ('395.794')."""
    f = float(v)
    return int(f) if f.is_integer() else f


def _fmt(v):
    """A coordinate as Glyphs writes it: at most 3 decimals, no trailing zeros.

    ('{:g}' would round to 6 significant digits, so 1234.567 -> 1234.57.)
    """
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def _serialize_paths(paths):
    chunks = []
    for p in paths:
        lines = ",\n".join(
            f'"{_fmt(x)} {_fmt(y)} {t}{" SMOOTH" if sm else ""}"'
            for x, y, t, sm in p["nodes"])
        closed = int(p.get("closed", 1))
        chunks.append(f"{{\nclosed = {closed};\nnodes = (\n" + lines + "\n);\n}")
    return "paths = (\n" + ",\n".join(chunks) + "\n);"


def validate_paths(paths):
    """Raise ValueError unless paths is a list of {nodes: [[x,y,type,smooth]]}."""
    if not isinstance(paths, list) or not paths:
        raise ValueError("paths must be a non-empty list")
    for p in paths:
        nodes = p.get("nodes") if isinstance(p, dict) else None
        if not isinstance(nodes, list) or len(nodes) < 3:
            raise ValueError("each path needs a nodes list of 3+ nodes")
        for n in nodes:
            if (not isinstance(n, list) or len(n) != 4
                    or not all(isinstance(v, (int, float)) for v in n[:2])
                    or n[2] not in NODE_TYPES or not isinstance(n[3], bool)):
                raise ValueError(f"bad node {n!r} — want [x, y, type, smooth]")


def write_glyph(name, width=None, paths=None, path=GLYPHS_FILE):
    """Replace one glyph's paths and/or width in place. Returns the glyph."""
    text = path.read_text()
    for gname, s, e in _glyph_blocks(text):
        if gname == name:
            break
    else:
        raise ValueError(f"glyph {name!r} not found")
    block = text[s:e]

    if paths is not None:
        validate_paths(paths)
        new_paths = _serialize_paths(paths)
        pm = re.search(r"^paths = \(", block, re.M)
        if pm:
            ps, pe = _paren_span(block, pm.end() - 1)
            block = block[:pm.start()] + new_paths + block[pe:]
        else:
            wm = re.search(r"^width = ", block, re.M)
            if not wm:
                raise ValueError(f"glyph {name!r} has no layer width to anchor paths to")
            block = block[:wm.start()] + new_paths + "\n" + block[wm.start():]
    if width is not None:
        if int(width) < 0:
            raise ValueError(f"width must be >= 0, got {width}")
        block = re.sub(r"^width = \d+;$", f"width = {int(width)};",
                       block, count=1, flags=re.M)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S +0000")
    block = re.sub(r'^lastChange = "[^"]*";$', f'lastChange = "{stamp}";',
                   block, count=1, flags=re.M)
    path.write_text(text[:s] + block + text[e:])
    return _parse_block(name, block)


def payload():
    """Everything the editor page needs, as one JSON-able dict."""
    order, glyphs = read_glyphs()
    return {
        "familyName": "On Kawara",
        "upm": 1000,
        "metrics": {"ascender": 800, "capHeight": 700,
                    "xHeight": 500, "descender": -200},
        "glyphToChar": GLYPH_TO_CHAR,
        "order": order,
        "glyphs": glyphs,
    }


def export_js(out_path):
    data = payload()
    out_path.write_text(
        "// generated by tools/kawara_glyphs.py export — do not edit by hand\n"
        "window.KAWARA_GLYPHS = " + json.dumps(data, indent=1, sort_keys=True) + ";\n"
    )
    n = len(data["order"])
    print(f"exported {n} glyph outlines -> {out_path}")


def apply_json(json_path):
    raw = json.loads(Path(json_path).read_text())
    edits = raw if isinstance(raw, list) else [raw]
    for edit in edits:
        g = write_glyph(edit["name"], width=edit.get("width"),
                        paths=edit.get("paths"))
        print(f"wrote {g['name']}: width {g['width']}, "
              f"{sum(len(p['nodes']) for p in g['paths'])} nodes")
    print("run `make build` to bake into the OTF")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_exp = sub.add_parser("export", help="write outlines to www/glyphdata.js")
    p_exp.add_argument("-o", "--out", default=str(REPO / "www" / "glyphdata.js"))
    p_app = sub.add_parser("apply", help="apply a glyph JSON (editor export) to the .glyphs source")
    p_app.add_argument("json_file")
    args = ap.parse_args()
    if args.cmd == "export":
        export_js(Path(args.out))
    elif args.cmd == "apply":
        apply_json(args.json_file)


if __name__ == "__main__":
    main()
