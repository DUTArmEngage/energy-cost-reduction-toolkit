#   make            list the targets
#   make build      compile for the Uno
#   make flash      compile and upload
#   make monitor    serial monitor at 115200 baud (Ctrl+C to leave)
#   make run        flash, then monitor
#   make test       run the logic tests on this computer (needs a C++ compiler)
#   make check      tests, then build
#   make clean      remove build output
#   make devices    list serial ports
#
# If PlatformIO picks the wrong serial port, name it:  make run PORT=/dev/ttyACM0

PIO  ?= pio
PORT ?=

# Only a real USB serial port counts. Without this PlatformIO falls back to /dev/ttyS0 (a motherboard port with nothing on it)
# and avrdude hangs or reports "programmer is not responding".
FOUND := $(firstword $(wildcard /dev/ttyACM* /dev/ttyUSB*))
USE_PORT = $(or $(PORT),$(FOUND))

UPLOAD_PORT  = --upload-port $(USE_PORT)
MONITOR_PORT = --port $(USE_PORT)

define need_port
	@test -n "$(USE_PORT)" || { echo ""; echo "No Uno found: there is no /dev/ttyACM* or /dev/ttyUSB* port."; \
	  echo "Check the USB cable (many are charge-only), try another port, then: lsusb ; sudo dmesg | tail"; \
	  echo "If the port has another name:  make $@ PORT=/dev/..."; echo ""; exit 1; }
	@echo "Using $(USE_PORT)"
endef

.DEFAULT_GOAL := help
.PHONY: help build flash monitor run test check clean devices

help:
	@sed -n '1,11p' Makefile | sed 's/^# \{0,1\}//'

build:
	$(PIO) run -e uno

flash:
	$(need_port)
	$(PIO) run -e uno -t upload $(UPLOAD_PORT)

monitor:
	$(need_port)
	$(PIO) device monitor -e uno $(MONITOR_PORT)

run: flash
	@$(MAKE) --no-print-directory monitor

test:
	$(PIO) test -e native

check: test build

clean:
	$(PIO) run -t clean

devices:
	$(PIO) device list
