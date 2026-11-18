# Firmware

Code that runs on the two controllers of the ECRT. Only a starter Uno project exists so far (it builds, but only sets up the relays and serial). This file records what each side must do and the pin map
from the control schematic (`diagrams/ecrt_schematic_control.png`), so the code and the hardware stay in step.

## Layout (planned)

```
firmware/
  arduino/ Arduino Uno project (PlatformIO): PZEM readings, keypad, LCD, relay outputs, USB serial to the Pi
  pi/      Raspberry Pi 3B+ (Python only, uv project): tariff and cost calculation, load scheduling, SQLite history, web dashboard
```

## Arduino Uno (`arduino/`)

5 V logic, ATmega328P. Powered at VIN from the 12 V supply.

| Pins | Function | Notes |
|---|---|---|
| D0 / D1 | USB serial to the Pi | Reserved: do not use for anything else |
| D2 (RX), D3 (TX) | PZEM-004T V4 TTL serial | SoftwareSerial, 9600 baud |
| D4, D5, D6, D7 | Relay module IN1 to IN4 | Active-low (MD0010): LOW = relay on, HIGH = off |
| D8, D9 | Spare | |
| D10, D11, D12, D13 | Keypad rows R1 to R4 | |
| A0, A1, A3, A2 | Keypad columns C1 to C4 | Analog pins used as digital I/O. Keypad connector pins 7 and 8 are columns 4 and 3 (found with `test_keypad`), so C3 is on A3 and C4 on A2 |
| SDA, SCL (header pins next to AREF, same as A4, A5) | LCD 1602 I2C backpack | Address 0x27 is typical: confirm with an I2C scan |

Behaviour to implement:

- Read voltage, current, active power and accumulated energy from the PZEM and send them to the Pi over USB serial.
- Switch each of the four relay channels on command from the Pi, and from the keypad.
- Show readings and channel states on the LCD.
- Set every relay pin HIGH (off) before configuring it as an output, so no channel clicks on at power-up.
- Speak the serial format for measurements and commands. A provisional CSV one is defined in `.scratch/pi/src/ecrt_pi_scratch/feed.py`: about once a second the Uno sends one line of ten numbers (volts, amps, watts, kWh, Hz, power factor, relays 1 to 4; no header and no field names, the order is fixed in code), and the Pi sends `R,channel,state`.

## Raspberry Pi (`pi/`)

Everything on the Pi is Python, managed with uv (`uv sync`, `uv run ecrt-pi`).

- Receive measurements from the Uno over USB serial and store them in SQLite.
- Configurable Time-of-Use tariff (peak, standard, off-peak) and cost calculation from the measured energy.
- Scheduling: shift flexible channels away from expensive periods, within user-defined operating requirements.
- Web dashboard served by Python (consumption, estimated cost, channel status, manual control).
- Keep baseline and managed runs separate so energy reduction and cost reduction can be compared (see the project brief, section 6).

## Open items

- The PZEM TX voltage level and the relay module's trigger behaviour should be confirmed on the bench before relying on them.
- The serial format (provisional CSV) is not final. The dashboard framework is Streamlit in the scratch project and not final either.
