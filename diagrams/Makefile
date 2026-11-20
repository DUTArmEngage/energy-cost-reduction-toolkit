# Regenerate the drawings and view them in the interactive index.
#
#   make               list the targets
#   make serve         build index.html, start a local server and open it in the browser (Ctrl+C to stop)
#   make index         build index.html (also regenerates the block diagram and both schematic sheets)
#   make diagrams      block diagram + control and mains schematics only
#   make all           everything
#
# Options:  make serve PORT=9000      use another port
#           make serve NO_OPEN=1      do not open the browser

PYTHON ?= python3
PORT   ?= 8000
URL     = http://localhost:$(PORT)/index.html
OPEN   := $(shell command -v xdg-open 2>/dev/null || command -v open 2>/dev/null)

.DEFAULT_GOAL := help
.PHONY: help all diagrams index serve clean

help:
	@echo "  make serve        build index.html, start a local server and open the browser"
	@echo "  make index        build index.html (also redraws the block diagram and schematics)"
	@echo "  make diagrams     block diagram + control and mains schematics"
	@echo "  make all          everything"
	@echo "  make clean        remove generated PNG, SVG, PDF and index.html"
	@echo ""
	@echo "Options: PORT=$(PORT)   NO_OPEN=1 to skip opening the browser"

all: diagrams index

diagrams:
	$(PYTHON) gen_diagrams.py


index:
	$(PYTHON) gen_index.py

serve: index
	@echo "Serving $(CURDIR) at $(URL)  (Ctrl+C to stop)"
	@$(if $(or $(NO_OPEN),$(if $(OPEN),,1)),echo "Open $(URL) in your browser.",(sleep 1; $(OPEN) $(URL) >/dev/null 2>&1) &)
	@$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory $(CURDIR)

clean:
	rm -f ecrt_*.png ecrt_*.svg ecrt_*.pdf*.png*.pdf index.html
