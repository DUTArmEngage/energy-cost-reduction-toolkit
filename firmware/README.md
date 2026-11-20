# Firmware

Code that runs on the two controllers of the ECRT. The Uno firmware is written: it builds, its protocol code is unit-tested, and on the bench the dashboard has shown live PZEM readings from it. The Pi side is a Streamlit dashboard in `.scratch/pi` (the final application in `pi/` is still a placeholder). This file records what each side does and the pin map
from the control schematic (`diagrams/ecrt_schematic_control.png`), so the code and the hardware stay in step.

## Layout

```
firmware/
  arduino/ Arduino Uno project (PlatformIO): PZEM readings, keypad, LCD, relay outputs, USB serial to the Pi
  pi/      Raspberry Pi 3B+ (Python only, uv project): placeholder for the final application (tariff and cost, scheduling, SQLite history, web dashboard)
```

## Arduino Uno (`arduino/`)

5 V logic, ATmega328P. Powered at VIN from the 12 V supply.

| Pins | Function | Notes |
|---|---|---|
| D0 / D1 | USB serial to the Pi | Reserved: do not use for anything else |
| D2 (RX), D3 (TX) | PZEM-004T V4 TTL serial | SoftwareSerial, 9600 baud |
| D4, D5, D6, D7 | Relay module IN1 to IN4 | Polarity is `RELAY_ACTIVE_LOW` in `pins.h`: the MD0010 is active-low, single-channel signal / voltage / ground modules are usually active-high. Only IN1 (D4) is fitted on the bench |
| D8, D9 | Spare | |
| D10, D11, D12, D13 | Keypad rows R1 to R4 | |
| A0, A1, A3, A2 | Keypad columns C1 to C4 | Analog pins used as digital I/O. Keypad connector pins 7 and 8 are columns 4 and 3 (found with `test_keypad`), so C3 is on A3 and C4 on A2 |
| SDA, SCL (header pins next to AREF, same as A4, A5) | LCD 1602 I2C backpack | Address 0x27 is typical: confirm with an I2C scan |

### What the firmware does

- Reads voltage, current, power, energy, frequency and power factor from the PZEM once a second and sends one CSV line to the Pi: `volts,amps,watts,kWh,Hz,pf,r1,r2,r3,r4` (no header, six empty fields when the PZEM does not answer). The line is also sent straight after any relay change.
- Switches a relay on `R,channel,state` from the Pi (channel 1 to 4, state 1 = on) and from the keypad. Nothing else is ever printed on the USB serial.
- Keypad: `1` to `4` toggle that channel, `A` / `B` next / previous LCD page, `*` all off.
- LCD pages: power and energy; frequency, power factor and the four channel states (`+` on, `-` off); meter and Pi link status. Keypad actions show a short message on the second line.
- Contactor protection: a channel will not change again until it has held its state for `MIN_SWITCH_MS` (5 s, in `include/config.h`). A command that arrives too soon is ignored, and the next report line carries the real state. "All off" ignores the limit.
- Every relay pin is set to its off level before it becomes an output, so no channel clicks on at power-up. Relays stay in their last state if the Pi goes quiet: there is no watchdog yet (see open items).
- Meter robustness: when the PZEM is silent the Uno retries every 3 s instead of blocking the loop on every read, and a reply outside a plausible range (`PZEM_*` limits in `config.h`) counts as no answer, because SoftwareSerial can corrupt a frame that still passes the CRC.

### Code layout

```
arduino/
  include/pins.h, config.h      pin map; baud rates, report interval, switching limit
  lib/ecrt_protocol/            line format and parsing, no Arduino dependencies (unit-tested on the PC)
  src/main.cpp                  loop: Pi commands, keypad, meter, report, LCD
  src/relays.*  meter.*  ui.*   relay outputs, PZEM reads, LCD and keypad
  test/test_protocol/           pio test -e native
```

Build and flash from `arduino/` with `make` (it lists the targets and refuses to flash when no `/dev/ttyACM*` or `/dev/ttyUSB*` port exists), or `pio run -t upload`. Libraries (PZEM-004T-v30, LiquidCrystal_I2C, Keypad) are fetched by PlatformIO. The component test programs are in `.scratch/arduino` and use the same `pins.h`.

## Raspberry Pi (`pi/`)

Everything on the Pi is Python, managed with uv (`uv sync`, `uv run ecrt-pi`).

- Receive measurements from the Uno over USB serial and store them in SQLite.
- Configurable Time-of-Use tariff (peak, standard, off-peak) and cost calculation from the measured energy.
- Scheduling: shift flexible channels away from expensive periods, within user-defined operating requirements.
- Web dashboard served by Python (consumption, estimated cost, channel status, manual control).
- Keep baseline and managed runs separate so energy reduction and cost reduction can be compared (see the project brief, section 6).

## Open items

- Confirmed on the bench: PZEM readings reach the dashboard through the Uno. Not recorded yet: keypad, LCD pages and the relay timing with a real contactor. Bring them up in the order of the scratch tests, with the mains side disconnected for the relay and a qualified person present for the PZEM.
- SoftwareSerial (the PZEM link) disables interrupts while it receives, so a command byte arriving from the Pi in that ~25 ms window each second can be lost. The Pi should confirm the state in the next report line and resend if it did not change.
- There is no fail-safe if the Pi stops sending: the relays keep their last state. Decide what the loads should do (stay, or switch off after a timeout) before real use.
- The PZEM TX voltage level should be confirmed on the bench. The relay polarity is now a setting: check it matches your module (a relay that is on when it should be off needs `RELAY_ACTIVE_LOW` flipped).
- The serial format (provisional CSV) is not final. The dashboard framework is Streamlit in the scratch project (serial only: the mock feed was removed) and not final either.
