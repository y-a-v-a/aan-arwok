# Uses .venv/ if it exists (created by `make setup`), system python3 otherwise.
PY = python3
VPY = $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

help:
	@echo "make setup   - create .venv and install the font toolchain (fontTools, glyphsLib, ufo2ft)"
	@echo "make build   - compile kawara2.glyphs -> OnKawara-Regular.otf (+ www copy, kerning.js)"
	@echo "make kern    - build, then serve the kerning workbench (kern.html) + glyph editor (glyphed.html) at http://localhost:8765/"
	@echo "make apply FILE=kerning.json - apply a workbench JSON export to kawara2.glyphs and rebuild"
	@echo "make apply-glyph FILE=glyph-X.json - apply a glyph-editor JSON export to kawara2.glyphs and rebuild"
	@echo "make audit   - report case-inconsistent kerning pairs"
	@echo "make gaps    - regenerate KERNING_CHECK.md (pairs with no kerning)"
	@echo "make test    - run the unit and end-to-end tests (never writes kawara2.glyphs)"

setup:
	$(PY) -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

build:
	$(VPY) tools/build.py

kern: build
	$(VPY) tools/kernserver.py

apply:
	$(VPY) tools/kawara_kerning.py apply $(FILE)
	$(VPY) tools/build.py

apply-glyph:
	$(VPY) tools/kawara_glyphs.py apply $(FILE)
	$(VPY) tools/build.py

audit:
	$(VPY) tools/kawara_kerning.py audit

gaps:
	$(VPY) tools/kawara_kerning.py gaps

test:
	$(VPY) -m unittest discover -s tests -t tests

.PHONY: help setup build kern apply apply-glyph audit gaps test
