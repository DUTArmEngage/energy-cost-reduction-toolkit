#pragma once
// Arduino Uno pin map: see diagrams/ecrt_schematic_control.png and firmware/README.md.
// D0/D1 are the USB serial link to the Pi: do not use them.

// PZEM-004T V4 TTL serial (SoftwareSerial, 9600 baud)
constexpr uint8_t PIN_PZEM_RX = 2;  // Uno receives, wired to the PZEM TX
constexpr uint8_t PIN_PZEM_TX = 3;  // Uno transmits, wired to the PZEM RX

// 4-channel relay module (MD0010): active-low, LOW = relay on, HIGH = relay off
constexpr uint8_t PIN_RELAY[4] = {4, 5, 6, 7};

// 4x4 keypad
constexpr uint8_t PIN_KP_ROW[4] = {10, 11, 12, 13};
// Columns C1..C4 are the keypad's physical columns. Bench test: the keypad connector's pins 7 and 8 are columns 4 and 3, so the
// last two column lines are crossed and C3 is on A3, C4 on A2.
constexpr uint8_t PIN_KP_COL[4] = {A0, A1, A3, A2};

// LCD 1602 I2C backpack on A4 (SDA) / A5 (SCL), address 0x27 is typical: confirm with an I2C scan
constexpr uint8_t LCD_I2C_ADDR = 0x27;

// D8, D9: spare
