// Test: USB serial link to the Pi (D0/D1 through the Uno's USB port).
// Sends a heartbeat every second and answers what it receives:
//   "ping"  -> "pong"
//   others  -> "echo: <line>"
#include <Arduino.h>

static String line;
static unsigned long lastBeat = 0;
static unsigned long beats = 0;

void setup() {
  Serial.begin(115200);
  Serial.println(F("serial link test: type 'ping' or any text"));
}

void loop() {
  if (millis() - lastBeat >= 1000) {
    lastBeat = millis();
    Serial.print(F("heartbeat "));
    Serial.println(++beats);
  }

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length()) {
        if (line == "ping") {
          Serial.println(F("pong"));
        } else {
          Serial.print(F("echo: "));
          Serial.println(line);
        }
        line = "";
      }
    } else if (line.length() < 80) {
      line += c;
    }
  }
}
