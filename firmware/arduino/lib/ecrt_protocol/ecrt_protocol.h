#pragma once
// The serial protocol between the Uno and the Raspberry Pi, with no Arduino dependencies so it can be unit-tested on a PC
// (`pio test -e native`). The format is defined in .scratch/pi/src/ecrt_pi_scratch/feed.py:
//   Uno -> Pi, about 1 Hz: volts,amps,watts,kWh,Hz,pf,r1,r2,r3,r4        e.g.  230.1,1.234,283.9,12.345,50.0,0.98,0,1,0,0
//                          the six measurements are empty when the PZEM did not answer:   ,,,,,,0,1,0,0
//   Pi -> Uno, on demand:  R,channel,state                                e.g.  R,2,1   (channel 1..4, state 1 = on, 0 = off)
// No header and no field names are ever sent.
#include <stddef.h>
#include <stdint.h>

namespace ecrt {

constexpr uint8_t N_RELAYS = 4;

struct Measurement {
  bool valid = false;  // false = the PZEM did not answer (or answered with an error)
  float volts = 0, amps = 0, watts = 0, kwh = 0, hz = 0, pf = 0;
};

// Write v with a fixed number of decimals ("12.345") and a terminating NUL. Returns the length, or 0 if v is NaN / infinite /
// too large or the buffer is too small (the buffer then holds an empty string). No printf: AVR's printf has no float support.
size_t formatFixed(char* out, size_t cap, float v, uint8_t decimals);

// One report line including the trailing '\n'. Returns its length, or 0 if the buffer is too small.
size_t formatLine(char* out, size_t cap, const Measurement& m, const bool relays[N_RELAYS]);

// Parse "R,channel,state". On success channel0 is 0..3 and on is the requested state.
bool parseCommand(const char* line, uint8_t& channel0, bool& on);

// Collects characters into lines without blocking. '\r' is ignored, an over-long line is dropped whole.
class LineReader {
 public:
  // Returns true when a complete, non-empty line is ready: read it with line() before the next feed().
  bool feed(char c);
  const char* line() const { return buf_; }
  uint16_t dropped() const { return dropped_; }  // over-long lines discarded so far

 private:
  static constexpr uint8_t CAP = 24;
  char buf_[CAP] = {0};
  uint8_t len_ = 0;
  bool overflow_ = false;
  bool ready_ = false;
  uint16_t dropped_ = 0;
};

}  // namespace ecrt
