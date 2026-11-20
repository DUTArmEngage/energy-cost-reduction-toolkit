# ECRT Pi scratch project: run the UI, build a .tar.gz and a .deb.
#
#   make run                      dashboard (opens SERIAL_PORT at start; or connect from the page)
#   make tar                      dist/<name>-<version>.tar.gz   (source distribution)
#   make deb                      dist/<name>_<version>_arm64.deb  (self-contained: every dependency inside, installs offline)
#   make dist                     both
#   make package                  everything: locked sync, lint, tests, clean build, tar + deb, checksums
#   make clean                    remove dist/ and build/
#
# TARGET=pi64 (default) builds for 64-bit Raspberry Pi OS Trixie (Debian 13: arm64, Python 3.13). TARGET=pi64-bookworm is the older
# Debian 12 image (Python 3.11). TARGET=host builds for this machine, so the package can be tried here:  make deb TARGET=host
# Check the Pi first with:  dpkg --print-architecture && python3 --version

NAME    := $(shell sed -n 's/^name = "\(.*\)"/\1/p' pyproject.toml | head -1)
VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
PYNAME  := $(subst -,_,$(NAME))

UV          ?= uv
PORT        ?= 8501
SERIAL_PORT ?= /dev/ttyACM0
BAUD        ?= 115200

# What the .deb is built for: its architecture, the Python version whose compiled packages it bundles, and the uv platform name.
TARGET ?= pi64
ifeq ($(TARGET),pi64)
  DEB_ARCH    := arm64
  PYVER       := 3.13
  UV_PLATFORM := aarch64-manylinux_2_40
else ifeq ($(TARGET),pi64-bookworm)
  DEB_ARCH    := arm64
  PYVER       := 3.11
  UV_PLATFORM := aarch64-manylinux_2_36
else ifeq ($(TARGET),host)
  DEB_ARCH    := $(shell dpkg --print-architecture)
  PYVER       := $(shell /usr/bin/python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
  UV_PLATFORM := x86_64-manylinux_2_36
else
  $(error TARGET must be pi64, pi64-bookworm or host)
endif
PYNEXT := $(shell echo $(PYVER) | awk -F. '{print $$1 "." $$2 + 1}')

DIST    := dist
TARBALL := $(DIST)/$(PYNAME)-$(VERSION).tar.gz
WHEEL   := $(DIST)/$(PYNAME)-$(VERSION)-py3-none-any.whl
DEB     := $(DIST)/$(NAME)_$(VERSION)_$(DEB_ARCH).deb
DEB_DIR := build/deb/$(NAME)_$(VERSION)_$(DEB_ARCH)
APP_DIR := /usr/lib/$(NAME)

.DEFAULT_GOAL := help
.PHONY: help sync lint test check run tar wheel deb dist checksums package clean distclean

help:
	@echo "  make run          dashboard, opens SERIAL_PORT at start (PORT=$(PORT))"
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
	ECRT_PORT=$(SERIAL_PORT) ECRT_BAUD=$(BAUD) $(UV) run ecrt-ui --server.port $(PORT)

tar:
	$(UV) build --sdist --out-dir $(DIST)
	@echo "built $(TARBALL)"

wheel:
	$(UV) build --wheel --out-dir $(DIST)

# The deb is self-contained: the pinned dependencies from uv.lock are installed for the target platform at build time and shipped
# inside it, compiled to bytecode for the target Python, so nothing is downloaded or built when it is installed. It also holds a
# launcher, a systemd service and its settings file.
deb: wheel
	rm -rf build/deb build/site
	mkdir -p build/site $(DEB_DIR)/DEBIAN $(DEB_DIR)$(APP_DIR)/lib $(DEB_DIR)/usr/bin $(DEB_DIR)/lib/systemd/system $(DEB_DIR)/etc/default
	$(UV) export --frozen --no-dev --no-hashes --no-emit-project -o build/requirements.txt
	$(UV) pip install --target build/site --python-platform $(UV_PLATFORM) --python-version $(PYVER) --no-deps --no-build \
		-r build/requirements.txt $(WHEEL)
	tar -C build/site --exclude=./bin --exclude=tests --exclude=test -cf - . | tar -C $(DEB_DIR)$(APP_DIR)/lib -xf -
	$(UV) run --no-project --python $(PYVER) python -m compileall -q -j 0 -d $(APP_DIR)/lib $(DEB_DIR)$(APP_DIR)/lib
	sed -e 's/@NAME@/$(NAME)/g' -e 's/@VERSION@/$(VERSION)/g' -e 's/@ARCH@/$(DEB_ARCH)/g' -e 's/@PYVER@/$(PYVER)/g' \
		-e 's/@PYNEXT@/$(PYNEXT)/g' packaging/deb/control.in > $(DEB_DIR)/DEBIAN/control
	for f in postinst prerm postrm; do \
		sed -e 's/@NAME@/$(NAME)/g' -e 's/@PYVER@/$(PYVER)/g' packaging/deb/$$f > $(DEB_DIR)/DEBIAN/$$f; chmod 0755 $(DEB_DIR)/DEBIAN/$$f; done
	sed 's/@NAME@/$(NAME)/g' packaging/deb/launcher > $(DEB_DIR)/usr/bin/ecrt-ui
	chmod 0755 $(DEB_DIR)/usr/bin/ecrt-ui
	sed 's/@NAME@/$(NAME)/g' packaging/deb/service.in > $(DEB_DIR)/lib/systemd/system/$(NAME).service
	sed 's/@NAME@/$(NAME)/g' packaging/deb/default.in > $(DEB_DIR)/etc/default/$(NAME)
	echo /etc/default/$(NAME) > $(DEB_DIR)/DEBIAN/conffiles
	chmod -R go-w $(DEB_DIR)
	echo "Installed-Size: $$(du -sk $(DEB_DIR) | cut -f1)" >> $(DEB_DIR)/DEBIAN/control
	dpkg-deb -Zxz --build --root-owner-group $(DEB_DIR) $(DEB)

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
