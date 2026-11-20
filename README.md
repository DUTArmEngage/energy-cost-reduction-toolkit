# energy-cost-reduction-toolkit

Design, simulation and implementation of an IoT-based Energy Cost Reduction Toolkit (ECRT): it monitors the aggregate electricity
use of a supply, calculates cost from Time-of-Use (ToU) tariffs and switches four appliance channels to shift flexible loads away
from expensive tariff periods. Full description: [`references/PROJECT_BRIEF.md`](references/PROJECT_BRIEF.md).

## Hardware (current design)

| Part | Role |
|---|---|
| Arduino Uno R3 (5 V logic) | Local controller: PZEM readings, keypad, LCD, four relay outputs. USB serial link to the Pi |
| Raspberry Pi 3B+ | Python: tariff, cost and scheduling; web dashboard; SQLite history. Wi-Fi built in |
| PZEM-004T V4 + 100 A CT | Single aggregate meter (voltage, current, power, energy), TTL serial |
| 12 V 4-channel relay module (Keyestudio MD0010, active-low) | Switches the 230 V coils of four contactors. The firmware drives IN1 to IN4 on D4 to D7 and its polarity is a setting (`RELAY_ACTIVE_LOW` in `firmware/arduino/include/pins.h`). On the bench the original module failed and one channel on IN1 is in use |
| 4 x 25 A 2xNO modular contactors | Mains switching (enclosure, not on the board) |
| 1602 I2C LCD, 4x4 keypad | Local user interface |
| K7805 SMPS (5 V 2 A) | Supplies the Pi from the 12 V rail |

Mains wiring and commissioning must be done by a qualified electrician. Develop and test with low-voltage loads first.

## Repository layout

```
references/          project brief and the Mantech quote (QUO156660)
diagrams/            block diagram, control and mains schematics, 3D layout and the interactive viewer (`make serve`)
  gen_diagrams.py       drawings and the net / part registry (net classes and colours are defined here)
  gen_3d.py, view3d.js  3D layout: modules as boxes at real sizes, wires routed flat on the board
  gen_index.py          builds index.html from the drawings
  gen_stripboard.py     stripboard layout (out of date: still the Pro Mini, see below)
firmware/
  arduino/             Uno firmware (PlatformIO): PZEM, relays, keypad, LCD, CSV link to the Pi. `make` lists the targets
  pi/                  placeholder uv project for the final Pi application
.scratch/
  arduino/             one test program per component, sharing the firmware's pin map
  pi/                  Streamlit dashboard reading the Uno over USB serial, with the .tar.gz and offline .deb build
```

## Status and open items

- **Firmware and dashboard:** the Uno firmware builds and its protocol logic is unit-tested. On the bench the dashboard has shown live
  PZEM readings from the Uno. The dashboard (`.scratch/pi`, version 0.1.6) no longer has a simulated data feed: it needs the Uno.
  The `.deb` is built for a Raspberry Pi on Debian 13 (arm64, Python 3.13) and installs offline. The final Pi application in
  `firmware/pi` is still a placeholder.
- The **stripboard layout is still for the Arduino Pro Mini** and no longer matches the Uno schematic. It needs redoing for the Uno
  (a larger board that connects through headers).
- The Mantech quote predates the Uno design. Not used now: Pro Mini, ESP8266, AMS1117. Still needed and not on the quote: the Uno,
  a USB A-to-B cable, a 12 V DC adapter, three more contactors (the quote has one) and a per-channel MCB.
- Check before building: relay module logic (the firmware setting must match the module), PZEM TX level, the K7805's 2 A against the Pi's 2.5 A rating. With only the PZEM TTL side wired and no mains on its L/N terminals the meter does not answer.
- `references/PROJECT_BRIEF.md` still mentions Node-RED. The design now uses a Python-served web dashboard instead.
