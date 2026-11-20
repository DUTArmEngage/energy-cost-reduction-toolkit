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

UPLOAD_PORT  = $(if $(PORT),--upload-port $(PORT),)
MONITOR_PORT = $(if $(PORT),--port $(PORT),)

.DEFAULT_GOAL := help
.PHONY: help build flash monitor run test check clean devices

help:
	@sed -n '2,12p' Makefile | sed 's/^# \{0,1\}//'

build:
	$(PIO) run -e uno

flash:
	$(PIO) run -e uno -t upload $(UPLOAD_PORT)

monitor:
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
