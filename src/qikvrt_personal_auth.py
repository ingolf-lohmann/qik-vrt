# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Opt-in Personal authentication; no file/database fallback for secrets.

The existing terminal owns the listener and lifetime writer lock. OIDC identity
is separate from model API entitlement. Test injection never attests live SSO.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

LIMIT = 128 * 1024
ROOT = Path(__file__).resolve().parents[1]


class AuthBlock(ValueError):
    """Only fixed, non-secret reason strings may cross the HTTP boundary."""


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def unb64(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value) or len(value) > LIMIT:
        raise AuthBlock("OIDC_BASE64_INVALID")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def object_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AuthBlock("AUTH_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(AuthBlock("AUTH_JSON_NONFINITE")))
        if not isinstance(value, dict):
            raise AuthBlock("AUTH_JSON_OBJECT_REQUIRED")
        return value
    except (ValueError, TypeError, UnicodeError):
        raise AuthBlock("AUTH_JSON_INVALID") from None


class OSSecretStore:
    """Linux Secret Service, via libsecret's fixed system executable and stdin.

    Requires the user's protected login collection; no auto-unlock, plaintext
    fallback, environment export, or secret-bearing command argument. Secret
    Service/desktop protection is a native acceptance obligation, not inferred
    from the existence of this adapter. Run as the desktop user, never root.
    """
    evidence_class = "OS_SECRET_SERVICE_ADAPTER"

    def __init__(self, state_dir, provider):
        if sys.platform != "linux":
            raise AuthBlock("NATIVE_SECRET_STORE_NOT_IMPLEMENTED_FOR_PLATFORM")
        self.command = Path("/usr/bin/secret-tool")
        try:
            info = self.command.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise AuthBlock("OS_SECRET_TOOL_NOT_TRUSTED_SYSTEM_BINARY")
        except OSError:
            raise AuthBlock("OS_SECRET_SERVICE_UNAVAILABLE_NO_FALLBACK") from None
        if os.geteuid() == 0:
            raise AuthBlock("PERSONAL_SECRET_STORE_REQUIRES_DESKTOP_USER")
        root = Path(state_dir).expanduser().absolute()
        if root == ROOT or ROOT in root.parents or any(p.is_symlink() or (p / ".git/config").is_file() or (p / ".git").is_file() for p in [root, *root.parents]):
            raise AuthBlock("AUTH_PROFILE_MUST_BE_PRIVATE_OUTSIDE_REPOSITORY")
        self.profile = hashlib.sha256(encoded([str(root.resolve()), provider])).hexdigest()
        self.attributes = ["application", "org.qikvrt.personal", "profile", self.profile]

    def _run(self, action, payload=None):
        environment = {k: v for k, v in os.environ.items() if k in {
            "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR", "DISPLAY", "WAYLAND_DISPLAY", "LANG", "HOME"}}
        environment["PATH"] = "/usr/bin:/bin"
        args = [str(self.command), action]
        if action == "store":
            args += ["--label=QIK-VRT Personal protected runtime"]
        try:
            result = subprocess.run(args + self.attributes, input=payload,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=environment, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            raise AuthBlock("OS_SECRET_SERVICE_RESULT_UNRESOLVED_NO_RETRY") from None
        if len(result.stdout) > LIMIT:
            raise AuthBlock("OS_SECRET_SERVICE_RESPONSE_TOO_LARGE")
        if result.returncode:
            if action == "lookup" and result.returncode == 1 and not result.stdout and not result.stderr:
                return None
            raise AuthBlock("OS_SECRET_SERVICE_LOCKED_OR_UNAVAILABLE")
        return result.stdout

    def read(self):
        raw = self._run("lookup")
        if raw is None:
            return {"schema": "qikvrt_protected_personal_v1", "profile": self.profile}
        value = object_json(raw)
        if value.get("schema") != "qikvrt_protected_personal_v1" or value.get("profile") != self.profile:
            raise AuthBlock("PROTECTED_PROFILE_BINDING_INVALID")
        return value

    def write(self, value):
        if value.get("profile") != self.profile:
            raise AuthBlock("PROTECTED_PROFILE_BINDING_INVALID")
        raw = encoded(value)
        if len(raw) > LIMIT:
            raise AuthBlock("PROTECTED_PROFILE_TOO_LARGE")
        self._run("store", raw)
        if not hmac.compare_digest(encoded(self.read()), raw):
            raise AuthBlock("PROTECTED_STORE_READBACK_MISMATCH")

    @contextlib.contextmanager
    def provision_lock(self, state_dir):
        # Reuse the existing PersonalRuntime lifetime lock. A separate CLI
        # credential update must not overwrite an in-flight rotated token.
        import fcntl
        root = Path(state_dir).expanduser().absolute()
        if any(p.is_symlink() for p in [root, *root.parents]):
            raise AuthBlock("PRIVATE_STATE_DIRECTORY_UNSAFE")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not root.is_dir() or root.stat().st_mode & 0o077:
            raise AuthBlock("PRIVATE_STATE_DIRECTORY_REQUIRES_MODE_0700")
        descriptor = os.open(root / "writer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise AuthBlock("OS_CREDENTIAL_PROFILE_IN_USE") from None
            yield
        finally:
            os.close(descriptor)


def load_config(path, origin):
    requested = Path(path).expanduser().absolute()
    if requested == ROOT or ROOT in requested.parents or requested.is_symlink() or any(p.is_symlink() or (p / ".git/config").is_file() or (p / ".git").is_file() for p in requested.parents):
        raise AuthBlock("OIDC_CONFIG_MUST_BE_PRIVATE_OUTSIDE_REPOSITORY")
    try:
        info = requested.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT or info.st_mode & 0o077:
            raise AuthBlock("OIDC_CONFIG_REQUIRES_PRIVATE_REGULAR_FILE")
        return validate_config(object_json(requested.read_bytes()), origin)
    except OSError:
        raise AuthBlock("OIDC_REGISTERED_CLIENT_CONFIG_UNAVAILABLE") from None


def validate_config(config, origin):
    required = {"issuer", "client_id", "subject", "authorization_endpoint", "token_endpoint", "jwks_uri",
                "redirect_uri", "refresh_protection"}
    if set(config) - required - {"revocation_endpoint", "end_session_endpoint"} or not required <= set(config):
        raise AuthBlock("OIDC_CONFIG_FIELDS_INVALID")
    if config["refresh_protection"] != "rotation":
        raise AuthBlock("OIDC_PUBLIC_CLIENT_REFRESH_ROTATION_REQUIRED")
    for field in required - {"refresh_protection"}:
        if not isinstance(config[field], str) or not config[field] or len(config[field]) > 2048 or "<" in config[field]:
            raise AuthBlock("OIDC_EXPLICIT_REGISTERED_OWNER_BINDING_REQUIRED")
    for field in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "revocation_endpoint", "end_session_endpoint"):
        if field not in config:
            continue
        if not isinstance(config[field], str):
            raise AuthBlock("OIDC_PINNED_HTTPS_ENDPOINT_REQUIRED")
        uri = urlsplit(config[field])
        if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password or uri.fragment or uri.query):
            raise AuthBlock("OIDC_PINNED_HTTPS_ENDPOINT_REQUIRED")
    if config["redirect_uri"] != origin + "/personal/auth/callback" or not re.fullmatch(r"http://127\.0\.0\.1:[0-9]+", origin):
        raise AuthBlock("OIDC_EXACT_LOOPBACK_REDIRECT_REQUIRED")
    try:
        if not 1 <= urlsplit(origin).port <= 65535:
            raise AuthBlock("OIDC_EXACT_LOOPBACK_REDIRECT_REQUIRED")
    except ValueError:
        raise AuthBlock("OIDC_EXACT_LOOPBACK_REDIRECT_REQUIRED") from None
    if len(config["subject"]) > 255 or not config["subject"].isascii():
        raise AuthBlock("OIDC_OWNER_SUBJECT_INVALID")
    return dict(config)


class NoAuthRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise AuthBlock("OIDC_REDIRECT_REFUSED")


class OIDCTransport:
    evidence_class = "LIVE_HTTPS_OIDC_TRANSPORT"

    def __init__(self):
        self.opener = build_opener(NoAuthRedirect())

    def request(self, url, fields=None):
        request = Request(url, data=urlencode(fields).encode() if fields is not None else None,
                          headers={"Accept": "application/json", **({"Content-Type": "application/x-www-form-urlencoded"} if fields is not None else {})})
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read(LIMIT + 1)
                if len(raw) > LIMIT:
                    raise AuthBlock("OIDC_RESPONSE_TOO_LARGE")
                if not raw and fields is not None:
                    return {}  # RFC7009 successful empty response.
                return object_json(raw)
        except HTTPError as exc:
            if exc.code in {400, 401, 403}:
                raise AuthBlock("OIDC_AUTHENTICATION_REJECTED") from None
            raise AuthBlock("OIDC_RESULT_UNRESOLVED_NO_RETRY") from None
        except (URLError, OSError, TimeoutError):
            raise AuthBlock("OIDC_RESULT_UNRESOLVED_NO_RETRY") from None


def require_crypto_runtime():
    try:
        import cryptography
        if cryptography.__version__ != "50.0.2":
            raise AuthBlock("OIDC_CRYPTOGRAPHY_RUNTIME_BINDING_UNAVAILABLE")
    except ImportError:
        raise AuthBlock("OIDC_CRYPTOGRAPHY_RUNTIME_BINDING_UNAVAILABLE") from None


def verify_id_token(token, config, jwks, nonce, access_token, now, *, nonce_optional=False):
    """Pinned RS256 only; cryptographic primitives supplied by cryptography."""
    require_crypto_runtime()
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        raise AuthBlock("OIDC_CRYPTOGRAPHY_RUNTIME_BINDING_UNAVAILABLE") from None
    try:
        if not isinstance(token, str) or len(token) > LIMIT:
            raise AuthBlock("OIDC_ID_TOKEN_INVALID")
        head, body, signature = token.split(".")
        header, claims = object_json(unb64(head)), object_json(unb64(body))
        if (header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or
            set(header) - {"alg", "kid", "typ"} or header.get("typ", "JWT") != "JWT"):
            raise AuthBlock("OIDC_JOSE_HEADER_REJECTED")
        keys = [key for key in jwks["keys"] if key.get("kid") == header["kid"] and key.get("kty") == "RSA"
                and key.get("use", "sig") == "sig" and key.get("alg", "RS256") == "RS256"
                and key.get("key_ops", ["verify"]) == ["verify"]]
        if len(keys) != 1:
            raise AuthBlock("OIDC_SIGNING_KEY_NOT_UNIQUE")
        key = keys[0]
        n, e = int.from_bytes(unb64(key["n"]), "big"), int.from_bytes(unb64(key["e"]), "big")
        if not 2048 <= n.bit_length() <= 8192 or e < 3 or e % 2 == 0:
            raise AuthBlock("OIDC_RSA_KEY_REJECTED")
        rsa.RSAPublicNumbers(e, n).public_key().verify(unb64(signature), (head + "." + body).encode(), padding.PKCS1v15(), hashes.SHA256())
        if claims.get("iss") != config["issuer"] or claims.get("sub") != config["subject"]:
            raise AuthBlock("OIDC_ISSUER_OR_OWNER_MISMATCH")
        audience = claims.get("aud")
        if audience != config["client_id"] and audience != [config["client_id"]]:
            raise AuthBlock("OIDC_AUDIENCE_MISMATCH")
        if claims.get("azp", config["client_id"]) != config["client_id"]:
            raise AuthBlock("OIDC_AUTHORIZED_PARTY_MISMATCH")
        for key in ("exp", "iat"):
            if type(claims.get(key)) not in {int, float} or not math.isfinite(claims[key]):
                raise AuthBlock("OIDC_TIME_CLAIM_INVALID")
        if claims["exp"] <= now or claims["iat"] > now + 30 or claims["iat"] < now - 300:
            raise AuthBlock("OIDC_TOKEN_EXPIRED_OR_STALE")
        if "nbf" in claims and (type(claims["nbf"]) not in {int, float} or not math.isfinite(claims["nbf"]) or claims["nbf"] > now + 30):
            raise AuthBlock("OIDC_TOKEN_NOT_YET_VALID")
        if nonce is not None and (not nonce_optional or "nonce" in claims) and claims.get("nonce") != nonce:
            raise AuthBlock("OIDC_NONCE_MISMATCH")
        if "at_hash" in claims and claims["at_hash"] != b64(hashlib.sha256(access_token.encode()).digest()[:16]):
            raise AuthBlock("OIDC_ACCESS_TOKEN_HASH_MISMATCH")
        return claims
    except (KeyError, TypeError, ValueError, InvalidSignature):
        raise AuthBlock("OIDC_ID_TOKEN_REJECTED") from None


class PersonalAuth:
    def __init__(self, store, config, *, transport=None, clock=time.time):
        config = validate_config(config, config["redirect_uri"].split("/personal/")[0])
        self.store, self.config, self.clock = store, config, clock
        self.transport = transport if transport is not None else OIDCTransport()
        self.lock, self.pending, self.observed = threading.RLock(), None, False
        self.binding = hashlib.sha256(encoded(config)).hexdigest()
        bundle = store.read()
        auth = bundle.get("auth", {})
        if auth and auth.get("binding") != self.binding:
            raise AuthBlock("PROTECTED_IDENTITY_BINDING_CHANGED_REVOKE_OLD_PROFILE_FIRST")

    def _save(self, auth):
        bundle = self.store.read()
        bundle["auth"] = auth
        self.store.write(bundle)

    def _state(self):
        state = self.store.read().get("auth", {})
        if state and state.get("binding") != self.binding:
            raise AuthBlock("PROTECTED_IDENTITY_BINDING_MISMATCH")
        return state

    def begin(self):
        with self.lock:
            require_crypto_runtime()  # Before issuing any authorization request.
            if self.pending and self.clock() < self.pending["until"]:
                raise AuthBlock("OIDC_AUTHORIZATION_ALREADY_PENDING")
            if self._state().get("state") in {"AUTHORIZATION_PENDING", "REFRESH_PENDING", "REVOCATION_PENDING"}:
                raise AuthBlock("OIDC_PRIOR_EFFECT_UNRESOLVED_NO_RETRY")
            metadata = self.transport.request(self.config["issuer"].rstrip("/") + "/.well-known/openid-configuration")
            for key in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "revocation_endpoint", "end_session_endpoint"):
                if key in self.config and metadata.get(key) != self.config[key]:
                    raise AuthBlock("OIDC_DISCOVERY_PIN_MISMATCH")
            if ("S256" not in metadata.get("code_challenge_methods_supported", []) or
                "form_post" not in metadata.get("response_modes_supported", []) or
                "RS256" not in metadata.get("id_token_signing_alg_values_supported", []) or
                "none" not in metadata.get("token_endpoint_auth_methods_supported", [])):
                raise AuthBlock("OIDC_REGISTERED_PUBLIC_CLIENT_PROTOCOL_UNSUPPORTED")
            verifier, state, nonce = secrets.token_urlsafe(48), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self.pending = {"verifier": verifier, "state": state, "nonce": nonce, "until": self.clock() + 300}
            fields = {"client_id": self.config["client_id"], "redirect_uri": self.config["redirect_uri"],
                      "response_type": "code", "response_mode": "form_post", "scope": "openid offline_access",
                      "code_challenge_method": "S256", "code_challenge": b64(hashlib.sha256(verifier.encode()).digest()),
                      "state": state, "nonce": nonce}
            return {"authorization_url": self.config["authorization_endpoint"] + "?" + urlencode(fields), "state": state}

    def _tokens(self, result, nonce, previous=None):
        if not isinstance(result.get("token_type"), str) or result["token_type"].lower() != "bearer":
            raise AuthBlock("OIDC_TOKEN_TYPE_REJECTED")
        for key in ("access_token", "refresh_token"):
            if not isinstance(result.get(key), str) or not result[key] or len(result[key]) > 16384 or any(c.isspace() for c in result[key]):
                raise AuthBlock("OIDC_ROTATABLE_TOKEN_PAIR_REQUIRED")
        expires = result.get("expires_in")
        if type(expires) not in {int, float} or not math.isfinite(expires) or not 30 <= expires <= 86400:
            raise AuthBlock("OIDC_TOKEN_LIFETIME_INVALID")
        if not isinstance(result.get("scope", "openid offline_access"), str) or set(result.get("scope", "openid offline_access").split()) - {"openid", "offline_access"}:
            raise AuthBlock("OIDC_SCOPE_ESCALATION_REJECTED")
        if not previous or "id_token" in result:
            verify_id_token(result.get("id_token"), self.config, self.transport.request(self.config["jwks_uri"]),
                            nonce, result["access_token"], self.clock(), nonce_optional=bool(previous))
        if previous and result["refresh_token"] == previous["refresh_token"]:
            raise AuthBlock("OIDC_REFRESH_ROTATION_NOT_OBSERVED")
        return {"binding": self.binding, "state": "AUTHENTICATED", "access_token": result["access_token"],
                "refresh_token": result["refresh_token"], "expires_at": self.clock() + expires,
                "nonce": nonce, "local_token": previous["local_token"] if previous else secrets.token_urlsafe(48),
                "local_until": previous["local_until"] if previous else self.clock() + 43200,
                "evidence_class": self.transport.evidence_class}

    def complete(self, fields):
        with self.lock:
            pending = self.pending
            if (not pending or self.clock() >= pending["until"] or
                not hmac.compare_digest(str(fields.get("state", "")), pending["state"])):
                raise AuthBlock("OIDC_STATE_EXPIRED_OR_MISMATCH")
            self.pending = None  # Consume before token exchange; never redeem a code twice.
            if (set(fields) - {"code", "state", "iss", "error", "error_description", "error_uri"} or
                "error" in fields or fields.get("iss", self.config["issuer"]) != self.config["issuer"] or
                not isinstance(fields.get("code"), str) or not 1 <= len(fields["code"]) <= 4096):
                raise AuthBlock("OIDC_AUTHORIZATION_REJECTED")
            previous = self._state()
            if previous.get("state") in {"AUTHORIZATION_PENDING", "REFRESH_PENDING", "REVOCATION_PENDING"}:
                raise AuthBlock("OIDC_PRIOR_EFFECT_UNRESOLVED_NO_RETRY")
            self._save({"binding": self.binding, "state": "AUTHORIZATION_PENDING", "previous_auth": previous})
            try:
                result = self.transport.request(self.config["token_endpoint"], {
                    "grant_type": "authorization_code", "client_id": self.config["client_id"],
                    "redirect_uri": self.config["redirect_uri"], "code": fields["code"], "code_verifier": pending["verifier"]})
            except AuthBlock as exc:
                if str(exc) == "OIDC_AUTHENTICATION_REJECTED":
                    self._save(previous or {"binding": self.binding, "state": "REAUTH_REQUIRED"})
                raise
            try:
                auth = self._tokens(result, pending["nonce"])
            except AuthBlock:
                self._save(previous or {"binding": self.binding, "state": "REAUTH_REQUIRED"})
                raise
            if previous.get("state") == "AUTHENTICATED":
                retired = self._retire(previous, replacement=auth)
                if retired["remote_revocation"] == "UNRESOLVED_NO_RETRY":
                    raise AuthBlock("OIDC_PREVIOUS_GRANT_REVOCATION_UNRESOLVED")
            else:
                self._save(auth)
            self.observed = True
            return auth["local_token"]

    def authenticate(self, token, *, renew=False, logging_out=False):
        with self.lock:
            auth = self._state()
            if (auth.get("state") != "AUTHENTICATED" or (not logging_out and self.clock() >= auth.get("local_until", 0)) or
                not isinstance(token, str) or not hmac.compare_digest(token, auth.get("local_token", ""))):
                raise AuthBlock("PERSONAL_REAUTHENTICATION_REQUIRED")
            if logging_out:
                return True
            if renew or not self.observed or self.clock() >= auth["expires_at"] - 30:
                pending = dict(auth, state="REFRESH_PENDING")
                self._save(pending)  # Crash/timeout after rotation cannot retry an old token.
                self.observed = False
                try:
                    result = self.transport.request(self.config["token_endpoint"], {
                        "grant_type": "refresh_token", "client_id": self.config["client_id"], "refresh_token": auth["refresh_token"]})
                    auth = self._tokens(result, auth["nonce"], auth)
                    self._save(auth)
                    self.observed = True
                except AuthBlock as exc:
                    if str(exc) == "OIDC_AUTHENTICATION_REJECTED":
                        self._save({"binding": self.binding, "state": "REAUTH_REQUIRED"})
                    raise
            return True

    def _retire(self, auth, replacement=None):
        auth = dict(auth)
        auth.update(binding=self.binding, state="REVOCATION_PENDING", local_token="")
        if replacement:
            auth["replacement"] = replacement
        self._save(auth)
        remote = "UNSUPPORTED"
        if "revocation_endpoint" in self.config:
            for kind in ("refresh_token", "access_token"):
                if not auth.get(kind):
                    continue
                try:
                    self.transport.request(self.config["revocation_endpoint"], {
                        "client_id": self.config["client_id"], "token": auth[kind], "token_type_hint": kind})
                except AuthBlock:
                    return {"local_logout": True, "remote_revocation": "UNRESOLVED_NO_RETRY"}
                auth.pop(kind)
                self._save(auth)
            remote = "ENDPOINT_ACKNOWLEDGED_NOT_INDEPENDENTLY_ATTESTED"
        self._save(replacement or {"binding": self.binding, "state": "SIGNED_OUT"})
        return {"local_logout": True, "remote_revocation": remote}

    def logout(self):
        with self.lock:
            auth = self._state()
            self.observed, self.pending = False, None
            state = auth.get("state")
            if state in {"AUTHORIZATION_PENDING", "REFRESH_PENDING", "REVOCATION_PENDING"}:
                raise AuthBlock("OIDC_PRIOR_EFFECT_UNRESOLVED_NO_RETRY")
            result = self._retire(auth)
            if "end_session_endpoint" in self.config:
                result["provider_logout_url"] = self.config["end_session_endpoint"] + "?" + urlencode({"client_id": self.config["client_id"]})
            return result

    def sensitive_values(self):
        auth = self._state()
        values = []
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"access_token", "refresh_token", "local_token", "nonce"} and isinstance(item, str):
                        values.append(item)
                    elif isinstance(item, dict):
                        visit(item)
        visit(auth)
        if self.pending:
            values += list(self.pending.values())
        return [value for value in values if isinstance(value, str) and value]

    def status(self):
        with self.lock:
            auth = self._state()
            return {"state": auth.get("state", "SIGNED_OUT"), "credential_store": self.store.evidence_class,
                    "credential_reference": self.store.profile, "issuer": self.config["issuer"],
                    "live_authentication_observed_this_process": bool(self.observed and type(self.store) is OSSecretStore and type(self.transport) is OIDCTransport),
                    "evidence_class": self.transport.evidence_class, "biometric_verification": "DELEGATED_TO_IDP_NOT_ATTESTED",
                    "chatgpt_session_transfer": False}
