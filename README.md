# openclaw-csn-sat

An [OpenClaw](https://openclaw.ai) skill to control a
[CSN Technologies S.A.T.](http://csntechnologies.net/sat) (Self-contained Antenna Tracker)
over its local web API: read position, point the antenna, start the built-in
satellite tracker, park/stop, and toggle rotator simulation.

Stdlib-only Python 3, no dependencies. Unofficial; not affiliated with CSN Technologies.

## Install

```bash
openclaw skills install git:w2ayz/openclaw-csn-sat
openclaw config patch '{ skills: { entries: { "csn-sat": { env: { CSN_SAT_HOST: "192.168.x.x" } } } } }'
```

Then start a new session (`/new`) and ask things like *"where is the antenna pointing?"*,
*"track the ISS"*, or *"park the rotator"*.

## CLI

The script works standalone too:

```bash
export CSN_SAT_HOST=192.168.x.x
scripts/satctl.py status
scripts/satctl.py goto 180 30 --wait
scripts/satctl.py track SO-50
scripts/satctl.py sats
scripts/satctl.py stop | park | ready
scripts/satctl.py sim on | off
```

`--json` on any command gives machine-readable output.

## How it talks to the box

All actions go through `GET /cmd?a=<command>` exactly as the S.A.T. web UI does;
state comes from `/track`, `/status`, and `/viewtle`. Tested on firmware 9.188
with a Yaesu-type rotator in simulation mode.

| Action | Command |
|---|---|
| Point AZ/EL | `P\|az\|el\|` |
| Track satellite | `U\|<catalog no.>` |
| Stop | `S\|X` |
| Park / Ready | `z` / `y` |
| Simulation on/off | `Z\|X\|1` / `Z\|X\|0` |

The box also listens on Hamlib port 4533 but only answers `p`/`P`; `rotctl -m 2`
fails against it because it never replies to `\dump_state`.

## License

MIT
