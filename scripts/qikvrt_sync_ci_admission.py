#!/usr/bin/env python3
"""Bounded, fail-closed synchronous GitHub Actions dispatcher (stdlib only).

Run from an authorized controller, never from an untrusted PR or with a
production environment token. Does not merge or deploy.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SHA = re.compile(r"^[0-9a-f]{40}$")
WORKFLOW = "qikvrt_ci.yml"


class AdmissionError(RuntimeError):
    pass


def request(method, path, token, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-exact-head-ci-admission",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise AdmissionError("GitHub HTTP %d for %s" % (exc.code, path)) from exc


def execute(repo, ref, expected, token, deadline_seconds=900, interval=10):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise AdmissionError("invalid repository")
    if not SHA.fullmatch(expected):
        raise AdmissionError("expected exact 40-digit commit SHA")
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", ref)
            or ".." in ref or ref.startswith("-")):
        raise AdmissionError("invalid ref")
    base = "/repos/" + repo
    def head():
        return request("GET", base + "/commits/" + ref, token)["sha"]
    if head() != expected:
        raise AdmissionError("HEAD_DRIFT before dispatch")
    started = time.monotonic()
    # Snapshot prior run IDs; never attribute an unrelated run to this dispatch.
    path = base + "/actions/workflows/" + WORKFLOW + "/runs?event=workflow_dispatch&per_page=100"
    prior = {x["id"] for x in request("GET", path, token).get("workflow_runs", [])}
    request("POST", base + "/actions/workflows/" + WORKFLOW + "/dispatches",
            token, {"ref": ref})
    selected = None
    while time.monotonic() - started < deadline_seconds:
        if head() != expected:
            raise AdmissionError("HEAD_DRIFT after dispatch")
        runs = request("GET", path, token).get("workflow_runs", [])
        candidates = [x for x in runs if x["id"] not in prior
                      and x.get("head_sha") == expected
                      and x.get("event") == "workflow_dispatch"]
        if len(candidates) > 1:
            raise AdmissionError("AMBIGUOUS_DISPATCH_RUN")
        if candidates:
            if selected is not None and selected != candidates[0]["id"]:
                raise AdmissionError("DISPATCH_RUN_CHANGED")
            selected = candidates[0]["id"]
            run = request("GET", base + "/actions/runs/" + str(selected), token)
            if run.get("head_sha") != expected:
                raise AdmissionError("RUN_HEAD_MISMATCH")
            if run.get("status") == "completed":
                if run.get("conclusion") != "success":
                    raise AdmissionError("CI_" + str(run.get("conclusion")))
                jobs = request("GET", base + "/actions/runs/" + str(selected)
                               + "/jobs?per_page=100", token)
                entries = jobs.get("jobs", [])
                if not entries or jobs.get("total_count") != len(entries):
                    raise AdmissionError("NO_COMPLETE_JOB_EVIDENCE")
                if any(j.get("conclusion") != "success" for j in entries):
                    raise AdmissionError("JOB_NOT_SUCCESSFUL")
                if head() != expected:
                    raise AdmissionError("HEAD_DRIFT after completion")
                return {"status": "CI_VERIFIED", "head": expected,
                        "run_id": selected, "job_count": len(entries),
                        "effect_ack_done": False}
        time.sleep(interval)
    raise AdmissionError("CI_TIMEOUT_OR_ADMISSION_HOLD")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="ingolf-lohmann/qik-vrt")
    parser.add_argument("--ref", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        token = os.environ.get("GH_TOKEN", "")
        if not token:
            raise AdmissionError("GH_TOKEN_MISSING")
        result = execute(args.repo, args.ref, args.expected_head, token,
                         deadline_seconds=max(1, min(args.timeout, 3600)))
        print(json.dumps(result, sort_keys=True))
    except (AdmissionError, KeyError, ValueError, urllib.error.URLError) as exc:
        print(json.dumps({"status": "CONTINUATION_REQUIRED",
                          "effect_ack_done": False, "reason": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
