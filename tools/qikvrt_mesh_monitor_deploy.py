#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""One exact deployment of the existing monitor; no interactive admission path.

Uses the already staged Railway patch, the existing redirect guard, bounded
subprocess runner and the monitor's own independent client validator. No CLI
installation, source upload, service creation, merge or governance mutation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.qikvrt_subprocess import run_bounded
from tools.qikvrt_zenodo_actions import NoRedirectHandler, SafeArgumentParser
from tools.qikvrt_workflow_executor import canonical_json_bytes

REPOSITORY = "ingolf-lohmann/qik-vrt"
SOURCE_HEAD = "674aa35ec0659119a19cda66b88f32050e34f105"
SOURCE_TREE = "5100b66a299ded9ecb64622d2d36a5a77ef1f85d"
PROJECT = "a2440de5-6250-4d02-8845-c166aeaa3d0d"
ENVIRONMENT = "1286f33e-9f11-43d9-b86c-be5df57718a0"
SERVICE = "dc3773e0-d057-4779-b9c1-9ca0f2074f69"
VOLUME = "e802140e-b6a9-476c-a937-dde322253539"
PATCH = "9d4860c4-5003-48ef-a07f-d383f303b539"
PUBLIC = "https://mesh-monitor-production.up.railway.app"
CONTRACT_PATH = "state/deployments/MESH_MONITOR_RAILWAY_EXACT_674aa35.json"
LOCK = "tags/qikvrt-monitor-deploy/" + SOURCE_HEAD
API = "https://backboard.railway.com/graphql/v2"
MAX_BYTES = 8 * 1024 * 1024
ACTIVE = {"INITIALIZING", "QUEUED", "WAITING", "BUILDING", "DEPLOYING"}
EXPECTED_VARIABLES = {
    "QIKVRT_MONITOR_NODE_ID": "mirror:ingolf-lohmann/qik-vrt",
    "QIKVRT_MONITOR_SOURCE_HEAD": SOURCE_HEAD,
    "QIKVRT_MONITOR_SOURCE_TREE": SOURCE_TREE,
    "QIKVRT_MONITOR_SOURCE_REPOSITORY": REPOSITORY,
    "QIKVRT_MONITOR_STATE_DIR": "/var/lib/qikvrt/monitor",
}
EXPECTED_SETTINGS = {
    "source.repo": REPOSITORY,
    "source.branch": "candidate/mesh-monitor-mirror-20261004-29a55ae4",
    "source.commitSha": SOURCE_HEAD,
    "source.rootDirectory": "/docs/monitor",
    "source.image": None,
    "build.builder": "RAILPACK",
    "build.buildCommand": "npm test",
    "build.watchPatterns": ["docs/monitor/**"],
    "deploy.startCommand": "npm start",
    "deploy.healthcheckPath": "/health",
    "deploy.healthcheckTimeout": 60,
    "deploy.restartPolicyType": "ALWAYS",
    "deploy.restartPolicyMaxRetries": 3,
    "deploy.sleepApplication": False,
    "deploy.multiRegionConfig": {"iad": {"numReplicas": 1}},
    "volumeMounts": {VOLUME: {"mountPath": "/var/lib/qikvrt/monitor"}},
}
OBSERVE = """query MonitorDeployment($environmentId: String!, $serviceId: String!) {
  environment(id: $environmentId) {
    id projectId name isEphemeral config(decryptVariables: true)
    volumeInstances { edges { node { volumeId serviceId mountPath state } } }
  }
  serviceInstance(serviceId: $serviceId, environmentId: $environmentId) {
    serviceName latestDeployment { id status meta }
  }
  environmentStagedChanges(environmentId: $environmentId) {
    id status patch(decryptVariables: true)
  }
}"""
COMMIT = """mutation CommitMonitorPatch($environmentId: String!, $commitMessage: String!) {
  environmentPatchCommitStaged(environmentId: $environmentId, commitMessage: $commitMessage)
}"""
DEPLOY = """mutation DeployExactMonitor($environmentId: String!, $serviceId: String!, $commitSha: String!) {
  serviceInstanceDeployV2(environmentId: $environmentId, serviceId: $serviceId, commitSha: $commitSha)
}"""


