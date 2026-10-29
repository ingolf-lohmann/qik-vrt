# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Existing #446 credential resolver, extracted without priority changes.

Source: 3e8530f2beb158cdfebd3fa74d25498e7ac2aa4a,
tools/qikvrt_authority_url_probe.py. An unverified workspace GITHUB_TOKEN
does not establish Authority scope; Authority consumers exclude that fallback
from the input mapping. Repository roles follow the current canonical policy.
"""
CREDENTIALS = (
    "QIKVRT_RULESET_ADMIN_TOKEN", "QIKVRT_GITHUB_ADMIN_TOKEN",
    "QIKVRT_MESH_TOKEN", "QIKVRT_AUTHORITY_APP_TOKEN", "GITHUB_TOKEN",
)

def credential(environment):
    present = {name: bool(environment.get(name)) for name in CREDENTIALS}
    for name in CREDENTIALS:
        if present[name]:
            return environment[name], name, present
    return "", None, present


# The existing resolver and protected SSO store own this additional fixed
# operation. It is not an export of the ChatGPT connector's credential.
PRODUCTION_REPOSITORY = "ingolf-lohmann/qik-vrt"
PRODUCTION_ENVIRONMENT = "qikvrt-production"
PRODUCTION_VARIABLES = ("QIKVRT_LINUX_HOST_BINDING_JSON", "QIKVRT_LINUX_HOST_BINDING_SHA256")
PRODUCTION_SECRETS = ("QIKVRT_LINUX_HOST_CA", "QIKVRT_LINUX_HOST_CERT", "QIKVRT_LINUX_HOST_KEY")
PRODUCTION_SCHEMA = "qikvrt-production-environment-rest/v1"
PRODUCTION_MATERIAL_SOURCE = ("QIKVRT_PRODUCTION_MATERIAL_SOURCE", "QIKVRT_PRODUCTION_MATERIAL_SOURCE_SHA256")


class ProductionBlock(ValueError):
    """Fixed reason codes only; never forward a provider body or credential."""


def _encoded(value):
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _pin(value):
    import hashlib
    return hashlib.sha256(_encoded(value)).hexdigest()


def _production_private_bytes(value, maximum):
    """Reuse the native private-file reader, with repository and change guards."""
    from pathlib import Path
    from tools.qikvrt_self_host import private_path, publication_private_bytes
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_UNAVAILABLE")
    path = Path(value)
    try:
        if any((parent / ".git").exists() for parent in path.parents):
            raise ValueError()
        private_path(path.parent, directory=True)
        private_path(path)
        before = path.lstat()
        if before.st_nlink != 1:
            raise ValueError()
        raw = publication_private_bytes(path, maximum)
        after = path.lstat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink,
                              s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or not raw:
            raise ValueError()
        return raw
    except (OSError, ValueError, TypeError):
        # Native paths, exception bodies and input bytes never reach a receipt.
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_UNAVAILABLE") from None


def production_file_material(environment):
    """Read explicitly pinned original files; no discovery, export or fallback.

    The original native operator supplies the private descriptor and its
    independent hash. Neither SSO nor a request can invent that source binding.
    Existing host-preparation files are read in place and never rewritten.
    """
    import hashlib
    import re
    from src.qikvrt_personal_auth import object_json
    source, source_pin = (environment.get(name, "") for name in PRODUCTION_MATERIAL_SOURCE)
    if (not isinstance(source, str) or not source or not isinstance(source_pin, str)
            or not re.fullmatch(r"[a-f0-9]{64}", source_pin)):
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_REQUIRED")
    if any(environment.get(name) for name in PRODUCTION_VARIABLES + PRODUCTION_SECRETS):
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_AMBIGUOUS")
    raw = _production_private_bytes(source, 16 * 1024)
    if hashlib.sha256(raw).hexdigest() != source_pin:
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_PIN_MISMATCH")
    try:
        descriptor = object_json(raw)
        names = (PRODUCTION_VARIABLES[0], *PRODUCTION_SECRETS)
        if (set(descriptor) != {"schema", "repository", "environment", "binding_sha256", "files"}
                or descriptor["schema"] != "qikvrt-production-material-files/v1"
                or descriptor["repository"] != PRODUCTION_REPOSITORY
                or descriptor["environment"] != PRODUCTION_ENVIRONMENT
                or not isinstance(descriptor["binding_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", descriptor["binding_sha256"])
                or not isinstance(descriptor["files"], dict) or set(descriptor["files"]) != set(names)):
            raise ValueError()
        values = {name: _production_private_bytes(descriptor["files"][name], 48 * 1024).decode("utf-8")
                  for name in names}
        values[PRODUCTION_VARIABLES[1]] = descriptor["binding_sha256"]
        return values
    except ProductionBlock:
        raise
    except (ValueError, TypeError, KeyError):
        raise ProductionBlock("ORIGINAL_PROTECTED_MATERIAL_SOURCE_INVALID") from None


def production_material(environment):
    """Validate the original process bindings or explicitly pinned native files.

    A selected file source never mixes with or falls back to process values.
    Browser/connector credentials, generated replacements and public payloads
    remain excluded. Missing source admission is not global material absence.
    """
    import hashlib
    from tools.qikvrt_self_host_container import binding, IMAGE
    values = (production_file_material(environment) if any(name in environment for name in PRODUCTION_MATERIAL_SOURCE)
              else {name: environment.get(name, "") for name in PRODUCTION_VARIABLES + PRODUCTION_SECRETS})
    if any(not isinstance(v, str) or not v or len(v.encode()) > 48 * 1024 for v in values.values()):
        raise ProductionBlock("ORIGINAL_FIVE_PROTECTED_BINDINGS_REQUIRED")
    raw = values[PRODUCTION_VARIABLES[0]].encode()
    if hashlib.sha256(raw).hexdigest() != values[PRODUCTION_VARIABLES[1]]:
        raise ProductionBlock("INDEPENDENT_HOST_BINDING_PIN_MISMATCH")
    try:
        from src.qikvrt_personal_auth import object_json
        value = object_json(raw)
        binding(raw, values[PRODUCTION_VARIABLES[1]], IMAGE + "@" + value["image_digest"])
        # Reject malformed or mismatched native material before any GitHub write.
        from src.qikvrt_personal_auth import require_crypto_runtime
        require_crypto_runtime()
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        x509.load_pem_x509_certificate(values[PRODUCTION_SECRETS[0]].encode())
        cert = x509.load_pem_x509_certificate(values[PRODUCTION_SECRETS[1]].encode())
        key = serialization.load_pem_private_key(values[PRODUCTION_SECRETS[2]].encode(), password=None)
        public = lambda k: k.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if public(cert.public_key()) != public(key.public_key()):
            raise ValueError()
    except (ValueError, KeyError, TypeError, ImportError, AttributeError):
        raise ProductionBlock("ORIGINAL_HOST_OR_MTLS_MATERIAL_INVALID") from None
    return values


def seal_environment_secret(public_key, plaintext):
    """GitHub's documented LibSodium sealed-box format; optional locked runtime."""
    import base64
    try:
        import nacl
        from nacl.public import PublicKey, SealedBox
        if nacl.__version__ != "1.6.2":
            raise ValueError()
        key = base64.b64decode(public_key, validate=True)
        if len(key) != 32:
            raise ValueError()
        return base64.b64encode(SealedBox(PublicKey(key)).encrypt(plaintext.encode())).decode("ascii")
    except (ImportError, ValueError, TypeError):
        raise ProductionBlock("LOCKED_GITHUB_SEALED_BOX_RUNTIME_OR_KEY_UNAVAILABLE") from None


