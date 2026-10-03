#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Measure local Git comparisons separately from a complete sandbox cycle.

The live carrier reads only the two fixed remotes. Reconciliation changes a
disposable local replica, never either remote. Its end-to-end clock includes
subject binding, remote FETCH, comparison, replica reconciliation, an independent
remote refetch and byte/mode/object readback. This is not evidence of a production
Authority-to-Mirror mutation or a distributed speedup.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qikvrt_authority_credentials import credential, CREDENTIALS

MIRROR_URL = "https://github.com/ingolf-lohmann/qik-vrt.git"
AUTHORITY_URL = "https://github.com/Goldkelch/qik-vrt.git"
REPEATS = 12
END_TO_END_REPEATS = 3
LOCAL_SCOPE = "LOCAL_GIT_OBJECT_COMPARISON_ONLY"
END_TO_END_SCOPE = "REMOTE_FETCH_TO_ISOLATED_REPLICA_AND_FRESH_READBACK"
PHASES = ("bind_fixed_subjects", "transport_fetch", "comparison",
          "reconciliation", "fresh_readback")
OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class CycleHold(RuntimeError):
    """A fixed-subject trial cannot establish its declared cycle."""


def local_environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and k not in CREDENTIALS
           and k not in {"QIKVRT_RULESET_APP_PRIVATE_KEY", "GH_TOKEN"}}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1", LC_ALL="C")
    return env


def run(*args, cwd=None, check=True, env=None):
    # Blob bytes and NUL-delimited paths must never pass through text decoding.
    try:
        p = subprocess.run(args, cwd=cwd, text=False, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           env=local_environment() if env is None else env,
                           timeout=120)
    except subprocess.TimeoutExpired:
        raise RuntimeError("GIT_OPERATION_TIMEOUT") from None
    except OSError:
        raise RuntimeError("GIT_OPERATION_UNAVAILABLE") from None
    if check and p.returncode:
        # Never persist arbitrary subprocess diagnostics or command arguments.
        raise RuntimeError("GIT_OPERATION_FAILED")
    return p


def git_value(repo, revision):
    value = run("git", "-C", str(repo), "rev-parse", "--verify", revision).stdout
    try:
        oid = value.strip().decode("ascii")
    except UnicodeDecodeError:
        raise RuntimeError("INVALID_GIT_OBJECT_ID") from None
    if not OBJECT_ID.fullmatch(oid):
        raise RuntimeError("INVALID_GIT_OBJECT_ID")
    return oid


def network_environment(url, token=""):
    if url not in {AUTHORITY_URL, MIRROR_URL}:
        raise ValueError("FIXED_REPOSITORY_SCOPE_REQUIRED")
    env = local_environment()
    settings = [("credential.helper", ""), ("http.followRedirects", "false")]
    if url == AUTHORITY_URL:
        if not token:
            raise ValueError("AUTHORITY_CREDENTIAL_REQUIRED")
        header = "AUTHORIZATION: basic " + base64.b64encode(
            ("x-access-token:" + token).encode()).decode("ascii")
        settings.append(("http." + AUTHORITY_URL + ".extraheader", header))
    env["GIT_CONFIG_COUNT"] = str(len(settings))
    for i, (key, value) in enumerate(settings):
        env[f"GIT_CONFIG_KEY_{i}"] = key
        env[f"GIT_CONFIG_VALUE_{i}"] = value
    return env


def head(url, token=""):
    p = run("git", "ls-remote", "--heads", url, "refs/heads/main",
            check=False, env=network_environment(url, token))
    if p.returncode or not p.stdout.strip():
        return None, "MAIN_READ_FAILED"
    fields = p.stdout.strip().split()
    if len(fields) != 2 or fields[1] != b"refs/heads/main":
        return None, "INVALID_MAIN_SUBJECT"
    try:
        sha = fields[0].decode("ascii")
    except UnicodeDecodeError:
        return None, "INVALID_MAIN_SUBJECT"
    return (sha, None) if OBJECT_ID.fullmatch(sha) else (None, "INVALID_MAIN_SUBJECT")


def fetch_repo(url, sha, dest, token=""):
    # Bare stores avoid worktree encoding, filters, executable-bit and symlink
    # normalization. Exact commit identity is checked after every remote fetch.
    run("git", "init", "-q", "--bare", str(dest))
    run("git", "-C", str(dest), "remote", "add", "origin", url)
    run("git", "-C", str(dest), "fetch", "-q", "--no-tags", "--depth=1",
        "origin", sha, env=network_environment(url, token))
    if git_value(dest, "FETCH_HEAD^{commit}") != sha:
        raise RuntimeError("FETCH_SUBJECT_MISMATCH")
    run("git", "-C", str(dest), "update-ref", "refs/heads/bench", sha)
    run("git", "-C", str(dest), "symbolic-ref", "HEAD", "refs/heads/bench")


