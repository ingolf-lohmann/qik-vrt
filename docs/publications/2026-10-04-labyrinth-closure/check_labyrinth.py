# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent exhaustive finite-model checks and adversarial boundary checks."""
import argparse
import copy
import hashlib
import itertools
import json
import platform
import os
import re
import subprocess
import sys
from pathlib import Path
from labyrinth import classify, explore, snapshot_graph, verify_certificate

THEOREMS = ["reverse_is_same_portal", "grow_preserves_soundness",
            "grow_is_monotone", "two_witnesses_are_sound",
            "closed_set_covers_reachable", "connected_closed_set_covers_all",
            "no_infinite_strict_rank_descent", "complete_empty_is_zero",
            "complete_singleton_is_unique", "partial_empty_does_not_imply_zero"]


def kernel_check(lean, output):
    """Check the exact model source, its dependencies, and a false negative."""
    source = Path(__file__).with_name("LabyrinthClosure.lean").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compiled = output.with_suffix(".olean")
    version = subprocess.run([str(lean), "--version"], capture_output=True, text=True, timeout=30)
    result = {"schema": "qikvrt_labyrinth_kernel_evidence_v1",
              "status": "BLOCKED", "kernel_verified": False,
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "source_git_blob_sha1": hashlib.sha1(
                  f"blob {source.stat().st_size}\0".encode() + source.read_bytes()).hexdigest(),
              "source_bytes": source.stat().st_size,
              "lean_version_exit": version.returncode,
              "lean_version_stdout": version.stdout,
              "lean_version_stderr": version.stderr,
              "scope": "Ten abstract model lemmas only; no Python refinement, stochastic theorem, or production conformance.",
              "github_context": {k: os.environ.get(k) for k in
                                  ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")}}
    def save():
        output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if version.returncode or not re.search(r"version 4\.19\.0(?:\s|,)", version.stdout):
        result["blocker"] = "Declared Lean 4.19.0 compiler cannot be verified"
        save()
        raise RuntimeError(result["blocker"])
    result["lean_githash"] = subprocess.check_output([str(lean), "--githash"], text=True, timeout=30).strip()
    argv = [str(lean), "-E", "hasSorry", "--root=" + str(source.parent),
            "-o", str(compiled), str(source)]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    log = run.stdout + run.stderr
    output.with_suffix(".log").write_text(log, encoding="utf-8")
    result.update({"command": argv, "exit_code": run.returncode,
                   "log_sha256": hashlib.sha256(log.encode()).hexdigest()})
    pattern = re.compile(r"'([^']+)' (?:does not depend on any axioms|depends on axioms:\s*\[([^]]*)\])")
    audit = []
    for line in log.splitlines():
        m = pattern.fullmatch(line)
        if not m:
            result["blocker"] = "Unexpected compiler/audit output"
            save()
            raise RuntimeError(log)
        axioms = [x.strip() for x in (m.group(2) or "").split(",") if x.strip()]
        audit.append({"theorem": m.group(1), "axioms": axioms})
    expected = ["QIKVRT.Labyrinth." + t for t in THEOREMS]
    if run.returncode or [a["theorem"] for a in audit] != expected or any(
            set(a["axioms"]) - {"propext", "Classical.choice", "Quot.sound"} for a in audit):
        result["blocker"] = "Compilation, exact theorem inventory, or dependency audit failed"
        save()
        raise RuntimeError(result["blocker"] + "\n" + log)
    negative = output.with_name("KernelNegative.lean")
    negative.write_text("import Std\nexample : False := by decide\n", encoding="utf-8")
    reject = subprocess.run([str(lean), "-E", "hasSorry", str(negative)],
                            capture_output=True, text=True, timeout=30)
    result.update({"false_statement_rejected": reject.returncode != 0,
                   "negative_exit_code": reject.returncode,
                   "negative_output_sha256": hashlib.sha256((reject.stdout + reject.stderr).encode()).hexdigest(),
                   "axiom_audit": audit,
                   "compiled_object_sha256": hashlib.sha256(compiled.read_bytes()).hexdigest()})
    if reject.returncode == 0:
        result["blocker"] = "False negative statement was accepted"
        save()
        raise RuntimeError(result["blocker"])
    result.update({"status": "KERNEL_VERIFIED_WITHIN_DECLARED_MODEL_LEMMAS",
                   "kernel_verified": True})
    save()
    return result


def rejects(fn):
    try:
        fn()
    except (ValueError, KeyError):
        return
    raise AssertionError("invalid evidence unexpectedly accepted")


def run(max_vertices=5):
    counts = {"graphs": 0, "graph_partition_start_cases": 0,
              "connected_cases": 0, "disconnected_cases": 0,
              "negative_checks": 0, "counts_by_vertices": {}}
    for n in range(1, max_vertices + 1):
        possible = list(itertools.combinations(range(n), 2))
        local = {"graphs": 0, "cases": 0}
        for mask in range(1 << len(possible)):
            graph = {v: [] for v in range(n)}
            edges = [e for i, e in enumerate(possible) if mask & (1 << i)]
            for a, b in edges:
                graph[a].append(b)
                graph[b].append(a)
            graph = snapshot_graph(graph)
            counts["graphs"] += 1
            local["graphs"] += 1
            for partition in range(1 << n):
                inside = {v: bool(partition & (1 << v)) for v in graph}
                # Direct cut enumeration is independent of the exploration.
                global_cut = {e for e in edges if inside[e[0]] != inside[e[1]]}
                for start in graph:
                    cert = explore(graph.__getitem__, inside.__getitem__, start)
                    result = verify_certificate(graph, inside, cert)
                    component = {v for v, _ in cert["expanded_rows"]}
                    expected = {e for e in global_cut if e[0] in component}
                    assert {tuple(e) for e in cert["portals"]} == expected
                    assert result["portal_count"] == len(expected)
                    assert result["global_complete"] == (len(component) == n)
                    counts["graph_partition_start_cases"] += 1
                    counts["connected_cases" if result["global_complete"] else "disconnected_cases"] += 1
                    local["cases"] += 1
        counts["counts_by_vertices"][str(n)] = local

    # No discovery cannot be promoted to ZERO; one discovery is not EXACTLY_ONE.
    assert classify([], False) == "UNDETERMINED"
    assert classify([(0, 1)], False) == "AT_LEAST_ONE"
    assert classify([(0, 1), (1, 2)], False) == "MORE_THAN_ONE"
    assert classify([(0, 1), (1, 0)], False) == "AT_LEAST_ONE"
    counts["negative_checks"] += 4
    # Reverse traversal has the same identity when canonicalised by the explorer.
    line = {0: [1], 1: [0]}
    inside = {0: False, 1: True}
    cert = explore(line.__getitem__, inside.__getitem__, 0)
    assert cert["portals"] == [[0, 1]]
    counts["negative_checks"] += 1
    for field in ("portals", "inspected_edges", "expanded_rows"):
        bad = copy.deepcopy(cert)
        bad[field] = []
        rejects(lambda: verify_certificate(line, inside, bad))
        counts["negative_checks"] += 1
    bad = copy.deepcopy(cert)
    bad["portals"].append([1, 0])
    rejects(lambda: verify_certificate(line, inside, bad))
    counts["negative_checks"] += 1
    bad = copy.deepcopy(cert)
    bad["classification"] = "ZERO"
    rejects(lambda: verify_certificate(line, inside, bad))
    counts["negative_checks"] += 1
    bad = copy.deepcopy(cert)
    bad["expanded_rows"][0][1] = []
    rejects(lambda: verify_certificate(line, inside, bad))
    counts["negative_checks"] += 1
    bad = copy.deepcopy(cert)
    bad["expanded_rows"].append(copy.deepcopy(bad["expanded_rows"][0]))
    rejects(lambda: verify_certificate(line, inside, bad))
    counts["negative_checks"] += 1
    for graph in ({0: [1], 1: []}, {0: [0]}, {0: [1, 1], 1: [0]}, {0: [2]}):
        rejects(lambda: snapshot_graph(graph))
        counts["negative_checks"] += 1
    # Globally hidden portal: one component has no portal, another has one.
    hidden = {0: [1], 1: [0], 2: [3], 3: [2]}
    side = {0: False, 1: False, 2: True, 3: False}
    hidden_cert = explore(hidden.__getitem__, side.__getitem__, 0)
    assert hidden_cert["classification"] == "ZERO"
    assert not verify_certificate(hidden, side, hidden_cert)["global_complete"]
    rejects(lambda: verify_certificate(hidden, side, hidden_cert, require_global=True))
    counts["negative_checks"] += 1
    # Visiting all vertices does not imply traversing all cut edges.
    triangle = {(0, 1), (0, 2), (1, 2)}
    walk = [0, 2, 1]
    walked = {tuple(sorted(e)) for e in zip(walk, walk[1:])}
    assert set(walk) == {0, 1, 2}
    assert {(0, 1), (1, 2)} - walked == {(0, 1)}
    counts["negative_checks"] += 1
    # Every finite number of failed trials has positive exact probability.
    from fractions import Fraction
    assert all(Fraction(1, 2) ** k > 0 for k in (1, 2, 10, 100, 1000))
    counts["negative_checks"] += 1
    return {
        "schema": "qikvrt_labyrinth_exhaustive_check_v1",
        "status": "PASS_WITHIN_DECLARED_FINITE_TEST_SCOPE",
        "scope": {"model": "all labelled simple undirected graphs, all Boolean partitions, every start",
                  "max_vertices": max_vertices, "includes_disconnected_graphs": True},
        "counts": counts,
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation()},
        "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ("labyrinth.py", "check_labyrinth.py")},
        "proof_assistant_kernel_verified": False,
        "tests_are_not_an_unbounded_theorem_proof": True,
        "production_qikvrt_conformance_proved": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-vertices", type=int, default=5, choices=range(1, 7))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--lean", type=Path)
    parser.add_argument("--kernel-output", type=Path)
    args = parser.parse_args()
    result = run(args.max_vertices)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    if args.lean:
        if not args.kernel_output:
            parser.error("--lean requires --kernel-output")
        print(json.dumps(kernel_check(args.lean.resolve(), args.kernel_output.resolve()), indent=2))
