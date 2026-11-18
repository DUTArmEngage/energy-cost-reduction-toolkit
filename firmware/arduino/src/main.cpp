// ECRT Uno firmware: PZEM energy meter, four relay channels, 4x4 keypad, 1602 LCD, CSV link to the Raspberry Pi.
//
// Every second (and straight after a relay changes) the Uno sends one line to the Pi:  volts,amps,watts,kWh,Hz,pf,r1,r2,r3,r4
// The Pi sends  R,channel,state  to switch a channel. See lib/ecrt_protocol/ecrt_protocol.h and firmware/README.md.
// Nothing else is ever printed on the USB serial, so the Pi can treat every line as data.
#include <Arduino.h>

#include "config.h"
#include "ecrt_protocol.h"
#include "meter.h"
#include "relays.h"
#include "ui.h"

static Relays relays;
static Meter meter;
static Ui ui;
static ecrt::LineReader reader;
static uint32_t lastHostMs = 0;
static bool hostSeen = false;

static void report() {
  char line[64];
  size_t n = ecrt::formatLine(line, sizeof line, meter.latest(), relays.states());
  if (n) Serial.write(line, n);
}

void setup() {
  relays.begin();  // first: nothing may click on at power-up
  Serial.begin(HOST_BAUD);
  ui.begin();
  meter.begin();
}

void loop() {
  uint32_t now = millis();
  bool changed = false;

  while (Serial.available() > 0) {
    if (!reader.feed((char)Serial.read())) continue;
    uint8_t ch;
    bool on;
    if (!ecrt::parseCommand(reader.line(), ch, on)) continue;  // not ours: ignore silently
    lastHostMs = now;
    hostSeen = true;
    changed |= relays.set(ch, on, now) == Relays::Result::Applied;
  }

  changed |= ui.pollKeys(now, relays);

  if (meter.poll(now) || changed) report();  // changed: the Pi sees the new relay state without waiting for the next second

  ui.draw(millis(), meter.latest(), relays, lastHostMs, hostSeen);
}