@dataclass(frozen=True)
class Entry:
    mode: str
    kind: str
    oid: str


def tree_entries(repo, ref="HEAD"):
    output = run("git", "-C", str(repo), "ls-tree", "-r", "-z",
                 "--full-tree", ref).stdout
    entries = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        if (mode, kind) not in {("100644", "blob"), ("100755", "blob"),
                               ("120000", "blob"), ("160000", "commit")}:
            raise RuntimeError("UNSUPPORTED_TREE_ENTRY")
        if not path or path in entries or not OBJECT_ID.fullmatch(oid):
            raise RuntimeError("INVALID_TREE_ENTRY")
        entries[path] = Entry(mode, kind, oid)
    return entries


def files(repo, ref="HEAD"):
    return sorted(tree_entries(repo, ref))


def blob_digest(repo, entry):
    if entry.kind == "commit":
        # A gitlink binds a commit ID, not a locally present submodule blob.
        return None
    payload = run("git", "-C", str(repo), "cat-file", "blob", entry.oid).stdout
    object_bytes = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    algorithm = "sha1" if len(entry.oid) == 40 else "sha256"
    if hashlib.new(algorithm, object_bytes).hexdigest() != entry.oid:
        raise RuntimeError("BLOB_OBJECT_ID_MISMATCH")
    return hashlib.sha256(payload).digest()


def hash_path(repo, path, ref="HEAD"):
    """Content digest of an exact tree path; absence differs from read failure."""
    path = os.fsencode(path)
    entry = tree_entries(repo, ref).get(path)
    return None if entry is None else blob_digest(repo, entry)


def signature(repo, entry):
    if entry is None:
        return None
    return entry.mode, entry.kind, entry.oid, blob_digest(repo, entry)


def full_compare(a, b, universe=None, a_ref="HEAD", b_ref="HEAD"):
    left, right = tree_entries(a, a_ref), tree_entries(b, b_ref)
    paths = sorted(left.keys() | right.keys())
    if universe is not None and {os.fsencode(p) for p in universe} != set(paths):
        raise RuntimeError("INCOMPLETE_COMPARISON_UNIVERSE")
    return [p for p in paths
            if signature(a, left.get(p)) != signature(b, right.get(p))]


def import_subject(dest, source, sha):
    # Only disposable local stores are changed by this carrier.
    run("git", "-C", str(dest), "fetch", "-q", "--no-tags", "--update-shallow",
        str(source), sha)
    if git_value(dest, "FETCH_HEAD^{commit}") != sha:
        raise RuntimeError("LOCAL_IMPORT_SUBJECT_MISMATCH")


def delta_compare(a, b, a_ref="HEAD", b_ref="HEAD"):
    left, right = tree_entries(a, a_ref), tree_entries(b, b_ref)
    # Both exact commits must already be imported into a's object store.
    after = git_value(b, b_ref + "^{commit}")
    output = run("git", "-C", str(a), "diff", "--no-renames", "--no-ext-diff",
                 "--no-textconv", "--ignore-submodules=none", "--name-only",
                 "-z", a_ref, after, "--").stdout
    changed = sorted(p for p in output.split(b"\0") if p)
    if len(changed) != len(set(changed)):
        raise RuntimeError("DUPLICATE_DELTA_PATH")
    for path in changed:
        if signature(a, left.get(path)) == signature(b, right.get(path)):
            raise RuntimeError("DELTA_ENTRY_IDENTITY_MISMATCH")
    return changed


COMPARISONS = {"full": full_compare, "delta": delta_compare}


def path_digest(paths):
    return hashlib.sha256(b"\0".join(paths)).hexdigest()


def measure_local(a, b, repeats=REPEATS, clock=time.perf_counter):
    samples = {name: [] for name in COMPARISONS}
    reference = None
    for trial in range(repeats):
        outputs = {}
        # Alternate ordering to avoid always giving the delta lane a warm turn.
        order = ("full", "delta") if trial % 2 == 0 else ("delta", "full")
        for name in order:
            started = clock()
            outputs[name] = COMPARISONS[name](a, b)
            samples[name].append(clock() - started)
        if outputs["full"] != outputs["delta"]:
            raise RuntimeError("COMPARISON_RESULT_MISMATCH")
        if reference is not None and reference != outputs["full"]:
            raise RuntimeError("LOCAL_SUBJECT_CHANGED")
        reference = outputs["full"]
    medians = {name: statistics.median(values) for name, values in samples.items()}
    return {"status": "MEASURED", "scope": LOCAL_SCOPE,
            "excluded_phases": ["subject_binding", "remote_fetch",
                                "reconciliation", "fresh_readback"],
            "samples_s": samples, "medians_s": medians,
            "median_ratio_full_over_delta": medians["full"] / medians["delta"]
            if medians["delta"] else None,
            "changed_file_count": len(reference),
            "changed_paths_sha256": path_digest(reference),
            "result_equivalence_verified": True,
            "distributed_speedup_claim": False}


