#!/usr/bin/env python3
"""Interactive deployment helper for the csn-sat OpenClaw skill.

Finds the S.A.T. over one of the network topologies in Deployment.md, verifies it
answers, and stores its address as CSN_SAT_HOST in the OpenClaw config.
Stdlib only. Run it yourself in a terminal; it asks before changing anything.
"""
import argparse
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from satctl import Sat, SatError, __version__, check_host

CONFIG_KEY = "skills.entries.csn-sat.env.CSN_SAT_HOST"
TAILNET = ipaddress.ip_network("100.64.0.0/10")
MAC_TAILSCALE = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

TOPOLOGIES = {
    "lan": "Same LAN: OpenClaw runs on the S.A.T.'s network (Deployment.md §1)",
    "tailscale": "Tailscale subnet router: another device on the S.A.T.'s LAN advertises a route (§2)",
    "ssh": "SSH tunnel through a device on the S.A.T.'s LAN (§3)",
    "local": "OpenClaw installed on the LAN-local device itself (§4)",
}


def say(msg=""):
    print(msg, flush=True)


def ask(prompt, default=""):
    if not sys.stdin.isatty():
        return default
    hint = f" [{default}]" if default else ""
    try:
        reply = input(f"{prompt}{hint}: ").strip()
    except EOFError:
        return default
    return reply or default


def confirm(prompt, default=False):
    if not sys.stdin.isatty():
        return False
    reply = ask(f"{prompt} ({'Y/n' if default else 'y/N'})").lower()
    return default if not reply else reply.startswith("y")


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


# ---- probing -------------------------------------------------------------------------

def probe(host):
    """Return the S.A.T.'s /track data if `host` answers like one, else None."""
    try:
        t = Sat(host)._json("/track", timeout=8)  # slack for tunnels and Wi-Fi
    except SatError:
        return None
    return t if isinstance(t, dict) and {"az", "el", "rotEnable"} <= t.keys() else None


def describe(host, t):
    rot = "enabled" if t.get("rotEnable") == 1 else "DISABLED"
    return f"S.A.T. at {host}: AZ {t['az']:.1f}  EL {t['el']:.1f}, rotator {rot}"


def source_ip(host):
    # Which local address the OS would use to reach host (no packets are sent).
    name = host.rsplit(":", 1)[0]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((name, 80))
            return ipaddress.ip_address(s.getsockname()[0])
    except (OSError, ValueError):
        return None


def is_loopback(host):
    name = host.rsplit(":", 1)[0]
    return name == "localhost" or name.startswith("127.")


# ---- tailscale -----------------------------------------------------------------------

def tailscale_bin():
    return shutil.which("tailscale") or (MAC_TAILSCALE if os.path.exists(MAC_TAILSCALE) else None)


def tailscale_routes():
    """[(peer name, route ip)] for single-host (/32) subnet routes advertised on the tailnet."""
    ts = tailscale_bin()
    out = run([ts, "status", "--json"]) if ts else None
    if not out:
        return []
    routes = []
    for peer in (json.loads(out).get("Peer") or {}).values():
        name = peer.get("DNSName", "").split(".")[0] or peer.get("HostName", "?")
        for r in peer.get("PrimaryRoutes") or []:
            net = ipaddress.ip_network(r, strict=False)
            if net.version == 4 and net.prefixlen == 32:
                routes.append((name, str(net.network_address)))
    return routes


def tailscale_accepts_routes():
    ts = tailscale_bin()
    out = run([ts, "debug", "prefs"]) if ts else None
    if not out:
        return None  # unknown
    return bool(json.loads(out).get("RouteAll"))


def offer_accept_routes():
    if sys.platform == "darwin":
        say("  Turn on \"Use Tailscale subnets\" in the Tailscale menu, then run setup again.")
        return False
    cmd = ["sudo", tailscale_bin(), "set", "--accept-routes"]
    say("  This host doesn't accept Tailscale subnet routes, so the S.A.T.'s route is ignored.")
    if not confirm(f"  Enable it now? (runs: {' '.join(cmd)})"):
        return False
    return subprocess.run(cmd, check=False).returncode == 0


