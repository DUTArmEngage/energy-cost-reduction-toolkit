#pragma once
// Timing and limits for the Uno firmware. Pin numbers are in pins.h.
#include <stdint.h>

constexpr uint32_t HOST_BAUD = 115200;          // USB serial to the Pi (the Pi side uses the same default)
constexpr uint32_t PZEM_BAUD = 9600;            // PZEM-004T V4 TTL serial
constexpr uint32_t REPORT_INTERVAL_MS = 1000;   // one measurement line to the Pi per second

// Contactor protection: a channel will not change state again until it has been in its current state for this long, so a
// misbehaving scheduler (or a bouncing finger) cannot chatter a 25 A contactor. 0 disables it. "All off" ignores it.
constexpr uint32_t MIN_SWITCH_MS = 5000;

constexpr uint32_t LCD_REFRESH_MS = 250;
constexpr uint32_t TOAST_MS = 2000;             // how long a keypad message replaces the second LCD line
constexpr uint32_t HOST_FRESH_MS = 10000;       // the Pi link counts as alive if a command arrived within this time
