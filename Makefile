PY = python3

help:
	@echo "make setup   - install the font toolchain (fontTools, glyphsLib, ufo2ft)"
	@echo "make build   - compile kawara2.glyphs -> OnKawara-Regular.otf (+ www copy, kerning.js)"
	@echo "make kern    - build, then serve the kerning workbench at http://localhost:8765/kern.html"
	@echo "make apply FILE=kerning.json - apply a workbench JSON export to kawara2.glyphs and rebuild"
	@echo "make audit   - report case-inconsistent kerning pairs"

setup:
	$(PY) -m pip install -r requirements.txt

build:
	$(PY) tools/build.py

kern: build
	$(PY) tools/kernserver.py

apply:
	$(PY) tools/kawara_kerning.py apply $(FILE)
	$(PY) tools/build.py

audit:
	$(PY) tools/kawara_kerning.py audit

.PHONY: help setup build kern apply audit