# ---- topology flows ------------------------------------------------------------------

def classify(host):
    if is_loopback(host):
        return "ssh"
    if any(ip == host for _, ip in tailscale_routes()):
        return "tailscale"
    src = source_ip(host)
    return "tailscale" if src and src in TAILNET else "lan"


def verify(host):
    try:
        check_host(host)
    except SatError as e:
        say(f"  {e}")
        return None
    t = probe(host)
    say(f"  ✓ {describe(host, t)}" if t else f"  ✗ no S.A.T. answering at {host}")
    return t


def flow_lan(default):
    host = ask("S.A.T. LAN IP or hostname", default)
    if not host:
        return None
    if verify(host):
        src = source_ip(host)
        if src and src in TAILNET:
            say("  Note: traffic to it goes over Tailscale, so this is really the subnet-router setup.")
        return host
    say("  Check the IP on the S.A.T.'s display or your router's DHCP list, and that this host is on that network.")
    return None


def flow_tailscale(default):
    if not tailscale_bin():
        say("  Tailscale is not installed on this host. See Deployment.md §2.")
        return None
    routes = tailscale_routes()
    if routes:
        say("  Single-host routes advertised on your tailnet:")
        for i, (peer, ip) in enumerate(routes, 1):
            say(f"    {i}) {ip}  via {peer}")
        pick = ask("  Pick one, or type the S.A.T.'s LAN IP", "1")
        host = routes[int(pick) - 1][1] if pick.isdigit() and 0 < int(pick) <= len(routes) else pick
    else:
        say("  No /32 subnet routes are advertised. On the LAN-local device run:")
        say("    sudo tailscale up --advertise-routes=<SAT_LAN_IP>/32 --accept-routes")
        say("  then approve the route in the Tailscale admin console (Deployment.md §2).")
        host = ask("  S.A.T. LAN IP (blank to go back)", default if default and not is_loopback(default) else "")
    if not host:
        return None
    if verify(host):
        return host
    if tailscale_accepts_routes() is False and offer_accept_routes() and verify(host):
        return host
    if not any(ip == host for _, ip in routes):
        say("  No tailnet device advertises that IP; approve its /32 route in the admin console.")
    return None


def flow_ssh(default):
    port = ask("Local port for the tunnel", default.rsplit(":", 1)[1] if default and is_loopback(default) and ":" in default else "8080")
    host = f"localhost:{port}"
    if probe(host):
        say(f"  ✓ tunnel already up: {describe(host, probe(host))}")
        return host
    jump = ask("SSH login of the device on the S.A.T.'s LAN (user@host)")
    sat_ip = ask("S.A.T. LAN IP, as seen from that device")
    if not jump or not sat_ip:
        return None
    cmd = ["ssh", "-f", "-N", "-o", "ExitOnForwardFailure=yes", "-L", f"{port}:{sat_ip}:80", jump]
    if confirm(f"  Start the tunnel now? (runs: {' '.join(cmd)})", default=True):
        subprocess.run(cmd, check=False)
    if not verify(host):
        return None
    say("  The tunnel won't survive a reboot or a dropped connection. Keep it alive with")
    say(f"  autossh -M 0 -N -L {port}:{sat_ip}:80 {jump}  under systemd or launchd (Deployment.md §3).")
    return host


def flow_local(default):
    say("  From the skill's point of view this is the same as the same-LAN setup.")
    return flow_lan(default)


FLOWS = {"lan": flow_lan, "tailscale": flow_tailscale, "ssh": flow_ssh, "local": flow_local}


