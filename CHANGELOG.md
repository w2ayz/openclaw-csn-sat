# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/).

## [1.0.2] - 2026-10-11

### Added

- `Deployment.md`: network topologies for reaching the S.A.T. from OpenClaw —
  same-LAN, Tailscale subnet router (recommended for a constrained LAN-local
  device like a Raspberry Pi), SSH tunnel fallback, and running OpenClaw
  directly on the LAN-local device — plus security notes (the S.A.T.'s HTTP
  API has no authentication and no TLS, so it should never be exposed beyond
  a private LAN/tailnet).

## [1.0.1] - 2026-10-11

### Added

- README: documented the TLE data sources behind the device's TLE/FREQ DB
  SOURCE URL field — AMSAT's weekly `nasabare.txt`, CSN's mirror of it, and
  CSN's `csnbare.txt` (CelesTrak-derived, updated daily) — and noted the
  device only accepts plain `http://` URLs.

## [1.0.0] - 2026-10-02

### Added

- `csn-sat` OpenClaw skill (`SKILL.md`) with gating on `python3` and host
  configuration through `skills.entries.csn-sat.env.CSN_SAT_HOST`.
- `scripts/satctl.py` CLI (Python standard library only) with commands
  `status`, `goto`, `track`, `sats`, `stop`, `park`, `ready`, `sim` and `--version`.
- `--json` output on every command.
- Satellite lookup by name, partial name or NORAD catalog number against the
  list loaded on the device.
- AZ/EL range validation (0–450° / 0–180°); `goto` stops tracking first.
- Request pacing and retry for the device's embedded web server.
- Agent safety rules: move only on explicit request; simulation state is write-only.

[1.0.2]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.2
[1.0.1]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.1
[1.0.0]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.0
