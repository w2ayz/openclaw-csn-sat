---
name: csn-sat
description: "Control the CSN S.A.T. antenna rotator/satellite tracker: position, point AZ/EL, track a satellite, park, stop, simulate."
homepage: https://github.com/w2ayz/openclaw-csn-sat
metadata:
  {
    "openclaw":
      {
        "emoji": "📡",
        "os": ["linux", "darwin"],
        "requires": { "bins": ["python3"] },
        "primaryEnv": "CSN_SAT_HOST",
      },
  }
---

# CSN S.A.T. Antenna Tracker

Controls a CSN Technologies S.A.T. (Self-contained Antenna Tracker) on the LAN.
The box drives a Yaesu G-5400/5500/5600 rotator and an Icom rig, and has its
own satellite tracker. Use this skill for antenna/rotator position, pointing,
satellite tracking, and pass timing questions.

The S.A.T. host comes from `CSN_SAT_HOST` (set it in `skills.entries.csn-sat.env`)
or `--host <ip>`.

## Commands

Run with the `exec` tool:

```bash
python3 {baseDir}/scripts/satctl.py status            # position, tracking state, next pass
python3 {baseDir}/scripts/satctl.py goto 180 30 --wait # point at AZ 180, EL 30 and wait
python3 {baseDir}/scripts/satctl.py track ISS          # start built-in tracker (name or catalog no.)
python3 {baseDir}/scripts/satctl.py sats SO-           # list loaded satellites, optional filter
python3 {baseDir}/scripts/satctl.py stop               # stop tracking and movement
python3 {baseDir}/scripts/satctl.py park               # move to park position
python3 {baseDir}/scripts/satctl.py ready              # move to ready position
python3 {baseDir}/scripts/satctl.py sim on|off         # rotator simulation (no rotator attached)
```

Add `--json` to any command for machine-readable output.

## Rules

- **Moving a real antenna is physical.** Before `goto`, `track`, `park`, or
  `ready`, make sure the user asked for the movement. Never move it on your own
  initiative (heartbeats, guesses, "testing").
- Azimuth must be 0–450, elevation 0–180. `goto` stops any active tracking first,
  otherwise the tracker would immediately pull the antenna back.
- `track` answers "when is the next pass": while the satellite is below the
  horizon the box waits and reports AOS, LOS and max elevation.
- If a satellite is not found, run `sats <part-of-name>` and offer the matches.
- **Simulation state cannot be read back** — the web page always shows OFF. If
  the user says the rotator is disconnected, suggest `sim on`; remind them to
  run `sim off` before reconnecting the real rotator.
- If status shows `Rotator DISABLED`, movements are ignored; tell the user to
  enable it on the S.A.T. web page rather than toggling it blindly.
- Reboot, firmware, WiFi, calibration and rig settings are out of scope — send
  the user to the S.A.T. web page (`http://$CSN_SAT_HOST/`).

## Notes

- The device is an embedded web server: requests are paced and retried in the
  script. Don't run several `satctl.py` commands in parallel.
- The box also exposes a minimal Hamlib `rotctld` port (4533) that answers
  `p`/`P` (get/set position); Hamlib's own `rotctl -m 2` fails against it because the box
  ignores `\dump_state`. This skill uses the HTTP API instead.
