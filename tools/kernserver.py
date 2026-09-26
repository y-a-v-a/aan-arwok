#!/usr/bin/env python3
"""Local server for the kerning workbench.

    python3 tools/kernserver.py [port]     (default 8765)

Serves www/ and exposes:
    GET  /api/status    -> {"live": true}
    GET  /api/glyphs    -> glyph outlines parsed fresh from kawara2.glyphs
    POST /api/kerning   -> saves kerning into kawara2.glyphs and rebuilds the OTF
    POST /api/glyph     -> saves one glyph's paths/width and rebuilds the OTF

Open http://localhost:8765/kern.html (kerning) or /glyphed.html (outlines),
edit, hit Save — the .glyphs source and both OTFs are updated in place.
Ctrl+C to stop.
"""

import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build as build_mod
import kawara_glyphs
import kawara_kerning

# saves rewrite kawara2.glyphs and rebuild the OTFs; two at once (a double
# click on Save) would interleave those writes
SAVE_LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/status":
            return self._json(200, {"live": True})
        if route == "/api/glyphs":
            try:
                return self._json(200, kawara_glyphs.payload())
            except Exception as e:
                return self._json(500, {"error": str(e)})
        super().do_GET()

    def do_POST(self):
        route = urlsplit(self.path).path
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("expected a JSON object")
            if route == "/api/kerning":
                kerning = payload.get("kerning", payload)
                bad = kawara_kerning.unknown_glyphs(kerning)
                if bad:
                    return self._json(400, {"error": f"unknown glyphs: {bad}"})
                with SAVE_LOCK:
                    pairs = kawara_kerning.write_kerning(kerning)
                    build_mod.build()
                return self._json(200, {"ok": True, "pairs": pairs})
            if route == "/api/glyph":
                with SAVE_LOCK:
                    glyph = kawara_glyphs.write_glyph(
                        payload["name"], width=payload.get("width"),
                        paths=payload.get("paths"))
                    build_mod.build()
                return self._json(200, {"ok": True, "glyph": glyph})
            return self._json(404, {"error": "unknown endpoint"})
        except (ValueError, KeyError) as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:  # report the failure to the browser
            return self._json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        if any("/api/" in str(a) for a in args):
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = partial(Handler, directory=str(REPO / "www"))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"kerning workbench: http://localhost:{port}/kern.html")
    print(f"glyph editor:      http://localhost:{port}/glyphed.html   (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