def production_source(expected_head, expected_tree):
    """Reuse the original runtime source observer; source availability is not SSO."""
    from src.qikvrt_personal_assistant import subject
    observed = subject()
    return (observed.get("head") == expected_head and observed.get("tree") == expected_tree
            and observed.get("worktree_dirty") is False)


class ProductionEnvironmentAPI:
    """Bounded official REST, no redirect/retry; cooldown survives process exit."""
    def __init__(self, token, store, *, clock=None):
        import time
        import urllib.request
        from scripts.qikvrt_api_client import NoRedirectHandler
        self.token, self.store, self.clock = token, store, clock or time.time
        self.opener = urllib.request.build_opener(NoRedirectHandler())

    def _rate(self, headers, status):
        import math
        now = self.clock()
        until = 0
        try:
            if headers.get("Retry-After") is not None:
                until = now + max(60, float(headers.get("Retry-After")))
            if headers.get("X-RateLimit-Remaining") == "0":
                until = max(until, float(headers.get("X-RateLimit-Reset", now + 60)))
        except (ValueError, TypeError):
            until = now + 60
        if status == 429 or (status == 403 and not headers.get("X-GitHub-SSO")):
            until = max(until, now + 60)
        if not math.isfinite(until):
            until = now + 3600
        if until > now:
            state = self.store.read()
            state["github_environment_not_before"] = max(until, state.get("github_environment_not_before", 0))
            self.store.write(state)

    def call(self, method, path, body=None, *, missing=False):
        import json
        import re
        import urllib.error
        import urllib.request
        prefix = "/repos/" + PRODUCTION_REPOSITORY
        env = prefix + "/environments/" + PRODUCTION_ENVIRONMENT
        allowed = ((method == "GET" and path in ("/user", prefix, prefix + "/git/ref/heads/main", env, env + "/secrets/public-key"))
            or (method == "GET" and path.startswith(prefix + "/git/commits/")
                and re.fullmatch(r"[a-f0-9]{40}", path.removeprefix(prefix + "/git/commits/")))
            or (method == "GET" and path in tuple(env + "/variables/" + n for n in PRODUCTION_VARIABLES)
                + tuple(env + "/secrets/" + n for n in PRODUCTION_SECRETS))
            or (method == "POST" and path == env + "/variables")
            or (method == "PATCH" and path in tuple(env + "/variables/" + n for n in PRODUCTION_VARIABLES))
            or (method == "PUT" and path in tuple(env + "/secrets/" + n for n in PRODUCTION_SECRETS)))
        if not allowed:
            raise ProductionBlock("FIXED_PRODUCTION_REST_OPERATION_REQUIRED")
        if self.clock() < self.store.read().get("github_environment_not_before", 0):
            raise ProductionBlock("GITHUB_RATE_LIMIT_COOLDOWN_NO_REQUEST")
        from tools.ai_handoff import validate_client_tool_selection
        validate_client_tool_selection({"service": "github", "tool": "ProductionEnvironmentAPI.call",
            "method": method, "endpoint": "https://api.github.com" + path,
            "subject": {"repository": PRODUCTION_REPOSITORY, "environment": PRODUCTION_ENVIRONMENT}})
        request = urllib.request.Request("https://api.github.com" + path, method=method,
            data=None if body is None else _encoded(body), headers={"Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with self.opener.open(request, timeout=15) as response:
                self._rate(response.headers, response.status)
                if response.geturl() != request.full_url:
                    raise ProductionBlock("GITHUB_REDIRECT_REFUSED")
                raw = response.read(128 * 1024 + 1)
                if len(raw) > 128 * 1024:
                    raise ProductionBlock("GITHUB_RESPONSE_TOO_LARGE")
                expected = {"GET": {200}, "POST": {201}, "PATCH": {204}, "PUT": {201, 204}}[method]
                if response.status not in expected:
                    raise ProductionBlock("GITHUB_UNEXPECTED_RESPONSE_NO_RETRY")
                if not raw:
                    return {}
                from src.qikvrt_personal_auth import object_json
                return object_json(raw)
        except urllib.error.HTTPError as exc:
            self._rate(exc.headers, exc.code)
            status, sso = exc.code, bool(exc.headers.get("X-GitHub-SSO"))
            exc.close()  # Never read or persist error bodies.
            if missing and status == 404:
                return None
            raise ProductionBlock("GITHUB_SSO_AUTHORIZATION_REQUIRED" if sso else "GITHUB_HTTP_" + str(status) + "_NO_RETRY") from None
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError):
            raise ProductionBlock("GITHUB_RESULT_UNKNOWN_READBACK_ONLY") from None


def production_environment(auth, bearer, request, environment, *, write=False, api_factory=ProductionEnvironmentAPI):
    """Restore only the existing five bindings under the existing SSO session.

    One protected journal, before each mutation. Lost replies never authorize
    another upload. Secret metadata cannot establish delivered secret values.
    """
    import hmac
    import re
    with auth.lock:
        auth.authenticate(bearer)
        if not auth.status().get("live_authentication_observed_this_process"):
            raise ProductionBlock("LIVE_ORIGINAL_SSO_SESSION_REQUIRED")
        common = {"schema", "request_id", "expected_main_sha", "binding_sha256"}
        shapes = [common | {"effect_accepted"}] if write else [common, {"schema", "request_id"}]
        if (not isinstance(request, dict) or set(request) not in shapes
                or request.get("schema") != PRODUCTION_SCHEMA
                or not isinstance(request.get("request_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9_.=-]{1,128}", request["request_id"])
                or ("expected_main_sha" in request and (not isinstance(request["expected_main_sha"], str)
                    or not re.fullmatch(r"[a-f0-9]{40}", request["expected_main_sha"])))
                or ("binding_sha256" in request and (not isinstance(request["binding_sha256"], str)
                    or not re.fullmatch(r"[a-f0-9]{64}", request["binding_sha256"])))
                or (write and request.get("effect_accepted") is not True)):
            raise ProductionBlock("EXACT_PRODUCTION_ENVIRONMENT_REQUEST_REQUIRED")
        if (environment.get("QIKVRT_ALLOWED_REPOSITORY") != PRODUCTION_REPOSITORY
                or environment.get("QIKVRT_API_PRINCIPAL") != "ingolf-lohmann"):
            raise ProductionBlock("ORIGINAL_AUTHORITY_AND_PRINCIPAL_REQUIRED")
        token, reference, _ = credential({k: environment.get(k, "") for k in CREDENTIALS if k != "GITHUB_TOKEN"})
        if (not token or len(token) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token)
                or hmac.compare_digest(token, environment.get("QIKVRT_API_TOKEN", "")) or hmac.compare_digest(token, bearer)):
            raise ProductionBlock("ORIGINAL_PROTECTED_AUTHORITY_CREDENTIAL_REQUIRED")
        # Writes still require the original validated material before any HTTP.
        # A readback must remain usable when that material was never delivered
        # or was lost after an uncertain upload.
        values = production_material(environment) if write else None
        if write and values[PRODUCTION_VARIABLES[1]] != request["binding_sha256"]:
            raise ProductionBlock("REQUEST_HOST_BINDING_PIN_MISMATCH")
        api = api_factory(token, auth.store)
        prefix = "/repos/" + PRODUCTION_REPOSITORY
        target = prefix + "/environments/" + PRODUCTION_ENVIRONMENT
        account, repository = api.call("GET", "/user"), api.call("GET", prefix)
        if (account.get("login") != "ingolf-lohmann" or account.get("id") != 294949349
                or repository.get("id") != 1273784147 or repository.get("full_name") != PRODUCTION_REPOSITORY
                or repository.get("permissions", {}).get("admin") is not True):
            raise ProductionBlock("AUTHENTICATED_GITHUB_OWNER_ADMIN_REQUIRED")
        if not write and set(request) == {"schema", "request_id"}:
            request = dict(request, expected_main_sha=api.call("GET", prefix + "/git/ref/heads/main").get("object", {}).get("sha"))
            if not isinstance(request["expected_main_sha"], str) or not re.fullmatch(r"[a-f0-9]{40}", request["expected_main_sha"]):
                raise ProductionBlock("CURRENT_MAIN_SOURCE_UNVERIFIED")

        def source():
            result = api.call("GET", prefix + "/git/ref/heads/main")
            if result.get("ref") != "refs/heads/main" or result.get("object", {}).get("sha") != request["expected_main_sha"]:
                raise ProductionBlock("CURRENT_MAIN_SOURCE_CHANGED")

        source()
        commit = api.call("GET", prefix + "/git/commits/" + request["expected_main_sha"])
        source_tree = commit.get("tree", {}).get("sha")
        if commit.get("sha") != request["expected_main_sha"] or not isinstance(source_tree, str) or not re.fullmatch(r"[a-f0-9]{40}", source_tree):
            raise ProductionBlock("CURRENT_MAIN_TREE_UNVERIFIED")
        implementation_verified = production_source(request["expected_main_sha"], source_tree)
        if write and not implementation_verified:
            raise ProductionBlock("CLEAN_ORIGINAL_MAIN_RUNTIME_SOURCE_REQUIRED")
        original = api.call("GET", target)
        if original.get("name") != PRODUCTION_ENVIRONMENT or type(original.get("id")) is not int or original["id"] <= 0:
            raise ProductionBlock("EXISTING_EXACT_PRODUCTION_ENVIRONMENT_REQUIRED")
        protections = {k: original.get(k) for k in ("id", "name", "protection_rules", "deployment_branch_policy", "can_admins_bypass")}

        def observe():
            found = {n: api.call("GET", target + "/variables/" + n, missing=True) for n in PRODUCTION_VARIABLES}
            found.update({n: api.call("GET", target + "/secrets/" + n, missing=True) for n in PRODUCTION_SECRETS})
            if any(v is not None and v.get("name") != n for n, v in found.items()):
                raise ProductionBlock("GITHUB_BINDING_METADATA_NAME_MISMATCH")
            return found

        found = observe()
        material_reason = None
        if not write:
            try:
                values = production_material(environment)
                if "binding_sha256" in request and values[PRODUCTION_VARIABLES[1]] != request["binding_sha256"]:
                    raise ProductionBlock("REQUEST_HOST_BINDING_PIN_MISMATCH")
            except ProductionBlock as exc:
                values, material_reason = None, str(exc)
            except Exception:
                # The optional local checker may itself be unavailable. Keep
                # the already observed remote metadata; never expose its error.
                values, material_reason = None, "ORIGINAL_PROTECTED_MATERIAL_VALIDATION_UNAVAILABLE"
        journal = auth.store.read().get("github_environment_handoff", {})
        if journal and journal.get("auth_binding") != auth.binding:
            raise ProductionBlock("ORIGINAL_SSO_JOURNAL_BINDING_MISMATCH")
        # Input identity remains in protected storage; neither secret bytes nor
        # their digests are included in a public/client receipt.
        receipt = {"schema": PRODUCTION_SCHEMA, "request_id": request["request_id"], "repository": PRODUCTION_REPOSITORY,
            "environment": PRODUCTION_ENVIRONMENT, "expected_main_sha": request["expected_main_sha"],
            "source_tree": source_tree,
            "implementation_source_verified": implementation_verified,
            "binding_sha256": values[PRODUCTION_VARIABLES[1]] if values is not None else None, "credential_reference": reference,
            "protected_material_available": values is not None, "protected_material_reason": material_reason,
            "bindings": {n: {"present": found[n] is not None, **({"value_matches": (found[n] is not None and found[n].get("value") == values[n]) if values is not None else None} if n in PRODUCTION_VARIABLES else {})} for n in found},
            "mutation_count": 0, "state": "READBACK_ONLY", "secret_values_verified": False,
            "job_credential_delivery_verified": False, "host_identity_verified": False,
            "next_required_operation": "GET /v1.45/info" if values is not None else "CONNECT_ORIGINAL_PROTECTED_MATERIAL_SOURCE", "effect_ack_done": False, "ordinary_release": False}
        if not write:
            receipt["prior_attempt_state"] = journal.get("state", "NOT_ATTEMPTED")
            return receipt
        revision = _pin(values)
        if journal and (journal.get("state") != "COMPLETE" or journal.get("revision") == revision):
            receipt.update(state="NOOP", prior_attempt_state=journal.get("state"), reason="ORIGINAL_ATTEMPT_READBACK_ONLY_NO_RETRY")
            return receipt
        public_key = api.call("GET", target + "/secrets/public-key")
        if not isinstance(public_key.get("key_id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", public_key["key_id"]):
            raise ProductionBlock("GITHUB_ENVIRONMENT_KEY_ID_INVALID")
        sealed = {n: seal_environment_secret(public_key.get("key"), values[n]) for n in PRODUCTION_SECRETS}
        record = {"auth_binding": auth.binding, "revision": revision, "state": "IN_FLIGHT", "request_id": request["request_id"], "steps": []}

        def save():
            state = auth.store.read()
            state["github_environment_handoff"] = record
            auth.store.write(state)

        # Preserve the preceding original attempt, even for a deliberate change
        # of bindings. Bounded history is in the same private OS store.
        if journal:
            state = auth.store.read()
            history = state.setdefault("github_environment_handoff_history", [])
            if len(history) >= 16:
                raise ProductionBlock("PROTECTED_HANDOFF_HISTORY_FULL_NO_WITNESS_DISCARDED")
            history.append(journal)
            auth.store.write(state)
        save()
        try:
            for name in PRODUCTION_VARIABLES + PRODUCTION_SECRETS:
                source()
                if not production_source(request["expected_main_sha"], source_tree):
                    raise ProductionBlock("RUNNING_AUTHORITY_SOURCE_CHANGED")
                current = api.call("GET", target)
                if {k: current.get(k) for k in protections} != protections:
                    raise ProductionBlock("PRODUCTION_ENVIRONMENT_PROTECTION_DRIFT")
                if name in PRODUCTION_VARIABLES and found[name] is not None and found[name].get("value") == values[name]:
                    continue
                record["steps"].append({"name": name, "state": "UNKNOWN_READBACK_REQUIRED"})
                save()  # Durable original intent before this exact mutation.
                receipt["mutation_count"] += 1
                if name in PRODUCTION_VARIABLES:
                    method = "POST" if found[name] is None else "PATCH"
                    path = target + "/variables" + ("" if method == "POST" else "/" + name)
                    api.call(method, path, {"name": name, "value": values[name]})
                else:
                    api.call("PUT", target + "/secrets/" + name, {"key_id": public_key["key_id"], "encrypted_value": sealed[name]})
                record["steps"][-1]["state"] = "HTTP_ACKNOWLEDGED"
                save()
            fresh = observe()
            source()
            current = api.call("GET", target)
            if ({k: current.get(k) for k in protections} != protections
                    or any(fresh[n] is None or fresh[n].get("value") != values[n] for n in PRODUCTION_VARIABLES)
                    or any(fresh[n] is None for n in PRODUCTION_SECRETS)):
                raise ProductionBlock("PROTECTED_BINDINGS_METADATA_READBACK_MISMATCH")
            record["state"] = "COMPLETE"
            save()
            receipt.update(state="UPLOAD_ACKNOWLEDGED_METADATA_READBACK_VERIFIED",
                bindings={n: {"present": True, **({"value_matches": True} if n in PRODUCTION_VARIABLES else {})} for n in fresh})
            return receipt
        except Exception:
            # Acknowledgement and secret metadata cannot disambiguate whether
            # the expected secret bytes arrived. Never repeat an uncertain PUT.
            record["state"] = "UNKNOWN_READBACK_REQUIRED"
            save()
            raise ProductionBlock("PRODUCTION_HANDOFF_UNRESOLVED_READBACK_ONLY") from None
