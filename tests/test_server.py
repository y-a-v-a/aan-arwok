"""End-to-end tests for tools/kernserver.py.

Runs the real server as a subprocess inside a temporary copy of tools/,
www/ and kawara2.glyphs, so saves and OTF rebuilds happen in the copy.
"""

import json
import shutil
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

from helpers import REPO, TempDir, assert_real_source_untouched, load_generated_js

import kawara_glyphs
import kawara_kerning


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TempDir()
        root = cls.tmp.path
        shutil.copytree(REPO / "tools", root / "tools",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO / "www", root / "www")
        shutil.copyfile(REPO / "kawara2.glyphs", root / "kawara2.glyphs")
        cls.glyphs_file = root / "kawara2.glyphs"
        cls.otf = root / "OnKawara-Regular.otf"

        cls.port = free_port()
        # a file, not a pipe: nobody reads the log, and a full pipe would
        # block the server mid-rebuild
        cls.log = open(root / "server.log", "wb")
        cls.proc = subprocess.Popen(
            [sys.executable, str(root / "tools" / "kernserver.py"), str(cls.port)],
            cwd=root, stdout=cls.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 15
        while True:
            try:
                cls.get("/api/status")
                break
            except OSError:
                if cls.proc.poll() is not None or time.time() > deadline:
                    log = (root / "server.log").read_text()
                    cls.tearDownClass()
                    raise RuntimeError("kernserver did not start:\n" + log)
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.log.close()
        cls.tmp.cleanup()
        assert_real_source_untouched()

    # ---------- http helpers ----------
    @classmethod
    def request(cls, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{cls.port}{path}", data=data,
                                     method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.headers, e.read()

    @classmethod
    def get(cls, path):
        return cls.request(path)

    def api(self, path, body=None, raw=None):
        code, _, payload = self.request(path, body, raw)
        return code, json.loads(payload)

    # ---------- read-only endpoints ----------
    def test_status(self):
        self.assertEqual(self.api("/api/status"), (200, {"live": True}))
        self.assertEqual(self.api("/api/status?t=1"), (200, {"live": True}))

    def test_glyphs_payload(self):
        code, data = self.api("/api/glyphs")
        self.assertEqual(code, 200)
        self.assertEqual(data["upm"], 1000)
        self.assertIn("A", data["glyphs"])
        self.assertEqual(data["glyphs"]["A"]["name"], "A")

    def test_serves_the_workbench_pages_uncached(self):
        for page in ("kern.html", "glyphed.html", "workbench.css", "kerning.js"):
            with self.subTest(page=page):
                code, headers, body = self.get("/" + page)
                self.assertEqual(code, 200)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertTrue(body)
        self.assertEqual(self.get("/nope.html")[0], 404)

    # ---------- bad requests ----------
    def test_rejects_bad_posts_without_touching_the_source(self):
        before = self.glyphs_file.read_bytes()
        cases = [
            ("/api/kerning", b"{not json", 400, None),
            ("/api/kerning", b"[1, 2]", 400, "expected a JSON object"),
            ("/api/kerning", json.dumps({"kerning": {"A": {"Bogus": -5}}}).encode(), 400, "Bogus"),
            ("/api/glyph", json.dumps({"width": 5}).encode(), 400, "name"),
            ("/api/glyph", json.dumps({"name": "Nope", "width": 5}).encode(), 400, "not found"),
            ("/api/glyph", json.dumps({"name": "A", "width": -1}).encode(), 400, ">= 0"),
            ("/api/glyph", json.dumps({"name": "A", "paths": [{"nodes": []}]}).encode(), 400, "3+ nodes"),
            ("/api/glyphs", b"{}", 404, "unknown endpoint"),   # GET-only
            ("/api/elsewhere", b"{}", 404, "unknown endpoint"),
        ]
        for path, raw, code, msg in cases:
            with self.subTest(path=path, raw=raw):
                got, data = self.api(path, raw=raw)
                self.assertEqual(got, code, data)
                if msg:
                    self.assertIn(msg, data["error"])
        self.assertEqual(self.glyphs_file.read_bytes(), before)

    # ---------- saves (rebuild the OTF in the copy) ----------
    def test_kerning_save_writes_the_source_and_rebuilds(self):
        _, kern = kawara_kerning.read_kerning(self.glyphs_file)
        kern["A"]["V"] = kern["A"].get("V", 0) - 7
        kern.setdefault("Z", {})["Z"] = 13
        n = sum(len(rs) for rs in kern.values())
        stamp = self.otf.stat().st_mtime if self.otf.exists() else 0

        code, data = self.api("/api/kerning", {"kerning": kern})
        self.assertEqual((code, data), (200, {"ok": True, "pairs": n}))
        self.assertEqual(kawara_kerning.read_kerning(self.glyphs_file)[1], kern)
        self.assertGreater(self.otf.stat().st_mtime, stamp)
        exported = load_generated_js(self.tmp.path / "www" / "kerning.js", "KAWARA")
        self.assertEqual(exported["kerning"], kern)

    def test_glyph_save_writes_the_source_and_rebuilds(self):
        _, glyphs = kawara_glyphs.read_glyphs(self.glyphs_file)
        paths = glyphs["I"]["paths"]
        paths[0]["nodes"][0][0] += 3
        code, data = self.api("/api/glyph", {"name": "I", "width": 251, "paths": paths})
        self.assertEqual(code, 200, data)
        self.assertEqual((data["glyph"]["width"], data["glyph"]["paths"]), (251, paths))

        code, served = self.api("/api/glyphs")
        self.assertEqual(served["glyphs"]["I"]["width"], 251)
        self.assertEqual(served["glyphs"]["I"]["paths"], paths)
        self.assertTrue(self.otf.exists())
        self.assertTrue((self.tmp.path / "www" / "OnKawara-Regular.otf").exists())


if __name__ == "__main__":
    unittest.main()
