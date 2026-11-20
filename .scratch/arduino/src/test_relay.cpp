// Test: relay module inputs on D4-D7 (only IN1 = D4 is fitted at the moment). Polarity comes from RELAY_ACTIVE_LOW in pins.h.
// Switches each channel on for one second in turn, then all four together. KEEP MAINS DISCONNECTED: listen for the clicks and
// watch the LEDs on the module. Each state change is also printed to the USB serial.
#include <Arduino.h>

#include "pins.h"

static void setRelay(uint8_t ch, bool on) {
  digitalWrite(PIN_RELAY[ch], (on == RELAY_ACTIVE_LOW) ? LOW : HIGH);
  Serial.print(F("relay "));
  Serial.print(ch + 1);
  Serial.println(on ? F(" ON") : F(" OFF"));
}

void setup() {
  // Drive the off level before making the pin an output so no channel clicks on at power-up.
  for (uint8_t pin : PIN_RELAY) {
    digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW);
    pinMode(pin, OUTPUT);
  }
  Serial.begin(115200);
  Serial.println(F("relay test: all channels start OFF"));
  delay(1000);
}

void loop() {
  for (uint8_t ch = 0; ch < 4; ch++) {
    setRelay(ch, true);
    delay(1000);
    setRelay(ch, false);
    delay(500);
  }
  Serial.println(F("all on"));
  for (uint8_t ch = 0; ch < 4; ch++) setRelay(ch, true);
  delay(1500);
  for (uint8_t ch = 0; ch < 4; ch++) setRelay(ch, false);
  Serial.println(F("--"));
  delay(2000);
}
