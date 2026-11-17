// Test: PZEM-004T V4 energy meter on D2 (Uno RX, PZEM TX) and D3 (Uno TX, PZEM RX), SoftwareSerial at 9600 baud.
// Prints voltage, current, power, energy, frequency and power factor every 2 s. A read error means no reply from the module:
// check the 5 V on its TTL side, the TX/RX crossing, and that the mains side is powered (qualified person only).
#include <Arduino.h>
#include <PZEM004Tv30.h>
#include <SoftwareSerial.h>

#include "pins.h"

SoftwareSerial pzemSerial(PIN_PZEM_RX, PIN_PZEM_TX);
PZEM004Tv30 pzem(pzemSerial);

static void show(const __FlashStringHelper* label, float value, const __FlashStringHelper* unit, uint8_t decimals) {
  Serial.print(label);
  if (isnan(value)) {
    Serial.println(F("read error"));
  } else {
    Serial.print(value, decimals);
    Serial.println(unit);
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("PZEM test"));
}

void loop() {
  show(F("voltage:   "), pzem.voltage(), F(" V"), 1);
  show(F("current:   "), pzem.current(), F(" A"), 3);
  show(F("power:     "), pzem.power(), F(" W"), 1);
  show(F("energy:    "), pzem.energy(), F(" kWh"), 3);
  show(F("frequency: "), pzem.frequency(), F(" Hz"), 1);
  show(F("pf:        "), pzem.pf(), F(""), 2);
  Serial.println(F("--"));
  delay(2000);
}
