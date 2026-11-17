# ECRT Pi scratch project: run the UI, build a .tar.gz and a .deb.
#
#   make run                      dashboard with the mock feed
#   make run-serial               dashboard reading the Uno (SERIAL_PORT=/dev/ttyACM0)
#   make tar                      dist/<name>-<version>.tar.gz   (source distribution)
#   make deb                      dist/<name>_<version>_all.deb  (installs into its own venv on the Pi)
#   make dist                     both
#   make package                  everything: locked sync, lint, tests, clean build, tar + deb, checksums
#   make clean                    remove dist/ and build/

NAME    := $(shell sed -n 's/^name = "\(.*\)"/\1/p' pyproject.toml | head -1)
VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
PYNAME  := $(subst -,_,$(NAME))

UV          ?= uv
PORT        ?= 8501
SERIAL_PORT ?= /dev/ttyACM0
BAUD        ?= 115200

DIST    := dist
TARBALL := $(DIST)/$(PYNAME)-$(VERSION).tar.gz
WHEEL   := $(DIST)/$(PYNAME)-$(VERSION)-py3-none-any.whl
DEB     := $(DIST)/$(NAME)_$(VERSION)_all.deb
DEB_DIR := build/deb/$(NAME)_$(VERSION)_all
APP_DIR := /usr/lib/$(NAME)

.DEFAULT_GOAL := help
.PHONY: help sync lint test check run run-serial tar wheel deb dist checksums package clean distclean

help:
	@echo "  make run          dashboard with the mock feed (PORT=$(PORT))"
	@echo "  make run-serial   dashboard reading the Uno (SERIAL_PORT=$(SERIAL_PORT) BAUD=$(BAUD))"
	@echo "  make tar          $(TARBALL)"
	@echo "  make deb          $(DEB)"
	@echo "  make dist         tar + deb"
	@echo "  make check        lint + tests"
	@echo "  make package      everything: sync --locked, check, clean build, tar + deb, SHA256SUMS"
	@echo "  make clean        remove dist/ and build/   (distclean also removes .venv)"

sync:
	$(UV) sync

lint:
	$(UV) run ruff check .

test:
	$(UV) run pytest -q

check: lint test

run: sync
	ECRT_FEED=mock $(UV) run ecrt-ui --server.port $(PORT)

run-serial: sync
	ECRT_FEED=serial ECRT_PORT=$(SERIAL_PORT) ECRT_BAUD=$(BAUD) $(UV) run ecrt-ui --server.port $(PORT)

tar:
	$(UV) build --sdist --out-dir $(DIST)
	@echo "built $(TARBALL)"

wheel:
	$(UV) build --wheel --out-dir $(DIST)

# The deb holds the wheel, a launcher and a systemd service; postinst builds a venv, pip-installs the wheel and its dependencies,
# then enables and starts the service.
deb: wheel
	rm -rf $(DEB_DIR)
	mkdir -p $(DEB_DIR)/DEBIAN $(DEB_DIR)$(APP_DIR) $(DEB_DIR)/usr/bin
	cp $(WHEEL) $(DEB_DIR)$(APP_DIR)/
	sed -e 's/@NAME@/$(NAME)/g' -e 's/@VERSION@/$(VERSION)/g' packaging/deb/control.in > $(DEB_DIR)/DEBIAN/control
	for f in postinst prerm postrm; do sed 's/@NAME@/$(NAME)/g' packaging/deb/$$f > $(DEB_DIR)/DEBIAN/$$f; chmod 0755 $(DEB_DIR)/DEBIAN/$$f; done
	sed 's/@NAME@/$(NAME)/g' packaging/deb/launcher > $(DEB_DIR)/usr/bin/ecrt-ui
	chmod 0755 $(DEB_DIR)/usr/bin/ecrt-ui
	mkdir -p $(DEB_DIR)/lib/systemd/system $(DEB_DIR)/etc/default
	sed 's/@NAME@/$(NAME)/g' packaging/deb/service.in > $(DEB_DIR)/lib/systemd/system/$(NAME).service
	sed 's/@NAME@/$(NAME)/g' packaging/deb/default.in > $(DEB_DIR)/etc/default/$(NAME)
	echo /etc/default/$(NAME) > $(DEB_DIR)/DEBIAN/conffiles
	chmod -R go-w $(DEB_DIR)
	dpkg-deb --build --root-owner-group $(DEB_DIR) $(DEB)

dist: tar deb

checksums:
	cd $(DIST) && sha256sum $(notdir $(TARBALL)) $(notdir $(DEB)) > SHA256SUMS
	@cat $(DIST)/SHA256SUMS

# Everything: lint, tests, clean build, tar + deb, checksums.
package:
	$(UV) sync --locked
	$(MAKE) check
	$(MAKE) clean
	$(MAKE) dist
	$(MAKE) checksums

clean:
	rm -rf $(DIST) build

distclean: clean
	rm -rf .venv
