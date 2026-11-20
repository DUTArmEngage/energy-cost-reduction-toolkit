#pragma once
// Timing and limits for the Uno firmware. Pin numbers are in pins.h.
#include <stdint.h>

constexpr uint32_t HOST_BAUD = 115200;          // USB serial to the Pi (the Pi side uses the same default)
constexpr uint32_t PZEM_BAUD = 9600;            // PZEM-004T V4 TTL serial
constexpr uint32_t REPORT_INTERVAL_MS = 1000;   // one measurement line to the Pi per second
// When the PZEM does not answer, one attempt blocks for 100 ms (the library's timeout). Retry only this often so the loop stays
// responsive; a line is still sent every REPORT_INTERVAL_MS, with the measurement fields empty.
constexpr uint32_t PZEM_RETRY_MS = 3000;
// Plausible range of a PZEM-004T V4 reading (100 A version, 80-260 V). A reply outside it is a corrupted frame that happened to
// pass the CRC (SoftwareSerial loses bits when an interrupt lands mid-byte) and is treated as "no answer".
constexpr float PZEM_V_MIN = 80.0f, PZEM_V_MAX = 280.0f;
constexpr float PZEM_A_MAX = 120.0f;
constexpr float PZEM_W_MAX = 30000.0f;
constexpr float PZEM_HZ_MIN = 45.0f, PZEM_HZ_MAX = 65.0f;
constexpr float PZEM_KWH_MAX = 9999.0f;

// Contactor protection: a channel will not change state again until it has been in its current state for this long, so a
// misbehaving scheduler (or a bouncing finger) cannot chatter a 25 A contactor. 0 disables it. "All off" ignores it.
constexpr uint32_t MIN_SWITCH_MS = 5000;

constexpr uint32_t LCD_REFRESH_MS = 250;
constexpr uint32_t TOAST_MS = 2000;             // how long a keypad message replaces the second LCD line
constexpr uint32_t HOST_FRESH_MS = 10000;       // the Pi link counts as alive if a command arrived within this time
