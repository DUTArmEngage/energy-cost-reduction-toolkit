# Build, flash and monitor helpers for the Uno test programs (one PlatformIO environment per program).
#
#   make                       list the programs and targets
#   make build-test_relay      compile one program
#   make flash-test_relay      upload one program
#   make monitor-test_relay    open the serial monitor (Ctrl+C to leave)
#   make run-test_relay        flash, then monitor
#   make build                 compile every program
#
# If PlatformIO picks the wrong serial port, name it:  make run-test_lcd PORT=/dev/ttyACM0
# For the other programs from the firmware folder use PlatformIO directly:  cd ../../firmware/arduino && pio run -t upload

PIO  ?= pio
PORT ?=

# Keep this list in step with the [env:...] sections of platformio.ini.
PROGRAMS := hello test_blinky test_serial_link test_i2c_scan test_lcd test_keypad test_relay test_pzem

UPLOAD_PORT  = $(if $(PORT),--upload-port $(PORT),)
MONITOR_PORT = $(if $(PORT),--port $(PORT),)

BUILD_TARGETS   := $(addprefix build-,$(PROGRAMS))
FLASH_TARGETS   := $(addprefix flash-,$(PROGRAMS))
MONITOR_TARGETS := $(addprefix monitor-,$(PROGRAMS))
RUN_TARGETS     := $(addprefix run-,$(PROGRAMS))

.DEFAULT_GOAL := help
.PHONY: help build clean devices $(BUILD_TARGETS) $(FLASH_TARGETS) $(MONITOR_TARGETS) $(RUN_TARGETS)

help:
	@echo "Programs: $(PROGRAMS)"
	@echo ""
	@echo "  make build-<program>     compile"
	@echo "  make flash-<program>     upload to the Uno"
	@echo "  make monitor-<program>   serial monitor (115200 baud)"
	@echo "  make run-<program>       flash, then monitor"
	@echo "  make build               compile every program"
	@echo "  make clean               remove build output"
	@echo "  make devices             list serial ports"
	@echo ""
	@echo "Add PORT=/dev/ttyACM0 if PlatformIO picks the wrong port."

build:
	$(PIO) run

$(BUILD_TARGETS): build-%:
	$(PIO) run -e $*

$(FLASH_TARGETS): flash-%:
	$(PIO) run -e $* -t upload $(UPLOAD_PORT)

$(MONITOR_TARGETS): monitor-%:
	$(PIO) device monitor -e $* $(MONITOR_PORT)

$(RUN_TARGETS): run-%: flash-%
	@$(MAKE) --no-print-directory monitor-$*

clean:
	$(PIO) run -t clean

devices:
	$(PIO) device list
