# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/).

## [1.2.2] - 2026-10-11

### Changed

- `setup.py`: the SSH tunnel the wizard starts (option 3) now has an ssh control socket, so
  the wizard stops exactly that tunnel when you go back (`b`), press Ctrl-C, or the S.A.T.
  doesn't answer through it. Tunnels you started yourself are left alone. After a
  successful start it prints the command to stop the tunnel.
- `setup.py`: waits up to ~5 s for a freshly started tunnel before declaring it unreachable.
- `Deployment.md`, `README.md`: document the above.

## [1.2.1] - 2026-10-11

### Added

- `setup.py`: type `b` (or `back`) at any prompt, including the final save confirmation,
  to return to the start menu. Saving now happens inside the menu loop, so backing out
  never saves.
- `Deployment.md`: each topology section (§1–§4) now says which wizard option sets it up and
  which steps remain manual. The Quick setup section explains `b`.
- `README.md`: mention `b` in the wizard description.

## [1.2.0] - 2026-10-11

### Added

- `scripts/setup.py`: deployment wizard. Its menu offers **Automatically detect** or one of
  the four Deployment.md setups (same LAN, Tailscale subnet router, SSH tunnel, OpenClaw on
  the LAN-local device). It checks that the address answers like an S.A.T., offers to enable
  Tailscale `--accept-routes` or start the SSH tunnel, and saves `CSN_SAT_HOST`, asking first
  each time. `--check` is read-only; `--auto`, `--topology` and `--yes` skip the prompts.
- `SKILL.md`: when the S.A.T. is unreachable, the agent runs `setup.py --check` and reports.

### Changed

- `passes`: by default shows the S.A.T.'s whole forecast (it only predicts a few hours ahead)
  instead of a 12 h window. `--hours` now only narrows it, and the "no passes" message names
  the window the S.A.T. actually covered rather than claiming e.g. "none in the next 24 h".
- `SKILL.md`: don't tell users a satellite has no passes "today" from that short forecast.

## [1.1.0] - 2026-10-11

### Added

- `satctl.py passes [satellite...] [--hours N] [--min-el DEG] [--limit N] [--json]`: read-only
  list of upcoming passes, using the same `/future` prediction as the web UI's NEXT PASSES
  button. Defaults to the S.A.T.'s favorites.
- `SKILL.md`: agents must use `passes`, not `track`, to answer "when is the next pass", since
  `track` moves the antenna.

## [1.0.4] - 2026-10-11

### Security

- `satctl.py`: validate the host (bare IP or hostname, optional port); reject `@`, paths,
  queries and whitespace. Do not follow HTTP redirects.
- `SKILL.md`: tell the agent to treat device output (e.g. satellite names from the TLE
  file) as data, not instructions, and to use `--host` only when the user supplies it.

## [1.0.3] - 2026-10-11

### Changed

- `Deployment.md`: add a "Using the S.A.T. web UI" section (browser access over LAN,
  Tailscale subnet route and SSH tunnel; plain http only; no login).
- `Deployment.md`: use the generic name `Tailnet-LAN-SAT-Router` for the subnet-router device.
- `README.md`: point to the web UI section.

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

[1.2.2]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.2.2
[1.2.1]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.2.1
[1.2.0]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.2.0
[1.1.0]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.1.0
[1.0.4]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.4
[1.0.3]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.3
[1.0.2]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.2
[1.0.1]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.1
[1.0.0]: https://github.com/w2ayz/openclaw-csn-sat/releases/tag/v1.0.0
