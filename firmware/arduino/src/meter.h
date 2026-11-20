#pragma once
// PZEM-004T V4 energy meter over SoftwareSerial.
#include <stdint.h>

#include "ecrt_protocol.h"

class Meter {
 public:
  void begin();
  // Reads the meter once per REPORT_INTERVAL_MS. Returns true when a new sample (valid or not) is available in latest().
  // A read takes up to a few hundred ms when the meter does not answer, so everything else must tolerate that.
  bool poll(uint32_t now);
  const ecrt::Measurement& latest() const { return m_; }

 private:
  ecrt::Measurement m_;
  uint32_t lastReport_ = 0;
  uint32_t lastTry_ = 0;
  bool first_ = true;
};