def auto_detect(current, check_only=False):
    say("Looking for the S.A.T....")
    candidates = []
    if current:
        candidates.append((current, "current CSN_SAT_HOST"))
    for peer, ip in tailscale_routes():
        candidates.append((ip, f"Tailscale route via {peer}"))
    candidates.append(("localhost:8080", "SSH tunnel on port 8080"))

    seen, found, blocked = set(), [], []
    for host, why in candidates:
        if host in seen:
            continue
        seen.add(host)
        t = probe(host)
        say(f"  {'✓' if t else '·'} {host:<22} {why}")
        if t:
            found.append(host)
        elif why.startswith("Tailscale"):
            blocked.append(host)

    if not found and blocked and tailscale_accepts_routes() is False:
        if check_only:
            say("  Tailscale routes are advertised but this host doesn't accept them "
                "(tailscale set --accept-routes).")
        elif offer_accept_routes():
            found = [h for h in blocked if probe(h)]

    if not found:
        say("No S.A.T. found automatically.")
        return None
    host = found[0]
    if len(found) > 1 and not check_only:
        for i, h in enumerate(found, 1):
            say(f"  {i}) {h}")
        pick = ask("Several answer; use which", "1")
        host = found[int(pick) - 1] if pick.isdigit() and 0 < int(pick) <= len(found) else host
    say(f"Detected: {TOPOLOGIES[classify(host)]}")
    say(f"  ✓ {describe(host, probe(host))}")
    return host


# ---- config --------------------------------------------------------------------------

def openclaw_bin():
    return shutil.which("openclaw")


def current_host():
    oc = openclaw_bin()
    out = run([oc, "config", "get", CONFIG_KEY]) if oc else None
    value = (out or "").strip().strip('"')
    return value if value and value not in ("undefined", "null") else os.environ.get("CSN_SAT_HOST", "")


def save_host(host, yes):
    oc = openclaw_bin()
    if not oc:
        say("openclaw is not on PATH. Set it yourself:")
        say(f"  openclaw config set {CONFIG_KEY} {host}")
        return
    if not (yes or confirm(f"Save CSN_SAT_HOST={host} to the OpenClaw config?", default=True)):
        say("Not saved.")
        return
    r = subprocess.run([oc, "config", "set", CONFIG_KEY, host], capture_output=True, text=True, check=False)
    say("Saved. Start a new OpenClaw session (/new) to use it." if r.returncode == 0
        else f"openclaw config set failed:\n{r.stderr.strip()}")


def menu():
    say("How does this OpenClaw host reach the S.A.T.?")
    say("  0) Automatically detect (recommended)")
    keys = list(TOPOLOGIES)
    for i, k in enumerate(keys, 1):
        say(f"  {i}) {TOPOLOGIES[k]}")
    say("  q) Quit")
    pick = ask("Choose", "0").lower()
    if pick == "q":
        return "quit"
    if pick.isdigit() and 1 <= int(pick) <= len(keys):
        return keys[int(pick) - 1]
    return "auto"


def main(argv=None):
    p = argparse.ArgumentParser(description="Set up how the csn-sat skill reaches the S.A.T.")
    p.add_argument("--auto", action="store_true", help="skip the menu and detect automatically")
    p.add_argument("--topology", choices=list(TOPOLOGIES), help="skip the menu and use this setup")
    p.add_argument("--check", action="store_true",
                   help="detect and report only; change nothing (safe for scripts and agents)")
    p.add_argument("--yes", action="store_true", help="save the detected host without asking")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)

    current = current_host()
    say(f"csn-sat setup {__version__}" + (f"  (current CSN_SAT_HOST: {current})" if current else ""))

    if a.check:
        host = auto_detect(current, check_only=True)
        if host and host != current:
            say(f"CSN_SAT_HOST should be {host}; run setup.py without --check to save it.")
        return 0 if host else 1

    choice = a.topology or ("auto" if a.auto or not sys.stdin.isatty() else None)
    while True:
        choice = choice or menu()
        if choice == "quit":
            return 1
        say()
        host = auto_detect(current) if choice == "auto" else FLOWS[choice](current)
        if host:
            break
        if a.auto or a.topology or not sys.stdin.isatty():
            return 1
        say()
        choice = None

    if host == current:
        say("CSN_SAT_HOST is already set to that. Nothing to change.")
    else:
        save_host(host, a.yes)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say()
        sys.exit(130)
