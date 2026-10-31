#!/usr/bin/env python3
"""Observable bounded execution of the six-kernel Lean check (Python stdlib only)."""
import argparse
import datetime
import json
import os
import selectors
import signal
import subprocess
import sys
import time

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--idle-seconds", type=int, default=900)
    p.add_argument("--heartbeat-seconds", type=int, default=30)
    p.add_argument("--total-seconds", type=int, default=1800)
    p.add_argument("--log", default="multi-kernel-report.log")
    p.add_argument("--evidence", default="kernel-execution.json")
    args = p.parse_args()
    if min(args.idle_seconds, args.heartbeat_seconds, args.total_seconds) <= 0:
        p.error("timeouts must be positive")
    started = time.monotonic()
    last_output = started
    last_heartbeat = started
    bytes_seen = 0
    lines_seen = 0
    reason = "unknown"
    cmd = ["lake", "check", "--paranoid"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    print("QIKVRT_START command=%r pid=%d utc=%s" % (cmd, proc.pid, utc()), flush=True)
    try:
        with open(args.log, "wb") as log:
            while True:
                now = time.monotonic()
                if now - started >= args.total_seconds:
                    reason = "total_timeout"
                    break
                if now - last_output >= args.idle_seconds:
                    reason = "no_output_stagnation"
                    break
                events = selector.select(timeout=min(args.heartbeat_seconds, 2))
                for key, _ in events:
                    chunk = os.read(key.fd, 65536)
                    if chunk:
                        log.write(chunk)
                        log.flush()
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                        bytes_seen += len(chunk)
                        lines_seen += chunk.count(b"\n")
                        last_output = time.monotonic()
                    else:
                        selector.unregister(key.fileobj)
                now = time.monotonic()
                if now - last_heartbeat >= args.heartbeat_seconds:
                    print("QIKVRT_HEARTBEAT utc=%s elapsed_s=%d silence_s=%d bytes=%d lines=%d alive=%s" %
                          (utc(), now-started, now-last_output, bytes_seen, lines_seen,
                           proc.poll() is None), flush=True)
                    last_heartbeat = now
                if proc.poll() is not None and not selector.get_map():
                    reason = "completed" if proc.returncode == 0 else "process_failed"
                    break
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        selector.close()
        evidence = {
            "schema": "qikvrt.kernel-execution.v1",
            "commit": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "command": cmd,
            "started_utc": utc(),
            "elapsed_seconds": round(time.monotonic()-started, 2),
            "output_bytes": bytes_seen,
            "output_newlines": lines_seen,
            "last_output_age_seconds": round(time.monotonic()-last_output, 2),
            "exit_code": proc.returncode,
            "termination_reason": reason,
            "idle_limit_seconds": args.idle_seconds,
            "total_limit_seconds": args.total_seconds,
            "passed": reason == "completed" and bytes_seen > 0,
        }
        with open(args.evidence, "w", encoding="utf-8") as out:
            json.dump(evidence, out, indent=2, sort_keys=True)
            out.write("\n")
        print("QIKVRT_END " + json.dumps(evidence, sort_keys=True), flush=True)
    return 0 if evidence["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
