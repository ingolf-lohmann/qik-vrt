# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
# Additive, separately pinned hook for the unchanged original cloud supervisor.
# This guard must also prefix Railway's applied startCommand, before its Git,
# compiler, profile or follow-script writes. No automatic resume after capture.
[ ! -e /var/lib/qikvrt/.RAILWAY_CAPTURE_HOLD.json ] || {
  echo 'HOLD: private Railway capture fence is present' >&2
  exit 78
}

capture_once() {
  # A signal alone is not authority. Validate a separately sealed package and
  # exact private request before stopping any current role.
  if [ -z "${QIKVRT_CAPTURE_PACKAGE:-}" ] \
    || [ -z "${QIKVRT_CAPTURE_PACKAGE_SHA256:-}" ] \
    || [ -z "${QIKVRT_CAPTURE_REQUEST:-}" ] \
    || [ -z "${QIKVRT_CAPTURE_REQUEST_SHA256:-}" ] \
    || [ -z "${QIKVRT_CAPTURE_OUTPUT:-}" ]; then
    echo 'HOLD: exact private capture inputs are absent' >&2
    return
  fi
  if ! python3 -B "$QIKVRT_CAPTURE_PACKAGE/tools/qikvrt_self_host.py" migration-capture-arm \
    --root "$QIKVRT_CAPTURE_PACKAGE" --manifest-sha256 "$QIKVRT_CAPTURE_PACKAGE_SHA256" \
    --source-root "${QIKVRT_CAPTURE_SOURCE_ROOT:-/opt/qikvrt}" --live-volume /var/lib/qikvrt \
    --capture-request "$QIKVRT_CAPTURE_REQUEST" --capture-request-sha256 "$QIKVRT_CAPTURE_REQUEST_SHA256" \
    --output "$QIKVRT_CAPTURE_OUTPUT"; then
    return
  fi
  trap '' USR1
  # Existing supervisor, existing children; no provider mutation, second daemon
  # or forced kill. A writer refusing graceful stop means no capture.
  if QIKVRT_CAPTURE_PID_LIST="$PIDS" python3 -B - <<'PY'
import os, signal, time
from pathlib import Path
pids = [int(p) for p in os.environ['QIKVRT_CAPTURE_PID_LIST'].split()]
for pid in pids:
    try: os.kill(pid, signal.SIGTERM)
    except ProcessLookupError: pass
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    alive = []
    for pid in pids:
        try:
            if Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z': alive.append(pid)
        except FileNotFoundError: pass
    if not alive: break
    time.sleep(0.05)
else: raise SystemExit(78)
PY
  then
    for pid in $PIDS; do wait "$pid" 2>/dev/null || true; done
    PIDS=""
    python3 -B "$QIKVRT_CAPTURE_PACKAGE/tools/qikvrt_self_host.py" migration-capture \
      --root "$QIKVRT_CAPTURE_PACKAGE" --manifest-sha256 "$QIKVRT_CAPTURE_PACKAGE_SHA256" \
      --source-root "${QIKVRT_CAPTURE_SOURCE_ROOT:-/opt/qikvrt}" --live-volume /var/lib/qikvrt \
      --capture-request "$QIKVRT_CAPTURE_REQUEST" --capture-request-sha256 "$QIKVRT_CAPTURE_REQUEST_SHA256" \
      --output "$QIKVRT_CAPTURE_OUTPUT" || true
  else
    echo 'HOLD: source writer did not stop within capture budget' >&2
  fi
  # The durable fence survives all outcomes. Let the existing platform stop the
  # deployment; never restart a role or silently remove a quarantine marker.
  trap - EXIT
  exit 78
}
trap capture_once USR1
