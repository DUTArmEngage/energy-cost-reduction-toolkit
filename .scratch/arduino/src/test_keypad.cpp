// Test: 4x4 keypad on D10-D13 (rows R1..R4) and A0-A3 (columns C1..C4). Prints each key press to the USB serial.
// Expected layout (standard thin-film 4x4): 1 2 3 A / 4 5 6 B / 7 8 9 C / * 0 # D. If keys come out wrong, the header order is
// different from the assumption: note what each key prints and fix the wiring or the keymap.
#include <Arduino.h>
#include <Keypad.h>

#include "pins.h"

const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'},
};
byte rowPins[ROWS] = {PIN_KP_ROW[0], PIN_KP_ROW[1], PIN_KP_ROW[2], PIN_KP_ROW[3]};
byte colPins[COLS] = {PIN_KP_COL[0], PIN_KP_COL[1], PIN_KP_COL[2], PIN_KP_COL[3]};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

void setup() {
  Serial.begin(115200);
  Serial.println(F("keypad test: press keys"));
}

void loop() {
  char key = keypad.getKey();
  if (key) {
    Serial.print(F("key: "));
    Serial.println(key);
  }
}
