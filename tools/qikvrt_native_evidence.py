#!/usr/bin/env python3
"""Provider-independent, fail-closed QIK-VRT evidence snapshot (read-only)."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "ingolf-lohmann/qik-vrt"
PR_NUMBERS = (703, 705)
REQUIRED = ("admission", "ci", "governance", "integrity")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def evidence(state, value=None, source=None, method=None, **extra):
    return dict(state=state, value=value, source=source, method=method, observed_at=now(), **extra)

def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL, text=True, timeout=8).strip()

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "qikvrt-native-evidence/1", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.load(response)

def collect(root, host):
    result = {"schema": "qikvrt_native_evidence_v1", "observed_at": now(), "repository": REPO,
              "checks": {}, "prs": {}, "dod": "OPEN/BLOCKED"}
    checks = result["checks"]
    try:
        head, tree = git("-C", str(root), "rev-parse", "HEAD"), git("-C", str(root), "rev-parse", "HEAD^{tree}")
        dirty = bool(git("-C", str(root), "status", "--porcelain"))
        checks["exact_head_tree"] = evidence("confirmed", {"head": head, "tree": tree, "dirty": dirty},
                                               "local-git", "git rev-parse + status")
    except (OSError, subprocess.SubprocessError) as exc:
        checks["exact_head_tree"] = evidence("unknown", source="local-git", method="git rev-parse", error=type(exc).__name__)
    release = root / "interfaces" / "client-release.json"
    try:
        raw = release.read_bytes()
        data = json.loads(raw)
        gates = {key: data.get(key) for key in REQUIRED}
        state = "confirmed" if all(str(v).upper() in ("ADMITTED", "VERIFIED", "PASS") for v in gates.values()) else "open"
        checks["release"] = evidence(state, gates, str(release), "local-file SHA-256 + JSON",
                                     sha256=hashlib.sha256(raw).hexdigest())
    except (OSError, ValueError, TypeError) as exc:
        checks["release"] = evidence("unknown", source=str(release), method="local-file JSON", error=type(exc).__name__)
    for number in PR_NUMBERS:
        url = f"https://api.github.com/repos/{REPO}/pulls/{number}"
        try:
            pr = http_json(url)
            result["prs"][str(number)] = evidence("open" if pr.get("state") == "open" else "confirmed",
                {"state": pr.get("state"), "draft": pr.get("draft"), "head": pr.get("head", {}).get("sha")},
                url, "GitHub REST GET; status only, not review/CI admission")
        except (OSError, ValueError, KeyError) as exc:
            result["prs"][str(number)] = evidence("unknown", source=url, method="GitHub REST GET", error=type(exc).__name__)
    try:
        request = urllib.request.Request(host, method="GET", headers={"User-Agent": "qikvrt-native-evidence/1"})
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
        checks["public_tls"] = evidence("confirmed" if status == 200 else "open", status, host, "HTTPS GET + certificate verification")
    except urllib.error.HTTPError as exc:
        checks["public_tls"] = evidence("open", exc.code, host, "HTTPS GET + certificate verification")
    except (OSError, ValueError) as exc:
        checks["public_tls"] = evidence("unknown", source=host, method="HTTPS GET + certificate verification", error=type(exc).__name__)
    for key in ("native_ready", "admitted_mesh_runtime", "effect_ack_done", "writer_fencing",
                "original_host_authenticated", "independent_reviews", "artifact_sha_verified"):
        checks[key] = evidence("unknown", source="native readback required", method="not observed")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--host", default="https://raumzeitterminal.de/")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    snapshot = collect(args.root.resolve(), args.host)
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_name(args.output.name + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, args.output)
    else:
        sys.stdout.write(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
