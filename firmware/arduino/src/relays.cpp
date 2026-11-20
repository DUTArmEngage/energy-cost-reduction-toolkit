#include "relays.h"

#include <Arduino.h>

#include "config.h"
#include "pins.h"

// Pin level for a relay state, whatever the module's polarity.
static uint8_t level(bool on) { return (on == RELAY_ACTIVE_LOW) ? LOW : HIGH; }

void Relays::begin() {
  for (uint8_t i = 0; i < ecrt::N_RELAYS; i++) {
    digitalWrite(PIN_RELAY[i], level(false));
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
  digitalWrite(PIN_RELAY[ch], level(on));
  on_[ch] = on;
  changed_[ch] = now;
  everChanged_[ch] = true;
  return Result::Applied;
}

void Relays::allOff() {
  for (uint8_t ch = 0; ch < ecrt::N_RELAYS; ch++) {
    digitalWrite(PIN_RELAY[ch], level(false));
    if (on_[ch]) {
      on_[ch] = false;
      changed_[ch] = millis();
      everChanged_[ch] = true;
    }
  }
}
