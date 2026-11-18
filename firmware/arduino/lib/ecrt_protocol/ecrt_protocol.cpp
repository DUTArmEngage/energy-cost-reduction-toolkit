#include "ecrt_protocol.h"

#include <math.h>

namespace ecrt {

size_t formatFixed(char* out, size_t cap, float v, uint8_t decimals) {
  if (cap == 0) return 0;
  out[0] = '\0';
  if (isnan(v) || isinf(v) || decimals > 4) return 0;
  bool neg = v < 0;
  if (neg) v = -v;
  uint32_t scale = 1;
  for (uint8_t i = 0; i < decimals; i++) scale *= 10;
  float scaled = v * scale;
  if (scaled > 4.0e9f) return 0;
  uint32_t n = (uint32_t)scaled;
  if (scaled - (float)n >= 0.5f) n++;  // round half up without adding 0.5 first: float32 cannot hold 9999999.5
  if (n == 0) neg = false;
  char tmp[12];
  uint8_t t = 0;
  uint32_t ip = n / scale, fp = n % scale;
  do {
    tmp[t++] = char('0' + ip % 10);
    ip /= 10;
  } while (ip && t < sizeof tmp);
  size_t need = (neg ? 1 : 0) + t + (decimals ? 1 + decimals : 0) + 1;
  if (need > cap) return 0;
  size_t p = 0;
  if (neg) out[p++] = '-';
  while (t) out[p++] = tmp[--t];
  if (decimals) {
    out[p++] = '.';
    for (uint8_t i = decimals; i > 0; i--) {
      uint32_t d = 1;
      for (uint8_t k = 1; k < i; k++) d *= 10;
      out[p++] = char('0' + (fp / d) % 10);
    }
  }
  out[p] = '\0';
  return p;
}

size_t formatLine(char* out, size_t cap, const Measurement& m, const bool relays[N_RELAYS]) {
  static const uint8_t DECIMALS[6] = {1, 3, 1, 3, 1, 2};
  const float values[6] = {m.volts, m.amps, m.watts, m.kwh, m.hz, m.pf};
  size_t p = 0;
  for (uint8_t i = 0; i < 6; i++) {
    if (m.valid) {
      size_t n = formatFixed(out + p, cap - p, values[i], DECIMALS[i]);
      if (n == 0) return 0;
      p += n;
    }
    if (p + 1 >= cap) return 0;
    out[p++] = ',';
  }
  for (uint8_t i = 0; i < N_RELAYS; i++) {
    if (p + 2 >= cap) return 0;
    out[p++] = relays[i] ? '1' : '0';
    out[p++] = i + 1 < N_RELAYS ? ',' : '\n';
  }
  if (p >= cap) return 0;
  out[p] = '\0';
  return p;
}

bool parseCommand(const char* line, uint8_t& channel0, bool& on) {
  // exactly: R,<1-4>,<0|1>
  if (line[0] != 'R' || line[1] != ',' || line[3] != ',' || line[5] != '\0') return false;
  if (line[2] < '1' || line[2] > '0' + N_RELAYS) return false;
  if (line[4] != '0' && line[4] != '1') return false;
  channel0 = uint8_t(line[2] - '1');
  on = line[4] == '1';
  return true;
}

bool LineReader::feed(char c) {
  if (ready_) {  // the previous line was consumed by the caller
    len_ = 0;
    ready_ = false;
  }
  if (c == '\r') return false;
  if (c == '\n') {
    bool had = len_ > 0 && !overflow_;
    if (overflow_) dropped_++;
    overflow_ = false;
    if (!had) {
      len_ = 0;
      return false;
    }
    buf_[len_] = '\0';
    ready_ = true;
    return true;
  }
  if (overflow_) return false;
  if (len_ + 1 >= CAP) {
    overflow_ = true;
    len_ = 0;
    return false;
  }
  buf_[len_++] = c;
  return false;
}

}  // namespace ecrt
