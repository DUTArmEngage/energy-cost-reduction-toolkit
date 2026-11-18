#include "relays.h"

#include <Arduino.h>

#include "config.h"
#include "pins.h"

void Relays::begin() {
  for (uint8_t i = 0; i < ecrt::N_RELAYS; i++) {
    digitalWrite(PIN_RELAY[i], HIGH);
    pinMode(PIN_RELAY[i], OUTPUT);
  }
}

uint32_t Relays::waitMs(uint8_t ch, uint32_t now) const {
  if (!everChanged_[ch]) return 0;
  uint32_t held = now - changed_[ch];
  return held >= MIN_SWITCH_MS ? 0 : MIN_SWITCH_MS - held;
}

Relays::Result Relays::set(uint8_t ch, bool on, uint32_t now) {
  if (ch >= ecrt::N_RELAYS) return Result::Unchanged;
  if (on_[ch] == on) return Result::Unchanged;
  if (waitMs(ch, now) > 0) return Result::TooSoon;
  digitalWrite(PIN_RELAY[ch], on ? LOW : HIGH);
  on_[ch] = on;
  changed_[ch] = now;
  everChanged_[ch] = true;
  return Result::Applied;
}

void Relays::allOff() {
  for (uint8_t ch = 0; ch < ecrt::N_RELAYS; ch++) {
    digitalWrite(PIN_RELAY[ch], HIGH);
    if (on_[ch]) {
      on_[ch] = false;
      changed_[ch] = millis();
      everChanged_[ch] = true;
    }
  }
}
