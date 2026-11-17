// Test: I2C bus scan on A4 (SDA) / A5 (SCL). The LCD backpack is usually at 0x27 or 0x3F.
#include <Arduino.h>
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Serial.println(F("I2C scan (7-bit addresses), repeats every 5 s"));
}

void loop() {
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print(F("found device at 0x"));
      if (addr < 16) Serial.print('0');
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (!found) Serial.println(F("no I2C devices found: check SDA/SCL wiring and the backpack's 5 V and GND"));
  Serial.println(F("--"));
  delay(5000);
}
