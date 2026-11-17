# .scratch

Working area for throwaway experiments and bench notes. Nothing here is part of the deliverable: anything that proves useful
should be moved into `firmware/` or `diagrams/` and cleaned up first.

Typical contents:

- Single-purpose test sketches (for example reading the PZEM, scanning the I2C bus, driving one relay) before they go into `firmware/arduino/`.
- Quick Python experiments for the Pi side (tariff maths, serial parsing, scheduling ideas).
- Bench measurements and notes (PZEM TX level, relay trigger behaviour, supply rails).

Rules of thumb:

- Keep one experiment per sub-folder, with a short note saying what it tests and what the result was.
- Do not put secrets, credentials or Wi-Fi details here: the folder is tracked by git.
- Mains is never connected for these tests: use safe low-voltage loads (see the project brief, section 7).
