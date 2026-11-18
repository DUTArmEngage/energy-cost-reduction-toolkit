# iot-energy-cost-reduction-load-scheduling-system

Design, simulation and implementation of an IoT-based Energy Cost Reduction Toolkit (ECRT): it monitors the aggregate electricity
use of a supply, calculates cost from Time-of-Use (ToU) tariffs and switches four appliance channels to shift flexible loads away
from expensive tariff periods. Full description: [`references/PROJECT_BRIEF.md`](references/PROJECT_BRIEF.md).

## Hardware (current design)

| Part | Role |
|---|---|
| Arduino Uno R3 (5 V logic) | Local controller: PZEM readings, keypad, LCD, four relay outputs. USB serial link to the Pi |
| Raspberry Pi 3B+ | Python: tariff, cost and scheduling; web dashboard; SQLite history. Wi-Fi built in |
| PZEM-004T V4 + 100 A CT | Single aggregate meter (voltage, current, power, energy), TTL serial |
| 12 V 4-channel relay module (Keyestudio MD0010, active-low) | Switches the 230 V coils of four contactors |
| 4 x 25 A 2xNO modular contactors | Mains switching (enclosure, not on the board) |
| 1602 I2C LCD, 4x4 keypad | Local user interface |
| K7805 SMPS (5 V 2 A) | Supplies the Pi from the 12 V rail |

Mains wiring and commissioning must be done by a qualified electrician. Develop and test with low-voltage loads first.

## Repository layout

```
references/        project brief and the Mantech quote (QUO156660)
diagrams/
  gen_diagrams.py     block diagram + control and mains schematics
  gen_stripboard.py   stripboard layout for the low-voltage motherboard
```

## Status and open items

- The **stripboard layout is still for the Arduino Pro Mini** and no longer matches the Uno schematic. It needs redoing for the Uno
  (a larger board that connects through headers).
- The Mantech quote predates the Uno design. Not used now: Pro Mini, ESP8266, AMS1117. Still needed and not on the quote: the Uno,
  a USB A-to-B cable, a 12 V DC adapter, three more contactors (the quote has one) and a per-channel MCB.
- Check before building: relay module header order and logic (active-low), PZEM TX level, the K7805's 2 A against the Pi's 2.5 A rating.
- `references/PROJECT_BRIEF.md` still mentions Node-RED. The design now uses a Python-served web dashboard instead.