class Hold(RuntimeError):
    """Only static, safe capability/verification codes cross this boundary."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def at(value: dict, path: str) -> object:
    result = value
    for part in path.split("."):
        if not isinstance(result, dict) or part not in result:
            raise Hold("HOLD_RAILWAY_CONFIGURATION_INCOMPLETE")
        result = result[part]
    return result


def merge(base: dict, patch: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in patch.items():
        result[key] = merge(result.get(key, {}), value) if isinstance(value, dict) else copy.deepcopy(value)
    return result


class Api:
    def __init__(self, env: dict):
        project_token, account_token = env.get("RAILWAY_TOKEN"), env.get("RAILWAY_API_TOKEN")
        require(bool(project_token or account_token), "HOLD_RAILWAY_SERVER_CREDENTIAL_UNAVAILABLE")
        require(not (project_token and account_token), "HOLD_AMBIGUOUS_RAILWAY_CREDENTIAL")
        self.token = project_token or account_token
        require(not any(c.isspace() for c in self.token), "HOLD_INVALID_RAILWAY_CREDENTIAL")
        self.railway_header = {"Project-Access-Token": self.token} if project_token else {"Authorization": "Bearer " + self.token}
        self.github_token = env.get("GITHUB_TOKEN", "")
        self.opener = urllib.request.build_opener(NoRedirectHandler())

    def request(self, url: str, method: str, headers: dict, body: object = None, *, missing: bool = False) -> dict | None:
        require(url == API or url.startswith("https://api.github.com/repos/" + REPOSITORY + "/git/"), "HOLD_API_ORIGIN_NOT_ALLOWLISTED")
        request = urllib.request.Request(url, data=None if body is None else canonical_json_bytes(body), method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "qikvrt-mesh-monitor-deploy/1", **headers})
        try:
            with self.opener.open(request, timeout=30) as response:
                require(response.geturl() == url, "HOLD_API_REDIRECT")
                raw = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404 and missing:
                return None
            raise Hold("HOLD_API_HTTP_" + str(error.code)) from None
        except (OSError, urllib.error.URLError):
            raise Hold("HOLD_API_TRANSPORT_UNVERIFIED") from None
        require(len(raw) <= MAX_BYTES, "HOLD_API_RESPONSE_TOO_LARGE")
        # Never echo upstream errors, configs, variable values or bearer data.
        require(self.token.encode() not in raw and (not self.github_token or self.github_token.encode() not in raw), "HOLD_API_CREDENTIAL_ECHO")
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            raise Hold("HOLD_API_INVALID_JSON") from None
        require(isinstance(value, dict), "HOLD_API_INVALID_SHAPE")
        return value

    def gql(self, query: str, variables: dict) -> dict:
        operation = query.split("(", 1)[0].strip()
        print(json.dumps({"repository": REPOSITORY, "source_head": SOURCE_HEAD, "operation": operation, "stage": "BEGIN"}), file=sys.stderr)
        result = self.request(API, "POST", self.railway_header, {"query": query, "variables": variables})
        require(not result.get("errors"), "HOLD_RAILWAY_API_REJECTED")
        require(isinstance(result.get("data"), dict), "HOLD_RAILWAY_API_INCOMPLETE")
        print(json.dumps({"repository": REPOSITORY, "source_head": SOURCE_HEAD, "operation": operation, "stage": "READBACK_RECEIVED"}), file=sys.stderr)
        return result["data"]

    def github(self, method: str, path: str, body: object = None, *, missing: bool = False) -> dict | None:
        require(bool(self.github_token), "HOLD_GITHUB_DEPLOYMENT_LOCK_CAPABILITY_UNAVAILABLE")
        print(json.dumps({"repository": REPOSITORY, "source_head": SOURCE_HEAD, "operation": "Git-Data " + method, "stage": "BEGIN"}), file=sys.stderr)
        result = self.request("https://api.github.com/repos/" + REPOSITORY + "/git/" + path, method,
            {"Authorization": "Bearer " + self.github_token, "X-GitHub-Api-Version": "2022-11-28"}, body, missing=missing)
        print(json.dumps({"repository": REPOSITORY, "source_head": SOURCE_HEAD, "operation": "Git-Data " + method, "stage": "READBACK_RECEIVED"}), file=sys.stderr)
        return result

    def observe(self) -> dict:
        return self.gql(OBSERVE, {"environmentId": ENVIRONMENT, "serviceId": SERVICE})


def validate_observation(observed: dict) -> tuple[dict, dict | None, dict, bool]:
    environment, instance = observed["environment"], observed["serviceInstance"]
    require(environment["id"] == ENVIRONMENT and environment["projectId"] == PROJECT and
            environment["name"] == "production" and environment["isEphemeral"] is False and
            instance["serviceName"] == "mesh-monitor", "HOLD_RAILWAY_TARGET_MISMATCH")
    live = environment["config"]
    staged = observed["environmentStagedChanges"]
    pending = staged if staged and staged.get("status") == "STAGED" and staged.get("patch") else None
    require(not staged or staged.get("status") in {"STAGED", "COMMITTED"}, "HOLD_RAILWAY_PATCH_NOT_SETTLED")
    if pending:
        require(pending["id"] == PATCH, "HOLD_RAILWAY_STAGED_PATCH_ID_CHANGED")
        patch = pending["patch"]
        require(set(patch) <= {"services", "volumes"} and set(patch.get("services", {})) == {SERVICE} and
                set(patch.get("volumes", {})) == {VOLUME}, "HOLD_RAILWAY_UNRELATED_STAGED_RESOURCE")
        service_patch = patch["services"][SERVICE]
        allowed = {
            "source": {"repo", "branch", "commitSha", "image", "rootDirectory"},
            "build": {"buildCommand", "watchPatterns"},
            "deploy": {"startCommand", "healthcheckPath", "healthcheckTimeout", "restartPolicyType", "sleepApplication"},
            "volumeMounts": {VOLUME},
            "variables": set(EXPECTED_VARIABLES) | {"QIKVRT_GITHUB_WEBHOOK_SECRET"},
        }
        require(set(service_patch) <= set(allowed) and all(isinstance(value, dict) and set(value) <= allowed[key]
                for key, value in service_patch.items()), "HOLD_RAILWAY_UNREVIEWED_STAGED_FIELD")
        require(service_patch.get("volumeMounts", {}) == EXPECTED_SETTINGS["volumeMounts"], "HOLD_RAILWAY_VOLUME_MOUNT_CHANGED")
        require(patch["volumes"][VOLUME] == {"region": "iad", "sizeMB": 500, "isCreated": "CREATED"}, "HOLD_RAILWAY_VOLUME_PATCH_CHANGED")
        require(all(isinstance(v, dict) and set(v) == {"value"} for v in service_patch.get("variables", {}).values()), "HOLD_RAILWAY_STAGED_VARIABLE_SHAPE")
        effective = merge(live, patch)
    else:
        effective = live
    service = effective["services"][SERVICE]
    for key, expected in EXPECTED_SETTINGS.items():
        require(at(service, key) == expected, "HOLD_RAILWAY_CONFIGURATION_DRIFT")
    variables = service.get("variables", {})
    require(all(variables.get(k, {}).get("value") == v for k, v in EXPECTED_VARIABLES.items()), "HOLD_RAILWAY_RUNTIME_BINDING_DRIFT")
    require(bool(variables.get("QIKVRT_GITHUB_WEBHOOK_SECRET", {}).get("value")), "HOLD_RAILWAY_WEBHOOK_SECRET_UNAVAILABLE")
    volume_ready = any(edge["node"].get("volumeId") == VOLUME and edge["node"].get("serviceId") == SERVICE and
                       edge["node"].get("mountPath") == "/var/lib/qikvrt/monitor" and edge["node"].get("state") == "READY"
                       for edge in environment["volumeInstances"]["edges"])
    require(pending is not None or volume_ready, "HOLD_RAILWAY_PERSISTENT_VOLUME_NOT_PROVISIONED")
    return effective, pending, instance.get("latestDeployment") or {}, volume_ready


def source_contract(root: Path = ROOT) -> dict:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    require(contract["source_head"] == SOURCE_HEAD and contract["source_tree"] == SOURCE_TREE and
            contract["project_id"] == PROJECT and contract["environment_id"] == ENVIRONMENT and
            contract["service_id"] == SERVICE and contract["volume_id"] == VOLUME and
            contract["public_url"] == PUBLIC, "HOLD_DEPLOYMENT_CONTRACT_SUBSTITUTION")
    require(set(contract["artifact_files_sha256"]) == {"server.mjs", "observer.mjs", "index.html", "client-replica.js", "health-projection.js", "package.json"},
            "HOLD_SOURCE_ARTIFACT_SET_INCOMPLETE")
    result = run_bounded(["git", "rev-parse", SOURCE_HEAD + "^{tree}"], cwd=root, timeout=30)
    require(result.returncode == 0 and result.stdout.strip() == SOURCE_TREE, "HOLD_SOURCE_TREE_UNVERIFIED")
    for name, expected in contract["artifact_files_sha256"].items():
        require(name in {"server.mjs", "observer.mjs", "index.html", "client-replica.js", "health-projection.js", "package.json"}, "HOLD_SOURCE_PATH_SUBSTITUTION")
        result = run_bounded(["git", "show", SOURCE_HEAD + ":docs/monitor/" + name], cwd=root, timeout=30)
        require(result.returncode == 0 and hashlib.sha256(result.stdout.encode()).hexdigest() == expected,
                "HOLD_EXACT_SOURCE_ARTIFACT_MISMATCH")
    return contract


def verify_public(contract: dict, root: Path = ROOT) -> dict:
    # A separate process applies fresh HTTP responses through client-replica.js.
    clean = {k: v for k, v in os.environ.items() if k in {"PATH", "TMPDIR", "SystemRoot"}}
    result = run_bounded(["node", str(root / "tools/qikvrt_mesh_monitor_readback.mjs")], cwd=root, env=clean, timeout=90)
    require(result.returncode == 0 and not result.timed_out and not result.output_limit_exceeded,
            "HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK")
    try:
        receipt = json.loads(result.stdout)
    except ValueError:
        raise Hold("HOLD_INDEPENDENT_CLIENT_RECEIPT_INVALID") from None
    require(receipt.get("state") == "CLIENT_BYTE_READBACK_VERIFIED" and receipt.get("source_head") == SOURCE_HEAD and
            receipt.get("source_tree") == SOURCE_TREE and receipt.get("artifact_files_sha256") == contract["artifact_files_sha256"] and
            receipt.get("effect_ack_done") is False, "HOLD_INDEPENDENT_CLIENT_BINDING_MISMATCH")
    return receipt


def execute(api: Api, contract: dict, *, apply: bool, executor_head: str, ref: str, readback=verify_public) -> dict:
    effective, pending, latest, volume_ready = validate_observation(api.observe())
    current_source = (latest.get("meta") or {}).get("commitHash")
    if not pending and volume_ready and current_source == SOURCE_HEAD and latest.get("status") == "SUCCESS":
        return {"state": "PUBLIC_RUNTIME_READBACK_VERIFIED", "deployment_id": latest["id"], "mutation_count": 0,
                "readback": readback(contract), "effect_ack_done": False}
    require(not (latest.get("status") in ACTIVE), "HOLD_RAILWAY_DEPLOYMENT_IN_PROGRESS")
    require(apply, "HOLD_PUBLIC_EXACT_DEPLOYMENT_NOT_OBSERVED")
    require(bool(re.fullmatch(r"[a-f0-9]{40}", executor_head)), "HOLD_EXECUTOR_EXACT_HEAD_UNAVAILABLE")
    require(ref in {"main", EXPECTED_SETTINGS["source.branch"]}, "HOLD_EXECUTOR_REF_NOT_AUTHORIZED")
    branch = api.github("GET", "ref/heads/" + ref)
    require(branch["object"]["sha"] == executor_head, "HOLD_EXECUTOR_HEAD_CHANGED")
    existing = api.github("GET", "ref/" + LOCK, missing=True)
    if existing:
        require(existing["object"]["sha"] == SOURCE_HEAD, "HOLD_DEPLOYMENT_LOCK_BINDING_MISMATCH")
        raise Hold("HOLD_DEPLOYMENT_ATTEMPT_ALREADY_CLAIMED_REOBSERVE_ONLY")
    lock = api.github("POST", "refs", {"ref": "refs/" + LOCK, "sha": SOURCE_HEAD})
    require(lock["object"]["sha"] == SOURCE_HEAD and lock["ref"] == "refs/" + LOCK, "HOLD_DEPLOYMENT_LOCK_UNVERIFIED")
    second = api.observe()
    fresh, fresh_pending, fresh_latest, _ = validate_observation(second)
    require(digest([effective, pending, latest]) == digest([fresh, fresh_pending, fresh_latest]), "HOLD_RAILWAY_STATE_CHANGED_BEFORE_DISPATCH")
    # There is intentionally one mutation and no automatic retry, even if its
    # response is lost. The durable create-only Git ref survives runner loss.
    if fresh_pending:
        answer = api.gql(COMMIT, {"environmentId": ENVIRONMENT, "commitMessage": "QIKVRT exact monitor " + SOURCE_HEAD})
        require(bool(answer.get("environmentPatchCommitStaged")), "HOLD_RAILWAY_COMMIT_UNVERIFIED")
    else:
        answer = api.gql(DEPLOY, {"environmentId": ENVIRONMENT, "serviceId": SERVICE, "commitSha": SOURCE_HEAD})
        require(bool(answer.get("serviceInstanceDeployV2")), "HOLD_RAILWAY_DISPATCH_UNVERIFIED")
    return {"state": "HOLD_DEPLOYMENT_DISPATCHED_READBACK_PENDING", "mutation_count": 1,
            "lock_ref": "refs/" + LOCK, "effect_ack_done": False}


def main(argv: list[str] | None = None) -> int:
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".qikvrt/evidence/monitor-deploy/receipt.json")
    args = parser.parse_args(argv)
    result = {"schema": "qikvrt-monitor-deployment-receipt/v1", "source_repository": REPOSITORY,
              "source_head": SOURCE_HEAD, "source_tree": SOURCE_TREE, "service_id": SERVICE,
              "executor_head": os.environ.get("QIKVRT_EXECUTOR_HEAD") if re.fullmatch(r"[a-f0-9]{40}", os.environ.get("QIKVRT_EXECUTOR_HEAD", "")) else "UNAVAILABLE",
              "executor_ref": os.environ.get("QIKVRT_EXECUTOR_REF") if os.environ.get("QIKVRT_EXECUTOR_REF") in {"main", EXPECTED_SETTINGS["source.branch"]} else "UNAVAILABLE",
              "public_url": PUBLIC, "effect_ack_done": False, "PREDECESSOR_EVIDENCE_TRANSFER": False}
    code = 20
    try:
        api = Api(dict(os.environ))  # Missing credential stops before any network.
        contract = source_contract()
        result.update(execute(api, contract, apply=args.apply, executor_head=os.environ.get("QIKVRT_EXECUTOR_HEAD", ""),
                              ref=os.environ.get("QIKVRT_EXECUTOR_REF", "")))
        if result["state"] == "PUBLIC_RUNTIME_READBACK_VERIFIED":
            code = 0
    except Hold as error:
        result.update(state=str(error), mutation_count="NOT_ASSERTED")
        if str(error) == "HOLD_RAILWAY_SERVER_CREDENTIAL_UNAVAILABLE":
            result["mutation_count"] = 0
    except (KeyError, TypeError, ValueError, OSError, AttributeError):
        result.update(state="HOLD_API_OR_CONTRACT_SHAPE_UNSUPPORTED", mutation_count="NOT_ASSERTED")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