class LiveTransport:
    """Fixed read-only remote scope; credentials never reach the Mirror."""

    def __init__(self, token):
        if not token:
            raise ValueError("AUTHORITY_CREDENTIAL_REQUIRED")
        self.token = token

    def heads(self):
        ah, ae = head(AUTHORITY_URL, self.token)
        mh, me = head(MIRROR_URL)
        if not ah or not mh:
            raise CycleHold("HOLD_AUTHORITY_OR_MIRROR_MAIN_UNAVAILABLE")
        return ah, mh

    def fetch(self, role, sha, dest):
        if role == "authority":
            fetch_repo(AUTHORITY_URL, sha, dest, self.token)
        elif role == "mirror":
            fetch_repo(MIRROR_URL, sha, dest)
        else:
            raise ValueError("FIXED_REPOSITORY_SCOPE_REQUIRED")


def reconcile(authority, replica, subjects, changed):
    ah, mh = subjects
    if git_value(replica, "HEAD^{commit}") != mh:
        raise RuntimeError("REPLICA_BASE_MISMATCH")
    if changed != sorted(set(changed)):
        raise RuntimeError("INVALID_RECONCILIATION_DELTA")
    import_subject(replica, authority, ah)
    # CAS on a scratch ref; no push or production-Mirror mutation occurs.
    run("git", "-C", str(replica), "update-ref", "refs/heads/bench", ah, mh)


def fresh_readback(transport, replica, subjects, witness):
    ah, mh = subjects
    # Independent empty store and remote refetch: neither the comparison cache
    # nor FETCH_HEAD from reconciliation can stand in for readback evidence.
    transport.fetch("authority", ah, witness)
    observed_head = git_value(replica, "HEAD^{commit}")
    observed_tree = git_value(replica, "HEAD^{tree}")
    expected_tree = git_value(witness, "HEAD^{tree}")
    if observed_head != ah or observed_tree != expected_tree:
        raise RuntimeError("RECONCILIATION_READBACK_MISMATCH")
    if full_compare(replica, witness):
        raise RuntimeError("RECONCILIATION_OBJECT_READBACK_MISMATCH")
    if transport.heads() != (ah, mh):
        raise CycleHold("HOLD_REMOTE_SUBJECT_MOVED")
    return {"head": observed_head, "tree": observed_tree,
            "independent_remote_refetch": True,
            "all_blob_bytes_modes_and_objects_verified": True,
            "remote_subjects_reobserved_unchanged": True}


def end_to_end_cycle(transport, dest, subjects, method, clock=time.perf_counter):
    if method not in COMPARISONS:
        raise ValueError("UNKNOWN_COMPARISON_METHOD")
    started = clock()
    phases = {}
    completed = []
    changed = []
    readback = None

    def phase(name, operation):
        before = clock()
        value = operation()
        after = clock()
        phases[name] = {"start_offset_s": before - started,
                        "end_offset_s": after - started,
                        "duration_s": after - before}
        completed.append(name)
        return value

    def bind():
        if transport.heads() != subjects:
            raise CycleHold("HOLD_REMOTE_SUBJECT_MOVED")
        if subjects[0] == subjects[1]:
            raise CycleHold("HOLD_NEW_SUBJECT_NOT_ESTABLISHED")

    a, b, witness = (Path(dest) / name for name in ("authority", "replica", "witness"))

    def fetch():
        transport.fetch("authority", subjects[0], a)
        transport.fetch("mirror", subjects[1], b)
        import_subject(a, b, subjects[1])

    try:
        phase("bind_fixed_subjects", bind)
        phase("transport_fetch", fetch)
        changed = phase("comparison", lambda: COMPARISONS[method](a, b))
        phase("reconciliation", lambda: reconcile(a, b, subjects, changed))
        readback = phase("fresh_readback",
                         lambda: fresh_readback(transport, b, subjects, witness))
        status = "OBSERVED_SANDBOX_CYCLE"
    except CycleHold as exc:
        status = str(exc)
        readback = None
    elapsed = clock() - started
    return {"method": method, "scope": END_TO_END_SCOPE, "status": status,
            "elapsed_s": elapsed, "phases": phases,
            "completed_phases": completed,
            "complete_cycle_observed": tuple(completed) == PHASES
            and readback is not None,
            "fixed_subjects": {"authority": subjects[0], "mirror_base": subjects[1]},
            "changed_file_count": len(changed),
            "changed_paths_sha256": path_digest(changed), "readback": readback,
            "remote_mirror_mutated": False, "distributed_speedup_claim": False}


