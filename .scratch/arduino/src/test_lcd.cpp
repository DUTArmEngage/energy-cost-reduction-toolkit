// Test: LCD 1602 with I2C backpack on the SDA/SCL header pins (next to AREF, same as A4/A5). Shows a title and an uptime counter.
// If the screen stays blank, run test_i2c_scan to find the address, then adjust the potentiometer on the backpack (contrast).
#include <Arduino.h>
#include <LiquidCrystal_I2C.h>

#include "pins.h"

LiquidCrystal_I2C lcd(LCD_I2C_ADDR, 16, 2);

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print(F("ECRT LCD test"));
  Serial.println(F("LCD test running"));
}

void loop() {
  lcd.setCursor(0, 1);
  lcd.print(F("up "));
  lcd.print(millis() / 1000);
  lcd.print(F(" s     "));
  delay(250);
}
