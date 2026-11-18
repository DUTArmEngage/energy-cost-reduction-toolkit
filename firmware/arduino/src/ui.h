#pragma once
// LCD 1602 (I2C) and 4x4 keypad.
//   1-4 toggle channel 1-4     A next page     B previous page     * all channels off
// Pages: 0 power and energy, 1 frequency, power factor and the four channels, 2 link status.
#include <stdint.h>

#include "ecrt_protocol.h"
#include "relays.h"

class Ui {
 public:
  void begin();
  // Handles at most one key press. Returns true if a relay changed (so the caller reports the new state at once).
  bool pollKeys(uint32_t now, Relays& relays);
  void draw(uint32_t now, const ecrt::Measurement& m, const Relays& relays, uint32_t lastHostMs, bool hostSeen);

 private:
  void toast(const char* text, uint32_t now);
  void print(uint8_t row, const char* text);  // pads to 16 characters
  uint8_t page_ = 0;
  uint32_t lastDraw_ = 0;
  uint32_t toastUntil_ = 0;
  char toast_[17] = {0};
};
