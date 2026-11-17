#include <Arduino.h>

// Scratch sketch: throwaway experiments for the Uno. Move anything useful into firmware/arduino.

void setup() {
  Serial.begin(115200);
  Serial.println(F("scratch sketch running"));
}

void loop() {
  Serial.println(millis());
  delay(1000);
}
