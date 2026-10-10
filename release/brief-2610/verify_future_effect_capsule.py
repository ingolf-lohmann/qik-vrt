# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate a QIK-VRT future-effect capsule. Network-free, fail-closed.

Decides one thing: is the capsule's intended effect admitted, here and now?
Absence or ambiguity of evidence is never treated as success.

    python3 verify_future_effect_capsule.py CAPSULE.json [--tree-dir DIR]
      [--now ISO8601] [--custodian DIGEST ...] [--acceptor NAME]
"""
import argparse, datetime, hashlib, json, os, sys

CONTINUE, DONE = "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE"

def content_manifest_digest(root):
    """Format-independent content binding: no Git, no SHA-1, no object model.

    sha256 over "<sha256>  <relative/path>\\n" for every regular file
    outside .git, sorted by path.
    """
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            rows.append((rel, hashlib.sha256(open(full, "rb").read()).hexdigest()))
    rows.sort()
    agg = hashlib.sha256()
    for rel, digest in rows:
        agg.update((digest + "  " + rel + "\n").encode())
    return agg.hexdigest(), len(rows)

def evaluate(capsule, now, tree_dir, custodians, acceptor):
    results = []
    gate = capsule["admission_gate"]
    ladder = capsule["crypto_agility_ladder"]

    admit_from = datetime.datetime(2610, 1, 1, tzinfo=datetime.timezone.utc)
    results.append(("TEMPORAL_ADMISSION", now >= admit_from,
                    "reader time %s, admission opens %s" % (now.date(), admit_from.date())))

    if tree_dir:
        got, count = content_manifest_digest(tree_dir)
        want = capsule["subject_binding"]["content_manifest_sha256"]
        results.append(("EXACT_SUBJECT_BINDING", got == want,
                        "%d files, manifest %s vs bound %s" % (count, got[:12], want[:12])))
    else:
        results.append(("EXACT_SUBJECT_BINDING", False, "no --tree-dir supplied; binding unverified"))

    gens = ladder["ladder"]
    due = datetime.datetime.strptime(ladder["next_reseal_due_before"], "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc)
    continuous = now <= due or len(gens) > 1
    results.append(("CHAIN_CONTINUITY", continuous,
                    "%d generation(s), next re-seal due before %s" % (len(gens), due.date())))

    results.append(("INDEPENDENT_READBACK", len(set(custodians)) >= 2,
                    "%d distinct custodian digest(s) presented" % len(set(custodians))))

    results.append(("ACCEPTANCE", bool(acceptor), "acceptor: %s" % (acceptor or "none")))

    state = DONE if all(ok for _, ok, _ in results) else CONTINUE
    return state, results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("capsule")
    p.add_argument("--tree-dir")
    p.add_argument("--now")
    p.add_argument("--custodian", action="append", default=[])
    p.add_argument("--acceptor")
    a = p.parse_args()

    capsule = json.load(open(a.capsule))
    now = (datetime.datetime.fromisoformat(a.now) if a.now
           else datetime.datetime.now(datetime.timezone.utc))
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)

    state, results = evaluate(capsule, now, a.tree_dir, a.custodian, a.acceptor)
    print("capsule   : %s" % capsule["capsule_id"])
    print("reader now: %s" % now.isoformat())
    for name, ok, detail in results:
        print("  [%s] %-24s %s" % ("PASS" if ok else "    ", name, detail))
    print("effect_state: %s" % state)
    if state != DONE:
        print("ordinary_release: DENIED. The record is readable as history and inert as effect.")
        return 1
    print("ordinary_release: ADMITTED. Record the acceptance and seal the next generation.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
