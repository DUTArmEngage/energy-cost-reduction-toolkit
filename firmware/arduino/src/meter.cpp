#include "meter.h"

#include <Arduino.h>
#include <PZEM004Tv30.h>
#include <SoftwareSerial.h>

#include "config.h"
#include "pins.h"

static SoftwareSerial pzemSerial(PIN_PZEM_RX, PIN_PZEM_TX);
static PZEM004Tv30 pzem(pzemSerial);

void Meter::begin() { pzemSerial.begin(PZEM_BAUD); }

bool Meter::poll(uint32_t now) {
  if (!first_ && now - lastReport_ < REPORT_INTERVAL_MS) return false;
  bool retryDue = first_ || m_.valid || now - lastTry_ >= PZEM_RETRY_MS;
  first_ = false;
  lastReport_ = now;
  if (!retryDue) return true;  // meter is silent: report the empty line without blocking on another attempt
  lastTry_ = now;
  // The first call fetches every register in one exchange and the library caches them for 200 ms, so the rest cost nothing.
  // When the meter does not answer, stop after the first call: a failed read is not cached, so each further call would wait the
  // full 100 ms timeout again (six of them made the loop block for 600 ms every second).
  float v = pzem.voltage();
  if (isnan(v)) {
    m_.valid = false;
    return true;
  }
  float a = pzem.current(), w = pzem.power(), e = pzem.energy(), f = pzem.frequency(), pf = pzem.pf();
  bool ok = !(isnan(a) || isnan(w) || isnan(e) || isnan(f) || isnan(pf));
  m_.valid = ok;
  if (ok) {
    m_.volts = v;
    m_.amps = a;
    m_.watts = w;
    m_.kwh = e;
    m_.hz = f;
    m_.pf = pf;
  }
  return true;
}
