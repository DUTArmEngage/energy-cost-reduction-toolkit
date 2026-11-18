#include "ui.h"

#include <Arduino.h>
#include <Keypad.h>
#include <LiquidCrystal_I2C.h>
#include <string.h>

#include "config.h"
#include "pins.h"

static const char KEYS[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'},
};
static byte rowPins[4] = {PIN_KP_ROW[0], PIN_KP_ROW[1], PIN_KP_ROW[2], PIN_KP_ROW[3]};
static byte colPins[4] = {PIN_KP_COL[0], PIN_KP_COL[1], PIN_KP_COL[2], PIN_KP_COL[3]};
static Keypad keypad(makeKeymap(KEYS), rowPins, colPins, 4, 4);
static LiquidCrystal_I2C lcd(LCD_I2C_ADDR, 16, 2);

static const uint8_t PAGES = 3;

void Ui::begin() {
  lcd.init();
  lcd.backlight();
  print(0, "ECRT");
  print(1, "starting");
}

void Ui::print(uint8_t row, const char* text) {
  char line[17];
  uint8_t n = 0;
  while (n < 16 && text[n]) {
    line[n] = text[n];
    n++;
  }
  while (n < 16) line[n++] = ' ';
  line[16] = '\0';
  lcd.setCursor(0, row);
  lcd.print(line);
}

void Ui::toast(const char* text, uint32_t now) {
  strncpy(toast_, text, 16);
  toast_[16] = '\0';
  toastUntil_ = now + TOAST_MS;
}

bool Ui::pollKeys(uint32_t now, Relays& relays) {
  char k = keypad.getKey();
  if (!k) return false;
  if (k >= '1' && k <= '4') {
    uint8_t ch = k - '1';
    char msg[17];
    switch (relays.toggle(ch, now)) {
      case Relays::Result::Applied:
        snprintf(msg, sizeof msg, "CH%d %s", ch + 1, relays.on(ch) ? "ON" : "OFF");
        toast(msg, now);
        return true;
      case Relays::Result::TooSoon:
        snprintf(msg, sizeof msg, "CH%d wait %lus", ch + 1, (unsigned long)((relays.waitMs(ch, now) + 999) / 1000));
        toast(msg, now);
        return false;
      default:
        return false;
    }
  }
  if (k == '*') {
    bool any = false;
    for (uint8_t i = 0; i < ecrt::N_RELAYS; i++) any |= relays.on(i);
    relays.allOff();
    toast("All off", now);
    return any;
  }
  if (k == 'A') page_ = (page_ + 1) % PAGES;
  if (k == 'B') page_ = (page_ + PAGES - 1) % PAGES;
  lastDraw_ = 0;  // redraw straight away
  return false;
}

void Ui::draw(uint32_t now, const ecrt::Measurement& m, const Relays& relays, uint32_t lastHostMs, bool hostSeen) {
  if (lastDraw_ != 0 && now - lastDraw_ < LCD_REFRESH_MS) return;
  lastDraw_ = now ? now : 1;
  char a[24], b[24], num[12];
  a[0] = b[0] = '\0';
  auto cat = [](char* dst, const char* s) { strncat(dst, s, 23 - strlen(dst)); };
  auto fixed = [&](char* dst, float v, uint8_t d) {
    ecrt::formatFixed(num, sizeof num, v, d);
    cat(dst, num);
  };
  if (page_ == 0) {
    if (!m.valid) {
      cat(a, "PZEM: no reply");
      cat(b, "check meter");
    } else {
      fixed(a, m.volts, 1);
      cat(a, "V ");
      fixed(a, m.amps, 3);
      cat(a, "A");
      fixed(b, m.watts, 1);
      cat(b, "W ");
      fixed(b, m.kwh, 3);
      cat(b, "kWh");
    }
  } else if (page_ == 1) {
    if (m.valid) {
      fixed(a, m.hz, 1);
      cat(a, "Hz  PF ");
      fixed(a, m.pf, 2);
    } else {
      cat(a, "no meter data");
    }
    for (uint8_t i = 0; i < ecrt::N_RELAYS; i++) {
      char c[5] = {char('1' + i), ':', relays.on(i) ? '+' : '-', ' ', '\0'};
      cat(b, c);
    }
  } else {
    cat(a, m.valid ? "PZEM: ok" : "PZEM: no reply");
    if (!hostSeen) {
      cat(b, "Pi: no command");
    } else {
      cat(b, "Pi: ");
      bool fresh = now - lastHostMs < HOST_FRESH_MS;
      cat(b, fresh ? "linked" : "silent");
    }
  }
  print(0, a);
  if (toastUntil_ && (int32_t)(now - toastUntil_) < 0) {
    print(1, toast_);
  } else {
    toastUntil_ = 0;
    print(1, b);
  }
}
