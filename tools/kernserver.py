#!/usr/bin/env python3
"""Local server for the kerning workbench.

    python3 tools/kernserver.py [port]     (default 8765)

Serves www/ and exposes:
    GET  /api/status    -> {"live": true}
    POST /api/kerning   -> saves kerning into kawara2.glyphs and rebuilds the OTF

Open http://localhost:8765/kern.html, tune pairs, hit Save — the .glyphs
source and both OTFs are updated in place. Ctrl+C to stop.
"""

import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build as build_mod
import kawara_kerning


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
        if self.path.startswith("/api/status"):
            return self._json(200, {"live": True})
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/kerning"):
            return self._json(404, {"error": "unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            kerning = payload.get("kerning", payload)
            known = set(kawara_kerning.glyph_widths())
            bad = sorted({g for l, rs in kerning.items() for g in (l, *rs) if g not in known})
            if bad:
                return self._json(400, {"error": f"unknown glyphs: {bad}"})
            pairs = kawara_kerning.write_kerning(kerning)
            build_mod.build()
            return self._json(200, {"ok": True, "pairs": pairs})
        except Exception as e:  # report the failure to the browser
            return self._json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        if any("/api/" in str(a) for a in args):
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = partial(Handler, directory=str(REPO / "www"))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"kerning workbench: http://localhost:{port}/kern.html   (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