def measure_end_to_end(transport, dest, subjects, repeats=END_TO_END_REPEATS):
    cycles = []
    for trial in range(repeats):
        order = ("full", "delta") if trial % 2 == 0 else ("delta", "full")
        pair = {}
        for method in order:
            cycle = end_to_end_cycle(transport, Path(dest) / f"{trial}-{method}",
                                     subjects, method)
            cycles.append(cycle)
            if not cycle["complete_cycle_observed"]:
                return {"status": cycle["status"], "scope": END_TO_END_SCOPE,
                        "complete_cycle_observed": False, "cycles": cycles,
                        "distributed_speedup_claim": False}
            pair[method] = cycle
        for key in ("fixed_subjects", "changed_file_count", "changed_paths_sha256", "readback"):
            if pair["full"][key] != pair["delta"][key]:
                raise RuntimeError("END_TO_END_RESULT_MISMATCH")
    medians = {method: statistics.median(c["elapsed_s"] for c in cycles
                                        if c["method"] == method)
               for method in COMPARISONS}
    return {"status": "OBSERVED_SANDBOX_CYCLES", "scope": END_TO_END_SCOPE,
            "complete_cycle_observed": True, "cycles": cycles,
            "medians_s": medians, "fresh_stores_per_cycle": True,
            "sandbox_median_ratio_full_over_delta": medians["full"] / medians["delta"]
            if medians["delta"] else None,
            "distributed_speedup_claim": False}


def main():
    # Mirror GITHUB_TOKEN is never Authority evidence.
    token, source, present = credential({k: os.environ.get(k, "")
                                        for k in CREDENTIALS if k != "GITHUB_TOKEN"})
    result = {
        "schema": "qikvrt_live_authority_mirror_ab_v2",
        "authority_url": AUTHORITY_URL, "mirror_url": MIRROR_URL,
        "authority_head": None, "mirror_head": None,
        "local_repeats": REPEATS, "end_to_end_repeats": END_TO_END_REPEATS,
        "credential_source": source, "credential_names_present": present,
        "speedup_claim": False, "distributed_speedup_claim": False,
        "effect_ack_done": False, "predecessor_evidence_transfer": False,
        "executor_head": git_value(Path.cwd(), "HEAD^{commit}"),
        "executor_tree": git_value(Path.cwd(), "HEAD^{tree}"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "local_comparison": {"status": "NOT_OBSERVED", "scope": LOCAL_SCOPE},
        "end_to_end": {"status": "NOT_OBSERVED", "scope": END_TO_END_SCOPE,
                       "complete_cycle_observed": False},
        "distributed_cycle": {"status": "HOLD_PRODUCTION_REMOTE_RECONCILIATION_NOT_OBSERVED",
                              "complete_cycle_observed": False,
                              "remote_mirror_mutated": False,
                              "speedup_claim": False},
    }
    exit_code = 0
    if not token:
        result["status"] = "HOLD_AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED"
    else:
        try:
            transport = LiveTransport(token)
            subjects = transport.heads()
            result.update(authority_head=subjects[0], mirror_head=subjects[1])
            # Local setup is deliberately outside the local comparison clock.
            with tempfile.TemporaryDirectory(prefix="qikvrt-live-ab-") as td:
                a, b = Path(td) / "local-a", Path(td) / "local-b"
                before = time.perf_counter()
                transport.fetch("authority", subjects[0], a)
                transport.fetch("mirror", subjects[1], b)
                import_subject(a, b, subjects[1])
                result["local_setup_s"] = time.perf_counter() - before
                result.update(authority_tree=git_value(a, "HEAD^{tree}"),
                              mirror_tree=git_value(b, "HEAD^{tree}"))
                result["local_comparison"] = measure_local(a, b)
                result["end_to_end"] = measure_end_to_end(transport, td, subjects)
                result["status"] = ("MEASURED_LOCAL_AND_SANDBOX_END_TO_END"
                                    if result["end_to_end"]["complete_cycle_observed"]
                                    else result["end_to_end"]["status"])
        except CycleHold as exc:
            result["status"] = str(exc)
        except RuntimeError:
            result["status"] = "FAIL_BENCHMARK_OPERATION_OR_INVARIANT"
            exit_code = 1
    print(json.dumps(result, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
