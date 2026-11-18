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
  if (!first_ && now - last_ < REPORT_INTERVAL_MS) return false;
  first_ = false;
  last_ = now;
  // The library fetches all registers in one exchange and caches them for 200 ms, so these calls cost one reply.
  float v = pzem.voltage(), a = pzem.current(), w = pzem.power(), e = pzem.energy(), f = pzem.frequency(), pf = pzem.pf();
  bool ok = !(isnan(v) || isnan(a) || isnan(w) || isnan(e) || isnan(f) || isnan(pf));
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
