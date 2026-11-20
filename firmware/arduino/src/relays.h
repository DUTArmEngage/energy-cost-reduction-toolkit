#pragma once
// The four relay channels (polarity set by RELAY_ACTIVE_LOW in pins.h), with a minimum time between changes.
#include <stdint.h>

#include "ecrt_protocol.h"

class Relays {
 public:
  void begin();  // drives every pin to the off level before making it an output, so nothing clicks on at power-up

  enum class Result : uint8_t { Applied, Unchanged, TooSoon };
  Result set(uint8_t channel0, bool on, uint32_t now);
  Result toggle(uint8_t channel0, uint32_t now) { return set(channel0, !on_[channel0], now); }
  void allOff();  // ignores the minimum time

  bool on(uint8_t channel0) const { return on_[channel0]; }
  const bool* states() const { return on_; }
  uint32_t waitMs(uint8_t channel0, uint32_t now) const;  // how long until this channel may change again

 private:
  bool on_[ecrt::N_RELAYS] = {false, false, false, false};
  uint32_t changed_[ecrt::N_RELAYS] = {0, 0, 0, 0};
  bool everChanged_[ecrt::N_RELAYS] = {false, false, false, false};
};
