# openclaw-csn-sat 📡

An [OpenClaw](https://openclaw.ai) skill that lets your agent control a
[CSN Technologies S.A.T.](http://csntechnologies.net/sat) (Self-contained Antenna Tracker)
on your local network. You can read the antenna position, point it, start the built-in
satellite tracker, park or stop it, and switch rotator simulation on or off.

- Pure Python 3 standard library: nothing to install
- Uses the same local HTTP API as the S.A.T. web page; no cloud, no account
- Works as an OpenClaw skill or as a standalone CLI

> Unofficial. Not affiliated with or endorsed by CSN Technologies Inc.

## Requirements

- An S.A.T. reachable on your LAN (tested on firmware **9.188**)
- `python3` on the OpenClaw host
- OpenClaw 2026.9 or later (for the skill; the CLI runs anywhere)

## Install

```bash
# 1. Install the skill into your agent workspace
openclaw skills install git:w2ayz/openclaw-csn-sat

# 2. Tell it where the S.A.T. lives
echo '{ skills: { entries: { "csn-sat": { env: { CSN_SAT_HOST: "192.168.x.x" } } } } }' \
  | openclaw config patch --stdin

# 3. Confirm it loaded
openclaw skills list | grep csn-sat
```

Start a new session (`/new`) and ask things like:

- *"Where is the antenna pointing?"*
- *"Track the ISS. When is the next pass?"*
- *"Point the antenna at azimuth 180, elevation 30."*
- *"Park the rotator."*
- *"The rotator is disconnected, turn on simulation."*

To update, run the install command again. Git installs don't auto-update.

## CLI

```bash
export CSN_SAT_HOST=192.168.x.x        # or pass --host on each call

scripts/satctl.py status               # position, tracking state, next pass
scripts/satctl.py goto 180 30 --wait   # point and wait until the rotator settles
scripts/satctl.py track ISS            # satellite name or NORAD catalog number
scripts/satctl.py sats SO-             # list loaded satellites, optional filter
scripts/satctl.py stop                 # stop tracking and movement
scripts/satctl.py park                 # configured park position
scripts/satctl.py ready                # configured ready position
scripts/satctl.py sim on               # simulate a rotator (none attached)
scripts/satctl.py --version
```

Add `--json` to any command for machine-readable output. Errors go to stderr with
exit code 1.

Example:

```text
$ scripts/satctl.py track iss
Tracking ISS
Antenna   AZ  201.5  EL  20.9   (target AZ 200.0  EL 20.0)
Rotator   enabled
Tracking  ISS (#25544)  now AZ 303.9 EL -73.8
Next pass AOS 2026-10-02 18:36:31 PDT  LOS 2026-10-02 18:47:18 PDT  max EL 53.1
```

## Safety

This skill moves real hardware. The skill instructions tell the agent to:

- move the antenna only when the user explicitly asks; never on heartbeats or as a "test"
- stay within azimuth 0–450° and elevation 0–180°; the CLI also rejects anything outside that
- stop tracking before a manual `goto`, so the tracker doesn't immediately pull the antenna back
- leave reboot, firmware, WiFi, calibration and rig settings to the S.A.T. web page

Simulation state **cannot be read back** from the device (its web page always shows OFF).
Run `sim off` before reconnecting a real rotator.

## TLE database

The S.A.T. does not generate its own orbital data — it periodically downloads a TLE
(Two-Line Element) file from a **SOURCE URL** you configure in the TLE/FREQ DB panel.
The manufacturer's manual lists these known-good sources:

| Source | URL | Notes |
|---|---|---|
| AMSAT `nasabare.txt` | `http://www.amsat.org/tle/current/nasabare.txt` | updated weekly |
| CSN `nasabare.txt` | `http://www.csntechnologies.net/SAT/nasabare.txt` | mirror of AMSAT's file |
| CSN `csnbare.txt` | `http://www.csntechnologies.net/SAT/csnbare.txt` | same satellite set, generated from **CelesTrak** data, updated daily |

So the underlying database the box ultimately relies on is **CelesTrak** (via CSN's daily
`csnbare.txt` mirror) or **AMSAT** (weekly). The S.A.T. only accepts plain `http://` URLs
for the TLE source — `https://` is not supported.

## How it talks to the box

The S.A.T. has no published API. These commands were taken from its web UI:
every action is `GET /cmd?a=<pipe-separated command>`, and state comes from
`/track`, `/status` and `/viewtle`.

| Action | Command |
|---|---|
| Point AZ/EL | `P\|az\|el\|` |
| Track satellite | `U\|<catalog no.>` |
| Stop | `S\|X` |
| Park / Ready | `z` / `y` |
| Simulation on / off | `Z\|X\|1` / `Z\|X\|0` |

Notes:

- The device's embedded web server drops requests that arrive back-to-back, so
  the CLI paces and retries them. Don't run several commands in parallel.
- The S.A.T. also listens on Hamlib port **4533** but only answers `p`/`P`.
  Hamlib's `rotctl -m 2` fails against it because the box never replies to
  `\dump_state`.
- A firmware update could change these undocumented commands.

## Files

```text
SKILL.md            OpenClaw skill definition (frontmatter + agent instructions)
scripts/satctl.py   CLI used by the skill
CHANGELOG.md        release history
Deployment.md       network topologies for reaching the S.A.T. from OpenClaw, and security notes
```

See [Deployment.md](Deployment.md) if OpenClaw doesn't run on the same network as the
S.A.T. — it covers running on the same LAN, reaching it through a Tailscale subnet
router or SSH tunnel, and the security considerations for each.

## License

[MIT](LICENSE)
