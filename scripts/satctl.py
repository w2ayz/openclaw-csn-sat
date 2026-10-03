#!/usr/bin/env python3
"""Control a CSN Technologies S.A.T. (Self-contained Antenna Tracker) over its web API.

Stdlib only. Host comes from --host or the CSN_SAT_HOST environment variable.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

__version__ = "1.0.0"

AZ_RANGE = (0.0, 450.0)  # Yaesu G-5500 class rotators allow 450 deg azimuth
EL_RANGE = (0.0, 180.0)
TIMEOUT = 10


class SatError(Exception):
    pass


class Sat:
    def __init__(self, host):
        self.base = f"http://{host}"

    def _get(self, path, timeout=TIMEOUT, attempts=3):
        # The ESP-class web server drops connections that arrive back-to-back,
        # so pace requests and retry a dropped one.
        for i in range(attempts):
            time.sleep(0.4 if i == 0 else 1.5)
            try:
                with urllib.request.urlopen(self.base + path, timeout=timeout) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.URLError as e:
                if isinstance(e.reason, OSError) and not isinstance(e.reason, ConnectionError):
                    err = e  # unreachable host etc. - retrying won't help
                    break
                err = e
            except (ConnectionError, OSError) as e:
                err = e
        raise SatError(f"cannot reach S.A.T. at {self.base}: {err}")

    def _json(self, path, timeout=TIMEOUT):
        body = self._get(path, timeout)
        if not body.strip():
            raise SatError(f"empty response from {path}")
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise SatError(f"bad JSON from {path}: {e}") from e

    def cmd(self, arg):
        # The web UI sends every action as GET /cmd?a=<pipe-separated command>
        self._get("/cmd?a=" + urllib.parse.quote(arg, safe=""))

    def track_info(self):
        return self._json("/track")

    def status(self):
        return self._json("/status")

    def sats(self):
        return self._json("/viewtle", timeout=20).get("sats", [])


def fmt_time(epoch):
    if not epoch:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(epoch))


def summarize(t, s):
    tracking = t.get("mode") == 1
    out = {
        "tracking": tracking,
        "rotator_enabled": t.get("rotEnable") == 1,
        "az": round(t.get("az", 0.0), 1),
        "el": round(t.get("el", 0.0), 1),
        "target_az": round(t.get("taz", 0.0), 1),
        "target_el": round(t.get("tel", 0.0), 1),
        "park": [s.get("parkAZ"), s.get("parkEL")],
        "ready": [s.get("readyAZ"), s.get("readyEL")],
        "grid": s.get("grid"),
        "firmware": s.get("fw"),
        "wifi_rssi": t.get("rssi"),
    }
    if tracking:
        out["satellite"] = {
            "name": t.get("satname"),
            "catno": t.get("catno"),
            "az": round(t.get("satAZ", 0.0), 1),
            "el": round(t.get("satEL", 0.0), 1),
            "aos": fmt_time(t.get("aosTime")),
            "los": fmt_time(t.get("losTime")),
            "max_el": round(t.get("maxEL", 0.0), 1),
            "seconds_to_aos": t.get("ttaos"),
        }
    return out


def print_summary(d):
    print(f"Antenna   AZ {d['az']:6.1f}  EL {d['el']:5.1f}   "
          f"(target AZ {d['target_az']:.1f}  EL {d['target_el']:.1f})")
    print(f"Rotator   {'enabled' if d['rotator_enabled'] else 'DISABLED'}")
    sat = d.get("satellite")
    if sat:
        print(f"Tracking  {sat['name']} (#{sat['catno']})  now AZ {sat['az']:.1f} EL {sat['el']:.1f}")
        if sat["el"] < 0:
            print(f"Next pass AOS {sat['aos']}  LOS {sat['los']}  max EL {sat['max_el']:.1f}")
    else:
        print("Tracking  idle")


def check_range(name, val, lo_hi):
    lo, hi = lo_hi
    if not lo <= val <= hi:
        raise SatError(f"{name} {val} out of range {lo}-{hi}")


def resolve_sat(sat, query):
    q = query.strip().upper()
    sats = sat.sats()
    for s in sats:
        if s["ID"].lstrip("0") == q.lstrip("0") or s["Name"].upper() == q:
            return s
    hits = [s for s in sats if q in s["Name"].upper()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SatError(f"no satellite matching '{query}' in the S.A.T. list (try: satctl.py sats)")
    names = ", ".join(h["Name"] for h in hits[:10])
    raise SatError(f"'{query}' is ambiguous: {names}")


def wait_until_settled(sat, timeout):
    last = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        t = sat.track_info()
        pos = (round(t["az"], 1), round(t["el"], 1))
        if pos == last:
            return t
        last = pos
        time.sleep(1.5)
    return sat.track_info()


def main(argv=None):
    p = argparse.ArgumentParser(description="Control a CSN Technologies S.A.T. antenna tracker.")
    p.add_argument("--host", default=os.environ.get("CSN_SAT_HOST"),
                   help="S.A.T. IP or hostname (default: $CSN_SAT_HOST)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="action", required=True)

    def command(name, help):
        return sub.add_parser(name, help=help, parents=[common])

    command("status", "antenna position and tracking state")
    g = command("goto", "point the antenna at AZ/EL degrees (stops tracking)")
    g.add_argument("az", type=float)
    g.add_argument("el", type=float)
    g.add_argument("--wait", action="store_true", help="wait until the rotator stops moving")
    command("stop", "stop tracking and rotator movement")
    command("park", "move to the configured park position")
    command("ready", "move to the configured ready position")
    t = command("track", "start the built-in tracker on a satellite (name or catalog no.)")
    t.add_argument("satellite", nargs="+")
    s = command("sats", "list satellites loaded on the S.A.T.")
    s.add_argument("filter", nargs="?", default="")
    m = command("sim", "turn rotator simulation on/off (state is not readable back)")
    m.add_argument("state", choices=["on", "off"])

    a = p.parse_args(argv)
    if not a.host:
        p.error("no S.A.T. host: pass --host or set CSN_SAT_HOST")
    sat = Sat(a.host)

    def report(msg, data=None):
        if a.json:
            print(json.dumps(data if data is not None else {"ok": True, "message": msg}))
        else:
            print(msg)

    if a.action == "status":
        d = summarize(sat.track_info(), sat.status())
        print(json.dumps(d, indent=2)) if a.json else print_summary(d)

    elif a.action == "goto":
        check_range("azimuth", a.az, AZ_RANGE)
        check_range("elevation", a.el, EL_RANGE)
        sat.cmd("S|X")  # tracking would immediately override a manual position
        sat.cmd(f"P|{a.az:g}|{a.el:g}|")
        if a.wait:
            t = wait_until_settled(sat, timeout=180)
            report(f"Settled at AZ {t['az']:.1f} EL {t['el']:.1f} (asked {a.az:g}/{a.el:g})",
                   {"ok": True, "az": t["az"], "el": t["el"]})
        else:
            report(f"Moving to AZ {a.az:g} EL {a.el:g}")

    elif a.action == "stop":
        sat.cmd("S|X")
        report("Stopped")

    elif a.action == "park":
        sat.cmd("z")
        report("Moving to park position")

    elif a.action == "ready":
        sat.cmd("y")
        report("Moving to ready position")

    elif a.action == "track":
        target = resolve_sat(sat, " ".join(a.satellite))
        sat.cmd("U|" + target["ID"])
        time.sleep(2)
        d = summarize(sat.track_info(), sat.status())
        if a.json:
            print(json.dumps(d, indent=2))
        else:
            print(f"Tracking {target['Name']}")
            print_summary(d)

    elif a.action == "sats":
        f = a.filter.upper()
        rows = [x for x in sat.sats() if x["Name"] and f in x["Name"].upper()]
        if a.json:
            print(json.dumps(rows))
        else:
            for x in rows:
                print(f"{x['ID']:>6}  {x['Name']}")

    elif a.action == "sim":
        sat.cmd("Z|X|" + ("1" if a.state == "on" else "0"))
        report(f"Simulation {a.state}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SatError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
