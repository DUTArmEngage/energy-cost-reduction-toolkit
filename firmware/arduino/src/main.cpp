#include <Arduino.h>

#include "pins.h"

void setup() {
  // Relays are active-low: drive the pin HIGH (off) before making it an output so no channel clicks on at power-up.
  for (uint8_t pin : PIN_RELAY) {
    digitalWrite(pin, HIGH);
    pinMode(pin, OUTPUT);
  }

  Serial.begin(115200);  // USB serial link to the Pi
}

void loop() {
  // TODO: read the PZEM, handle the keypad and LCD, switch relays on command from the Pi.
}
