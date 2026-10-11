# Deployment

The S.A.T. only speaks plain HTTP on its local network, and has **no authentication** —
anything that can reach its IP on port 80 can move the antenna. This skill (and the
`satctl.py` CLI it wraps) just needs a plain TCP/IP path from wherever OpenClaw runs to
that IP. How you build that path depends on where OpenClaw runs relative to the S.A.T.'s
LAN. This doc lays out the common topologies.

## 1. OpenClaw on the same LAN as the S.A.T.

The simplest case: the machine running OpenClaw is already on the same local network as
the S.A.T. (e.g. a shack computer on the home WiFi).

```mermaid
flowchart LR
    subgraph LAN["Home / Shack LAN"]
        A["OpenClaw host<br/>(csn-sat skill)"] -->|"http://192.168.x.x"| B["S.A.T."]
    end
```

Set `CSN_SAT_HOST` to the S.A.T.'s LAN IP (or mDNS hostname, if your resolver supports
it). Nothing else is required.

## 2. OpenClaw on a different network, reached via a Tailscale subnet router

If OpenClaw runs somewhere that is **not** on the S.A.T.'s LAN — a cloud box, your main
desktop on a different network, etc. — but you have a small always-on device (a
Raspberry Pi, for example) that *is* on the S.A.T.'s LAN and already joined to your
tailnet, that device can act as a **subnet router**: it advertises a route into its LAN
over Tailscale and then does nothing but forward packets. It does not need to run
OpenClaw, Node, or anything else — this keeps the CPU/RAM footprint on something like a
Pi 4 essentially zero, instead of trying to run an agent gateway on constrained
hardware.

```mermaid
flowchart LR
    subgraph Tailnet["Tailnet (WireGuard-encrypted)"]
        A["OpenClaw host<br/>(csn-sat skill)"]
    end
    subgraph LAN["S.A.T.'s LAN"]
        R["pi-sat-controller<br/>(subnet router only —<br/>no OpenClaw installed)"]
        B["S.A.T."]
    end
    A -->|"Tailscale"| R
    R -->|"http:// (plain LAN)"| B
```

Setup, on the LAN-local device (`pi-sat-controller` below):

```bash
# one-time: enable IP forwarding, persisted across reboots
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf

# advertise a route to just the S.A.T.'s IP — not the whole LAN
sudo tailscale up --advertise-routes=<SAT_LAN_IP>/32 --accept-routes
```

Then, in the Tailscale admin console (**Machines → pi-sat-controller → Edit route
settings**), approve the advertised `/32` route. Once approved, any tailnet node with
route-accepting enabled (`tailscale up --accept-routes`, or `RouteAll` in its prefs) can
reach the S.A.T. directly:

```bash
curl http://<SAT_LAN_IP>/status
```

On the OpenClaw host, install the skill and point it at the S.A.T.'s **LAN** IP (not the
router's Tailscale IP — the subnet route makes that LAN IP directly reachable):

```bash
openclaw skills install git:w2ayz/openclaw-csn-sat
echo '{ skills: { entries: { "csn-sat": { env: { CSN_SAT_HOST: "<SAT_LAN_IP>" } } } } }' \
  | openclaw config patch --stdin
```

**Scope the advertised route as narrowly as possible.** Advertising `/32` for just the
S.A.T.'s IP (rather than the whole LAN as a `/24` or similar) means the subnet router
only ever exposes the one device you actually want reachable from the tailnet — not
every other thing sitting on that LAN.

## 3. OpenClaw on a different network, reached via SSH tunnel

If you don't have (or don't want) Tailscale subnet-route approval rights, an SSH local
port-forward through the LAN-local device works as a fallback, at the cost of needing a
persistent tunnel process:

```mermaid
flowchart LR
    A["OpenClaw host"] -->|"ssh -L 8080:SAT_IP:80"| R["LAN-local device<br/>(SSH only)"]
    R -->|"http:// (plain LAN)"| B["S.A.T."]
```

```bash
ssh -N -L 8080:<SAT_LAN_IP>:80 user@lan-local-device
```

Then set `CSN_SAT_HOST=localhost:8080` on the OpenClaw host. Because this tunnel is a
foreground (or `autossh`-managed) process, it needs its own supervision (e.g. a
LaunchAgent/systemd unit) to survive reboots and reconnects — the subnet-router approach
in §2 is generally less fragile since Tailscale's own daemon handles reconnection.

## 4. OpenClaw running directly on the LAN-local device

You *can* install OpenClaw and this skill directly on the device sitting on the S.A.T.'s
LAN, collapsing the whole path into one host. This avoids any routing setup, but puts
the full agent runtime (model calls, session state, any other skills you've enabled) on
whatever hardware that device has. On something CPU-constrained like a Raspberry Pi 4,
this is usually the wrong trade — prefer §2 and keep that device doing nothing but
routing.

## Security notes

- **The S.A.T.'s HTTP API has no authentication.** Anyone who can reach its IP on port
  80 can move the antenna or change its tracking state. Never expose it directly to the
  public internet; keep it reachable only from a private LAN and/or private tailnet.
- **No TLS.** The device doesn't support `https://`, so traffic to it is cleartext on
  whatever network segment carries it. This is fine on a private LAN, and fine over a
  tailnet (WireGuard-encrypted in transit) — just don't bridge it onto a network you
  don't trust.
- **Prefer the narrowest reachable scope.** When using a subnet router (§2), advertise a
  `/32` for the S.A.T. itself rather than its whole LAN, so other devices on that LAN
  aren't incidentally exposed to the tailnet.
- **Physical hardware, real movement.** The skill instructs the agent to only move the
  antenna on explicit user request — never on heartbeats, background checks, or as a
  "test." If you expose the OpenClaw agent through a chat channel (Slack, WeChat, etc.),
  anyone who can message that channel can move the antenna; scope channel/agent access
  accordingly.
- **Simulation state is write-only.** The device never reports whether simulation mode
  is on — if you enable it (`sim on`) for testing without a rotator attached, remember
  to `sim off` before reconnecting real hardware, since there's no way to query current
  state to catch a forgotten toggle.
