#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""REST persistence for the existing lifecycle generator; never writes Main.

The small append-only data branch is telemetry, not a reviewed source branch.
Reuses Seed identity/TTL validation, the native governance gate and the Git-Data
object/readback pattern of qikvrt_self_heal_pr_materializer (PR #499/#501).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

try:
    from tools import qikvrt_seed_common as seed
    from tools.qikvrt_required_review_gate import native_code_owner_rule_is_enforced
except ModuleNotFoundError:  # Existing Seed shell entrypoint executes tools/ directly.
    import qikvrt_seed_common as seed
    from qikvrt_required_review_gate import native_code_owner_rule_is_enforced

LIVE_BRANCH = "qikvrt/node-lifecycle"
WORKFLOW = ".github/workflows/qikvrt_mirror_node_lifecycle.yml"
PUBLICATION_STEP = "Publish review-independent lifecycle snapshot"
FILES = ("NODE_HEALTH.json", "NODE_REGISTRATION_RENEWAL.json", "LIFECYCLE.json")
SOURCE_PATHS = (WORKFLOW, "tools/qikvrt_mirror_node_lifecycle.sh",
                "tools/qikvrt_mirror_node_lifecycle.py",
                "qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv")
SHA = re.compile(r"[0-9a-f]{40}\Z")


class Block(seed.SeedError):
    pass


class ApiError(Block):
    def __init__(self, status=None):
        self.status = status
        super().__init__(f"LIFECYCLE_API_{status or 'UNCERTAIN'}")


class Rest:
    """Fixed host, bounded reads, no redirects, retries or credential output."""
    def __init__(self, repository, token=""):
        seed._validate_repository(repository, "lifecycle repository")
        self.repository, self.token = repository, token
        self.opener = urllib.request.build_opener(seed._NoRedirect())

    def __call__(self, method, path, payload=None):
        if (path.startswith("/") or ".." in path or "#" in path
                or any(c.isspace() for c in path)):
            raise Block("LIFECYCLE_API_PATH_INVALID")
        if method != "GET" and not (
                method == "POST" and path in {"git/blobs", "git/trees", "git/commits", "git/refs", "pulls"}
                or method == "PATCH" and path == f"git/refs/heads/{LIVE_BRANCH}"):
            raise Block("LIFECYCLE_WRITE_SCOPE_INVALID")
        if method == "POST" and path == "git/refs":
            ref = (payload or {}).get("ref", "")
            if ref != f"refs/heads/{LIVE_BRANCH}" and not re.fullmatch(
                    r"refs/heads/automation/(?:mirror-lifecycle|seed-registry)-[0-9a-f]{24}", ref):
                raise Block("LIFECYCLE_WRITE_SCOPE_INVALID")
        if method == "POST" and path == "pulls" and not (
                (payload or {}).get("base") == "main" and (payload or {}).get("draft") is True
                and re.fullmatch(r"automation/seed-registry-[0-9a-f]{24}", (payload or {}).get("head", ""))):
            raise Block("LIFECYCLE_WRITE_SCOPE_INVALID")
        if method == "PATCH" and (payload or {}).get("force") is not False:
            raise Block("LIFECYCLE_FORCE_FORBIDDEN")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "qikvrt-lifecycle/1",
                   "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/{path}",
            data=None if payload is None else json.dumps(payload).encode(), headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read(2 * seed.MAX_INPUT_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code) from None
        except (OSError, urllib.error.URLError) as exc:
            raise ApiError() from None
        if len(raw) > 2 * seed.MAX_INPUT_BYTES:
            raise Block("LIFECYCLE_RESPONSE_TOO_LARGE")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            raise Block("LIFECYCLE_RESPONSE_INVALID") from None


def sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise Block("LIFECYCLE_SHA_INVALID")
    return value


def ref(api, branch, missing=False):
    try:
        value = api("GET", f"git/ref/heads/{branch}")
    except ApiError as exc:
        if missing and exc.status == 404:
            return None
        raise
    if value.get("ref") != f"refs/heads/{branch}" or value["object"]["type"] != "commit":
        raise Block("LIFECYCLE_REF_INVALID")
    return sha(value["object"]["sha"])


def blob_id(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def content(api, path, revision):
    value = api("GET", f"contents/{path}?ref={sha(revision)}")
    if value.get("type") != "file" or value.get("encoding") != "base64":
        raise Block("LIFECYCLE_CONTENT_INVALID")
    raw = base64.b64decode(value["content"], validate=False)
    if len(raw) > seed.MAX_INPUT_BYTES or blob_id(raw) != value["sha"]:
        raise Block("LIFECYCLE_CONTENT_HASH_MISMATCH")
    return raw


def upload_tree(api, files, base_tree=None):
    entries = []
    for path, raw in sorted(files.items()):
        expected = blob_id(raw)
        value = api("POST", "git/blobs", {"encoding": "base64", "content": base64.b64encode(raw).decode()})
        if value.get("sha") != expected:
            raise Block("LIFECYCLE_BLOB_READBACK_MISMATCH")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": expected})
    request = {"tree": entries}
    if base_tree:
        request["base_tree"] = sha(base_tree)
    return sha(api("POST", "git/trees", request)["sha"])


def snapshot(api, head):
    commit = api("GET", f"git/commits/{sha(head)}")
    if commit.get('sha') != head:
        raise Block('LIFECYCLE_COMMIT_READBACK_MISMATCH')
    tree = api("GET", f"git/trees/{sha(commit['tree']['sha'])}")
    if (tree.get("truncated") is not False or len(tree["tree"]) != len(FILES)
            or {e["path"] for e in tree["tree"]} != set(FILES)
            or any(e["type"] != "blob" or e["mode"] != "100644" for e in tree["tree"])):
        raise Block("LIFECYCLE_SNAPSHOT_TREE_INVALID")
    raw = {p: content(api, p, head) for p in FILES}
    for entry in tree["tree"]:
        if blob_id(raw[entry["path"]]) != entry["sha"]:
            raise Block("LIFECYCLE_SNAPSHOT_TREE_MISMATCH")
    values = {p: seed.parse_json_bytes(b, p) for p, b in raw.items()}
    manifest = values["LIFECYCLE.json"]
    if (manifest.get("schema") != "qikvrt_public_lifecycle_snapshot_v1"
            or manifest.get("main_persisted") is not False
            or manifest.get("effect_ack_done") is not False
            or manifest.get("review_state") != "UNREVIEWED_TELEMETRY"
            or manifest.get("source_head") not in [p["sha"] for p in commit["parents"]]
            or len(commit["parents"]) not in (1, 2)):
        raise Block("LIFECYCLE_SNAPSHOT_BINDING_INVALID")
    for p in FILES[:2]:
        if hashlib.sha256(raw[p]).hexdigest() != manifest["sha256"][p]:
            raise Block("LIFECYCLE_SNAPSHOT_HASH_MISMATCH")
    return values, raw


def validate_pair(values, node, now):
    health, renewal = (values[p] for p in FILES[:2])
    freshness, heartbeat, expiry = seed._validate_health(health, node, now)
    seed._validate_renewal(renewal, node)
    seed._require_exact(renewal, "node_branch", node.node_branch, "renewal")
    seed._require_exact(renewal, "status", "RENEWED", "renewal")
    seed._validate_boundaries(renewal.get("boundaries", {}), "renewal")
    if renewal.get("run_id") != health.get("run_id") or renewal.get("renewed_utc") != heartbeat:
        raise Block("LIFECYCLE_PAIR_MISMATCH")
    renewed = seed._parse_utc(renewal["renewed_utc"], "renewed")
    due = seed._parse_utc(renewal["next_renewal_due_utc"], "renewal due")
    if due <= renewed or due > renewed + dt.timedelta(hours=24, seconds=2):
        raise Block("LIFECYCLE_RENEWAL_WINDOW_INVALID")
    if freshness != "FRESH" or now > min(due, renewed + dt.timedelta(hours=24)):
        raise Block("LIFECYCLE_EXPIRED")
    return heartbeat, expiry


def publish(root, repository, source, run_id, api, now=None):
    now = now or seed._utc_now()
    source = sha(source)
    if not re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", run_id):
        raise Block("LIFECYCLE_RUN_INVALID")
    if ref(api, "main") != source:
        raise Block("LIFECYCLE_BASE_DRIFT")
    if not native_code_owner_rule_is_enforced(api("GET", "rules/branches/main")):
        raise Block("CODE_OWNER_RULE_NOT_ENFORCED")
    fields = next(l for l in (root / "qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv").read_text().splitlines()
                  if l and not l.startswith("#")).split("\t")
    node = seed.NodeRecord(fields[0], fields[1], fields[2], "", fields[5] or "main", int(fields[6] or 1500), "ACTIVE", "", 1)
    if (node.source_repository != repository or node.node_branch != "main"
            or not 1 <= node.heartbeat_ttl_minutes <= 10080):
        raise Block("LIFECYCLE_NODE_BINDING_INVALID")
    files = {p: (root / "qikvrt/runtime/onboarding" / p).read_bytes() for p in FILES[:2]}
    values = {p: seed.parse_json_bytes(b, p) for p, b in files.items()}
    validate_pair(values, node, now)
    if any(v.get("run_id") != run_id for v in values.values()):
        raise Block("LIFECYCLE_RUN_MISMATCH")
    for path in SOURCE_PATHS:
        if content(api, path, source) != (root / path).read_bytes():
            raise Block("LIFECYCLE_SOURCE_WORKTREE_MISMATCH")
    old = ref(api, LIVE_BRANCH, missing=True)
    if old:
        previous, _ = snapshot(api, old)
        prior = previous["LIFECYCLE.json"]
        if prior["repository"] != repository or prior["guid"] != node.guid:
            raise Block("LIFECYCLE_PREDECESSOR_IDENTITY_MISMATCH")
        if prior["run_id"] == run_id:
            if prior["source_head"] != source:
                raise Block("LIFECYCLE_REPLAY_SOURCE_MISMATCH")
            validate_pair(previous, node, now)  # Never renew a replay's clock.
            return {"state": "NOOP", "head": old, "source_head": source, "main_persisted": False}
        if seed._parse_utc(previous[FILES[0]]["heartbeat_utc"], "prior heartbeat") >= seed._parse_utc(values[FILES[0]]["heartbeat_utc"], "heartbeat"):
            raise Block("LIFECYCLE_OUT_OF_ORDER")
    files["LIFECYCLE.json"] = seed.canonical_json_bytes({
        "schema": "qikvrt_public_lifecycle_snapshot_v1", "repository": repository,
        "guid": node.guid, "source_head": source, "run_id": run_id, "workflow": WORKFLOW,
        "sha256": {p: hashlib.sha256(b).hexdigest() for p, b in files.items()},
        "main_persisted": False, "effect_ack_done": False, "review_state": "UNREVIEWED_TELEMETRY"})
    tree = upload_tree(api, files)
    parents = ([old] if old else []) + [source]
    head = sha(api("POST", "git/commits", {"tree": tree, "parents": parents,
               "message": f"chore(mesh): public lifecycle observation {run_id}"})["sha"])
    observed, raw = snapshot(api, head)
    if raw != files or ref(api, "main") != source or ref(api, LIVE_BRANCH, missing=True) != old:
        raise Block("LIFECYCLE_PREWRITE_DRIFT")
    # One non-force attempt. Divergent simultaneous writers cannot overwrite each other.
    error = None
    try:
        if old:
            api("PATCH", f"git/refs/heads/{LIVE_BRANCH}", {"sha": head, "force": False})
        else:
            api("POST", "git/refs", {"ref": f"refs/heads/{LIVE_BRANCH}", "sha": head})
    except ApiError as exc:
        error = exc
    if ref(api, LIVE_BRANCH, missing=True) != head:
        raise error or Block("LIFECYCLE_REF_READBACK_MISMATCH")
    _, readback = snapshot(api, head)
    if readback != files or ref(api, "main") != source:
        raise Block("LIFECYCLE_PUBLICATION_READBACK_MISMATCH")
    return {"state": "PUBLIC_TELEMETRY_READ_BACK", "head": head, "tree": tree,
            "source_head": source, "run_id": run_id, "main_persisted": False,
            "effect_ack_done": False, "review_state": "UNREVIEWED_TELEMETRY"}


def read_public(node, api, now):
    main, head = ref(api, "main"), ref(api, LIVE_BRANCH)
    values, raw = snapshot(api, head)
    manifest = values["LIFECYCLE.json"]
    if (manifest["repository"] != node.source_repository or manifest["guid"] != node.guid
            or manifest["workflow"] != WORKFLOW or manifest["run_id"] != values[FILES[0]]["run_id"]):
        raise Block("LIFECYCLE_PUBLIC_IDENTITY_MISMATCH")
    source = sha(manifest["source_head"])
    if not re.fullmatch(r'[1-9][0-9]*-[1-9][0-9]*', manifest['run_id']):
        raise Block('LIFECYCLE_RUN_INVALID')
    # The executing implementation/configuration must still match trusted Main.
    for path in SOURCE_PATHS:
        if content(api, path, source) != content(api, path, main):
            raise Block("LIFECYCLE_SOURCE_CONTRACT_CHANGED")
    relation = api("GET", f"compare/{source}...{main}")
    if relation.get("status") not in {"identical", "ahead"} or relation.get("behind_by") != 0:
        raise Block("LIFECYCLE_SOURCE_NOT_ON_MAIN")
    run_id, attempt = map(int, manifest["run_id"].split("-"))
    run = api("GET", f"actions/runs/{run_id}/attempts/{attempt}")
    if (run.get("id") != run_id or run.get("run_attempt") != attempt
            or run.get("repository", {}).get("full_name") != node.source_repository
            or run.get("head_sha") != source or run.get("head_branch") != "main"
            or run.get("path") != WORKFLOW or run.get("event") not in {"schedule", "workflow_dispatch"}):
        raise Block("LIFECYCLE_RUN_PROVENANCE_INVALID")
    jobs = api("GET", f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
    if jobs.get("total_count") != len(jobs.get("jobs", [])) or not any(
            j.get("head_sha") == source and any(s.get("name") == PUBLICATION_STEP and s.get("conclusion") == "success"
                for s in j.get("steps", [])) for j in jobs.get("jobs", [])):
        raise Block("LIFECYCLE_PUBLICATION_STEP_UNVERIFIED")
    validate_pair(values, node, now)
    heartbeat = seed._parse_utc(values[FILES[0]]["heartbeat_utc"], "heartbeat")
    start = seed._parse_utc(run["run_started_at"], "run start")
    if not start - dt.timedelta(minutes=5) <= heartbeat <= start + dt.timedelta(minutes=10):
        raise Block("LIFECYCLE_RUN_CLOCK_MISMATCH")
    ack_raw = content(api, "qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json", main)
    ack = seed.parse_json_bytes(ack_raw, "seed acknowledgement")
    seed._validate_ack(ack, node)
    if ref(api, "main") != main or ref(api, LIVE_BRANCH) != head:
        raise Block("LIFECYCLE_READ_DRIFT")
    pair = tuple(seed.FetchedJson(values[p], hashlib.sha256(raw[p]).hexdigest()) for p in FILES[:2])
    return (*pair, seed.FetchedJson(ack, hashlib.sha256(ack_raw).hexdigest())), head


def publish_candidate(root, repository, base, head, tree, branch, api):
    """Preserve #480's exact local candidate through create-only REST Git Data."""
    if not re.fullmatch(r"automation/mirror-lifecycle-[0-9a-f]{24}", branch):
        raise Block("LIFECYCLE_CANDIDATE_BRANCH_INVALID")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)
    if ref(api, "main") != base:
        raise Block("LIFECYCLE_BASE_DRIFT")
    paths = git("diff", "--name-only", base, head).decode().splitlines()
    run_id = os.environ['QIKVRT_RUN_ID']
    allowed = {'qikvrt/runtime/onboarding/' + p for p in FILES[:2]}
    allowed.update({f'evidence/{d}/{r}.json' for d in ('node_health', 'node_registration_renewal')
                    for r in ('LATEST', run_id)})
    allowed.update({'REPOSITORY_FILE_MANIFEST.json', 'REPOSITORY_FILE_MANIFEST.json.sha256', 'SHA256SUMS.txt'})
    allowed.update({'qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json',
                    f'evidence/node_seed_acknowledgement/runs/{run_id}.json',
                    'evidence/node_seed_acknowledgement/LATEST.json'})
    if not paths or set(paths) - allowed:
        raise Block('LIFECYCLE_NON_ALLOWLISTED_DELTA')
    files = {p: git("show", f"{head}:{p}") for p in paths}
    remote_tree = upload_tree(api, files, api("GET", f"git/commits/{base}")["tree"]["sha"])
    if remote_tree != tree:
        raise Block("LIFECYCLE_CANDIDATE_TREE_MISMATCH")
    # GitHub creates the commit; return its exact identity to the existing PR contract.
    remote = sha(api("POST", "git/commits", {"tree": tree, "parents": [base],
                      "message": "chore(mesh): renew mirror node lifecycle"})["sha"])
    current = ref(api, branch, missing=True)
    if current is None:
        if ref(api, "main") != base:
            raise Block("LIFECYCLE_BASE_DRIFT")
        try:
            api("POST", "git/refs", {"ref": f"refs/heads/{branch}", "sha": remote})
        except ApiError:
            pass  # Reobserve once; never retry the POST.
        current = ref(api, branch, missing=True)
    commit = api("GET", f"git/commits/{sha(current)}")
    if commit["tree"]["sha"] != tree or [p["sha"] for p in commit["parents"]] != [base]:
        raise Block("LIFECYCLE_CANDIDATE_READBACK_MISMATCH")
    return current


def propose_seed(root, repository, source, run_id, api):
    """Reuse the exact-head Git Data handoff for reviewed Seed output, never Main."""
    from tools import qikvrt_integrity as integrity
    source = sha(source)
    seed._validate_run_id(run_id)
    if ref(api, "main") != source:
        raise Block("SEED_BASE_DRIFT")
    if not native_code_owner_rule_is_enforced(api("GET", "rules/branches/main")):
        raise Block("CODE_OWNER_RULE_NOT_ENFORCED")
    nodes, policies = seed.load_nodes(root, repository)
    summary = seed.read_json(root / "evidence/seed_acceptance/LATEST.json")
    seed._require_exact(summary, "status", "PASS", "Seed acceptance")
    seed._require_exact(summary, "run_id", run_id, "Seed acceptance")
    seed._require_exact(summary, "seed_repository", repository, "Seed acceptance")
    index, status = seed.validate_aggregate_pair(root, repository)
    seed.validate_revalidation(root, status, repository)
    seed._require_exact(index, "run_id", run_id, "Seed index")
    for node in nodes:
        state, error = seed._validated_registry_entry(root, node, policies[node.guid])
        if error:
            raise Block(error)
        entry = seed.read_json(root / f"registry/nodes/{node.guid}.json")
        seed._require_exact(entry, "last_acceptance_run_id", run_id, "Seed entry")
    workflow = ".github/workflows/qikvrt_seed_registry_acceptance.yml"
    for path in (workflow, "tools/qikvrt_seed_common.py", "tools/qikvrt_mirror_node_lifecycle.py",
                 "registry/KNOWN_NODE_REQUESTS.tsv", "registry/NODE_POLICY.tsv"):
        if content(api, path, source) != (root / path).read_bytes():
            raise Block("SEED_SOURCE_WORKTREE_MISMATCH")
    allowed = {"registry/NODEMESH_INDEX.json", "registry/NODEMESH_STATUS.json",
               "registry/NODEMESH_REVALIDATION.json", "ledger/NODE_REGISTRATION_LEDGER.jsonl"}
    allowed.update(f"registry/nodes/{node.guid}.json" for node in nodes)
    allowed.update(f"evidence/seed_acceptance/{node.guid}.json" for node in nodes)
    allowed.update(f"evidence/{kind}/{item}.json" for kind in
                   ("seed_acceptance", "seed_mesh_maintenance", "seed_node_revalidation")
                   for item in ("LATEST", "runs/" + run_id))
    trio = {"REPOSITORY_FILE_MANIFEST.json", "REPOSITORY_FILE_MANIFEST.json.sha256", "SHA256SUMS.txt"}
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)
    if git("rev-parse", "HEAD").decode().strip() != source:
        raise Block("SEED_LOCAL_HEAD_MISMATCH")
    changed = set(git("diff", "--name-only", source).decode().splitlines())
    untracked = {p for p in git("ls-files", "--others", "--exclude-standard").decode().splitlines()
                 if not integrity.is_transient(p)}
    if (changed | untracked) - allowed - trio:
        raise Block("SEED_NON_ALLOWLISTED_DELTA")
    integrity.generate(root)
    if not integrity.verify(root).ok:
        raise Block("SEED_INTEGRITY_FAILED")
    git("add", "--", *sorted(p for p in allowed | trio if (root / p).is_file()))
    paths = git("diff", "--cached", "--name-only", source).decode().splitlines()
    if not paths or set(paths) - allowed - trio:
        raise Block("SEED_NON_ALLOWLISTED_DELTA")
    tree = git("write-tree").decode().strip()
    branch = "automation/seed-registry-" + hashlib.sha256((source + tree).encode()).hexdigest()[:24]
    existing = ref(api, branch, missing=True)
    if existing is None:
        remote_tree = upload_tree(api, {p: (root / p).read_bytes() for p in paths},
                                  api("GET", f"git/commits/{source}")["tree"]["sha"])
        if remote_tree != tree or ref(api, "main") != source:
            raise Block("SEED_CANDIDATE_TREE_OR_BASE_MISMATCH")
        existing = sha(api("POST", "git/commits", {"tree": tree, "parents": [source],
                           "message": f"chore(mesh): review Seed acceptance {run_id}"})["sha"])
        if ref(api, "main") != source:
            raise Block("SEED_BASE_DRIFT")
        try:
            api("POST", "git/refs", {"ref": f"refs/heads/{branch}", "sha": existing})
        except ApiError:
            pass  # One readback, no repeated write after ambiguous response.
    if ref(api, branch) != existing:
        raise Block("SEED_BRANCH_READBACK_MISMATCH")
    commit = api("GET", f"git/commits/{existing}")
    if commit.get("sha") != existing or commit["tree"]["sha"] != tree or [p["sha"] for p in commit["parents"]] != [source]:
        raise Block("SEED_COMMIT_READBACK_MISMATCH")
    if ref(api, "main") != source:
        raise Block("SEED_BASE_DRIFT")
    prs = api("GET", f"pulls?state=all&head={repository.split('/')[0]}:{branch}&per_page=100")
    if not isinstance(prs, list) or len(prs) > 1:
        raise Block("SEED_PR_INVENTORY_AMBIGUOUS")
    if prs:
        number = prs[0]["number"]
    else:
        number = api("POST", "pulls", {"base": "main", "head": branch, "draft": True,
                     "title": f"chore(mesh): review Seed acceptance {run_id}",
                     "body": f"Seed output from {source}; candidate {existing}, tree {tree}. "
                             "Generated output is a Draft proposal. No Main persistence, node acknowledgement, "
                             "live runtime acceptance or EFFECT_ACK_DONE is claimed. "
                             "Fresh exact-head gates and native Code Owner review remain required."})["number"]
    pr = api("GET", f"pulls/{number}")
    if not (pr.get("state") == "open" and pr.get("draft") is True
            and pr["head"]["sha"] == existing and pr["head"]["ref"] == branch
            and pr["head"]["repo"]["full_name"] == repository
            and pr["base"]["ref"] == "main" and pr["base"]["sha"] == source
            and ref(api, "main") == source):
        raise Block("SEED_PR_READBACK_MISMATCH")
    return {"state": "DRAFT_READ_BACK", "head": existing, "tree": tree,
            "base_head": source, "pull_request": number, "main_persisted": False,
            "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("publish", "candidate", "seed-review"))
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    if not os.environ.get("GH_TOKEN"):
        raise Block("LIFECYCLE_TOKEN_UNAVAILABLE")
    api = Rest(repository, os.environ["GH_TOKEN"])
    if args.operation == "seed-review":
        try:
            result = propose_seed(Path('.'), repository, os.environ['GITHUB_SHA'], os.environ['QIKVRT_RUN_ID'], api)
        except (seed.SeedError, KeyError, TypeError, ValueError, OSError) as exc:
            seed.write_json(Path(os.environ['LIFECYCLE_RECEIPT_DIR']) / 'PERSISTENCE.json', {
                'state': 'BLOCK', 'first_blocker': str(exc) if isinstance(exc, seed.SeedError) else 'SEED_INPUT_INVALID',
                'source_head': os.environ.get('GITHUB_SHA'), 'main_persisted': False, 'effect_ack_done': False})
            raise
        seed.write_json(Path(os.environ['LIFECYCLE_RECEIPT_DIR']) / 'PERSISTENCE.json', result)
        print(json.dumps(result, sort_keys=True))
    elif args.operation == "candidate":
        print(publish_candidate(Path('.'), repository, os.environ['BASE_SHA'], os.environ['CANDIDATE_HEAD'],
                                os.environ['CANDIDATE_TREE'], os.environ['CANDIDATE_BRANCH'], api))
    else:
        try:
            result = publish(Path('.'), repository, os.environ['GITHUB_SHA'], os.environ['QIKVRT_RUN_ID'], api)
        except (seed.SeedError, KeyError, TypeError, ValueError, OSError) as exc:
            seed.write_json(Path(os.environ['LIFECYCLE_RECEIPT_DIR']) / 'PUBLICATION.json', {
                'state': 'BLOCK', 'first_blocker': str(exc) if isinstance(exc, seed.SeedError) else 'LIFECYCLE_INPUT_INVALID',
                'source_head': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('QIKVRT_RUN_ID'),
                'main_persisted': False, 'effect_ack_done': False})
            raise
        seed.write_json(Path(os.environ['LIFECYCLE_RECEIPT_DIR']) / 'PUBLICATION.json', result)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Block, seed.SeedError, KeyError, ValueError, OSError) as exc:
        print(f"BLOCK {exc}", file=__import__('sys').stderr)
        raise SystemExit(2)
