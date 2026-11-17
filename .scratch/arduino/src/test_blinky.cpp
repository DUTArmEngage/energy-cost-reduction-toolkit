// Test: blinky. Blinks the Uno's onboard LED (LED_BUILTIN, D13) at 1 Hz and prints each change to the USB serial.
// Checks the board, the toolchain, the upload and the serial link with no wiring at all.
// NOTE: D13 is also keypad row R4 in the ECRT wiring. Unplug the keypad for this test, or accept a brief signal on that row.
#include <Arduino.h>

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
  Serial.println(F("blinky running"));
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println(F("LED on"));
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println(F("LED off"));
  delay(500);
}
